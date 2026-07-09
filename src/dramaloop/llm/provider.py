import json
import os
from typing import Any

from anthropic import Anthropic

from dramaloop.config import Settings
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.llm.mock import build_default_mock_client


class AnthropicCompatibleLLMClient(LLMClient):
    def __init__(self, api_key: str, model_name: str, base_url: str | None = None) -> None:
        self._base_url = base_url
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = Anthropic(**client_kwargs)
        self._model_name = model_name

    def _normalize_payload(self, role: str, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)
        if role == "premise_refinement":
            normalized.setdefault("title_candidate", normalized.get("title") or normalized.get("headline") or "未命名短剧")
            normalized.setdefault(
                "logline",
                normalized.get("logline") or normalized.get("summary") or normalized.get("premise") or normalized.get("story_logline") or "待补充故事概述",
            )
            normalized.setdefault(
                "hook_promise",
                normalized.get("hook_promise") or normalized.get("hook") or normalized.get("opening_hook") or "开场冲突快速引爆",
            )
            normalized.setdefault(
                "ending_payoff_plan",
                normalized.get("ending_payoff_plan") or normalized.get("ending") or normalized.get("payoff") or normalized.get("ending_payoff") or "结尾完成情绪回报",
            )
            normalized.setdefault(
                "core_conflict",
                normalized.get("core_conflict") or normalized.get("conflict") or normalized.get("main_conflict") or "主角与对手的核心对抗",
            )
            normalized.setdefault("tone_notes", normalized.get("tone_notes") or normalized.get("tone") or [])
            normalized.setdefault("hard_constraints", normalized.get("hard_constraints") or normalized.get("constraints") or [])
        return normalized

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=2000,
            temperature=0.7,
            system=f"You are the {role} stage in a structured short-drama generation system. Return valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMInvocationError(f"Structured response for role={role} was not valid JSON") from exc
        if isinstance(payload, dict):
            payload = self._normalize_payload(role, payload)
        return response_model.model_validate(payload)

    def generate_text(self, *, role: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=2500,
            temperature=0.8,
            system=f"You are the {role} stage in a short-drama generation system.",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def _resolve_api_key(settings: Settings) -> str | None:
    return settings.api_key or os.getenv("ANTHROPIC_API_KEY") or os.getenv("DEEPSEEK_API_KEY")


def _resolve_base_url(settings: Settings) -> str | None:
    return settings.base_url or os.getenv("ANTHROPIC_BASE_URL") or os.getenv("DEEPSEEK_BASE_URL")


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.provider == "mock":
        return build_default_mock_client()
    if settings.provider == "anthropic-compatible":
        api_key = _resolve_api_key(settings)
        if not api_key:
            raise LLMInvocationError(
                "Configure DRAMALOOP_API_KEY (or ANTHROPIC_API_KEY / DEEPSEEK_API_KEY) when DRAMALOOP_PROVIDER=anthropic-compatible"
            )
        return AnthropicCompatibleLLMClient(
            api_key=api_key,
            model_name=settings.model_name,
            base_url=_resolve_base_url(settings),
        )
    raise LLMInvocationError(f"Unsupported provider: {settings.provider}")
