from fastapi.testclient import TestClient

from dramaloop.web.app import create_app


def test_stream_endpoint_emits_stage_and_completion_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

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
    ).json()

    with client.stream("GET", created["stream_url"]) as response:
        chunks = list(response.iter_lines())

    text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in chunks)
    assert "event: stage_started" in text
    assert "event: stage_completed" in text
    assert "event: artifact_ready" in text
    assert "event: run_completed" in text
