from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from dramaloop.config import Settings
from dramaloop.harness.context_planner import HarnessContextPlanner
from dramaloop.harness.realization import (
    validate_artifact_output,
    validate_structured_contract,
    validate_text_output,
)
from dramaloop.harness.run_memory import RunMemoryStore, append_jsonl
from dramaloop.harness.skills import load_procedural_skills
from dramaloop.harness.stage_graph import get_stage_spec
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.schemas.context import ContextPack
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
        "usage_trace.jsonl",
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
        self.context_planner = HarnessContextPlanner(
            request=request,
            settings=settings,
            memory_store=self.memory_store,
            skills=self.skills,
            mode_level=self.mode_level,
        )

    @property
    def context_budget(self) -> int:
        return self.context_planner.context_budget

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
        plan = self.context_planner.build(stage, prompt)
        pack = plan.pack
        selected_skills = plan.selected_skills
        for decision in plan.regulation_decisions:
            self.record_regulation(decision)
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

    def record_provider_usage(self, client: LLMClient) -> None:
        drain = getattr(client, "drain_usage_records", None)
        if not callable(drain):
            return
        for record in drain():
            self._trace("usage_trace.jsonl", {"event": "provider_usage", **record})

    def record_regulation(self, decision: RegulationDecision) -> None:
        self._trace(
            "trajectory_trace.jsonl",
            {"event": "regulation_decision", **decision.model_dump(mode="json")},
        )
        degradation_signals = {
            "rewrite_target_mismatch",
            "repeated_context_drop",
            "continuity_recovery_context",
            "rewrite_limit",
        }
        if any(signal.signal_type in degradation_signals for signal in decision.signals):
            if "trajectory_degradation" not in self.memory_store.memory.failure_patterns:
                self.memory_store.memory.failure_patterns.append("trajectory_degradation")
                self.memory_store.persist()
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
        self.memory_store.finalize(status)
        self.record_decision(
            stage="run",
            action="stop",
            reason=reason or f"run {status}",
            layer="orchestrator",
        )

    def invalidate_episodes_after(self, episode_number: int) -> None:
        self.memory_store.invalidate_episodes_after(episode_number)

    def force_unresolved_threads_for_next_episode(self, failures: list[str]) -> None:
        if not self.regulation_enabled:
            return
        self.record_regulation(self.context_planner.force_unresolved_threads(failures))

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
            self.runtime.record_provider_usage(self.client)
            self.runtime.record_realization(
                RealizationResult(stage=role, status="blocked", issues=[str(exc)])
            )
            self.runtime.fail_stage(role, exc)
            raise
        self.runtime.record_provider_usage(self.client)
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
                self.runtime.record_provider_usage(self.client)
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
            self.runtime.record_provider_usage(self.client)
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
            self.runtime.record_provider_usage(self.client)
            self.runtime.record_realization(
                RealizationResult(stage=role, status="blocked", issues=[str(exc)])
            )
            self.runtime.fail_stage(role, exc)
            raise
        self.runtime.record_provider_usage(self.client)
        validation = (
            validate_text_output(role, output)
            if self.runtime.realization_enabled
            else RealizationResult(stage=role, status="accepted")
        )
        provider_result = getattr(self.client, "last_realization_result", None)
        result = validation if validation.status == "blocked" else provider_result or validation
        self.runtime.record_realization(result)
        if provider_result is not None:
            setattr(self.client, "last_realization_result", None)
        if result.status == "blocked":
            error = LLMInvocationError("; ".join(result.issues))
            self.runtime.fail_stage(role, error)
            raise error
        self.runtime.complete_stage(role)
        return output
