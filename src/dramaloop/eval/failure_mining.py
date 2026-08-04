from collections import Counter
from datetime import datetime
import json
from pathlib import Path

from dramaloop.eval.trace import evaluate_run_trace
from dramaloop.schemas.memory import RunMemory
from dramaloop.schemas.run import RunManifest
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def classify_run_failures(run_dir: Path, *, judge_score: float | None = None) -> list[str]:
    manifest = RunManifest.model_validate_json(
        (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    memory = RunMemory.model_validate_json(
        (run_dir / "run_memory.json").read_text(encoding="utf-8")
    )
    metrics = evaluate_run_trace(run_dir)
    failures: list[str] = []
    if manifest.status != "completed" or metrics["stage_completion_rate"] < 1:
        failures.append("contract_mismatch")
    if metrics["required_context_recall"] < 1:
        failures.append("context_loss")
    if metrics["memory_recall_rate"] < 0.5 and (memory.semantic_facts or memory.episode_memories):
        failures.append("memory_recall_gap")
    if memory.memory_conflicts:
        failures.append("memory_drift")
    if metrics["unsupported_memory_rate"] > 0:
        failures.append("unsupported_memory")
    if metrics["realization_block_rate"] > 0 or metrics["schema_valid_rate"] < 1:
        failures.append("realization_error")
    if memory.failure_patterns:
        failures.append("trajectory_degradation")
    if judge_score is not None and judge_score < 7:
        failures.append("quality_gap")
        skill_path = run_dir / "skill_trace.jsonl"
        selected_skills = []
        if skill_path.exists():
            selected_skills = [
                skill_id
                for line in skill_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
                for skill_id in json.loads(line).get("skill_ids", [])
            ]
        if not selected_skills:
            failures.append("skill_gap")
    return sorted(set(failures))


def mine_failures(
    run_results: list[dict],
    *,
    reports_dir: Path,
    stamp: str | None = None,
) -> dict:
    stamp = stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    patterns: list[dict] = []
    counts: Counter[str] = Counter()
    for item in run_results:
        run_dir = Path(item["run_dir"])
        categories = classify_run_failures(
            run_dir,
            judge_score=item.get("judge_score"),
        )
        counts.update(categories)
        patterns.append(
            {
                "run_id": run_dir.name,
                "case_id": item.get("case_id"),
                "mode": item.get("mode"),
                "categories": categories,
            }
        )
    report = {
        "run_count": len(run_results),
        "category_counts": dict(sorted(counts.items())),
        "patterns": patterns,
    }
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_json_artifact(reports_dir / f"{stamp}-failure-patterns.json", report)
    lines = [
        "# Research Harness Failure Patterns",
        "",
        f"- run_count: {report['run_count']}",
        "",
        "## Categories",
    ]
    if counts:
        lines.extend(f"- {name}: {count}" for name, count in sorted(counts.items()))
    else:
        lines.append("- no failures detected")
    lines.extend(["", "## Runs"])
    for item in patterns:
        category_text = ", ".join(item["categories"]) or "none"
        lines.append(
            f"- {item['run_id']} ({item.get('case_id')}, {item.get('mode')}): {category_text}"
        )
    write_markdown_artifact(
        reports_dir / f"{stamp}-failure-patterns.md",
        "\n".join(lines),
    )
    return report
