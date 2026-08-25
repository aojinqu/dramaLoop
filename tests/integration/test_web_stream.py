import asyncio
import json

from fastapi.testclient import TestClient

from dramaloop.config import Settings
from dramaloop.web.app import create_app
from dramaloop.web.runtime import stream_run_events
from dramaloop.web.store import WebRunStore


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
    final_story_artifact_events = [
        block
        for block in text.split("\n\n")
        if "event: artifact_ready" in block and '"artifact": "final_story.md"' in block
    ]
    assert len(final_story_artifact_events) == 1

    event_ids = [
        line.removeprefix("id: ")
        for line in text.splitlines()
        if line.startswith("id: ")
    ]
    event_cursors = [tuple(int(part) for part in event_id.split(":")) for event_id in event_ids]
    assert event_cursors == sorted(event_cursors)
    assert len(event_ids) == len(set(event_ids))

    resume_after = event_ids[0]
    resume_cursor = event_cursors[0]
    for request_kwargs in (
        {"headers": {"Last-Event-ID": str(resume_after)}},
        {"params": {"after": resume_after}},
    ):
        with client.stream("GET", created["stream_url"], **request_kwargs) as response:
            resumed_text = "\n".join(
                line.decode() if isinstance(line, bytes) else line
                for line in response.iter_lines()
            )
        resumed_ids = [
            line.removeprefix("id: ")
            for line in resumed_text.splitlines()
            if line.startswith("id: ")
        ]
        resumed_cursors = [
            tuple(int(part) for part in event_id.split(":"))
            for event_id in resumed_ids
        ]
        assert resumed_ids
        assert min(resumed_cursors) > resume_cursor


def test_stream_cursor_keeps_first_event_appended_after_terminal_boundary(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    run_id = "resume-after-terminal"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "stage": "run",
                        "event": "completed",
                        "artifact": "final_story.md",
                    }
                ),
                json.dumps({"stage": "run", "event": "resumed"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"status": "running", "format": "episodic_series"}),
        encoding="utf-8",
    )

    async def read_first_event() -> str:
        stream = stream_run_events(
            run_id,
            Settings(),
            WebRunStore(),
            after_event_id="2:0",
        )
        try:
            return await anext(stream)
        finally:
            await stream.aclose()

    resumed_event = asyncio.run(read_first_event())

    assert resumed_event.startswith("id: 2:1\nevent: run_resumed\n")
