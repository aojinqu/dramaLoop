import json
from datetime import datetime
from pathlib import Path
import threading
import time
from typing import Literal, cast

import typer
import yaml

from dramaloop.config import Settings
from dramaloop.eval.report import build_single_run_report, run_dataset_eval
from dramaloop.harness.episodic_orchestrator import run_episodic_pipeline
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent, RunResult
from dramaloop.storage.runs import plan_run_id


app = typer.Typer(no_args_is_help=True, help="Dramaloop short-drama generation CLI")


def _load_request(
    input_path: Path | None,
    idea: str | None,
    style: list[str],
    audience: str | None,
    constraint: list[str],
    request_format: str | None,
    episode_count: int | None,
    episode_min_words: int | None,
    episode_max_words: int | None,
) -> StoryRequest:
    if input_path is not None:
        payload = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        if request_format is not None:
            payload["format"] = request_format
        if episode_count is not None:
            payload["episode_count"] = episode_count
        if episode_min_words is not None:
            payload["episode_min_words"] = episode_min_words
        if episode_max_words is not None:
            payload["episode_max_words"] = episode_max_words
        return StoryRequest.model_validate(payload)
    if idea is None or not style:
        raise typer.BadParameter("Provide --input or provide --idea with at least one --style")
    return StoryRequest(
        idea=idea,
        style=style,
        length="short",
        format=cast(
            Literal["single_story", "episodic_series"],
            request_format or "single_story",
        ),
        audience=audience,
        constraints=constraint,
        episode_count=episode_count or 12,
        episode_min_words=episode_min_words or 500,
        episode_max_words=episode_max_words or 800,
    )


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
        f"success_rate: {report.get('success_rate', 0):.2f}",
        f"average_final_score: {report['average_final_score']:.2f}",
        f"average_completed_episode_ratio: {report.get('average_completed_episode_ratio', 0):.2f}",
        "reports:",
    ]
    for item in report["reports"]:
        if item.get("format") == "episodic_series":
            lines.append(
                f"- {item['run_id']}: format=episodic_series success={item.get('success')} "
                f"avg_score={item.get('average_episode_score', 0):.2f} "
                f"episodes={item.get('completed_episodes', 0)}/{item.get('total_episodes', 0)}"
            )
        else:
            scores = item.get("overall_scores") or [0.0]
            lines.append(f"- {item['run_id']}: final_score={scores[-1]:.2f}")
    return "\n".join(lines)


def _format_stream_event(event: RunEvent, run_format: str) -> str | None:
    if event.stage == "run":
        if event.event == "started":
            return f"[run] started {event.detail or ''}".strip()
        if event.event == "completed":
            return "[run] completed"
        if event.event == "failed":
            return f"[run] failed: {event.detail or 'unknown error'}"

    if run_format == "episodic_series":
        if event.stage == "season_planning" and event.event == "completed":
            return "[season] season_bible.json ready"
        if event.stage == "episode_plan_generation" and event.event == "completed":
            return "[season] episode_plan.json ready"
        if event.stage == "episode_generation":
            if event.event == "started":
                return f"[episode {event.iteration}] generating"
            if event.event == "completed":
                return f"[episode {event.iteration}] completed -> {event.artifact}"
            if event.event == "failed":
                return f"[episode {event.iteration}] failed: {event.detail or 'unknown error'}"
        if event.stage == "final_assembly":
            if event.event == "started":
                return "[final] assembling final story"
            if event.event == "completed":
                return f"[final] completed -> {event.artifact}"
        return None

    if event.event == "started":
        suffix = f" v{event.iteration}" if event.iteration is not None else ""
        return f"[{event.stage}] started{suffix}"
    if event.event == "completed":
        artifact = f" -> {event.artifact}" if event.artifact else ""
        suffix = f" v{event.iteration}" if event.iteration is not None else ""
        return f"[{event.stage}] completed{suffix}{artifact}"
    if event.event == "failed":
        return f"[{event.stage}] failed: {event.detail or 'unknown error'}"
    return None


def _stream_run_progress(run_dir: Path, request: StoryRequest, worker: threading.Thread) -> None:
    events_path = run_dir / "events.jsonl"
    seen_lines = 0

    while worker.is_alive():
        if events_path.exists():
            lines = events_path.read_text(encoding="utf-8").splitlines()
            for raw_line in lines[seen_lines:]:
                payload = RunEvent.model_validate(json.loads(raw_line))
                message = _format_stream_event(payload, request.format)
                if message:
                    typer.echo(message)
            seen_lines = len(lines)
        time.sleep(0.1)

    if events_path.exists():
        lines = events_path.read_text(encoding="utf-8").splitlines()
        for raw_line in lines[seen_lines:]:
            payload = RunEvent.model_validate(json.loads(raw_line))
            message = _format_stream_event(payload, request.format)
            if message:
                typer.echo(message)


@app.command()
def run(
    input: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False),
    idea: str | None = typer.Option(default=None),
    style: list[str] = typer.Option(default_factory=list),
    audience: str | None = typer.Option(default=None),
    constraint: list[str] = typer.Option(default_factory=list),
    format: str | None = typer.Option(default=None, help="single_story or episodic_series"),
    episode_count: int | None = typer.Option(default=None, min=1, max=12),
    episode_min_words: int | None = typer.Option(default=None, min=100),
    episode_max_words: int | None = typer.Option(default=None, min=100),
    stream: bool = typer.Option(default=True, help="Stream stage progress while the run is executing."),
) -> None:
    settings = Settings()
    request = _load_request(
        input,
        idea,
        style,
        audience,
        constraint,
        format,
        episode_count,
        episode_min_words,
        episode_max_words,
    )
    client = build_llm_client(settings)
    target = run_episodic_pipeline if request.format == "episodic_series" else run_story_pipeline
    if not stream:
        result = target(request, settings, client)
        typer.echo(str(result.run_dir))
        return

    started_at = datetime.now()
    run_id = plan_run_id(settings.runs_dir, request.idea, started_at)
    run_dir = settings.runs_dir / run_id
    holder: dict[str, object] = {}

    def _worker() -> None:
        try:
            holder["result"] = target(request, settings, client, started_at, run_id)
        except Exception as exc:  # pragma: no cover - integration behavior
            holder["error"] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    typer.echo(f"[run] output directory: {run_dir}")
    worker.start()
    _stream_run_progress(run_dir, request, worker)
    worker.join()

    if "error" in holder:
        raise holder["error"]  # type: ignore[misc]
    streamed_result = holder["result"]
    assert isinstance(streamed_result, RunResult)
    typer.echo(str(streamed_result.run_dir))


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


@app.command()
def web(
    host: str = typer.Option(default="127.0.0.1"),
    port: int = typer.Option(default=8000),
    reload: bool = typer.Option(default=False),
) -> None:
    import uvicorn

    uvicorn.run(
        "dramaloop.web.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
