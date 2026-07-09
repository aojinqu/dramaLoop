from datetime import datetime
from pathlib import Path

from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent, RunManifest
from dramaloop.storage.artifacts import append_event, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files, reserve_run_id


def test_build_run_id_uses_timestamp_and_ascii_slug_fallback() -> None:
    run_id = build_run_id("被未婚夫退婚后她嫁给死对头", datetime(2026, 7, 8, 15, 30, 0))

    assert run_id == "20260708-153000-story"


def test_reserve_run_id_adds_suffix_when_directory_exists(tmp_path: Path) -> None:
    (tmp_path / "20260708-153000-story").mkdir()

    assert reserve_run_id(tmp_path, "20260708-153000-story") == "20260708-153000-story-2"


def test_initialize_run_files_writes_request_manifest_and_events_file(tmp_path: Path) -> None:
    request = StoryRequest(idea="x", style=["都市"], length="short")
    manifest = RunManifest(
        run_id="20260708-153000-story",
        status="running",
        started_at="2026-07-08T15:30:00",
        model_provider="mock",
        model_name="mock-model",
        max_iterations=2,
        target_threshold=7.5,
        minimum_dimension_threshold=6,
        min_delta=0.3,
    )

    run_paths = create_run_paths(tmp_path, manifest.run_id)
    initialize_run_files(run_paths, request, manifest)

    assert run_paths.request_path.exists()
    assert run_paths.manifest_path.exists()
    assert run_paths.events_path.exists()


def test_append_event_writes_one_json_object_per_line(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    append_event(
        events_path,
        RunEvent(ts="2026-07-08T15:30:00", stage="premise_refinement", event="completed", artifact="premise.json"),
    )

    assert events_path.read_text(encoding="utf-8").strip().endswith('"artifact":"premise.json"}')


def test_write_markdown_artifact_creates_parent_directory(tmp_path: Path) -> None:
    markdown_path = tmp_path / "nested" / "draft_v1.md"
    write_markdown_artifact(markdown_path, "# Draft\n")

    assert markdown_path.read_text(encoding="utf-8") == "# Draft\n"
