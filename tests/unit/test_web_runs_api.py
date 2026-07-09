from datetime import datetime

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

import dramaloop.web.app as web_app_module
from dramaloop.web.app import create_app
from dramaloop.web.schemas import WebRunDetail



def test_create_run_returns_run_id_and_detail_snapshot() -> None:
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

    monkeypatch.setattr(web_app_module, "datetime", FixedDateTime)
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
