import json
from pathlib import Path

from dramaloop.config import Settings
from dramaloop.eval.ablation import run_research_harness_eval
from dramaloop.eval.judge import run_judge
from dramaloop.eval.trace import evaluate_run_trace
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.schemas.input import StoryRequest


def _run(tmp_path: Path):
    request = StoryRequest(
        idea="她在婚礼被抛弃后改嫁死对头",
        style=["都市情感"],
        length="short",
        constraints=["保留主角关系"],
    )
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    result = run_story_pipeline(request, settings, build_default_mock_client())
    return result, settings


def test_trace_eval_reports_harness_metrics(tmp_path: Path) -> None:
    result, _ = _run(tmp_path)

    metrics = evaluate_run_trace(result.run_dir)

    assert metrics["stage_completion_rate"] == 1.0
    assert metrics["schema_valid_rate"] == 1.0
    assert metrics["required_context_recall"] == 1.0
    assert metrics["unsupported_memory_rate"] == 0.0
    assert metrics["artifact_completion_rate"] == 1.0
    assert metrics["rewrite_target_alignment"] == 1.0


def test_mock_judge_writes_baseline_artifact(tmp_path: Path) -> None:
    result, _ = _run(tmp_path)

    judged = run_judge(result.run_dir, build_default_mock_client())

    assert judged.average_score > 0
    artifact = result.run_dir / "eval" / "judge_baseline.json"
    assert artifact.exists()
    payload = json.loads(artifact.read_text(encoding="utf-8"))
    assert payload["dimensions"]["continuity"] >= 1


def test_research_harness_dataset_runs_ablation_and_failure_mining(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "research.yaml"
    dataset.write_text(
        """
- id: constrained-001
  format: single_story
  idea: 她在婚礼被抛弃后改嫁死对头
  style: [都市情感]
  constraints: [必须保留主角关系]
  expected_contracts: [preserve_character_relationships]
  ablation_modes: [baseline, full_harness]
""".strip(),
        encoding="utf-8",
    )
    settings = Settings(
        runs_dir=tmp_path / "runs",
        evals_dir=tmp_path / "evals",
        provider="mock",
    )

    report = run_research_harness_eval(dataset, settings)

    assert report["case_count"] == 1
    assert len(report["ablation_runs"]) == 2
    assert {item["mode"] for item in report["ablation_runs"]} == {
        "baseline",
        "full_harness",
    }
    assert "pairwise" in report
    reports_dir = tmp_path / "evals" / "reports"
    assert list(reports_dir.glob("*-research-harness-report.json"))
    assert list(reports_dir.glob("*-failure-patterns.json"))
