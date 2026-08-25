from datetime import datetime

from dramaloop.config import Settings
from dramaloop.eval.scorer import calculate_overall_score
from dramaloop.harness.context import PipelineContext
from dramaloop.harness.loop import determine_stop_reason, should_continue_loop
from dramaloop.harness.realization import validate_rewrite_coverage
from dramaloop.harness.runtime import HarnessedLLMClient, HarnessRuntime
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
from dramaloop.harness.trajectory import TrajectoryRegulator


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


def run_story_pipeline(
    request: StoryRequest,
    settings: Settings,
    client: LLMClient,
    started_at: datetime | None = None,
    run_id: str | None = None,
) -> RunResult:
    started_at = started_at or datetime.now()
    if run_id is None:
        base_run_id = build_run_id(request.idea, started_at)
        run_id = reserve_run_id(settings.runs_dir, base_run_id)
    run_paths = create_run_paths(settings.runs_dir, run_id)
    manifest = build_running_manifest(run_id, settings, request, started_at)
    initialize_run_files(run_paths, request, manifest)
    context = PipelineContext(request=request, run_paths=run_paths)
    runtime = HarnessRuntime(
        run_root=run_paths.root,
        run_id=run_id,
        request=request,
        settings=settings,
    )
    client = HarnessedLLMClient(client, runtime)
    regulator = TrajectoryRegulator(max_rewrites=1)
    stop_reason = "max_iterations_reached"

    try:
        _record_stage_event(run_paths.events_path, "run", "started", detail=f"run_id={run_id}")

        _record_stage_event(run_paths.events_path, "premise_refinement", "started")
        context.premise = run_premise_stage(client, request)
        write_json_artifact(run_paths.root / "premise.json", context.premise)
        runtime.record_artifact(
            stage="premise_refinement",
            artifact_ref="premise.json",
            payload=context.premise,
        )
        _record_stage_event(run_paths.events_path, "premise_refinement", "completed", artifact="premise.json")

        _record_stage_event(run_paths.events_path, "character_card_generation", "started")
        context.characters = run_character_stage(client, context.premise)
        write_json_artifact(run_paths.root / "characters.json", context.characters)
        runtime.record_artifact(
            stage="character_card_generation",
            artifact_ref="characters.json",
            payload=context.characters,
        )
        _record_stage_event(run_paths.events_path, "character_card_generation", "completed", artifact="characters.json")

        _record_stage_event(run_paths.events_path, "story_outline_generation", "started")
        context.outline = run_outline_stage(client, context.premise, context.characters)
        write_json_artifact(run_paths.root / "outline.json", context.outline)
        runtime.record_artifact(
            stage="story_outline_generation",
            artifact_ref="outline.json",
            payload=context.outline,
        )
        _record_stage_event(run_paths.events_path, "story_outline_generation", "completed", artifact="outline.json")

        _record_stage_event(run_paths.events_path, "draft_generation", "started", iteration=1)
        draft = run_draft_stage(client, context.premise, context.characters, context.outline)
        context.drafts.append(draft)
        write_markdown_artifact(run_paths.root / "draft_v1.md", draft)
        runtime.record_artifact(
            stage="draft_generation",
            artifact_ref="draft_v1.md",
            payload=draft,
        )
        _record_stage_event(run_paths.events_path, "draft_generation", "completed", iteration=1, artifact="draft_v1.md")

        previous_score = None
        current_iteration = 1
        while True:
            _record_stage_event(run_paths.events_path, "critique_scoring", "started", iteration=current_iteration)
            critique = run_critique_stage(client, context.drafts[-1], context.premise, context.characters, context.outline)
            critique = critique.model_copy(
                update={"overall_score": calculate_overall_score(critique)}
            )
            stop_reason = determine_stop_reason(previous_score, critique, settings, current_iteration, request.max_iterations) or stop_reason
            should_rewrite = should_continue_loop(
                previous_score,
                critique,
                settings,
                current_iteration,
                request.max_iterations,
            )
            regulation = regulator.decide_rewrite(
                stage="targeted_rewrite",
                rewrite_needed=should_rewrite,
                rewrite_count=len(context.rewrites),
            )
            if runtime.regulation_enabled:
                runtime.record_regulation(regulation)
                should_rewrite = regulation.action == "rewrite"
                if regulation.action == "stop":
                    stop_reason = "trajectory_rewrite_limit_reached"

            if should_rewrite and runtime.regulation_enabled:
                alignment = regulator.align_rewrite_target(
                    stage="targeted_rewrite",
                    weakest_dimensions=list(critique.weakest_dimensions),
                    rewrite_target=critique.rewrite_target,
                )
                runtime.record_regulation(alignment)
                if alignment.action == "rewrite":
                    critique = critique.model_copy(
                        update={
                            "rewrite_target": regulator.target_for_dimension(
                                critique.weakest_dimensions[0]
                            )
                        }
                    )

            context.critiques.append(critique)
            write_json_artifact(run_paths.root / f"critique_v{current_iteration}.json", critique)
            runtime.record_artifact(
                stage="critique_scoring",
                artifact_ref=f"critique_v{current_iteration}.json",
                payload=critique,
            )
            _record_stage_event(run_paths.events_path, "critique_scoring", "completed", iteration=current_iteration, artifact=f"critique_v{current_iteration}.json")

            if not should_rewrite:
                runtime.record_decision(
                    stage="critique_scoring",
                    action="stop",
                    reason=stop_reason,
                    layer="orchestrator",
                )
                break

            _record_stage_event(
                run_paths.events_path,
                "targeted_rewrite",
                "started",
                iteration=current_iteration,
                detail=f"target={critique.rewrite_target}",
            )
            source_draft = context.drafts[-1]
            rewrite_artifact, next_draft = run_rewrite_stage(
                client,
                source_draft,
                critique,
                context.premise,
                context.characters,
                context.outline,
                next_version=current_iteration + 1,
            )
            if runtime.realization_enabled:
                rewrite_realization = validate_rewrite_coverage(
                    source_draft,
                    next_draft,
                    rewrite_target=critique.rewrite_target,
                )
                runtime.record_realization(rewrite_realization)
                if rewrite_realization.status == "blocked":
                    retry_reason = "; ".join(rewrite_realization.issues)
                    retry_plan = critique.rewrite_plan.model_copy(
                        update={
                            "must_fix": [
                                *critique.rewrite_plan.must_fix,
                                f"上一次改写未覆盖目标：{retry_reason}",
                            ]
                        }
                    )
                    retry_critique = critique.model_copy(
                        update={"rewrite_plan": retry_plan}
                    )
                    rewrite_artifact, next_draft = run_rewrite_stage(
                        client,
                        source_draft,
                        retry_critique,
                        context.premise,
                        context.characters,
                        context.outline,
                        next_version=current_iteration + 1,
                    )
                    retried_realization = validate_rewrite_coverage(
                        source_draft,
                        next_draft,
                        rewrite_target=critique.rewrite_target,
                    )
                    if retried_realization.status == "blocked":
                        runtime.record_realization(retried_realization)
                        raise RuntimeError("; ".join(retried_realization.issues))
                    runtime.record_realization(
                        retried_realization.model_copy(
                            update={
                                "status": "retried",
                                "issues": rewrite_realization.issues,
                                "retry_reason": retry_reason,
                            }
                        )
                    )
            context.rewrites.append(rewrite_artifact)
            write_json_artifact(run_paths.root / f"rewrite_plan_v{current_iteration}.json", rewrite_artifact)
            runtime.record_artifact(
                stage="targeted_rewrite",
                artifact_ref=f"rewrite_plan_v{current_iteration}.json",
                payload=rewrite_artifact,
            )
            _record_stage_event(run_paths.events_path, "artifact_write", "completed", iteration=current_iteration, artifact=f"rewrite_plan_v{current_iteration}.json")
            context.drafts.append(next_draft)
            write_markdown_artifact(run_paths.root / f"draft_v{current_iteration + 1}.md", next_draft)
            runtime.record_artifact(
                stage="targeted_rewrite",
                artifact_ref=f"draft_v{current_iteration + 1}.md",
                payload=next_draft,
            )
            _record_stage_event(
                run_paths.events_path,
                "targeted_rewrite",
                "completed",
                iteration=current_iteration,
                artifact=f"draft_v{current_iteration + 1}.md",
            )
            previous_score = critique.overall_score
            current_iteration += 1

        runtime.prepare_prompt("final_assembly", "")
        final_story_path = run_paths.root / "final_story.md"
        write_markdown_artifact(final_story_path, context.drafts[-1])
        runtime.record_artifact(
            stage="final_assembly",
            artifact_ref="final_story.md",
            payload=context.drafts[-1],
        )
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
        runtime.record_artifact(
            stage="final_assembly",
            artifact_ref="run_summary.md",
            payload=summary_path.read_text(encoding="utf-8"),
        )
        runtime.complete_stage("final_assembly")
        _record_stage_event(run_paths.events_path, "final_assembly", "completed", artifact="run_summary.md", detail=f"stop_reason={stop_reason}")
        manifest.status = "completed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.completed_iterations = len(context.critiques)
        manifest.final_artifact = "final_story.md"
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "completed", artifact="final_story.md")
        runtime.finalize("completed", reason=stop_reason)
        return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=summary_path)
    except Exception as exc:
        manifest.status = "failed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.error_message = str(exc)
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "failed", detail=str(exc))
        runtime.finalize("failed", reason=str(exc))
        raise
