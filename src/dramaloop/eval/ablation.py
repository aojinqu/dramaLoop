from datetime import datetime
from pathlib import Path
from time import monotonic
from typing import Any

import yaml

from dramaloop.config import Settings
from dramaloop.eval.failure_mining import mine_failures
from dramaloop.eval.judge import run_judge
from dramaloop.eval.pairwise import compare_runs
from dramaloop.eval.report import build_episodic_run_report, build_single_run_report
from dramaloop.eval.trace import evaluate_run_trace
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_judge_client, build_llm_client
from dramaloop.schemas.harness import HARNESS_MODES
from dramaloop.schemas.input import StoryRequest
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def _request_from_case(case: dict[str, Any]) -> StoryRequest:
    payload = {
        field_name: value
        for field_name, value in case.items()
        if field_name in StoryRequest.model_fields
    }
    payload.setdefault("length", "short")
    return StoryRequest.model_validate(payload)


def _completed_ratio(report: dict) -> float:
    total = report.get("total_episodes") or 0
    return (report.get("completed_episodes") or 0) / total if total else 0.0


def _render_report(report: dict) -> str:
    lines = [
        "# Research Harness Eval Report",
        "",
        f"- case_count: {report['case_count']}",
        f"- ablation_run_count: {len(report['ablation_runs'])}",
        f"- success_rate: {report['success_rate']}",
        f"- average_judge_score: {report['average_final_score']}",
        f"- pairwise_comparison_count: {len(report['pairwise'])}",
        "",
        "## Ablation Runs",
    ]
    for item in report["ablation_runs"]:
        lines.append(
            f"- {item['case_id']} / {item['mode']}: success={item['success']}, "
            f"judge={item['judge_score']:.2f}, completion={item['stage_completion_rate']:.2f}, "
            f"tokens={item['average_tokens']}, latency={item['latency_seconds']:.3f}s, "
            f"interventions={item['layer_intervention_count']}"
        )
    lines.extend(["", "## Pairwise"])
    for item in report["pairwise"]:
        lines.append(
            f"- {item['case_id']}: {item['mode_a']} vs {item['mode_b']} -> {item['winner']}"
        )
    lines.extend(["", "## Failure Mining"])
    category_counts = report["failure_mining"]["category_counts"]
    if category_counts:
        lines.extend(
            f"- {category}: {count}" for category, count in sorted(category_counts.items())
        )
    else:
        lines.append("- no failures detected")
    return "\n".join(lines)


def _summarize_modes(runs: list[dict]) -> list[dict]:
    summaries: list[dict] = []
    for mode in HARNESS_MODES:
        selected = [item for item in runs if item["mode"] == mode]
        if not selected:
            continue
        count = len(selected)
        summaries.append(
            {
                "mode": mode,
                "run_count": count,
                "completion_rate": round(
                    sum(bool(item["success"]) for item in selected) / count,
                    4,
                ),
                "average_judge_score": round(
                    sum(float(item["judge_score"]) for item in selected) / count,
                    2,
                ),
                "continuity_issue_count": sum(
                    int(item.get("continuity_failures", 0)) for item in selected
                ),
                "memory_recall_rate": round(
                    sum(float(item["memory_recall_rate"]) for item in selected) / count,
                    4,
                ),
                "memory_compression_ratio": round(
                    sum(float(item["memory_compression_ratio"]) for item in selected) / count,
                    4,
                ),
                "unsupported_memory_rate": round(
                    sum(float(item["unsupported_memory_rate"]) for item in selected) / count,
                    4,
                ),
                "average_tokens": round(
                    sum(int(item["average_tokens"]) for item in selected) / count,
                    2,
                ),
                "average_latency": round(
                    sum(float(item["latency_seconds"]) for item in selected) / count,
                    4,
                ),
                "layer_intervention_count": sum(
                    int(item["layer_intervention_count"]) for item in selected
                ),
            }
        )
    return summaries


def _summarize_pairwise(comparisons: list[dict]) -> dict:
    total = len(comparisons)
    ties = sum(item["winner"] == "tie" for item in comparisons)
    mode_wins: dict[str, int] = {}
    dimension_wins: dict[str, dict[str, int]] = {}
    for item in comparisons:
        winner = item["winner"]
        if winner == "A":
            mode_wins[item["mode_a"]] = mode_wins.get(item["mode_a"], 0) + 1
        elif winner == "B":
            mode_wins[item["mode_b"]] = mode_wins.get(item["mode_b"], 0) + 1
        for dimension, dimension_winner in item["dimension_winners"].items():
            mode = None
            if dimension_winner == "A":
                mode = item["mode_a"]
            elif dimension_winner == "B":
                mode = item["mode_b"]
            if mode:
                dimension_wins.setdefault(dimension, {})
                dimension_wins[dimension][mode] = dimension_wins[dimension].get(mode, 0) + 1
    return {
        "comparison_count": total,
        "tie_rate": round(ties / total, 4) if total else 0.0,
        "mode_win_rate": {
            mode: round(wins / total, 4) if total else 0.0
            for mode, wins in sorted(mode_wins.items())
        },
        "dimension_win_rate": {
            dimension: {
                mode: round(wins / total, 4) if total else 0.0
                for mode, wins in sorted(mode_counts.items())
            }
            for dimension, mode_counts in sorted(dimension_wins.items())
        },
    }


def run_research_harness_eval(dataset_path: Path, settings: Settings) -> dict:
    cases = yaml.safe_load(dataset_path.read_text(encoding="utf-8")) or []
    ablation_runs: list[dict] = []
    runs_by_case: dict[str, list[dict]] = {}

    for case in cases:
        case_id = str(case["id"])
        configured_modes = case.get("ablation_modes") or list(HARNESS_MODES)
        unknown_modes = set(configured_modes) - set(HARNESS_MODES)
        if unknown_modes:
            raise ValueError(f"Unknown ablation modes: {sorted(unknown_modes)}")
        for mode in configured_modes:
            mode_settings = settings.model_copy(update={"harness_mode": mode})
            request = _request_from_case(case)
            started = monotonic()
            client = build_llm_client(mode_settings)
            if request.format == "episodic_series":
                result = run_episodic_pipeline(request, mode_settings, client, controller=None)
                base_report = build_episodic_run_report(result.run_dir)
            else:
                result = run_story_pipeline(request, mode_settings, client)
                base_report = build_single_run_report(result.run_dir)
            latency = monotonic() - started
            judge = run_judge(result.run_dir, build_judge_client(mode_settings))
            trace = evaluate_run_trace(result.run_dir)
            run_report = {
                **base_report,
                **trace,
                "case_id": case_id,
                "mode": mode,
                "run_dir": str(result.run_dir),
                "judge_score": judge.average_score,
                "average_tokens": trace["context_tokens"],
                "latency_seconds": round(latency, 4),
            }
            ablation_runs.append(run_report)
            runs_by_case.setdefault(case_id, []).append(run_report)

    pairwise_results: list[dict] = []
    for case_id, case_runs in runs_by_case.items():
        for left, right in zip(case_runs, case_runs[1:]):
            comparison = compare_runs(
                Path(left["run_dir"]),
                Path(right["run_dir"]),
                build_judge_client(settings),
            )
            pairwise_results.append(
                {
                    "case_id": case_id,
                    "mode_a": left["mode"],
                    "mode_b": right["mode"],
                    "winner": comparison["winner"],
                    "dimension_winners": comparison["dimension_winners"],
                }
            )

    run_count = len(ablation_runs)
    success_rate = (
        round(sum(bool(item["success"]) for item in ablation_runs) / run_count, 4)
        if run_count
        else 0.0
    )
    average_score = (
        round(sum(float(item["judge_score"]) for item in ablation_runs) / run_count, 2)
        if run_count
        else 0.0
    )
    average_completed_ratio = (
        round(sum(_completed_ratio(item) for item in ablation_runs) / run_count, 4)
        if run_count
        else 0.0
    )
    report = {
        "case_count": len(cases),
        "success_rate": success_rate,
        "average_final_score": average_score,
        "average_completed_episode_ratio": average_completed_ratio,
        "reports": ablation_runs,
        "ablation_runs": ablation_runs,
        "ablation_summary": _summarize_modes(ablation_runs),
        "pairwise": pairwise_results,
        "pairwise_summary": _summarize_pairwise(pairwise_results),
    }
    reports_dir = settings.evals_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    report["failure_mining"] = mine_failures(
        ablation_runs,
        reports_dir=reports_dir,
        stamp=stamp,
    )
    write_json_artifact(reports_dir / f"{stamp}-research-harness-report.json", report)
    write_markdown_artifact(
        reports_dir / f"{stamp}-research-harness-report.md",
        _render_report(report),
    )
    return report
