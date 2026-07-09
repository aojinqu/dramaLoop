import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import build_running_manifest, run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent
from dramaloop.storage.artifacts import append_event
from dramaloop.storage.runs import plan_run_id
from dramaloop.utils.json_io import dump_json
from dramaloop.web.schemas import WebRunCreateRequest, WebRunDetail, WebStageSnapshot
from dramaloop.web.store import DEFAULT_STAGE_NAMES, WebRunStore


async def launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str:
    started_at = datetime.now()
    planned_run_id = plan_run_id(settings.runs_dir, request.idea, started_at)
    detail = store.create(planned_run_id, request)
    run_id = detail.run_id
    payload = _build_story_request(request)

    async def _run() -> None:
        try:
            client = build_llm_client(settings)
            await asyncio.to_thread(run_story_pipeline, payload, settings, client, started_at, run_id)
        except Exception as exc:  # pragma: no cover - exercised via integration behavior
            _ensure_failed_run_record(run_id, payload, settings, started_at, exc)
            detail = store.get(run_id)
            if detail is not None:
                detail.status = "failed"
                store.replace(detail)

    asyncio.create_task(_run())
    return run_id


async def stream_run_events(run_id: str, settings: Settings, store: WebRunStore) -> AsyncIterator[str]:
    events_path = settings.runs_dir / run_id / "events.jsonl"
    manifest_path = settings.runs_dir / run_id / "run_manifest.json"
    sent = 0
    terminal_stable_polls = 0

    while True:
        events = _read_json_lines(events_path)
        for payload in events[sent:]:
            sent += 1
            yield f"event: stage_{payload['event']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
            if payload.get("artifact"):
                artifact_payload = {"run_id": run_id, "artifact": payload["artifact"], "ts": payload.get("ts")}
                yield f"event: artifact_ready\ndata: {json.dumps(artifact_payload, ensure_ascii=False)}\n\n"

        manifest = _read_json_file(manifest_path)
        if manifest and manifest.get("status") in {"completed", "failed"}:
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
    detail.final_story = None
    detail.overall_score = None
    detail.rewrite_focus = None

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

        critique_paths = sorted(run_dir.glob("critique_v*.json"))
        if critique_paths:
            latest_critique = _read_json_file(critique_paths[-1])
            if isinstance(latest_critique, dict):
                detail.overall_score = latest_critique.get("overall_score")
                detail.rewrite_focus = latest_critique.get("rewrite_target")

        for artifact_path in run_dir.iterdir():
            if artifact_path.is_file() and artifact_path.name not in {"request.json", "run_manifest.json", "events.jsonl"}:
                artifacts.add(artifact_path.name)

    detail.available_artifacts = sorted(artifacts)

    manifest = _read_json_file(manifest_path)
    if manifest:
        detail.status = manifest["status"]
        if detail.status in {"completed", "failed"}:
            detail.current_stage = None

    return store.replace(detail)



def _build_story_request(request: WebRunCreateRequest) -> StoryRequest:
    return StoryRequest(
        idea=request.idea,
        style=request.style,
        audience=request.audience,
        constraints=request.constraints,
        max_iterations=request.max_iterations,
        length="short",
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
        stages=[WebStageSnapshot(name=name, status="pending") for name in DEFAULT_STAGE_NAMES],
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
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return [], False

    payloads: list[dict[str, Any]] = []
    has_partial_tail = False
    for raw in lines:
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            has_partial_tail = True
            break
        if isinstance(payload, dict):
            payloads.append(payload)
    return payloads, has_partial_tail
