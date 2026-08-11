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


def _evaluate_expected_contracts(
    expected_contracts: list[str],
    *,
    run_report: dict[str, Any],
    judge_dimensions: dict[str, float],
) -> dict[str, dict[str, Any]]:
    checks = {
        "preserve_user_constraints": (
            judge_dimensions["context_fidelity"] >= 7,
            "judge context_fidelity must be at least 7",
        ),
        "preserve_character_relationships": (
            judge_dimensions["character_consistency"] >= 7,
            "judge character_consistency must be at least 7",
        ),
        "complete_critique_rewrite": (
            run_report["rewrite_target_alignment"] == 1
            and run_report["artifact_completion_rate"] == 1,
            "rewrite target and artifacts must be complete",
        ),
        "carry_unresolved_threads": (
            judge_dimensions["continuity"] >= 7
            and int(run_report.get("continuity_failures", 0)) == 0,
            "continuity judge must pass without continuity failures",
        ),
        "required_context_recall": (
            run_report["required_context_recall"] == 1,
            "all required context must be selected",
        ),
        "evidence_backed_memory": (
            run_report["unsupported_memory_rate"] == 0
            and run_report["invalid_evidence_ref_count"] == 0,
            "all semantic memory must reference an existing artifact",
        ),
        "rewrite_target_alignment": (
            run_report["rewrite_target_alignment"] == 1,
            "rewrite target must match the weakest critique dimension",
        ),
        "originality_not_template": (
            judge_dimensions["originality"] >= 7,
            "judge originality must be at least 7",
        ),
    }
    results: dict[str, dict[str, Any]] = {}
    for contract in expected_contracts:
        if contract not in checks:
            results[contract] = {
                "passed": False,
                "reason": "unknown expected contract",
            }
            continue
        passed, reason = checks[contract]
        results[contract] = {"passed": passed, "reason": reason}
    return results


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
        "## Ablation Summary",
    ]
    for item in report["ablation_summary"]:
        lines.append(
            f"- {item['mode']}: completion_rate={item['completion_rate']:.4f}, "
            f"judge={item['average_judge_score']:.2f}, "
            f"originality={item['average_originality_score']:.2f}, "
            f"contract_pass_rate={item['contract_pass_rate']:.4f}, "
            f"memory_recall_rate={item['memory_recall_rate']:.4f}, "
            f"memory_compression_ratio={item['memory_compression_ratio']:.4f}, "
            f"unsupported_memory_rate={item['unsupported_memory_rate']:.4f}, "
            f"provider_tokens={item['provider_total_tokens']:.0f}, "
            f"regulation_actions={item['regulation_action_counts']}"
        )
    lines.extend(
        [
            "",
            "## Ablation Runs",
        ]
    )
    for item in report["ablation_runs"]:
        lines.append(
            f"- {item['case_id']} / {item['mode']}: success={item['success']}, "
            f"judge={item['judge_score']:.2f}, completion={item['stage_completion_rate']:.2f}, "
            f"tokens={item['average_tokens']}, latency={item['latency_seconds']:.3f}s, "
            f"interventions={item['layer_intervention_count']}"
        )
    pairwise_summary = report["pairwise_summary"]
    lines.extend(
        [
            "",
            "## Pairwise Summary",
            f"- comparison_count: {pairwise_summary['comparison_count']}",
            f"- tie_rate: {pairwise_summary['tie_rate']}",
            f"- mode_win_rate: {pairwise_summary['mode_win_rate']}",
            f"- dimension_win_rate: {pairwise_summary['dimension_win_rate']}",
            "",
            "## Pairwise",
        ]
    )
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
        regulation_action_counts: dict[str, int] = {}
        for item in selected:
            for action, action_count in item["regulation_action_counts"].items():
                regulation_action_counts[action] = (
                    regulation_action_counts.get(action, 0) + int(action_count)
                )
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
                "average_originality_score": round(
                    sum(float(item["judge_dimensions"]["originality"]) for item in selected)
                    / count,
                    2,
                ),
                "contract_pass_rate": round(
                    sum(float(item["contract_pass_rate"]) for item in selected) / count,
                    4,
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
                "average_provider_input_tokens": round(
                    sum(int(item["provider_input_tokens"]) for item in selected) / count,
                    2,
                ),
                "average_provider_output_tokens": round(
                    sum(int(item["provider_output_tokens"]) for item in selected) / count,
                    2,
                ),
                "provider_total_tokens": round(
                    sum(
                        int(item["provider_input_tokens"])
                        + int(item["provider_output_tokens"])
                        for item in selected
                    )
                    / count,
                    2,
                ),
                "average_latency": round(
                    sum(float(item["latency_seconds"]) for item in selected) / count,
                    4,
                ),
                "layer_intervention_count": sum(
                    int(item["layer_intervention_count"]) for item in selected
                ),
                "regulation_action_counts": dict(sorted(regulation_action_counts.items())),
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
        expected_contracts = [str(item) for item in case.get("expected_contracts", [])]
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
                "judge_dimensions": judge.dimensions.model_dump(),
                "average_tokens": trace["context_tokens"],
                "latency_seconds": round(latency, 4),
            }
            contract_results = _evaluate_expected_contracts(
                expected_contracts,
                run_report=run_report,
                judge_dimensions=judge.dimensions.model_dump(),
            )
            run_report["expected_contracts"] = expected_contracts
            run_report["contract_results"] = contract_results
            run_report["contract_pass_rate"] = (
                round(
                    sum(result["passed"] for result in contract_results.values())
                    / len(contract_results),
                    4,
                )
                if contract_results
                else 1.0
            )
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
