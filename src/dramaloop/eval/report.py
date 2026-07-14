from datetime import datetime
from pathlib import Path
import json

import yaml

from dramaloop.config import Settings
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.episode_critique import EpisodeCritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunManifest
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def build_single_run_report(run_dir: Path) -> dict:
    manifest = RunManifest.model_validate_json((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    critiques = [
        CritiqueArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(run_dir.glob("critique_v*.json"))
    ]
    success = manifest.status == "completed"
    return {
        "run_id": manifest.run_id,
        "status": manifest.status,
        "format": "single_story",
        "overall_scores": [item.overall_score for item in critiques],
        "weakest_dimensions": [item.weakest_dimensions[0] for item in critiques],
        "success": success,
        "completed_episodes": 1 if success else 0,
        "total_episodes": 1,
        "continuity_failures": 0,
        "episode_scores": [],
        "average_episode_score": 0.0,
    }


def build_episodic_run_report(run_dir: Path) -> dict:
    manifest = RunManifest.model_validate_json((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    critiques = [
        EpisodeCritiqueArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted((run_dir / "episodes").glob("episode_*_critique.json"))
    ]
    episode_scores = [item.overall_score for item in critiques]
    weakest_dimensions = [
        item.weakest_dimensions[0] for item in critiques if item.weakest_dimensions
    ]
    continuity_failures = 0
    events_path = run_dir / "events.jsonl"
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("stage") == "episode_generation" and payload.get("event") == "failed":
                continuity_failures += 1

    completed = manifest.completed_episodes or 0
    total = manifest.total_episodes or 0
    success = manifest.status == "completed" and completed == total and total > 0
    average_episode_score = (
        round(sum(episode_scores) / len(episode_scores), 2) if episode_scores else 0.0
    )
    return {
        "run_id": manifest.run_id,
        "status": manifest.status,
        "format": "episodic_series",
        "completed_episodes": completed,
        "total_episodes": total,
        "success": success,
        "continuity_failures": continuity_failures,
        "episode_scores": episode_scores,
        "average_episode_score": average_episode_score,
        "weakest_dimensions": weakest_dimensions,
        "overall_scores": episode_scores if episode_scores else [0.0],
    }


def _final_score_for_report(report: dict) -> float:
    if report.get("format") == "episodic_series":
        return float(report.get("average_episode_score") or 0.0)
    scores = report.get("overall_scores") or [0.0]
    return float(scores[-1])


def _completed_episode_ratio(report: dict) -> float:
    total = report.get("total_episodes") or 0
    if total <= 0:
        return 0.0
    completed = report.get("completed_episodes") or 0
    return completed / total


def _render_dataset_report_markdown(aggregate: dict) -> str:
    lines = [
        "# MVP Eval Report",
        "",
        f"- case_count: {aggregate['case_count']}",
        f"- success_rate: {aggregate['success_rate']}",
        f"- average_final_score: {aggregate['average_final_score']}",
        f"- average_completed_episode_ratio: {aggregate['average_completed_episode_ratio']}",
        "",
        "## Runs",
    ]
    for report in aggregate["reports"]:
        if report.get("format") == "episodic_series":
            lines.append(
                f"- {report['run_id']}: format=episodic_series, status={report['status']}, "
                f"success={report['success']}, avg_score={report['average_episode_score']:.2f}, "
                f"episodes={report['completed_episodes']}/{report['total_episodes']}, "
                f"continuity_failures={report['continuity_failures']}"
            )
        else:
            lines.append(
                f"- {report['run_id']}: format=single_story, status={report['status']}, "
                f"final_score={_final_score_for_report(report):.2f}"
            )
    return "\n".join(lines)


def run_dataset_eval(dataset_path: Path, settings: Settings) -> dict:
    cases = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
    reports = []
    for case in cases:
        request = StoryRequest.model_validate(case)
        client = build_llm_client(settings)
        if request.format == "episodic_series":
            result = run_episodic_pipeline(request, settings, client, controller=None)
            reports.append(build_episodic_run_report(result.run_dir))
        else:
            result = run_story_pipeline(request, settings, client)
            reports.append(build_single_run_report(result.run_dir))

    success_rate = (
        round(sum(1 for item in reports if item.get("success")) / len(reports), 2) if reports else 0.0
    )
    average_final_score = (
        round(sum(_final_score_for_report(item) for item in reports) / len(reports), 2) if reports else 0.0
    )
    average_completed_episode_ratio = (
        round(sum(_completed_episode_ratio(item) for item in reports) / len(reports), 2) if reports else 0.0
    )
    aggregate = {
        "case_count": len(reports),
        "success_rate": success_rate,
        "average_final_score": average_final_score,
        "average_completed_episode_ratio": average_completed_episode_ratio,
        "reports": reports,
    }
    reports_dir = settings.evals_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    write_json_artifact(reports_dir / f"{stamp}-mvp-eval-report.json", aggregate)
    write_markdown_artifact(
        reports_dir / f"{stamp}-mvp-eval-report.md",
        _render_dataset_report_markdown(aggregate),
    )
    return aggregate
