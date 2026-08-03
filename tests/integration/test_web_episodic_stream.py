from fastapi.testclient import TestClient

from dramaloop.web.app import create_app


def test_stream_endpoint_emits_episode_level_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

    client = TestClient(create_app())
    created = client.post(
        "/api/runs",
        json={
            "idea": "她被退婚后反手嫁给宿敌",
            "style": ["都市情感"],
            "constraints": [],
            "max_iterations": 2,
            "format": "episodic_series",
            "pause_after_plan": False,
        },
    ).json()

    with client.stream("GET", created["stream_url"]) as response:
        text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in response.iter_lines())

    assert "event: episode_completed" in text
    assert "event: episode_artifact_ready" in text
    assert "event: final_assembly_completed" in text
