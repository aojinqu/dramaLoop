from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from dramaloop.config import Settings
from dramaloop.harness.context import build_context_pack, estimate_tokens
from dramaloop.harness.memory_retriever import retrieve_stage_memories
from dramaloop.harness.realization import (
    validate_artifact_output,
    validate_structured_contract,
    validate_text_output,
)
from dramaloop.harness.run_memory import RunMemoryStore, append_jsonl
from dramaloop.harness.skills import load_procedural_skills, select_procedural_skills
from dramaloop.harness.stage_graph import get_stage_spec
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.schemas.context import ContextItem, ContextPack
from dramaloop.schemas.harness import HARNESS_MODE_LEVEL
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.realization import RealizationResult
from dramaloop.schemas.trajectory import RegulationDecision


class HarnessRuntime:
    TRACE_FILENAMES = (
        "stage_trace.jsonl",
        "memory_trace.jsonl",
        "context_trace.jsonl",
        "decision_trace.jsonl",
        "skill_trace.jsonl",
        "realization_trace.jsonl",
        "trajectory_trace.jsonl",
    )

    def __init__(
        self,
        *,
        run_root: Path,
        run_id: str,
        request: StoryRequest,
        settings: Settings,
    ) -> None:
        self.run_root = run_root
        self.request = request
        self.settings = settings
        self.mode_level = (
            HARNESS_MODE_LEVEL[settings.harness_mode] if settings.harness_enabled else 0
        )
        for filename in self.TRACE_FILENAMES:
            (run_root / filename).touch(exist_ok=True)
        self.memory_store = RunMemoryStore(run_root, run_id, request)
        self.skills = load_procedural_skills(settings.procedural_skills_path)

    @property
    def context_budget(self) -> int:
        return max(
            1,
            int(
                self.settings.model_context_window_tokens * self.settings.stage_context_budget_ratio
            ),
        )

    @property
    def realization_enabled(self) -> bool:
        return self.mode_level >= HARNESS_MODE_LEVEL["realization_enabled"]

    @property
    def regulation_enabled(self) -> bool:
        return self.mode_level >= HARNESS_MODE_LEVEL["trajectory_regulation_enabled"]

    def prepare_prompt(self, stage: str, prompt: str) -> str:
        spec = get_stage_spec(stage)
        self._trace(
            "stage_trace.jsonl",
            {"stage": stage, "event": "entered", "contract": spec.name},
        )
        candidates: list[ContextItem] = []
        candidates.append(
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
        )
        if self.mode_level >= HARNESS_MODE_LEVEL["contract_enabled"]:
            contract_guidance = [
                *spec.contract_rules,
                *(f"禁止：{behavior}" for behavior in spec.forbidden_behaviors),
            ]
            if contract_guidance:
                content = "；".join(contract_guidance)
                candidates.append(
                    ContextItem(
                        id=f"contract-{stage}",
                        kind="stage_contract",
                        content=content,
                        tokens_estimated=estimate_tokens(content),
                        priority=110,
                        reason="active stage contract rules",
                        required=True,
                    )
                )
        request_required = "request" in spec.required_context
        if request_required or "request" in spec.optional_context:
            candidates.append(
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
            )
        for required_name in spec.required_context:
            if required_name == "request":
                continue
            record = self._find_artifact(required_name)
            if record is not None:
                candidates.append(
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
            else:
                content = f"当前调用参数已直接提供 {required_name}"
                candidates.append(
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

        selected_skills = []
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

        memories = (
            retrieve_stage_memories(self.memory_store.memory, stage=stage)
            if self.mode_level >= HARNESS_MODE_LEVEL["memory_skill_enabled"]
            else []
        )
        budget = (
            self.context_budget
            if self.mode_level >= HARNESS_MODE_LEVEL["memory_context_budgeted"]
            else self.settings.model_context_window_tokens
        )
        pack = build_context_pack(
            stage=stage,
            budget_tokens=budget,
            candidate_items=candidates,
            memories=memories,
        )
        self._trace(
            "context_trace.jsonl",
            {"stage": stage, "event": "context_planned", **pack.model_dump(mode="json")},
        )
        self._trace(
            "skill_trace.jsonl",
            {
                "stage": stage,
                "event": "skills_selected",
                "skill_ids": [skill.id for skill in selected_skills],
                "triggers": [skill.trigger for skill in selected_skills],
                "evaluations": [
                    {
                        "skill_id": skill.id,
                        "trigger_matched": skill.id
                        in {selected.id for selected in selected_skills},
                    }
                    for skill in self.skills
                    if skill.stage == stage
                ],
            },
        )
        append_jsonl(
            self.run_root / "memory_trace.jsonl",
            {
                "ts": datetime.now().isoformat(),
                "event": "memory_recalled",
                "stage": stage,
                "memory_ids": pack.memory_refs,
            },
        )
        if self.mode_level < HARNESS_MODE_LEVEL["contract_enabled"] or not pack.selected_items:
            return prompt
        injected_items = [item for item in pack.selected_items if item.id != f"invocation-{stage}"]
        if not injected_items:
            return prompt
        injected_pack = pack.model_copy(update={"selected_items": injected_items})
        return f"{prompt}\n\n运行时上下文：\n{self._render_context(injected_pack)}"

    def complete_stage(self, stage: str) -> None:
        self.memory_store.complete_stage(stage)
        self._trace("stage_trace.jsonl", {"stage": stage, "event": "completed"})

    def fail_stage(self, stage: str, error: Exception) -> None:
        self._trace(
            "stage_trace.jsonl",
            {"stage": stage, "event": "failed", "detail": str(error)},
        )
        self.record_decision(
            stage=stage,
            action="stop",
            reason=f"stage failed: {error}",
            layer="runtime",
        )

    def record_artifact(
        self,
        *,
        stage: str,
        artifact_ref: str,
        payload: BaseModel | dict[str, Any] | str,
    ) -> None:
        if self.realization_enabled:
            realization = validate_artifact_output(stage, artifact_ref)
            self.record_realization(realization)
            if realization.status == "blocked":
                raise RuntimeError("; ".join(realization.issues))
        self.memory_store.record_artifact(
            artifact_ref=artifact_ref,
            payload=payload,
            stage=stage,
        )
        self._trace(
            "stage_trace.jsonl",
            {
                "stage": stage,
                "event": "artifact_written",
                "artifact": artifact_ref,
            },
        )

    def record_realization(self, result: RealizationResult) -> None:
        self._trace(
            "realization_trace.jsonl",
            {"event": "output_realized", **result.model_dump(mode="json", exclude_none=True)},
        )

    def record_regulation(self, decision: RegulationDecision) -> None:
        self._trace(
            "trajectory_trace.jsonl",
            {"event": "regulation_decision", **decision.model_dump(mode="json")},
        )
        self.record_decision(
            stage=decision.stage,
            action=decision.action,
            reason=decision.reason,
            layer="trajectory",
        )

    def record_decision(
        self,
        *,
        stage: str,
        action: str,
        reason: str,
        layer: str,
    ) -> None:
        self._trace(
            "decision_trace.jsonl",
            {
                "stage": stage,
                "event": "decision",
                "action": action,
                "reason": reason,
                "layer": layer,
            },
        )

    def finalize(self, status: str, *, reason: str | None = None) -> None:
        failure_pattern = "trajectory_degradation" if status == "failed" else None
        self.memory_store.finalize(status, failure_pattern=failure_pattern)
        self.record_decision(
            stage="run",
            action="stop",
            reason=reason or f"run {status}",
            layer="orchestrator",
        )

    def invalidate_episodes_after(self, episode_number: int) -> None:
        self.memory_store.invalidate_episodes_after(episode_number)

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
            if any(needle in evidence for evidence in record.evidence_refs for needle in needles):
                return record
        return None

    def _render_context(self, pack: ContextPack) -> str:
        return "\n".join(
            f"- [{item.kind}] {item.content} (evidence: {', '.join(item.evidence_refs) or 'n/a'})"
            for item in pack.selected_items
        )

    def _trace(self, filename: str, payload: dict[str, Any]) -> None:
        append_jsonl(
            self.run_root / filename,
            {"ts": datetime.now().isoformat(), **payload},
        )


class HarnessedLLMClient(LLMClient):
    def __init__(self, client: LLMClient, runtime: HarnessRuntime) -> None:
        self.client = client
        self.runtime = runtime

    def generate_structured(
        self,
        *,
        role: str,
        prompt: str,
        response_model: type[TModel],
    ) -> TModel:
        prepared = self.runtime.prepare_prompt(role, prompt)
        try:
            output = self.client.generate_structured(
                role=role,
                prompt=prepared,
                response_model=response_model,
            )
        except Exception as exc:
            self.runtime.record_realization(
                RealizationResult(stage=role, status="blocked", issues=[str(exc)])
            )
            self.runtime.fail_stage(role, exc)
            raise
        realization = getattr(self.client, "last_realization_result", None)
        contract_result = (
            validate_structured_contract(role, output)
            if self.runtime.realization_enabled
            else RealizationResult(stage=role, status="accepted")
        )
        if contract_result.status == "blocked":
            retry_reason = "; ".join(contract_result.issues)
            retry_prompt = (
                f"{prepared}\n\n上一次输出未满足 stage contract：{retry_reason}。"
                "请只补齐缺失内容，并返回完整合法结果。"
            )
            try:
                output = self.client.generate_structured(
                    role=role,
                    prompt=retry_prompt,
                    response_model=response_model,
                )
            except Exception as exc:
                self.runtime.record_realization(
                    RealizationResult(
                        stage=role,
                        status="blocked",
                        issues=[retry_reason, str(exc)],
                        retry_reason=retry_reason,
                    )
                )
                self.runtime.fail_stage(role, exc)
                raise
            retried_contract = validate_structured_contract(role, output)
            if retried_contract.status == "blocked":
                self.runtime.record_realization(retried_contract)
                error = LLMInvocationError("; ".join(retried_contract.issues))
                self.runtime.fail_stage(role, error)
                raise error
            realization = RealizationResult(
                stage=role,
                status="retried",
                issues=contract_result.issues,
                retry_reason=retry_reason,
            )
        self.runtime.record_realization(realization or contract_result)
        if realization is not None:
            setattr(self.client, "last_realization_result", None)
        self.runtime.complete_stage(role)
        return output

    def generate_text(self, *, role: str, prompt: str) -> str:
        prepared = self.runtime.prepare_prompt(role, prompt)
        try:
            output = self.client.generate_text(role=role, prompt=prepared)
        except Exception as exc:
            self.runtime.record_realization(
                RealizationResult(stage=role, status="blocked", issues=[str(exc)])
            )
            self.runtime.fail_stage(role, exc)
            raise
        result = (
            validate_text_output(role, output)
            if self.runtime.realization_enabled
            else RealizationResult(stage=role, status="accepted")
        )
        self.runtime.record_realization(result)
        if result.status == "blocked":
            error = LLMInvocationError("; ".join(result.issues))
            self.runtime.fail_stage(role, error)
            raise error
        self.runtime.complete_stage(role)
        return output
