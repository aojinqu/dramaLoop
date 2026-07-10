from pathlib import Path

from dramaloop.config import Settings
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.schemas.input import StoryRequest


def test_run_episodic_pipeline_writes_episode_files_and_final_story(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()
    request = StoryRequest(
        idea="她被退婚后反手嫁给宿敌",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    result = run_episodic_pipeline(request, settings, client)

    run_dir = result.run_dir
    assert (run_dir / "season_bible.json").exists()
    assert (run_dir / "episode_plan.json").exists()
    assert (run_dir / "continuity_state.json").exists()
    assert (run_dir / "episodes" / "episode_01.md").exists()
    assert (run_dir / "final_story.md").exists()
    assert "第1集" in (run_dir / "final_story.md").read_text(encoding="utf-8")


def test_run_episodic_pipeline_updates_manifest_episode_progress(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = build_default_mock_client()
    request = StoryRequest(
        idea="她被退婚后反手嫁给宿敌",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    result = run_episodic_pipeline(request, settings, client)
    manifest = (result.run_dir / "run_manifest.json").read_text(encoding="utf-8")

    assert '"format": "episodic_series"' in manifest
    assert '"completed_episodes": 12' in manifest
