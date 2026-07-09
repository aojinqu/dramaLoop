from pathlib import Path

from typer.testing import CliRunner

from dramaloop.main import app


runner = CliRunner()


def test_inspect_command_prints_summary_table(sample_run_dir: Path) -> None:
    result = runner.invoke(app, ["inspect", str(sample_run_dir)])

    assert result.exit_code == 0
    assert "20260708-153000-demo" in result.stdout
    assert "overall_scores" in result.stdout


def test_eval_command_supports_dataset_runs(tmp_path: Path, monkeypatch) -> None:
    dataset_path = tmp_path / "cases.yaml"
    dataset_path.write_text(
        """
- idea: 她在婚礼被抛弃后改嫁死对头
  style: [都市情感, 逆袭]
  length: short
- idea: 她被继妹算计后直播翻盘
  style: [狗血短剧感, 爽文]
  length: short
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("DRAMALOOP_EVALS_DIR", str(tmp_path / "evals"))

    result = runner.invoke(app, ["eval", "--dataset", str(dataset_path)])

    assert result.exit_code == 0
    reports = list((tmp_path / "evals" / "reports").glob("*.json"))
    assert len(reports) == 1


def test_eval_command_creates_distinct_run_directories_for_duplicate_story_slugs(tmp_path: Path, monkeypatch) -> None:
    dataset_path = tmp_path / "duplicate-cases.yaml"
    dataset_path.write_text(
        """
- idea: 中文故事A
  style: [都市情感]
  length: short
- idea: 中文故事B
  style: [都市情感]
  length: short
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("DRAMALOOP_EVALS_DIR", str(tmp_path / "evals"))

    result = runner.invoke(app, ["eval", "--dataset", str(dataset_path)])

    assert result.exit_code == 0
    created_runs = sorted(path.name for path in (tmp_path / "runs").iterdir())
    assert len(created_runs) == 2
    assert created_runs[0] != created_runs[1]
