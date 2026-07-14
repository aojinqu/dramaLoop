import json
from datetime import datetime

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import dramaloop.web.runtime as web_runtime_module
from dramaloop.harness.control import CONTROLLERS
from dramaloop.web.app import create_app
from dramaloop.web.schemas import WebRunDetail


def setup_function() -> None:
    CONTROLLERS.clear()


def teardown_function() -> None:
    CONTROLLERS.clear()


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


def test_create_episodic_run_defaults_to_series_mode(monkeypatch) -> None:
    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    app = create_app()
    client = TestClient(app)

    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后反手嫁给宿敌",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
            "format": "episodic_series",
        },
    )

    assert created.status_code == 202
    detail = client.get(f"/api/runs/{created.json()['run_id']}").json()
    assert detail["request"]["format"] == "episodic_series"
    assert detail["request"]["episode_min_words"] == 500
    assert detail["request"]["episode_max_words"] == 800


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
            "format": "episodic_series",
        },
    )
    run_id = created.json()["run_id"]
    run_dir = tmp_path / "runs" / run_id
    (run_dir / "episodes").mkdir(parents=True, exist_ok=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"ts": "2026-07-09T12:34:56", "stage": "episode_generation", "event": "started", "iteration": 1}),
                json.dumps(
                    {
                        "ts": "2026-07-09T12:35:00",
                        "stage": "episode_generation",
                        "event": "completed",
                        "iteration": 1,
                        "artifact": "episodes/episode_01.md",
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
                "format": "episodic_series",
                "max_iterations": 2,
                "completed_iterations": 0,
                "total_episodes": 12,
                "completed_episodes": 1,
                "current_episode": 1,
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
    (run_dir / "final_story.md").write_text("# 第1集 婚礼反击\n\n最终故事正文", encoding="utf-8")
    (run_dir / "episodes" / "episode_01.md").write_text("第1集正文", encoding="utf-8")
    (run_dir / "episodes" / "episode_01.json").write_text(
        json.dumps(
            {
                "episode_number": 1,
                "title": "婚礼反击",
                "markdown": "第1集正文",
                "word_count": 620,
                "episode_summary": "婚礼现场反手改嫁。",
                "hook_delivered": "顾承骁说他知道偷拍视频是谁放的。",
                "qa_passed": True,
                "overall_score": 5.5,
                "rewrite_applied": True,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "episodes" / "episode_01_critique.json").write_text(
        json.dumps(
            {
                "episode_number": 1,
                "overall_score": 5.5,
                "dimension_scores": {
                    "hook_strength": 5.0,
                    "conflict_intensity": 6.0,
                    "pacing": 5.5,
                    "short_drama_feel": 6.0,
                    "carryover": 8.0,
                },
                "weakest_dimensions": ["hook_strength"],
                "rewrite_needed": True,
                "rewrite_target": "强化集末钩子。",
                "issues": ["钩子偏软"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "season_bible.json").write_text(
        json.dumps(
            {
                "title_candidate": "婚礼反击",
                "series_logline": "退婚后的反击短剧",
                "core_conflict": "被退婚后的反击",
                "target_episode_count": 12,
                "final_payoff": "女主完成逆袭",
                "main_character_arcs": ["从隐忍到反击"],
                "must_land_beats": ["婚礼反转"],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (run_dir / "episode_plan.json").write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "episode_number": 1,
                        "title": "婚礼反击",
                        "opening_situation": "婚礼现场",
                        "core_conflict": "当众退婚",
                        "must_happen": ["退婚发生"],
                        "hook_ending": "新势力介入",
                        "sets_up_next": "下一集冲突",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    detail = client.get(f"/api/runs/{run_id}")

    assert detail.status_code == 200
    payload = detail.json()
    assert payload["status"] == "completed"
    assert payload["final_story"].startswith("# 第1集")
    assert payload["completed_episode_count"] == 1
    assert payload["episodes"][0]["title"] == "婚礼反击"
    assert payload["episodes"][0]["content"] == "第1集正文"
    assert payload["episodes"][0]["overall_score"] == 5.5
    assert payload["overall_score"] == 5.5
    assert payload["season_bible"]["title_candidate"] == "婚礼反击"
    assert payload["episode_plan"]["episodes"][0]["title"] == "婚礼反击"


def test_get_run_404s_for_unknown_run(monkeypatch) -> None:
    def fake_create_task(coro):
        coro.close()
        return None

    monkeypatch.setattr(web_runtime_module.asyncio, "create_task", fake_create_task)
    client = TestClient(create_app())

    response = client.get("/api/runs/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "run not found"}
