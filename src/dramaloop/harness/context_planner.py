from dataclasses import dataclass

from dramaloop.config import Settings
from dramaloop.harness.context import build_context_pack, estimate_tokens, memory_to_context_item
from dramaloop.harness.memory_retriever import retrieve_stage_memories
from dramaloop.harness.run_memory import RunMemoryStore
from dramaloop.harness.skills import select_procedural_skills
from dramaloop.harness.stage_graph import get_stage_spec
from dramaloop.harness.trajectory import TrajectoryRegulator
from dramaloop.schemas.context import ContextItem, ContextPack
from dramaloop.schemas.harness import HARNESS_MODE_LEVEL
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.skill import ProceduralSkill
from dramaloop.schemas.trajectory import RegulationDecision


@dataclass(frozen=True)
class ContextPlan:
    pack: ContextPack
    selected_skills: list[ProceduralSkill]
    regulation_decisions: list[RegulationDecision]


class HarnessContextPlanner:
    def __init__(
        self,
        *,
        request: StoryRequest,
        settings: Settings,
        memory_store: RunMemoryStore,
        skills: list[ProceduralSkill],
        mode_level: int,
    ) -> None:
        self.request = request
        self.settings = settings
        self.memory_store = memory_store
        self.skills = skills
        self.mode_level = mode_level
        self.regulator = TrajectoryRegulator()
        self._context_drop_counts: dict[str, int] = {}
        self._force_unresolved_threads = False

    def build(self, stage: str, prompt: str) -> ContextPlan:
        candidates = [
            ContextItem(
                id=f"invocation-{stage}",
                kind="invocation_input",
                content="当前 stage prompt 与直接调用参数",
                tokens_estimated=estimate_tokens(prompt),
                priority=120,
                reason="base prompt and direct stage inputs are required",
                required=True,
                evidence_refs=[f"invocation:{stage}"],
            )
        ]
        candidates.extend(self._contract_items(stage))
        candidates.extend(self._request_items(stage))
        candidates.extend(self._required_context_items(stage))

        selected_skills: list[ProceduralSkill] = []
        if self.mode_level >= HARNESS_MODE_LEVEL["memory_skill_enabled"]:
            selected_skills = select_procedural_skills(
                self.skills,
                stage=stage,
                request=self.request,
                memory=self.memory_store.memory,
            )
            candidates.extend(
                ContextItem(
                    id=skill.id,
                    kind="procedural_skill",
                    content=skill.guidance,
                    tokens_estimated=estimate_tokens(skill.guidance),
                    priority=skill.priority,
                    reason=f"skill trigger matched: {skill.trigger}",
                )
                for skill in selected_skills
            )

        candidates.extend(self._memory_items(stage))
        regulation_decisions: list[RegulationDecision] = []
        if self.mode_level >= HARNESS_MODE_LEVEL["trajectory_regulation_enabled"]:
            candidates, decision = self.regulator.prioritize_repeated_context(
                stage=stage,
                items=candidates,
                consecutive_drop_counts=self._context_drop_counts,
            )
            if decision is not None:
                regulation_decisions.append(decision)

        budget = (
            self.context_budget
            if self.mode_level >= HARNESS_MODE_LEVEL["memory_context_budgeted"]
            else self.settings.model_context_window_tokens
        )
        pack = build_context_pack(
            stage=stage,
            budget_tokens=budget,
            candidate_items=candidates,
        )
        self._update_drop_counts(pack)
        return ContextPlan(
            pack=pack,
            selected_skills=selected_skills,
            regulation_decisions=regulation_decisions,
        )

    @property
    def context_budget(self) -> int:
        return max(
            1,
            int(
                self.settings.model_context_window_tokens
                * self.settings.stage_context_budget_ratio
            ),
        )

    def force_unresolved_threads(self, failures: list[str]) -> RegulationDecision:
        self._force_unresolved_threads = True
        return self.regulator.require_continuity_recovery(
            stage="episode_draft_generation",
            failures=failures,
        )

    def _contract_items(self, stage: str) -> list[ContextItem]:
        if self.mode_level < HARNESS_MODE_LEVEL["contract_enabled"]:
            return []
        spec = get_stage_spec(stage)
        guidance = [
            *spec.contract_rules,
            *(f"禁止：{behavior}" for behavior in spec.forbidden_behaviors),
        ]
        if not guidance:
            return []
        content = "；".join(guidance)
        return [
            ContextItem(
                id=f"contract-{stage}",
                kind="stage_contract",
                content=content,
                tokens_estimated=estimate_tokens(content),
                priority=110,
                reason="active stage contract rules",
                required=True,
            )
        ]

    def _request_items(self, stage: str) -> list[ContextItem]:
        spec = get_stage_spec(stage)
        request_required = "request" in spec.required_context
        if not request_required and "request" not in spec.optional_context:
            return []
        return [
            ContextItem(
                id="request",
                kind="request",
                content=self.memory_store.memory.request_summary,
                tokens_estimated=estimate_tokens(self.memory_store.memory.request_summary),
                priority=100,
                reason="stage contract requires the original request",
                required=request_required,
                evidence_refs=["request.json"],
            )
        ]

    def _required_context_items(self, stage: str) -> list[ContextItem]:
        items: list[ContextItem] = []
        for required_name in get_stage_spec(stage).required_context:
            if required_name == "request":
                continue
            record = self._find_artifact(required_name)
            if record is not None:
                items.append(
                    ContextItem(
                        id=f"required-{required_name}",
                        kind="artifact",
                        content=record.content,
                        tokens_estimated=estimate_tokens(record.content),
                        priority=100,
                        reason=f"required by {stage} stage contract",
                        required=True,
                        evidence_refs=record.evidence_refs,
                    )
                )
                continue
            content = f"当前调用参数已直接提供 {required_name}"
            items.append(
                ContextItem(
                    id=f"invocation-{required_name}",
                    kind="invocation_input",
                    content=content,
                    tokens_estimated=estimate_tokens(content),
                    priority=100,
                    reason=f"required {required_name} is present in the stage invocation",
                    required=True,
                    evidence_refs=[f"invocation:{stage}"],
                )
            )
        return items

    def _memory_items(self, stage: str) -> list[ContextItem]:
        if self.mode_level < HARNESS_MODE_LEVEL["memory_skill_enabled"]:
            return []
        memories = retrieve_stage_memories(self.memory_store.memory, stage=stage)
        items = [memory_to_context_item(memory) for memory in memories]
        if not self._force_unresolved_threads or stage != "episode_draft_generation":
            return items
        forced_ids = {record.id for record in self.memory_store.memory.unresolved_threads}
        items = [item for item in items if item.id not in forced_ids]
        items.extend(
            memory_to_context_item(record, priority=130).model_copy(
                update={
                    "required": True,
                    "reason": "continuity recovery requires this unresolved thread",
                }
            )
            for record in self.memory_store.memory.unresolved_threads
        )
        self._force_unresolved_threads = False
        return items

    def _find_artifact(self, context_name: str):
        aliases = {
            "season": ("season_bible",),
            "episode_plan": ("episode_plan",),
            "continuity": ("continuity_state",),
            "episode_draft": ("episode_",),
            "episode_critique": ("critique",),
            "completed_drafts": ("draft_", "episode_"),
            "rewrite_target": ("critique", "rewrite_plan"),
        }
        needles = aliases.get(context_name, (context_name,))
        for record in reversed(self.memory_store.memory.raw_artifacts):
            if any(
                needle in evidence
                for evidence in record.evidence_refs
                for needle in needles
            ):
                return record
        return None

    def _update_drop_counts(self, pack: ContextPack) -> None:
        for item in pack.selected_items:
            self._context_drop_counts[item.id] = 0
        for item in pack.dropped_items:
            self._context_drop_counts[item.id] = self._context_drop_counts.get(item.id, 0) + 1
