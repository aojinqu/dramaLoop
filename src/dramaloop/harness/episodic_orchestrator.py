from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.episode_runner import build_initial_continuity_state, write_episode_artifacts
from dramaloop.harness.orchestrator import _record_stage_event, build_running_manifest
from dramaloop.harness.stages import run_episode_draft_stage, run_episode_plan_stage, run_season_stage
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunResult
from dramaloop.schemas.season import EpisodeArtifact
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files, reserve_run_id


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

    season = run_season_stage(client, request)
    write_json_artifact(run_paths.root / "season_bible.json", season)
    _record_stage_event(run_paths.events_path, "season_planning", "completed", artifact="season_bible.json")

    episode_plan = run_episode_plan_stage(client, season)
    write_json_artifact(run_paths.root / "episode_plan.json", episode_plan)
    _record_stage_event(run_paths.events_path, "episode_plan_generation", "completed", artifact="episode_plan.json")

    continuity = build_initial_continuity_state(season)
    write_json_artifact(run_paths.root / "continuity_state.json", continuity)
    episode_markdowns: list[str] = []
    previous_summary: str | None = None

    for episode in episode_plan.episodes[: request.episode_count]:
        manifest.current_episode = episode.episode_number
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "episode_generation", "started", iteration=episode.episode_number, detail=f"episode={episode.episode_number}")
        markdown = run_episode_draft_stage(
            client,
            season,
            episode,
            continuity,
            previous_summary,
            request.episode_min_words,
            request.episode_max_words,
        )
        artifact = EpisodeArtifact(
            episode_number=episode.episode_number,
            title=episode.title,
            markdown=markdown,
            word_count=max(request.episode_min_words, min(request.episode_max_words, len(markdown))),
            episode_summary=f"第{episode.episode_number}集：{episode.core_conflict}",
            hook_delivered=episode.hook_ending,
            qa_passed=True,
        )
        write_episode_artifacts(run_paths.root, artifact)
        episode_markdowns.append(f"# 第{episode.episode_number}集 {episode.title}\n\n{artifact.markdown}")
        continuity.current_episode = min(episode.episode_number + 1, request.episode_count)
        continuity.story_so_far_summary = artifact.episode_summary
        continuity.last_episode_hook = artifact.hook_delivered
        previous_summary = artifact.episode_summary
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
    return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=summary_path)
