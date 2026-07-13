from datetime import datetime
from difflib import SequenceMatcher
import re

from dramaloop.config import Settings
from dramaloop.harness.episode_runner import build_initial_continuity_state, write_episode_artifacts
from dramaloop.harness.orchestrator import _record_stage_event, build_running_manifest
from dramaloop.harness.stages import run_episode_draft_stage, run_episode_plan_stage, run_season_stage
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunResult
from dramaloop.schemas.season import EpisodeArtifact, EpisodePlanArtifact, EpisodePlanItem, SeasonBible
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files, reserve_run_id


_CONTINUITY_SIMILARITY_THRESHOLD = 0.98


def _normalize_markdown(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _extract_signal_fragments(text: str | None) -> list[str]:
    if not text:
        return []
    fragments: list[str] = []
    seen: set[str] = set()
    for raw_fragment in re.split(r"[，。！？；：、,.!?:;\s\"“”‘’《》()（）]+", text):
        fragment = raw_fragment.strip()
        if len(fragment) < 4:
            continue
        candidates = [fragment]
        if len(fragment) > 8:
            candidates.extend([fragment[:4], fragment[-4:]])
        if len(fragment) > 12:
            candidates.extend([fragment[:8], fragment[-8:]])
        for candidate in candidates:
            if len(candidate) < 4 or candidate in seen:
                continue
            seen.add(candidate)
            fragments.append(candidate)
            if len(fragments) == 10:
                return fragments
    return fragments


def _extract_actual_hook_signal(markdown: str, planned_hook: str) -> str:
    raw_segments = re.split(r"(?<=[。！？!?])", markdown)
    sentences = [segment.strip(" \n\t\r\"'“”‘’") for segment in raw_segments]
    sentences = [segment for segment in sentences if segment]
    if not sentences:
        compact = markdown.strip(" \n\t\r\"'“”‘’")
        return compact[-60:] if len(compact) > 60 else compact

    planned_fragments = _extract_signal_fragments(planned_hook)
    candidates = sentences[-3:]
    best_sentence = candidates[-1]
    best_score = -1
    for sentence in candidates:
        score = _count_carryover_matches(sentence, planned_fragments)
        if score > best_score:
            best_sentence = sentence
            best_score = score

    signal = best_sentence.strip()
    return signal[-80:] if len(signal) > 80 else signal


def _count_carryover_matches(text: str, fragments: list[str]) -> int:
    return sum(1 for fragment in fragments if fragment in text)


def _has_continuation_cue(text: str) -> bool:
    continuation_cues = (
        "当晚",
        "那晚",
        "第二天",
        "次日",
        "此时",
        "与此同时",
        "同一时间",
        "之后",
        "以后",
        "随后",
        "接着",
        "紧接着",
        "立刻",
        "直接",
        "顺着",
        "继续",
        "带离",
        "带上车",
        "追出来",
        "没有再",
        "后，",
        "后。",
    )
    return any(cue in text for cue in continuation_cues)


def _detect_continuity_failures(
    *,
    actual_total_episodes: int,
    episode: EpisodePlanItem,
    markdown: str,
    continuity: ContinuityState,
    previous_summary: str | None,
    previous_markdown: str | None,
) -> list[str]:
    failures: list[str] = []
    if episode.episode_number > 1:
        restart_signals = (
            "故事刚开始",
            "一切要从",
            "重新开始",
            "回到最初",
            "第1集",
            "第一集",
            "初次见到",
            "第一次见到",
        )
        if any(signal in markdown for signal in restart_signals):
            failures.append("看起来像在重新开篇，而不是承接上一集继续推进")

        carryover_fragments = [
            *_extract_signal_fragments(previous_summary),
            *_extract_signal_fragments(continuity.last_episode_hook),
        ]
        opening_window = markdown[:180]
        if carryover_fragments and _count_carryover_matches(opening_window, carryover_fragments) == 0 and not _has_continuation_cue(opening_window):
            failures.append("开篇缺少对上一集收尾或摘要的明显承接")

        if previous_markdown is not None:
            previous_compact = _normalize_markdown(previous_markdown)
            current_compact = _normalize_markdown(markdown)
            if min(len(previous_compact), len(current_compact)) >= 80:
                similarity = SequenceMatcher(None, previous_compact, current_compact).ratio()
                if similarity >= _CONTINUITY_SIMILARITY_THRESHOLD:
                    failures.append("正文与上一集高度重复，接近重写上一集")

    if episode.episode_number < actual_total_episodes:
        premature_ending_signals = (
            "故事到这里结束",
            "一切都结束了",
            "从此以后",
            "从此过上",
            "大结局",
            "全文完",
            "终于迎来了结局",
            "彻底结束了",
        )
        if any(signal in markdown for signal in premature_ending_signals):
            failures.append("非最终集写出了整季完结感")

    return failures


def _build_retry_continuity(continuity: ContinuityState, episode: EpisodePlanItem, failures: list[str]) -> ContinuityState:
    failure_text = "；".join(failures)
    return continuity.model_copy(
        update={
            "story_so_far_summary": (
                f"{continuity.story_so_far_summary}。重写要求：第{episode.episode_number}集必须直接承接上一集实际收尾信号"
                f"“{continuity.last_episode_hook}”，禁止把故事重写成新开篇，禁止重复上一集正文，"
                "非最终集禁止提前写成整季完结。"
                f"上一次失败原因：{failure_text}。这一次开头前两句必须明确写出对上一集收尾的承接，"
                "至少点出上一集收尾中的一个关键人物、动作、物件或结果。"
            )
        }
    )


def _build_episode_summary(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    actual_total_episodes: int,
    hook_signal: str,
) -> str:
    must_happen = "、".join(episode.must_happen[:2])
    opening_clause = (
        f"承接上一集实际收尾“{continuity.last_episode_hook}”" if episode.episode_number > 1 else f"从“{episode.opening_situation}”开局"
    )
    closing_clause = (
        f"并完成“{season.final_payoff}”的终局回收。"
        if episode.episode_number == actual_total_episodes
        else f"并以实际收尾“{hook_signal}”把悬念推向下一集。"
    )
    return (
        f"第{episode.episode_number}集《{episode.title}》{opening_clause}，围绕“{episode.core_conflict}”"
        f"推进{must_happen}，{closing_clause}"
    )


def _validate_episode_plan_range(episodes: list[EpisodePlanItem], requested_episode_count: int) -> None:
    expected_numbers = list(range(1, requested_episode_count + 1))
    actual_numbers = [episode.episode_number for episode in episodes[:requested_episode_count]]
    if actual_numbers != expected_numbers:
        raise RuntimeError(f"Episode plan does not cover requested range 1-{requested_episode_count}")


def _collect_episode_plan_chunk(
    episodes: list[EpisodePlanItem],
    *,
    start_episode: int,
    end_episode: int,
) -> list[EpisodePlanItem]:
    selected = [episode for episode in episodes if start_episode <= episode.episode_number <= end_episode]
    expected_numbers = list(range(start_episode, end_episode + 1))
    actual_numbers = [episode.episode_number for episode in selected]
    if actual_numbers != expected_numbers:
        raise RuntimeError(f"Episode plan does not cover requested range {start_episode}-{end_episode}")
    return selected


def _build_episode_plan_in_chunks(
    client: LLMClient,
    season: SeasonBible,
    requested_episode_count: int,
    *,
    chunk_size: int = 4,
) -> list[EpisodePlanItem]:
    collected: list[EpisodePlanItem] = []
    for start_episode in range(1, requested_episode_count + 1, chunk_size):
        end_episode = min(start_episode + chunk_size - 1, requested_episode_count)
        chunk_artifact = run_episode_plan_stage(
            client,
            season,
            start_episode=start_episode,
            end_episode=end_episode,
            prior_episodes=collected,
        )
        collected.extend(
            _collect_episode_plan_chunk(
                chunk_artifact.episodes,
                start_episode=start_episode,
                end_episode=end_episode,
            )
        )
    return collected


def run_episodic_pipeline(
    request: StoryRequest,
    settings: Settings,
    client: LLMClient,
    started_at: datetime | None = None,
    run_id: str | None = None,
) -> RunResult:
    started_at = started_at or datetime.now()
    if run_id is None:
        run_id = reserve_run_id(settings.runs_dir, build_run_id(request.idea, started_at))
    run_paths = create_run_paths(settings.runs_dir, run_id)
    manifest = build_running_manifest(run_id, settings, request, started_at)
    manifest.format = "episodic_series"
    manifest.total_episodes = request.episode_count
    initialize_run_files(run_paths, request, manifest)

    try:
        _record_stage_event(run_paths.events_path, "run", "started", detail=f"run_id={run_id}")

        season = run_season_stage(client, request)
        write_json_artifact(run_paths.root / "season_bible.json", season)
        _record_stage_event(run_paths.events_path, "season_planning", "completed", artifact="season_bible.json")

        episode_plan = EpisodePlanArtifact(
            episodes=_build_episode_plan_in_chunks(
                client,
                season,
                request.episode_count,
            )
        )
        write_json_artifact(run_paths.root / "episode_plan.json", episode_plan)
        _record_stage_event(run_paths.events_path, "episode_plan_generation", "completed", artifact="episode_plan.json")
        _validate_episode_plan_range(episode_plan.episodes, request.episode_count)

        continuity = build_initial_continuity_state(season)
        write_json_artifact(run_paths.root / "continuity_state.json", continuity)
        episode_markdowns: list[str] = []
        previous_markdown: str | None = None

        for episode in episode_plan.episodes[: request.episode_count]:
            manifest.current_episode = episode.episode_number
            write_json_artifact(run_paths.manifest_path, manifest)

            final_failures: list[str] = []
            markdown = ""
            for attempt in range(3):
                _record_stage_event(
                    run_paths.events_path,
                    "episode_generation",
                    "started",
                    iteration=episode.episode_number,
                    detail=f"episode={episode.episode_number};attempt={attempt + 1}",
                )
                continuity_input = continuity if attempt == 0 else _build_retry_continuity(continuity, episode, final_failures)
                previous_summary = continuity.story_so_far_summary if episode.episode_number > 1 else None
                markdown = run_episode_draft_stage(
                    client,
                    season,
                    episode,
                    continuity_input,
                    previous_summary,
                    request.episode_min_words,
                    request.episode_max_words,
                    request.episode_count,
                )
                final_failures = _detect_continuity_failures(
                    actual_total_episodes=request.episode_count,
                    episode=episode,
                    markdown=markdown,
                    continuity=continuity,
                    previous_summary=previous_summary,
                    previous_markdown=previous_markdown,
                )
                if not final_failures:
                    break

            if final_failures:
                detail = f"episode={episode.episode_number};reasons={' | '.join(final_failures)}"
                _record_stage_event(
                    run_paths.events_path,
                    "episode_generation",
                    "failed",
                    iteration=episode.episode_number,
                    detail=detail,
                )
                raise RuntimeError(f"Episode {episode.episode_number} failed continuity gate: {'; '.join(final_failures)}")

            hook_signal = _extract_actual_hook_signal(markdown, episode.hook_ending)
            artifact = EpisodeArtifact(
                episode_number=episode.episode_number,
                title=episode.title,
                markdown=markdown,
                word_count=max(request.episode_min_words, min(request.episode_max_words, len(markdown))),
                episode_summary=_build_episode_summary(season, episode, continuity, request.episode_count, hook_signal),
                hook_delivered=hook_signal,
                qa_passed=True,
            )
            write_episode_artifacts(run_paths.root, artifact)
            episode_markdowns.append(f"# 第{episode.episode_number}集 {episode.title}\n\n{artifact.markdown}")
            continuity.current_episode = min(episode.episode_number + 1, request.episode_count)
            continuity.story_so_far_summary = artifact.episode_summary
            continuity.last_episode_hook = artifact.hook_delivered
            previous_markdown = artifact.markdown
            write_json_artifact(run_paths.root / "continuity_state.json", continuity)
            manifest.completed_episodes = episode.episode_number
            write_json_artifact(run_paths.manifest_path, manifest)
            _record_stage_event(
                run_paths.events_path,
                "episode_generation",
                "completed",
                iteration=episode.episode_number,
                artifact=f"episodes/episode_{episode.episode_number:02d}.md",
            )

        final_story_path = run_paths.root / "final_story.md"
        _record_stage_event(run_paths.events_path, "final_assembly", "started")
        write_markdown_artifact(final_story_path, "\n\n".join(episode_markdowns))
        summary_path = run_paths.root / "run_summary.md"
        write_markdown_artifact(summary_path, f"已完成 {manifest.completed_episodes} / {manifest.total_episodes} 集")
        _record_stage_event(run_paths.events_path, "final_assembly", "completed", artifact="final_story.md")
        manifest.status = "completed"
        manifest.final_artifact = "final_story.md"
        manifest.finished_at = datetime.now().isoformat()
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "completed", artifact="final_story.md")
        return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=summary_path)
    except Exception as exc:
        manifest.status = "failed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.error_message = str(exc)
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "failed", detail=str(exc))
        raise
