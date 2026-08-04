import json
from pathlib import Path
from typing import Any

from dramaloop.harness.trajectory import TrajectoryRegulator
from dramaloop.harness.stage_graph import stage_names_for_format
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.memory import RunMemory
from dramaloop.schemas.run import RunManifest


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _ratio(numerator: int | float, denominator: int | float, *, empty: float = 1.0) -> float:
    if denominator == 0:
        return empty
    return round(numerator / denominator, 4)


def _required_artifacts(manifest: RunManifest, request: StoryRequest) -> list[str]:
    common = [
        "request.json",
        "run_manifest.json",
        "events.jsonl",
        "final_story.md",
        "run_summary.md",
    ]
    if manifest.format == "episodic_series":
        episodic = ["season_bible.json", "episode_plan.json", "continuity_state.json"]
        for number in range(1, (manifest.total_episodes or 0) + 1):
            episodic.extend(
                [
                    f"episodes/episode_{number:02d}.json",
                    f"episodes/episode_{number:02d}.md",
                ]
            )
            if request.enable_episode_critique:
                episodic.append(f"episodes/episode_{number:02d}_critique.json")
        return [*common, *episodic]
    single = [
        *common,
        "premise.json",
        "characters.json",
        "outline.json",
    ]
    iterations = max(1, manifest.completed_iterations)
    for version in range(1, iterations + 1):
        single.extend([f"draft_v{version}.md", f"critique_v{version}.json"])
        if version < iterations:
            single.append(f"rewrite_plan_v{version}.json")
    return single


def _expected_stages(run_dir: Path, request: StoryRequest) -> set[str]:
    registered = set(stage_names_for_format(request.format))
    if request.format == "episodic_series":
        expected = {
            "season_planning",
            "episode_plan_generation",
            "episode_draft_generation",
            "final_assembly",
        }
        if request.enable_episode_critique:
            expected.add("episode_critique_scoring")
        if any(
            payload.get("rewrite_applied")
            for path in (run_dir / "episodes").glob("episode_[0-9][0-9].json")
            if isinstance(
                payload := json.loads(path.read_text(encoding="utf-8")),
                dict,
            )
        ):
            expected.add("episode_targeted_rewrite")
        return expected & registered
    expected = {
        "premise_refinement",
        "character_card_generation",
        "story_outline_generation",
        "draft_generation",
        "critique_scoring",
        "final_assembly",
    }
    if any(run_dir.glob("rewrite_plan_v*.json")):
        expected.add("targeted_rewrite")
    return expected & registered


def evaluate_run_trace(run_dir: Path) -> dict[str, float | int]:
    manifest = RunManifest.model_validate_json(
        (run_dir / "run_manifest.json").read_text(encoding="utf-8")
    )
    request = StoryRequest.model_validate_json(
        (run_dir / "request.json").read_text(encoding="utf-8")
    )
    memory = RunMemory.model_validate_json(
        (run_dir / "run_memory.json").read_text(encoding="utf-8")
    )
    stage_events = _read_jsonl(run_dir / "stage_trace.jsonl")
    context_events = _read_jsonl(run_dir / "context_trace.jsonl")
    realization_events = _read_jsonl(run_dir / "realization_trace.jsonl")
    trajectory_events = _read_jsonl(run_dir / "trajectory_trace.jsonl")
    skill_events = _read_jsonl(run_dir / "skill_trace.jsonl")

    completed = {event.get("stage") for event in stage_events if event.get("event") == "completed"}
    expected_stages = _expected_stages(run_dir, request)

    realization_statuses = [
        event.get("status")
        for event in realization_events
        if event.get("event") == "output_realized"
    ]
    valid_realizations = sum(
        status in {"accepted", "repaired", "retried"} for status in realization_statuses
    )

    selected_items = [
        item
        for event in context_events
        for item in event.get("selected_items", [])
        if isinstance(item, dict)
    ]
    dropped_items = [
        item
        for event in context_events
        for item in event.get("dropped_items", [])
        if isinstance(item, dict)
    ]
    required_selected = sum(bool(item.get("required")) for item in selected_items)
    required_dropped = sum(bool(item.get("required")) for item in dropped_items)

    memory_ids = {item.id for item in [*memory.episode_memories, *memory.semantic_facts]}
    recalled_ids = {
        item_id
        for event in context_events
        for item_id in event.get("memory_refs", [])
        if item_id in memory_ids
    }
    unsupported = sum(not item.evidence_refs for item in memory.semantic_facts)

    artifact_bytes = sum(
        path.stat().st_size
        for path in run_dir.rglob("*")
        if path.is_file()
        and path.name
        not in {
            "run_memory.json",
            "memory_trace.jsonl",
            "stage_trace.jsonl",
            "context_trace.jsonl",
            "decision_trace.jsonl",
            "skill_trace.jsonl",
            "realization_trace.jsonl",
            "trajectory_trace.jsonl",
        }
    )
    compressed_chars = sum(
        len(item.content)
        for item in [
            *memory.raw_artifacts,
            *memory.episode_memories,
            *memory.semantic_facts,
        ]
    )

    skill_selections = {
        skill_id for event in skill_events for skill_id in event.get("skill_ids", [])
    }
    skill_evaluations = {
        evaluation.get("skill_id"): bool(evaluation.get("trigger_matched"))
        for event in skill_events
        for evaluation in event.get("evaluations", [])
        if isinstance(evaluation, dict)
    }
    valid_skill_selections = sum(
        skill_evaluations.get(skill_id, False) for skill_id in skill_selections
    )

    rewrite_checks: list[bool] = []
    regulator = TrajectoryRegulator()
    for rewrite_path in sorted(run_dir.glob("rewrite_plan_v*.json")):
        version = rewrite_path.stem.rsplit("v", 1)[-1]
        critique_path = run_dir / f"critique_v{version}.json"
        if not critique_path.exists():
            rewrite_checks.append(False)
            continue
        rewrite = json.loads(rewrite_path.read_text(encoding="utf-8"))
        critique = json.loads(critique_path.read_text(encoding="utf-8"))
        weakest = (critique.get("weakest_dimensions") or [""])[0]
        rewrite_checks.append(
            rewrite.get("target_section") == regulator.target_for_dimension(weakest)
        )

    required_artifacts = _required_artifacts(manifest, request)
    existing_artifacts = sum((run_dir / relative).exists() for relative in required_artifacts)
    return {
        "stage_completion_rate": _ratio(
            len(completed & expected_stages),
            len(expected_stages),
        ),
        "schema_valid_rate": _ratio(valid_realizations, len(realization_statuses)),
        "required_context_recall": _ratio(
            required_selected,
            required_selected + required_dropped,
        ),
        "memory_recall_rate": _ratio(len(recalled_ids), len(memory_ids), empty=0.0),
        "memory_compression_ratio": round(compressed_chars / artifact_bytes, 4)
        if artifact_bytes
        else 0.0,
        "unsupported_memory_rate": _ratio(
            unsupported,
            len(memory.semantic_facts),
            empty=0.0,
        ),
        "skill_trigger_precision": _ratio(
            valid_skill_selections,
            len(skill_selections),
        ),
        "realization_repair_rate": _ratio(
            realization_statuses.count("repaired"),
            len(realization_statuses),
            empty=0.0,
        ),
        "realization_block_rate": _ratio(
            realization_statuses.count("blocked"),
            len(realization_statuses),
            empty=0.0,
        ),
        "rewrite_target_alignment": _ratio(
            sum(rewrite_checks),
            len(rewrite_checks),
        ),
        "artifact_completion_rate": _ratio(
            existing_artifacts,
            len(required_artifacts),
        ),
        "context_tokens": sum(int(item.get("tokens_estimated", 0)) for item in selected_items),
        "context_budget_overflow_tokens": sum(
            int(event.get("budget_overflow_tokens", 0)) for event in context_events
        ),
        "dropped_context_items": len(dropped_items),
        "layer_intervention_count": sum(
            status in {"repaired", "retried", "blocked"} for status in realization_statuses
        )
        + sum(
            event.get("action") in {"rewrite", "retry_stage", "stop"}
            for event in trajectory_events
            if event.get("event") == "regulation_decision"
        ),
    }
