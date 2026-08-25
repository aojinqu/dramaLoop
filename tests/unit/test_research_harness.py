import json
from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import BaseModel

from dramaloop.config import Settings
from dramaloop.harness.context import build_context_pack
from dramaloop.harness.episodic_orchestrator import (
    continue_episodic_run,
    regenerate_episode,
    run_episodic_pipeline,
)
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.harness.realization import realize_structured_output
from dramaloop.harness.runtime import HarnessedLLMClient, HarnessRuntime
from dramaloop.harness.stage_graph import get_stage_spec, list_stage_specs
from dramaloop.harness.trajectory import TrajectoryRegulator
from dramaloop.llm.mock import (
    DEFAULT_STRUCTURED_OUTPUTS,
    DEFAULT_TEXT_OUTPUTS,
    MockLLMClient,
    build_default_mock_client,
)
from dramaloop.schemas.context import ContextItem
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.memory import MemoryRecord
from dramaloop.schemas.premise import PremiseArtifact


class _RequiredOutput(BaseModel):
    title: str
    value: int


def _request() -> StoryRequest:
    return StoryRequest(
        idea="她在婚礼被抛弃后改嫁死对头",
        style=["都市情感"],
        length="short",
        constraints=["必须保留林晚与顾承骁的盟友关系"],
    )


def test_stage_registry_covers_single_and_episodic_stages() -> None:
    names = {spec.name for spec in list_stage_specs()}

    assert {
        "premise_refinement",
        "character_card_generation",
        "story_outline_generation",
        "draft_generation",
        "critique_scoring",
        "targeted_rewrite",
        "originality_mechanism_planning",
        "season_planning",
        "episode_plan_generation",
        "episode_draft_generation",
        "episode_critique_scoring",
        "episode_targeted_rewrite",
        "final_assembly",
    } <= names
    assert "draft" in get_stage_spec("critique_scoring").required_context
    assert "originality_plan" in get_stage_spec("season_planning").optional_context


def test_story_run_writes_harness_traces_and_evidence_backed_memory(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")

    result = run_story_pipeline(_request(), settings, build_default_mock_client())

    for filename in (
        "run_memory.json",
        "memory_trace.jsonl",
        "stage_trace.jsonl",
        "context_trace.jsonl",
        "decision_trace.jsonl",
        "skill_trace.jsonl",
        "realization_trace.jsonl",
        "trajectory_trace.jsonl",
    ):
        assert (result.run_dir / filename).exists()

    memory = json.loads((result.run_dir / "run_memory.json").read_text(encoding="utf-8"))
    assert memory["final_status"] == "completed"
    assert "premise_refinement" in memory["completed_stages"]
    assert memory["raw_artifacts"]
    assert memory["semantic_facts"]
    assert all(item["evidence_refs"] for item in memory["semantic_facts"])

    stage_events = [
        json.loads(line)
        for line in (result.run_dir / "stage_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert any(
        event["stage"] == "premise_refinement" and event["event"] == "completed"
        for event in stage_events
    )
    assert any(event.get("artifact") == "final_story.md" for event in stage_events)


def test_failed_run_writes_partial_memory(tmp_path: Path) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    client = MockLLMClient(structured_outputs={}, text_outputs={})

    with pytest.raises(Exception, match="Missing mock structured output"):
        run_story_pipeline(_request(), settings, client)

    run_dir = next((tmp_path / "runs").iterdir())
    memory = json.loads((run_dir / "run_memory.json").read_text(encoding="utf-8"))
    assert memory["final_status"] == "failed"
    assert (run_dir / "decision_trace.jsonl").stat().st_size > 0


def test_episodic_run_consolidates_episode_memory_with_evidence(
    tmp_path: Path,
) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    request = _request().model_copy(update={"format": "episodic_series", "episode_count": 1})

    result = run_episodic_pipeline(request, settings, build_default_mock_client())

    memory = json.loads((result.run_dir / "run_memory.json").read_text(encoding="utf-8"))
    assert memory["episode_memories"]
    assert memory["episode_memories"][0]["evidence_refs"] == ["episodes/episode_01.json"]
    assert memory["unresolved_threads"]


def test_context_budget_keeps_required_items_and_records_drops() -> None:
    required = ContextItem(
        id="request",
        kind="request",
        content="必须保留的用户约束",
        tokens_estimated=20,
        priority=100,
        reason="stage required context",
        required=True,
    )
    optional = ContextItem(
        id="old-draft",
        kind="artifact",
        content="较早版本草稿",
        tokens_estimated=20,
        priority=10,
        reason="optional history",
    )
    memory = MemoryRecord(
        id="fact-1",
        kind="semantic_fact",
        scope="story",
        content="林晚与顾承骁是盟友",
        evidence_refs=["characters.json"],
        created_stage="character_card_generation",
    )

    pack = build_context_pack(
        stage="targeted_rewrite",
        budget_tokens=21,
        candidate_items=[optional, required],
        memories=[memory],
    )

    assert [item.id for item in pack.selected_items] == ["request"]
    assert {item.id for item in pack.dropped_items} == {"old-draft", "fact-1"}
    assert pack.memory_refs == []


def test_realization_repairs_fenced_json_and_retries_missing_fields() -> None:
    repaired = realize_structured_output(
        "season_planning",
        '```json\n{"title": "A", "value": 1}\n```',
        _RequiredOutput,
    )
    retried = realize_structured_output(
        "season_planning",
        '{"title": "A"}',
        _RequiredOutput,
        retry=lambda _: '{"title": "A", "value": 2}',
    )

    assert repaired.result.status == "repaired"
    assert repaired.output == _RequiredOutput(title="A", value=1)
    assert retried.result.status == "retried"
    assert retried.output == _RequiredOutput(title="A", value=2)


def test_realization_repairs_yaml_output() -> None:
    repaired = realize_structured_output(
        "season_planning",
        "title: A\nvalue: 3",
        _RequiredOutput,
    )

    assert repaired.result.status == "repaired"
    assert repaired.output == _RequiredOutput(title="A", value=3)


def test_realization_blocks_unrecoverable_contract_output() -> None:
    blocked = realize_structured_output(
        "season_planning",
        '{"title": "A"}',
        _RequiredOutput,
    )

    assert blocked.result.status == "blocked"
    assert blocked.output is None
    assert blocked.result.issues


def test_mock_provider_exposes_missing_field_retry_to_realization_trace(
    tmp_path: Path,
) -> None:
    request = _request()
    run_root = tmp_path / "run"
    run_root.mkdir()
    runtime = HarnessRuntime(
        run_root=run_root,
        run_id="test-run",
        request=request,
        settings=Settings(provider="mock"),
    )
    client = HarnessedLLMClient(
        MockLLMClient(
            structured_outputs={
                "premise_refinement": [
                    '{"title_candidate": "A"}',
                    {
                        "title_candidate": "A",
                        "logline": "B",
                        "core_conflict": "C",
                        "hook_promise": "D",
                        "ending_payoff_plan": "E",
                        "tone_notes": [],
                        "hard_constraints": [],
                    },
                ]
            },
            text_outputs={},
        ),
        runtime,
    )

    output = client.generate_structured(
        role="premise_refinement",
        prompt="生成故事前提",
        response_model=PremiseArtifact,
    )

    assert output.title_candidate == "A"
    trace = (run_root / "realization_trace.jsonl").read_text(encoding="utf-8")
    assert '"status":"retried"' in trace


def test_runtime_retries_critique_with_missing_dimensions(tmp_path: Path) -> None:
    structured = deepcopy(DEFAULT_STRUCTURED_OUTPUTS)
    critique_outputs = structured["critique_scoring"]
    assert isinstance(critique_outputs, list)
    incomplete = deepcopy(critique_outputs[0])
    assert isinstance(incomplete, dict)
    incomplete["dimension_scores"].pop("ending_payoff")
    structured["critique_scoring"] = [incomplete, critique_outputs[0]]

    result = run_story_pipeline(
        _request(),
        Settings(runs_dir=tmp_path / "runs", provider="mock"),
        MockLLMClient(
            structured_outputs=structured,
            text_outputs=deepcopy(DEFAULT_TEXT_OUTPUTS),
        ),
    )

    trace = (result.run_dir / "realization_trace.jsonl").read_text(encoding="utf-8")
    assert '"stage":"critique_scoring","status":"retried"' in trace


def test_trajectory_regulator_aligns_rewrite_and_stops_after_one_rewrite() -> None:
    regulator = TrajectoryRegulator(max_rewrites=1)

    aligned = regulator.align_rewrite_target(
        stage="targeted_rewrite",
        weakest_dimensions=["ending_payoff"],
        rewrite_target="opening_hook",
    )
    after_rewrite = regulator.decide_rewrite(
        stage="targeted_rewrite",
        rewrite_needed=True,
        rewrite_count=1,
    )

    assert aligned.action == "rewrite"
    assert aligned.reason == "rewrite target aligned to weakest critique dimension"
    assert aligned.signals[0].recommended_action == "use target ending_payoff"
    assert after_rewrite.action == "stop"


def test_trajectory_regulator_boosts_repeatedly_dropped_context() -> None:
    regulator = TrajectoryRegulator()
    old_thread = ContextItem(
        id="thread-1",
        kind="semantic_fact",
        content="必须延续的旧线索",
        tokens_estimated=10,
        priority=50,
        reason="unresolved thread",
        evidence_refs=["episodes/episode_01.json"],
    )

    boosted, decision = regulator.prioritize_repeated_context(
        stage="episode_draft_generation",
        items=[old_thread],
        consecutive_drop_counts={"thread-1": 2},
    )

    assert boosted[0].priority > old_thread.priority
    assert "priority raised" in boosted[0].reason
    assert decision is not None
    assert decision.signals[0].signal_type == "repeated_context_drop"


def test_trajectory_regulator_marks_continuity_recovery_context() -> None:
    decision = TrajectoryRegulator().require_continuity_recovery(
        stage="episode_draft_generation",
        failures=["opening does not carry the previous hook"],
    )

    assert decision.action == "continue"
    assert decision.signals[0].signal_type == "continuity_recovery_context"
    assert "unresolved threads" in decision.signals[0].recommended_action


def test_runtime_forces_unresolved_threads_into_next_episode_context(tmp_path: Path) -> None:
    run_root = tmp_path / "run"
    run_root.mkdir()
    runtime = HarnessRuntime(
        run_root=run_root,
        run_id="continuity-recovery",
        request=_request().model_copy(update={"format": "episodic_series"}),
        settings=Settings(provider="mock"),
    )
    runtime.memory_store.memory.unresolved_threads = [
        MemoryRecord(
            id="thread-1",
            kind="semantic_fact",
            scope="story",
            content="偷拍视频来源仍未查明",
            evidence_refs=["continuity_state.json"],
            created_stage="episode_draft_generation",
        )
    ]

    runtime.force_unresolved_threads_for_next_episode(["opening continuity failed"])
    runtime.prepare_prompt("episode_draft_generation", "生成下一集")

    context_events = [
        json.loads(line)
        for line in (run_root / "context_trace.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    selected = context_events[-1]["selected_items"]
    forced = next(item for item in selected if item["id"] == "thread-1")
    assert forced["required"] is True
    assert "continuity recovery" in forced["reason"]


def test_pipeline_forces_rewrite_target_to_weakest_dimension(tmp_path: Path) -> None:
    structured = deepcopy(DEFAULT_STRUCTURED_OUTPUTS)
    critique_outputs = structured["critique_scoring"]
    assert isinstance(critique_outputs, list)
    first_critique = dict(critique_outputs[0])
    first_critique["rewrite_target"] = "opening_hook"
    critique_outputs[0] = first_critique
    client = MockLLMClient(
        structured_outputs=structured,
        text_outputs=deepcopy(DEFAULT_TEXT_OUTPUTS),
    )

    result = run_story_pipeline(
        _request(),
        Settings(runs_dir=tmp_path / "runs", provider="mock"),
        client,
    )

    rewrite = json.loads((result.run_dir / "rewrite_plan_v1.json").read_text(encoding="utf-8"))
    assert rewrite["target_section"] == "ending_payoff"


def test_regenerate_and_continue_append_harness_memory_and_traces(
    tmp_path: Path,
) -> None:
    settings = Settings(runs_dir=tmp_path / "runs", provider="mock")
    request = _request().model_copy(update={"format": "episodic_series", "episode_count": 2})
    initial = run_episodic_pipeline(
        request,
        settings,
        build_default_mock_client(),
    )
    stage_trace = initial.run_dir / "stage_trace.jsonl"
    initial_trace_size = stage_trace.stat().st_size

    regenerated = regenerate_episode(
        run_id=initial.run_id,
        episode_number=1,
        settings=settings,
        client=build_default_mock_client(),
    )
    assert regenerated.run_dir == initial.run_dir
    assert not (initial.run_dir / "episodes" / "episode_02.json").exists()

    continued = continue_episodic_run(
        run_id=initial.run_id,
        settings=settings,
        client=build_default_mock_client(),
    )
    memory = json.loads((continued.run_dir / "run_memory.json").read_text(encoding="utf-8"))

    assert memory["final_status"] == "completed"
    assert {item["id"] for item in memory["episode_memories"]} == {
        "episode-1",
        "episode-2",
    }
    assert stage_trace.stat().st_size > initial_trace_size
