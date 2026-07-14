import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.harness.control import CONTROLLERS
from dramaloop.harness.episodic_orchestrator import (
    continue_episodic_run,
    regenerate_episode,
    run_episodic_pipeline,
)
from dramaloop.harness.orchestrator import build_running_manifest, run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent
from dramaloop.schemas.season import EpisodePlanArtifact
from dramaloop.storage.artifacts import append_event, write_json_artifact
from dramaloop.storage.runs import plan_run_id
from dramaloop.utils.json_io import dump_json, load_json
from dramaloop.web.schemas import (
    WebControlResponse,
    WebEpisodePlanUpdateRequest,
    WebEpisodeSnapshot,
    WebRunCreateRequest,
    WebRunDetail,
    WebStageSnapshot,
)
from dramaloop.web.store import WebRunStore, stage_names_for_request


def _append_human_action(
    run_dir: Path,
    *,
    action: str,
    episode_number: int | None = None,
    payload_summary: str | None = None,
) -> None:
    record = {
        "ts": datetime.now().isoformat(),
        "action": action,
        "episode_number": episode_number,
        "payload_summary": payload_summary,
    }
    path = run_dir / "human_actions.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


async def launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str:
    started_at = datetime.now()
    planned_run_id = plan_run_id(settings.runs_dir, request.idea, started_at)
    detail = store.create(planned_run_id, request)
    detail.pause_after_plan = request.pause_after_plan
    store.replace(detail)
    run_id = detail.run_id
    payload = _build_story_request(request)
    controller = (
        CONTROLLERS.create(run_id, pause_after_plan=request.pause_after_plan)
        if payload.format == "episodic_series"
        else None
    )

    async def _run() -> None:
        try:
            client = build_llm_client(settings)
            if payload.format == "episodic_series":
                await asyncio.to_thread(
                    run_episodic_pipeline,
                    payload,
                    settings,
                    client,
                    started_at,
                    run_id,
                    controller,
                )
            else:
                await asyncio.to_thread(run_story_pipeline, payload, settings, client, started_at, run_id)
        except Exception as exc:  # pragma: no cover - exercised via integration behavior
            _ensure_failed_run_record(run_id, payload, settings, started_at, exc)
            current = store.get(run_id)
            if current is not None:
                current.status = "failed"
                store.replace(current)
        finally:
            CONTROLLERS.discard(run_id)

    asyncio.create_task(_run())
    return run_id


def pause_run(run_id: str, settings: Settings, store: WebRunStore) -> WebControlResponse:
    detail = hydrate_run_detail(run_id, settings, store)
    if detail is None:
        raise KeyError(run_id)
    if detail.status not in {"running", "paused"}:
        raise ValueError(f"cannot pause run in status={detail.status}")
    controller = CONTROLLERS.get(run_id)
    if controller is None:
        raise ValueError("no active controller for this run")
    controller.pause(phase="between_episodes")
    _append_human_action(settings.runs_dir / run_id, action="pause", payload_summary="between_episodes")
    return WebControlResponse(run_id=run_id, status="paused", control_phase=controller.phase)


async def resume_run(run_id: str, settings: Settings, store: WebRunStore) -> WebControlResponse:
    detail = hydrate_run_detail(run_id, settings, store)
    if detail is None:
        raise KeyError(run_id)
    controller = CONTROLLERS.get(run_id)
    if controller is not None:
        controller.resume()
        _append_human_action(settings.runs_dir / run_id, action="resume", payload_summary="live_controller")
        return WebControlResponse(run_id=run_id, status="running", control_phase="idle")

    # No live pipeline (e.g. after regenerate invalidated later episodes): spawn continue worker.
    if detail.status not in {"paused", "cancelled"}:
        raise ValueError(f"cannot resume run in status={detail.status}")
    if detail.request.format != "episodic_series":
        raise ValueError("resume is only supported for episodic runs")
    if detail.completed_episode_count >= detail.request.episode_count:
        raise ValueError("all episodes already completed")

    new_controller = CONTROLLERS.create(run_id, pause_after_plan=False)

    async def _continue() -> None:
        try:
            client = build_llm_client(settings)
            await asyncio.to_thread(
                continue_episodic_run,
                run_id=run_id,
                settings=settings,
                client=client,
                controller=new_controller,
            )
        finally:
            CONTROLLERS.discard(run_id)

    asyncio.create_task(_continue())
    _append_human_action(
        settings.runs_dir / run_id,
        action="resume",
        payload_summary=f"continue_from_{detail.completed_episode_count + 1}",
    )
    return WebControlResponse(run_id=run_id, status="running", control_phase="idle")


def cancel_run(run_id: str, settings: Settings, store: WebRunStore) -> WebControlResponse:
    detail = hydrate_run_detail(run_id, settings, store)
    if detail is None:
        raise KeyError(run_id)
    controller = CONTROLLERS.get(run_id)
    if controller is not None:
        controller.cancel()
        _append_human_action(settings.runs_dir / run_id, action="cancel", payload_summary="live_controller")
        return WebControlResponse(run_id=run_id, status="cancelled", control_phase="idle")
    if detail.status in {"completed", "failed", "cancelled"}:
        return WebControlResponse(run_id=run_id, status=detail.status, control_phase=detail.control_phase)
    # Soft-cancel persisted state when no live worker.
    run_dir = settings.runs_dir / run_id
    manifest_path = run_dir / "run_manifest.json"
    manifest = _read_json_file(manifest_path)
    if manifest is not None:
        manifest["status"] = "cancelled"
        manifest["finished_at"] = datetime.now().isoformat()
        dump_json(manifest_path, manifest)
    _append_human_action(run_dir, action="cancel", payload_summary="soft_cancel")
    return WebControlResponse(run_id=run_id, status="cancelled", control_phase="idle")


def update_episode_plan(
    run_id: str,
    payload: WebEpisodePlanUpdateRequest,
    settings: Settings,
    store: WebRunStore,
) -> WebRunDetail:
    detail = hydrate_run_detail(run_id, settings, store)
    if detail is None:
        raise KeyError(run_id)
    if detail.status not in {"paused", "cancelled", "completed"}:
        raise ValueError("episode plan can only be edited while paused, cancelled, or completed")
    if detail.request.format != "episodic_series":
        raise ValueError("episode plan updates require episodic_series format")
    if len(payload.episodes) != detail.request.episode_count:
        raise ValueError(f"expected {detail.request.episode_count} episodes in plan")

    plan = EpisodePlanArtifact(episodes=payload.episodes)
    write_json_artifact(settings.runs_dir / run_id / "episode_plan.json", plan)
    append_event(
        settings.runs_dir / run_id / "events.jsonl",
        RunEvent(
            ts=datetime.now().isoformat(),
            stage="episode_plan_generation",
            event="completed",
            artifact="episode_plan.json",
            detail="manual_edit",
        ),
    )
    _append_human_action(
        settings.runs_dir / run_id,
        action="plan_edit",
        payload_summary=f"episodes={len(payload.episodes)}",
    )
    hydrated = hydrate_run_detail(run_id, settings, store)
    assert hydrated is not None
    return hydrated


async def launch_episode_regeneration(
    run_id: str,
    episode_number: int,
    settings: Settings,
    store: WebRunStore,
) -> WebControlResponse:
    detail = hydrate_run_detail(run_id, settings, store)
    if detail is None:
        raise KeyError(run_id)
    if detail.status not in {"paused", "cancelled", "completed"}:
        raise ValueError("regenerate requires paused, cancelled, or completed status")
    if CONTROLLERS.get(run_id) is not None:
        raise ValueError("cannot regenerate while the live pipeline is still attached; cancel or wait, then regenerate")
    if episode_number < 1 or episode_number > detail.request.episode_count:
        raise ValueError("episode_number out of range")

    async def _regen() -> None:
        try:
            client = build_llm_client(settings)
            await asyncio.to_thread(
                regenerate_episode,
                run_id=run_id,
                episode_number=episode_number,
                settings=settings,
                client=client,
            )
        except Exception:
            current = store.get(run_id)
            if current is not None:
                current.status = "failed"
                store.replace(current)
            raise

    asyncio.create_task(_regen())
    _append_human_action(
        settings.runs_dir / run_id,
        action="regenerate",
        episode_number=episode_number,
        payload_summary=f"episode={episode_number}",
    )
    return WebControlResponse(run_id=run_id, status="running", control_phase="idle")


async def stream_run_events(run_id: str, settings: Settings, store: WebRunStore) -> AsyncIterator[str]:
    events_path = settings.runs_dir / run_id / "events.jsonl"
    manifest_path = settings.runs_dir / run_id / "run_manifest.json"
    sent = 0
    terminal_stable_polls = 0

    while True:
        events = _read_json_lines(events_path)
        manifest = _read_json_file(manifest_path)
        run_format = manifest.get("format", "single_story") if manifest else "single_story"

        for payload in events[sent:]:
            sent += 1
            for event_name, event_payload in _translate_event(payload, run_id, run_format):
                yield f"event: {event_name}\ndata: {json.dumps(event_payload, ensure_ascii=False)}\n\n"

        if manifest and manifest.get("status") in {"completed", "failed", "cancelled"}:
            final_events, has_partial_tail = _read_json_lines_state(events_path)
            if len(final_events) > sent or has_partial_tail:
                terminal_stable_polls = 0
                await asyncio.sleep(0.25)
                continue
            terminal_stable_polls += 1
            if terminal_stable_polls < 2:
                await asyncio.sleep(0.25)
                continue
            hydrated = hydrate_run_detail(run_id, settings, store)
            status = hydrated.status if hydrated is not None else manifest["status"]
            yield f"event: run_{status}\ndata: {json.dumps({'run_id': run_id, 'status': status}, ensure_ascii=False)}\n\n"
            break

        terminal_stable_polls = 0
        await asyncio.sleep(0.25)



def hydrate_run_detail(run_id: str, settings: Settings, store: WebRunStore) -> WebRunDetail | None:
    detail = _load_or_create_run_detail(run_id, settings, store)
    if detail is None:
        return None

    run_dir = settings.runs_dir / run_id
    events_path = run_dir / "events.jsonl"
    manifest_path = run_dir / "run_manifest.json"

    stage_by_name = {stage.name: stage for stage in detail.stages}
    for stage in detail.stages:
        stage.status = "pending"

    detail.current_stage = None
    detail.current_episode_number = None
    detail.completed_episode_count = 0
    detail.episodes = []
    detail.final_story = None
    detail.overall_score = None
    detail.rewrite_focus = None
    detail.season_summary = None
    detail.season_bible = None
    detail.episode_plan = None
    detail.control_phase = None

    artifacts: set[str] = set()
    running_stages: set[str] = set()

    for payload in _read_json_lines(events_path):
        stage_name = payload.get("stage")
        event_name = payload.get("event")
        artifact_name = payload.get("artifact")
        if artifact_name:
            artifacts.add(artifact_name)
        if stage_name not in stage_by_name:
            continue
        stage = stage_by_name[stage_name]
        if event_name == "started":
            stage.status = "running"
            running_stages.add(stage_name)
        elif event_name == "completed":
            stage.status = "completed"
            running_stages.discard(stage_name)
        elif event_name == "failed":
            stage.status = "failed"
            running_stages.discard(stage_name)

    detail.current_stage = next((stage.name for stage in detail.stages if stage.name in running_stages), None)

    if run_dir.exists():
        final_story_path = run_dir / "final_story.md"
        if final_story_path.exists():
            detail.final_story = final_story_path.read_text(encoding="utf-8")
            artifacts.add("final_story.md")

        if detail.request.format == "episodic_series":
            season_bible = _read_json_file(run_dir / "season_bible.json")
            if season_bible is not None:
                detail.season_bible = season_bible
                detail.season_summary = season_bible.get("series_logline") or season_bible.get("core_conflict")
                artifacts.add("season_bible.json")
            episode_plan = _read_json_file(run_dir / "episode_plan.json")
            if episode_plan is not None:
                detail.episode_plan = episode_plan
                artifacts.add("episode_plan.json")
            if (run_dir / "continuity_state.json").exists():
                artifacts.add("continuity_state.json")

            episodes_dir = run_dir / "episodes"
            if episodes_dir.exists():
                episode_scores: list[float] = []
                for json_path in sorted(episodes_dir.glob("episode_*.json")):
                    # Skip critique artifacts like episode_01_critique.json
                    if "_critique" in json_path.stem:
                        continue
                    payload = _read_json_file(json_path) or {}
                    number = payload.get("episode_number", 0)
                    md_path = episodes_dir / f"episode_{number:02d}.md"
                    content = md_path.read_text(encoding="utf-8") if md_path.exists() else None
                    critique_path = episodes_dir / f"episode_{number:02d}_critique.json"
                    critique = _read_json_file(critique_path) if critique_path.exists() else None
                    score = None
                    if isinstance(critique, dict) and critique.get("overall_score") is not None:
                        score = float(critique["overall_score"])
                        artifacts.add(f"episodes/{critique_path.name}")
                    elif payload.get("overall_score") is not None:
                        score = float(payload["overall_score"])
                    if score is not None:
                        episode_scores.append(score)
                    detail.episodes.append(
                        WebEpisodeSnapshot(
                            episode_number=number,
                            title=payload.get("title", ""),
                            status="completed",
                            word_count=payload.get("word_count"),
                            hook_line=payload.get("hook_delivered"),
                            content=content,
                            overall_score=score,
                        )
                    )
                    artifacts.add(f"episodes/{json_path.name}")
                    if md_path.exists():
                        artifacts.add(f"episodes/{md_path.name}")
                detail.completed_episode_count = len(detail.episodes)
                if episode_scores:
                    detail.overall_score = round(sum(episode_scores) / len(episode_scores), 2)
        else:
            critique_paths = sorted(run_dir.glob("critique_v*.json"))
            if critique_paths:
                latest_critique = _read_json_file(critique_paths[-1])
                if isinstance(latest_critique, dict):
                    detail.overall_score = latest_critique.get("overall_score")
                    detail.rewrite_focus = latest_critique.get("rewrite_target")
            for artifact_path in run_dir.iterdir():
                if artifact_path.is_file() and artifact_path.name not in {"request.json", "run_manifest.json", "events.jsonl"}:
                    artifacts.add(artifact_path.name)

    manifest = _read_json_file(manifest_path)
    if manifest:
        detail.status = manifest["status"]
        detail.current_episode_number = manifest.get("current_episode")
        detail.completed_episode_count = max(detail.completed_episode_count, manifest.get("completed_episodes", 0))
        if detail.status in {"completed", "failed"}:
            detail.current_stage = None

    controller = CONTROLLERS.get(run_id)
    detail.has_live_controller = controller is not None
    if controller is not None:
        detail.control_phase = controller.phase
        if controller.paused and detail.status == "running":
            detail.status = "paused"
    elif detail.status == "paused":
        detail.control_phase = "between_episodes"
    else:
        detail.control_phase = "idle"

    detail.available_artifacts = sorted(artifacts)
    return store.replace(detail)



def _build_story_request(request: WebRunCreateRequest) -> StoryRequest:
    return StoryRequest(
        idea=request.idea,
        style=request.style,
        audience=request.audience,
        constraints=request.constraints,
        max_iterations=request.max_iterations,
        length="short",
        format=request.format,
        episode_count=request.episode_count,
        episode_min_words=request.episode_min_words,
        episode_max_words=request.episode_max_words,
        delivery_mode=request.delivery_mode,
    )



def _load_or_create_run_detail(run_id: str, settings: Settings, store: WebRunStore) -> WebRunDetail | None:
    detail = store.get(run_id)
    if detail is not None:
        return detail

    request_payload = _read_story_request(settings.runs_dir / run_id / "request.json")
    if request_payload is None:
        return None

    reconstructed = WebRunDetail(
        run_id=run_id,
        status="running",
        request=request_payload,
        stages=[WebStageSnapshot(name=name, status="pending") for name in stage_names_for_request(request_payload)],
    )
    return store.replace(reconstructed)



def _read_story_request(path: Path) -> StoryRequest | None:
    payload = _read_json_file(path)
    if payload is None:
        return None
    try:
        return StoryRequest.model_validate(payload)
    except ValidationError:
        return None



def _ensure_failed_run_record(
    run_id: str,
    payload: StoryRequest,
    settings: Settings,
    started_at: datetime,
    exc: Exception,
) -> None:
    run_dir = settings.runs_dir / run_id
    request_path = run_dir / "request.json"
    manifest_path = run_dir / "run_manifest.json"
    events_path = run_dir / "events.jsonl"

    if manifest_path.exists():
        return

    run_dir.mkdir(parents=True, exist_ok=True)
    dump_json(request_path, payload)

    manifest = build_running_manifest(run_id, settings, payload, started_at)
    manifest.format = payload.format
    if payload.format == "episodic_series":
        manifest.total_episodes = payload.episode_count
    manifest.status = "failed"
    manifest.finished_at = datetime.now().isoformat()
    manifest.error_message = str(exc)
    dump_json(manifest_path, manifest)

    append_event(
        events_path,
        RunEvent(
            ts=datetime.now().isoformat(),
            stage="run",
            event="failed",
            detail=str(exc),
        ),
    )



def _translate_event(payload: dict[str, Any], run_id: str, run_format: str) -> list[tuple[str, dict[str, Any]]]:
    stage = payload.get("stage")
    event = payload.get("event")
    artifact = payload.get("artifact")
    translated: list[tuple[str, dict[str, Any]]] = []

    if run_format == "episodic_series":
        event_name: str | None = None
        if stage == "run" and event in {"paused", "resumed", "cancelled"}:
            event_name = f"run_{event}"
        elif stage == "season_planning":
            event_name = f"season_{event}"
        elif stage == "episode_plan_generation" and event == "completed":
            event_name = "episode_plan_ready"
        elif stage == "episode_generation":
            event_name = f"episode_{event}"
        elif stage == "final_assembly":
            event_name = f"final_assembly_{event}"
        if event_name is not None:
            translated.append((event_name, payload))
        if artifact is not None:
            artifact_event = "episode_artifact_ready" if stage == "episode_generation" else "artifact_ready"
            translated.append((artifact_event, {"run_id": run_id, "artifact": artifact, "ts": payload.get("ts")}))
        return translated

    translated.append((f"stage_{event}", payload))
    if artifact is not None:
        translated.append(("artifact_ready", {"run_id": run_id, "artifact": artifact, "ts": payload.get("ts")}))
    return translated



def _read_json_file(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    if not raw.strip():
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None



def _read_json_lines(path: Path) -> list[dict[str, Any]]:
    payloads, _has_partial_tail = _read_json_lines_state(path)
    return payloads



def _read_json_lines_state(path: Path) -> tuple[list[dict[str, Any]], bool]:
    if not path.exists():
        return [], False
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return [], False

    payloads: list[dict[str, Any]] = []
    has_partial_tail = bool(raw) and not raw.endswith("\n")
    for line in raw.splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads, has_partial_tail
