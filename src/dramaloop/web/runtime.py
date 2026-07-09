import asyncio
import json
from collections.abc import AsyncIterator
from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.storage.runs import plan_run_id
from dramaloop.web.schemas import WebRunCreateRequest
from dramaloop.web.store import WebRunStore


async def launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str:
    started_at = datetime.now()
    planned_run_id = plan_run_id(settings.runs_dir, request.idea, started_at)
    detail = store.create(planned_run_id, request)
    run_id = detail.run_id

    async def _run() -> None:
        client = build_llm_client(settings)
        payload = StoryRequest(
            idea=request.idea,
            style=request.style,
            audience=request.audience,
            constraints=request.constraints,
            max_iterations=request.max_iterations,
            length="short",
        )
        await asyncio.to_thread(run_story_pipeline, payload, settings, client, started_at, run_id)

    asyncio.create_task(_run())
    return run_id


async def stream_run_events(run_id: str, settings: Settings, store: WebRunStore) -> AsyncIterator[str]:
    events_path = settings.runs_dir / run_id / "events.jsonl"
    manifest_path = settings.runs_dir / run_id / "run_manifest.json"
    sent = 0

    while True:
        if events_path.exists():
            lines = events_path.read_text(encoding="utf-8").splitlines()
            for raw in lines[sent:]:
                payload = json.loads(raw)
                sent += 1
                yield f"event: stage_{payload['event']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if payload.get("artifact"):
                    artifact_payload = {"run_id": run_id, "artifact": payload["artifact"], "ts": payload.get("ts")}
                    yield f"event: artifact_ready\ndata: {json.dumps(artifact_payload, ensure_ascii=False)}\n\n"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["status"] in {"completed", "failed"}:
                yield (
                    f"event: run_{manifest['status']}\n"
                    f"data: {json.dumps({'run_id': run_id, 'status': manifest['status']}, ensure_ascii=False)}\n\n"
                )
                detail = store.get(run_id)
                if detail is not None:
                    detail.status = manifest["status"]
                break
        await asyncio.sleep(0.25)
