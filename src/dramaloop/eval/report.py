from datetime import datetime
from pathlib import Path

import yaml

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunManifest
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def build_single_run_report(run_dir: Path) -> dict:
    manifest = RunManifest.model_validate_json((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    critiques = [
        CritiqueArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(run_dir.glob("critique_v*.json"))
    ]
    return {
        "run_id": manifest.run_id,
        "status": manifest.status,
        "overall_scores": [item.overall_score for item in critiques],
        "weakest_dimensions": [item.weakest_dimensions[0] for item in critiques],
    }


def _render_dataset_report_markdown(aggregate: dict) -> str:
    lines = [
        "# MVP Eval Report",
        "",
        f"- case_count: {aggregate['case_count']}",
        f"- average_final_score: {aggregate['average_final_score']}",
        "",
        "## Runs",
    ]
    for report in aggregate["reports"]:
        lines.append(
            f"- {report['run_id']}: status={report['status']}, final_score={report['overall_scores'][-1]:.2f}"
        )
    return "\n".join(lines)


def run_dataset_eval(dataset_path: Path, settings: Settings) -> dict:
    cases = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
    reports = []
    for case in cases:
        request = StoryRequest.model_validate(case)
        result = run_story_pipeline(request, settings, build_llm_client(settings))
        reports.append(build_single_run_report(result.run_dir))
    aggregate = {
        "case_count": len(reports),
        "average_final_score": round(sum(item["overall_scores"][-1] for item in reports) / len(reports), 2),
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
