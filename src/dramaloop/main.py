from pathlib import Path

import typer
import yaml

from dramaloop.config import Settings
from dramaloop.eval.report import build_single_run_report, run_dataset_eval
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest


app = typer.Typer(no_args_is_help=True, help="Dramaloop short-drama generation CLI")


def _load_request(
    input_path: Path | None,
    idea: str | None,
    style: list[str],
    audience: str | None,
    constraint: list[str],
) -> StoryRequest:
    if input_path is not None:
        payload = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        return StoryRequest.model_validate(payload)
    if idea is None or not style:
        raise typer.BadParameter("Provide --input or provide --idea with at least one --style")
    return StoryRequest(idea=idea, style=style, length="short", audience=audience, constraints=constraint)


def _format_single_run_report(report: dict) -> str:
    scores = ", ".join(f"v{index + 1}={score:.2f}" for index, score in enumerate(report["overall_scores"]))
    weakest = ", ".join(report["weakest_dimensions"])
    return "\n".join(
        [
            f"run_id: {report['run_id']}",
            f"status: {report['status']}",
            f"overall_scores: {scores}",
            f"weakest_dimensions: {weakest}",
        ]
    )


def _format_dataset_report(report: dict) -> str:
    lines = [
        f"case_count: {report['case_count']}",
        f"average_final_score: {report['average_final_score']:.2f}",
        "reports:",
    ]
    for item in report["reports"]:
        lines.append(f"- {item['run_id']}: final_score={item['overall_scores'][-1]:.2f}")
    return "\n".join(lines)


@app.command()
def run(
    input: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False),
    idea: str | None = typer.Option(default=None),
    style: list[str] = typer.Option(default_factory=list),
    audience: str | None = typer.Option(default=None),
    constraint: list[str] = typer.Option(default_factory=list),
) -> None:
    settings = Settings()
    request = _load_request(input, idea, style, audience, constraint)
    client = build_llm_client(settings)
    result = run_story_pipeline(request, settings, client)
    typer.echo(str(result.run_dir))


@app.command()
def inspect(run_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)) -> None:
    typer.echo(_format_single_run_report(build_single_run_report(run_dir)))


@app.command(name="eval")
def eval_command(
    run: Path | None = typer.Option(default=None, exists=True, file_okay=False, dir_okay=True),
    dataset: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False),
) -> None:
    settings = Settings()
    if run is not None:
        typer.echo(_format_single_run_report(build_single_run_report(run)))
        raise typer.Exit(code=0)
    if dataset is None:
        raise typer.BadParameter("Provide --run or --dataset")
    typer.echo(_format_dataset_report(run_dataset_eval(dataset, settings)))
