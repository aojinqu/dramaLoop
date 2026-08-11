import json
from pathlib import Path

from dramaloop.config import Settings
from dramaloop.eval.ablation import run_research_harness_eval
from dramaloop.eval.failure_mining import classify_run_failures
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
    assert metrics["invalid_evidence_ref_count"] == 0
    assert metrics["artifact_completion_rate"] == 1.0
    assert metrics["rewrite_target_alignment"] == 1.0


def test_trace_eval_rejects_missing_evidence_artifacts(tmp_path: Path) -> None:
    result, _ = _run(tmp_path)
    memory_path = result.run_dir / "run_memory.json"
    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    memory["semantic_facts"][0]["evidence_refs"] = ["missing-artifact.json"]
    memory_path.write_text(json.dumps(memory, ensure_ascii=False), encoding="utf-8")

    metrics = evaluate_run_trace(result.run_dir)

    assert metrics["unsupported_memory_rate"] > 0
    assert metrics["invalid_evidence_ref_count"] == 1


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
    assert all(
        item["expected_contracts"] == ["preserve_character_relationships"]
        for item in report["ablation_runs"]
    )
    assert all(
        item["contract_results"]["preserve_character_relationships"]["passed"]
        for item in report["ablation_runs"]
    )
    assert all(item["contract_pass_rate"] == 1.0 for item in report["ablation_runs"])
    assert "pairwise" in report
    assert "regulation_action_counts" in report["ablation_summary"][0]
    reports_dir = tmp_path / "evals" / "reports"
    assert list(reports_dir.glob("*-research-harness-report.json"))
    assert list(reports_dir.glob("*-failure-patterns.json"))
    markdown_path = next(reports_dir.glob("*-research-harness-report.md"))
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "## Ablation Summary" in markdown
    assert "memory_recall_rate" in markdown
    assert "regulation_actions" in markdown
    assert "## Pairwise Summary" in markdown


def test_generic_provider_failure_is_not_trajectory_degradation(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    request = StoryRequest(
        idea="测试失败分类",
        style=["都市情感"],
        length="short",
    )

    try:
        run_story_pipeline(request, settings, build_default_mock_client())
    except Exception:
        raise AssertionError("default mock client should not fail")

    run_dir = next((tmp_path / "runs").iterdir())
    memory_path = run_dir / "run_memory.json"
    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    memory["failure_patterns"] = []
    memory_path.write_text(json.dumps(memory, ensure_ascii=False), encoding="utf-8")
    manifest_path = run_dir / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["status"] = "failed"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")

    failures = classify_run_failures(run_dir)

    assert "contract_mismatch" in failures
    assert "trajectory_degradation" not in failures
