import asyncio
import json
from datetime import datetime
from pathlib import Path

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import dramaloop.web.runtime as web_runtime_module
from dramaloop.config import Settings
from dramaloop.web.app import create_app
from dramaloop.web.schemas import WebRunCreateRequest, WebRunDetail
from dramaloop.web.store import WebRunStore



def test_create_run_returns_run_id_and_detail_snapshot(monkeypatch) -> None:
    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "被未婚夫当众退婚后，她转身嫁给了他的死对头",
            "style": ["都市情感", "逆袭", "狗血短剧感"],
            "audience": "女性向短剧用户",
            "constraints": ["节奏快", "结尾有回报"],
            "max_iterations": 2,
        },
    )

    assert created.status_code == 202
    payload = created.json()
    assert payload["status"] == "running"
    assert payload["stream_url"] == f"/api/runs/{payload['run_id']}/stream"

    detail = client.get(f"/api/runs/{payload['run_id']}")

    assert detail.status_code == 200
    snapshot = detail.json()
    assert snapshot["request"]["idea"] == "被未婚夫当众退婚后，她转身嫁给了他的死对头"
    assert snapshot["status"] == "running"
    assert snapshot["stages"][0]["name"] == "premise_refinement"



def test_create_run_request_defaults_length_to_short_and_detail_route_declares_response_model() -> None:
    app = create_app()
    client = TestClient(app)

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后转身嫁给死对头",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )

    assert created.status_code == 202
    payload = created.json()

    detail = client.get(f"/api/runs/{payload['run_id']}")

    assert detail.status_code == 200
    assert detail.json()["request"]["length"] == "short"

    detail_route = next(
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path == "/api/runs/{run_id}" and "GET" in route.methods
    )
    assert detail_route.response_model is WebRunDetail



def test_create_run_uses_unique_ids_within_same_second(monkeypatch) -> None:
    fixed_now = datetime(2026, 7, 9, 12, 34, 56)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls) -> datetime:
            return fixed_now

    monkeypatch.setattr(web_runtime_module, "datetime", FixedDateTime)
    client = TestClient(create_app())

    first = client.post(
        "/api/runs",
        json={
            "idea": "女主逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )
    second = client.post(
        "/api/runs",
        json={
            "idea": "男主复仇",
            "style": ["复仇爽文"],
            "constraints": [],
            "max_iterations": 2,
        },
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["run_id"] != second.json()["run_id"]



def test_create_run_returns_store_assigned_run_id_when_background_is_not_running(tmp_path, monkeypatch) -> None:
    fixed_now = datetime(2026, 7, 9, 12, 34, 56)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls) -> datetime:
            return fixed_now

    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(web_runtime_module, "datetime", FixedDateTime)
    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    first = client.post(
        "/api/runs",
        json={
            "idea": "被退婚后她逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )
    second = client.post(
        "/api/runs",
        json={
            "idea": "被退婚后她逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["run_id"] == "20260709-123456-story"
    assert second.json()["run_id"] == "20260709-123456-story-2"



def test_get_run_hydrates_completed_status_from_manifest(tmp_path, monkeypatch) -> None:
    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )
    run_id = created.json()["run_id"]
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"}),
                json.dumps(
                    {
                        "ts": "2026-07-09T12:35:00",
                        "stage": "premise_refinement",
                        "event": "completed",
                        "artifact": "premise.json",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "completed",
                "started_at": "2026-07-09T12:34:56",
                "finished_at": "2026-07-09T12:35:10",
                "model_provider": "mock",
                "model_name": "claude-sonnet-5",
                "max_iterations": 2,
                "completed_iterations": 1,
                "target_threshold": 7.5,
                "minimum_dimension_threshold": 6,
                "min_delta": 0.3,
                "final_artifact": "final_story.md",
                "error_message": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "final_story.md").write_text("最终故事正文", encoding="utf-8")
    (run_dir / "critique_v1.json").write_text(
        json.dumps(
            {
                "dimension_scores": {
                    "hook_strength": {
                        "score": 8,
                        "reason": "hook",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "character_consistency": {
                        "score": 8,
                        "reason": "character",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "conflict_intensity": {
                        "score": 8,
                        "reason": "conflict",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "pacing": {
                        "score": 8,
                        "reason": "pacing",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "short_drama_feel": {
                        "score": 8,
                        "reason": "feel",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "ending_payoff": {
                        "score": 7,
                        "reason": "ending",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                    "language_fluency": {
                        "score": 8,
                        "reason": "language",
                        "evidence": "evidence",
                        "improvement_advice": "advice",
                    },
                },
                "overall_score": 7.9,
                "weakest_dimensions": ["ending_payoff"],
                "rewrite_target": "ending_payoff",
                "rewrite_plan": {"scope": "ending", "must_fix": ["payoff"], "keep": ["tone"]},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    detail = client.get(f"/api/runs/{run_id}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "completed"
    assert payload["stages"][0]["status"] == "completed"
    assert payload["final_story"] == "最终故事正文"
    assert payload["overall_score"] == 7.9
    assert payload["rewrite_focus"] == "ending_payoff"
    assert "premise.json" in payload["available_artifacts"]
    assert "final_story.md" in payload["available_artifacts"]



def test_launch_run_persists_failure_when_background_setup_crashes(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

    created_coroutines = []

    def fake_create_task(coro):
        created_coroutines.append(coro)
        return None

    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)

    def failing_build_llm_client(_settings):
        raise RuntimeError("missing api key")

    monkeypatch.setattr(web_runtime_module, "build_llm_client", failing_build_llm_client)
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )

    assert created.status_code == 202
    run_id = created.json()["run_id"]
    assert len(created_coroutines) == 1

    asyncio.run(created_coroutines[0])

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "failed"

    run_dir = tmp_path / "runs" / run_id
    manifest = json.loads((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["error_message"] == "missing api key"

    events_text = (run_dir / "events.jsonl").read_text(encoding="utf-8")
    assert '"event":"failed"' in events_text



def test_hydration_ignores_partial_json_writes(tmp_path, monkeypatch) -> None:
    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后逆袭",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
        },
    )
    run_id = created.json()["run_id"]
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"}),
                '{"ts": "2026-07-09T12:34:57", "stage": "premise_refinement"',
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text('{"run_id": ', encoding="utf-8")
    (run_dir / "critique_v1.json").write_text('{"overall_score": ', encoding="utf-8")

    detail = client.get(f"/api/runs/{run_id}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "running"
    assert payload["stages"][0]["status"] == "running"
    assert payload["overall_score"] is None



def test_get_run_recovers_from_disk_without_store_membership(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    client = TestClient(create_app())

    run_id = "20260709-123456-story"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "request.json").write_text(
        json.dumps(
            {
                "idea": "她被退婚后逆袭",
                "style": ["都市情感"],
                "length": "short",
                "audience": None,
                "constraints": [],
                "max_iterations": 2,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        json.dumps({"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"}) + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "running",
                "started_at": "2026-07-09T12:34:56",
                "finished_at": None,
                "model_provider": "mock",
                "model_name": "claude-sonnet-5",
                "max_iterations": 2,
                "completed_iterations": 0,
                "target_threshold": 7.5,
                "minimum_dimension_threshold": 6,
                "min_delta": 0.3,
                "final_artifact": None,
                "error_message": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    detail = client.get(f"/api/runs/{run_id}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["run_id"] == run_id
    assert payload["request"]["idea"] == "她被退婚后逆袭"
    assert payload["stages"][0]["status"] == "running"



def test_stream_endpoint_recovers_from_disk_without_store_membership(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    client = TestClient(create_app())

    run_id = "20260709-123456-story"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "request.json").write_text(
        json.dumps(
            {
                "idea": "她被退婚后逆袭",
                "style": ["都市情感"],
                "length": "short",
                "audience": None,
                "constraints": [],
                "max_iterations": 2,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"}),
                json.dumps(
                    {
                        "ts": "2026-07-09T12:35:00",
                        "stage": "final_assembly",
                        "event": "completed",
                        "artifact": "run_summary.md",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "completed",
                "started_at": "2026-07-09T12:34:56",
                "finished_at": "2026-07-09T12:35:05",
                "model_provider": "mock",
                "model_name": "claude-sonnet-5",
                "max_iterations": 2,
                "completed_iterations": 1,
                "target_threshold": 7.5,
                "minimum_dimension_threshold": 6,
                "min_delta": 0.3,
                "final_artifact": "final_story.md",
                "error_message": None,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    with client.stream("GET", f"/api/runs/{run_id}/stream") as response:
        chunks = list(response.iter_lines())

    assert response.status_code == 200
    text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in chunks)
    assert "event: stage_started" in text
    assert "event: artifact_ready" in text
    assert "event: run_completed" in text



def test_stream_run_events_drains_tail_before_terminal_event(tmp_path) -> None:
    settings = Settings.model_validate({"runs_dir": str(tmp_path / "runs")})
    store = WebRunStore()
    run_id = "20260709-123456-story"
    store.create(
        run_id,
        WebRunCreateRequest(
            idea="她被退婚后逆袭",
            style=["都市情感"],
            constraints=[],
            max_iterations=2,
        ),
    )

    run_dir = settings.runs_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "request.json").write_text(
        json.dumps(
            {
                "idea": "她被退婚后逆袭",
                "style": ["都市情感"],
                "length": "short",
                "audience": None,
                "constraints": [],
                "max_iterations": 2,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    original_read_json_lines = web_runtime_module._read_json_lines
    original_read_json_lines_state = web_runtime_module._read_json_lines_state
    call_count = {"events": 0, "state": 0}

    def fake_read_json_lines(path: Path):
        if path.name != "events.jsonl":
            return original_read_json_lines(path)
        call_count["events"] += 1
        if call_count["events"] == 1:
            return [
                {"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"},
            ]
        return [
            {"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"},
            {
                "ts": "2026-07-09T12:35:00",
                "stage": "final_assembly",
                "event": "completed",
                "artifact": "run_summary.md",
            },
        ]

    def fake_read_json_lines_state(path: Path):
        if path.name != "events.jsonl":
            return original_read_json_lines_state(path)
        call_count["state"] += 1
        if call_count["state"] == 1:
            return [
                {"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"},
            ], True
        return [
            {"ts": "2026-07-09T12:34:56", "stage": "premise_refinement", "event": "started"},
            {
                "ts": "2026-07-09T12:35:00",
                "stage": "final_assembly",
                "event": "completed",
                "artifact": "run_summary.md",
            },
        ], False

    web_runtime_module._read_json_lines = fake_read_json_lines
    web_runtime_module._read_json_lines_state = fake_read_json_lines_state
    try:
        (run_dir / "run_manifest.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": "completed",
                    "started_at": "2026-07-09T12:34:56",
                    "finished_at": "2026-07-09T12:35:05",
                    "model_provider": "mock",
                    "model_name": "claude-sonnet-5",
                    "max_iterations": 2,
                    "completed_iterations": 1,
                    "target_threshold": 7.5,
                    "minimum_dimension_threshold": 6,
                    "min_delta": 0.3,
                    "final_artifact": "final_story.md",
                    "error_message": None,
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        async def collect() -> list[str]:
            messages = []
            async for chunk in web_runtime_module.stream_run_events(run_id, settings, store):
                messages.append(chunk)
            return messages

        messages = asyncio.run(collect())
    finally:
        web_runtime_module._read_json_lines = original_read_json_lines
        web_runtime_module._read_json_lines_state = original_read_json_lines_state

    text = "".join(messages)
    assert "event: stage_started" in text
    assert "event: artifact_ready" in text
    assert "run_summary.md" in text
    assert text.rfind("event: artifact_ready") < text.rfind("event: run_completed")
