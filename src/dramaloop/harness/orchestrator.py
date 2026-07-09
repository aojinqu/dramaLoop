from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.context import PipelineContext
from dramaloop.harness.loop import determine_stop_reason, should_continue_loop
from dramaloop.harness.stages import (
    run_character_stage,
    run_critique_stage,
    run_draft_stage,
    run_outline_stage,
    run_premise_stage,
    run_rewrite_stage,
)
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent, RunManifest, RunResult
from dramaloop.storage.artifacts import append_event, write_json_artifact, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files, reserve_run_id
from dramaloop.utils.markdown import render_run_summary


def build_running_manifest(run_id: str, settings: Settings, request: StoryRequest, started_at: datetime) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        status="running",
        started_at=started_at.isoformat(),
        model_provider=settings.provider,
        model_name=settings.model_name,
        max_iterations=request.max_iterations,
        target_threshold=settings.target_threshold,
        minimum_dimension_threshold=settings.minimum_dimension_threshold,
        min_delta=settings.min_delta,
    )


def _record_stage_event(
    run_events_path,
    stage: str,
    event: str,
    *,
    iteration: int | None = None,
    artifact: str | None = None,
    detail: str | None = None,
) -> None:
    append_event(
        run_events_path,
        RunEvent(
            ts=datetime.now().isoformat(),
            stage=stage,
            event=event,
            iteration=iteration,
            artifact=artifact,
            detail=detail,
        ),
    )


def run_story_pipeline(request: StoryRequest, settings: Settings, client: LLMClient, started_at: datetime | None = None) -> RunResult:
    started_at = started_at or datetime.now()
    base_run_id = build_run_id(request.idea, started_at)
    run_id = reserve_run_id(settings.runs_dir, base_run_id)
    run_paths = create_run_paths(settings.runs_dir, run_id)
    manifest = build_running_manifest(run_id, settings, request, started_at)
    initialize_run_files(run_paths, request, manifest)
    context = PipelineContext(request=request, run_paths=run_paths)
    stop_reason = "max_iterations_reached"

    try:
        _record_stage_event(run_paths.events_path, "run", "started", detail=f"run_id={run_id}")

        _record_stage_event(run_paths.events_path, "premise_refinement", "started")
        context.premise = run_premise_stage(client, request)
        write_json_artifact(run_paths.root / "premise.json", context.premise)
        _record_stage_event(run_paths.events_path, "premise_refinement", "completed", artifact="premise.json")

        _record_stage_event(run_paths.events_path, "character_card_generation", "started")
        context.characters = run_character_stage(client, context.premise)
        write_json_artifact(run_paths.root / "characters.json", context.characters)
        _record_stage_event(run_paths.events_path, "character_card_generation", "completed", artifact="characters.json")

        _record_stage_event(run_paths.events_path, "story_outline_generation", "started")
        context.outline = run_outline_stage(client, context.premise, context.characters)
        write_json_artifact(run_paths.root / "outline.json", context.outline)
        _record_stage_event(run_paths.events_path, "story_outline_generation", "completed", artifact="outline.json")

        _record_stage_event(run_paths.events_path, "draft_generation", "started", iteration=1)
        draft = run_draft_stage(client, context.premise, context.characters, context.outline)
        context.drafts.append(draft)
        write_markdown_artifact(run_paths.root / "draft_v1.md", draft)
        _record_stage_event(run_paths.events_path, "draft_generation", "completed", iteration=1, artifact="draft_v1.md")

        previous_score = None
        current_iteration = 1
        while True:
            _record_stage_event(run_paths.events_path, "critique_scoring", "started", iteration=current_iteration)
            critique = run_critique_stage(client, context.drafts[-1], context.premise, context.characters, context.outline)
            context.critiques.append(critique)
            write_json_artifact(run_paths.root / f"critique_v{current_iteration}.json", critique)
            _record_stage_event(run_paths.events_path, "critique_scoring", "completed", iteration=current_iteration, artifact=f"critique_v{current_iteration}.json")

            stop_reason = determine_stop_reason(previous_score, critique, settings, current_iteration, request.max_iterations) or stop_reason
            if not should_continue_loop(previous_score, critique, settings, current_iteration, request.max_iterations):
                break

            _record_stage_event(
                run_paths.events_path,
                "targeted_rewrite",
                "started",
                iteration=current_iteration,
                detail=f"target={critique.rewrite_target}",
            )
            rewrite_artifact, next_draft = run_rewrite_stage(
                client,
                context.drafts[-1],
                critique,
                context.premise,
                context.characters,
                context.outline,
                next_version=current_iteration + 1,
            )
            context.rewrites.append(rewrite_artifact)
            write_json_artifact(run_paths.root / f"rewrite_plan_v{current_iteration}.json", rewrite_artifact)
            _record_stage_event(run_paths.events_path, "artifact_write", "completed", iteration=current_iteration, artifact=f"rewrite_plan_v{current_iteration}.json")
            context.drafts.append(next_draft)
            write_markdown_artifact(run_paths.root / f"draft_v{current_iteration + 1}.md", next_draft)
            _record_stage_event(
                run_paths.events_path,
                "targeted_rewrite",
                "completed",
                iteration=current_iteration,
                artifact=f"draft_v{current_iteration + 1}.md",
            )
            previous_score = critique.overall_score
            current_iteration += 1

        final_story_path = run_paths.root / "final_story.md"
        write_markdown_artifact(final_story_path, context.drafts[-1])
        _record_stage_event(run_paths.events_path, "final_assembly", "completed", artifact="final_story.md")
        summary_path = run_paths.root / "run_summary.md"
        write_markdown_artifact(
            summary_path,
            render_run_summary(
                request=request,
                critique_history=context.critiques,
                rewrite_history=context.rewrites,
                final_story_path="final_story.md",
                stop_reason=stop_reason,
            ),
        )
        _record_stage_event(run_paths.events_path, "final_assembly", "completed", artifact="run_summary.md", detail=f"stop_reason={stop_reason}")
        manifest.status = "completed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.completed_iterations = len(context.critiques)
        manifest.final_artifact = "final_story.md"
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "completed", artifact="final_story.md")
        return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=summary_path)
    except Exception as exc:
        manifest.status = "failed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.error_message = str(exc)
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "failed", detail=str(exc))
        raise
