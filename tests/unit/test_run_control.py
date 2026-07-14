import json
from datetime import datetime

from fastapi.testclient import TestClient

import dramaloop.web.runtime as web_runtime_module
from dramaloop.harness.control import CONTROLLERS, RunCancelled, RunController
from dramaloop.web.app import create_app


def setup_function() -> None:
    CONTROLLERS.clear()


def teardown_function() -> None:
    CONTROLLERS.clear()


def test_pause_resume_cancel_endpoints(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "控制流测试",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
            "format": "episodic_series",
            "episode_count": 2,
            "pause_after_plan": True,
        },
    )
    assert created.status_code == 202
    run_id = created.json()["run_id"]

    controller = CONTROLLERS.get(run_id)
    assert controller is not None
    controller.pause(phase="awaiting_plan_review")

    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "request.json").write_text(
        json.dumps(
            {
                "idea": "控制流测试",
                "style": ["都市情感"],
                "length": "short",
                "format": "episodic_series",
                "constraints": [],
                "max_iterations": 2,
                "episode_count": 2,
                "episode_min_words": 500,
                "episode_max_words": 800,
                "delivery_mode": "stream_and_final",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "paused",
                "started_at": datetime.now().isoformat(),
                "finished_at": None,
                "model_provider": "mock",
                "model_name": "mock",
                "format": "episodic_series",
                "max_iterations": 2,
                "completed_iterations": 0,
                "total_episodes": 2,
                "completed_episodes": 0,
                "current_episode": None,
                "target_threshold": 7.5,
                "minimum_dimension_threshold": 6,
                "min_delta": 0.3,
                "final_artifact": None,
                "error_message": None,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "events.jsonl").write_text("", encoding="utf-8")
    (run_dir / "episode_plan.json").write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "开端",
                        "opening_situation": "开场",
                        "core_conflict": "冲突",
                        "must_happen": ["事件A"],
                        "hook_ending": "钩子",
                        "sets_up_next": "下一集",
                    },
                    {
                        "episode_number": 2,
                        "title": "发展",
                        "opening_situation": "开场2",
                        "core_conflict": "冲突2",
                        "must_happen": ["事件B"],
                        "hook_ending": "钩子2",
                        "sets_up_next": "收束",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    detail = client.get(f"/api/runs/{run_id}")
    assert detail.status_code == 200
    assert detail.json()["status"] == "paused"
    assert detail.json()["has_live_controller"] is True

    updated = client.put(
        f"/api/runs/{run_id}/episode-plan",
        json={
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "开端改",
                    "opening_situation": "开场改",
                    "core_conflict": "冲突改",
                    "must_happen": ["事件A改"],
                    "hook_ending": "钩子改",
                    "sets_up_next": "下一集改",
                },
                {
                    "episode_number": 2,
                    "title": "发展",
                    "opening_situation": "开场2",
                    "core_conflict": "冲突2",
                    "must_happen": ["事件B"],
                    "hook_ending": "钩子2",
                    "sets_up_next": "收束",
                },
            ]
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["episode_plan"]["episodes"][0]["title"] == "开端改"

    human_actions = (run_dir / "human_actions.jsonl").read_text(encoding="utf-8")
    assert '"action": "plan_edit"' in human_actions

    resumed = client.post(f"/api/runs/{run_id}/resume")
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "running"
    assert CONTROLLERS.get(run_id) is not None
    assert not CONTROLLERS.get(run_id).paused

    cancelled = client.post(f"/api/runs/{run_id}/cancel")
    assert cancelled.status_code == 200
    assert CONTROLLERS.get(run_id).cancelled

    human_actions = (run_dir / "human_actions.jsonl").read_text(encoding="utf-8")
    assert '"action": "resume"' in human_actions
    assert '"action": "cancel"' in human_actions


def test_controller_checkpoint_cancel() -> None:
    controller = RunController(pause_after_plan=False)
    controller.cancel()
    try:
        controller.checkpoint(label="test")
        raise AssertionError("expected RunCancelled")
    except RunCancelled:
        pass
