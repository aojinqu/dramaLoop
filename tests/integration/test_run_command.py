from pathlib import Path

from typer.testing import CliRunner

from dramaloop.llm.base import LLMInvocationError
from dramaloop.main import app


runner = CliRunner()


class ExplodingClient:
    def generate_structured(self, *, role: str, prompt: str, response_model):
        raise LLMInvocationError("boom")

    def generate_text(self, *, role: str, prompt: str) -> str:
        raise LLMInvocationError("boom")


def test_run_command_creates_required_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    result = runner.invoke(
        app,
        [
            "run",
            "--idea",
            "她被退婚后嫁给死对头",
            "--style",
            "都市情感",
            "--style",
            "逆袭",
        ],
    )

    assert result.exit_code == 0
    created_runs = list((tmp_path / "runs").iterdir())
    assert len(created_runs) == 1
    run_dir = created_runs[0]
    assert (run_dir / "premise.json").exists()
    assert (run_dir / "characters.json").exists()
    assert (run_dir / "outline.json").exists()
    assert (run_dir / "draft_v1.md").exists()
    assert (run_dir / "critique_v1.json").exists()
    assert (run_dir / "rewrite_plan_v1.json").exists()
    assert (run_dir / "draft_v2.md").exists()
    assert (run_dir / "critique_v2.json").exists()
    assert (run_dir / "final_story.md").exists()
    assert (run_dir / "run_summary.md").exists()


def test_run_command_marks_manifest_failed_when_stage_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr("dramaloop.main.build_llm_client", lambda settings: ExplodingClient())

    result = runner.invoke(app, ["run", "--idea", "x", "--style", "都市情感"])

    assert result.exit_code != 0
    created_runs = list((tmp_path / "runs").iterdir())
    assert len(created_runs) == 1
    assert '"status": "failed"' in (created_runs[0] / "run_manifest.json").read_text(encoding="utf-8")
