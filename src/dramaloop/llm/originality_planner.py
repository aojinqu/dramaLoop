from __future__ import annotations

import json
from time import monotonic
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.prompts.originality import PLANNER_SYSTEM_PROMPT
from dramaloop.schemas.realization import RealizationResult


class OpenAICompatiblePlannerClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str,
        model_name: str,
        base_url: str,
        timeout_seconds: float = 120.0,
        max_retries: int = 1,
    ) -> None:
        self._api_key = api_key
        self._model_name = model_name
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._usage_records: list[dict[str, Any]] = []
        self.last_realization_result: RealizationResult | None = None

    def drain_usage_records(self) -> list[dict[str, Any]]:
        records = list(self._usage_records)
        self._usage_records = []
        return records

    def _post_chat_completion(self, *, prompt: str, attempt: int) -> dict[str, Any]:
        retry_instruction = (
            "\n\n上一次响应无效。请压缩措辞，只返回完整、闭合、严格符合 schema 的 JSON object。"
            if attempt > 1
            else ""
        )
        payload = {
            "model": self._model_name,
            "messages": [
                {"role": "system", "content": PLANNER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt + retry_instruction},
            ],
            "temperature": 0.2,
            "top_p": 0.8,
            "max_tokens": 1800,
        }
        request = Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        started = monotonic()
        try:
            with urlopen(request, timeout=self._timeout_seconds) as response:
                body = response.read().decode("utf-8")
        except HTTPError as exc:
            raise LLMInvocationError(f"Originality planner returned HTTP {exc.code}") from exc
        except (URLError, TimeoutError, OSError) as exc:
            raise LLMInvocationError(f"Originality planner request failed: {exc}") from exc

        try:
            envelope = json.loads(body)
        except json.JSONDecodeError as exc:
            raise LLMInvocationError("Originality planner returned invalid response JSON") from exc
        if not isinstance(envelope, dict):
            raise LLMInvocationError("Originality planner response must be a JSON object")

        usage = envelope.get("usage")
        usage = usage if isinstance(usage, dict) else {}
        choices = envelope.get("choices")
        choice = choices[0] if isinstance(choices, list) and choices else {}
        choice = choice if isinstance(choice, dict) else {}
        self._usage_records.append(
            {
                "role": "originality_mechanism_planning",
                "attempt": attempt,
                "model": envelope.get("model") or self._model_name,
                "stop_reason": choice.get("finish_reason"),
                "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
                "output_tokens": int(usage.get("completion_tokens", 0) or 0),
                "latency_ms": round((monotonic() - started) * 1000),
                "provider": "openai-compatible-planner",
            }
        )
        return envelope

    @staticmethod
    def _assistant_text(envelope: dict[str, Any]) -> tuple[str, str | None]:
        choices = envelope.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise LLMInvocationError("Originality planner response contained no choices")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise LLMInvocationError("Originality planner response contained no assistant text")
        content = message["content"].strip()
        if not content:
            raise LLMInvocationError("Originality planner returned empty assistant text")
        return content, choice.get("finish_reason")

    @staticmethod
    def _parse_plan_payload(text: str) -> dict[str, Any]:
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMInvocationError(
                "Originality planner assistant text was not a strict JSON object"
            ) from exc
        if not isinstance(payload, dict):
            raise LLMInvocationError("Originality planner assistant output must be a JSON object")
        return payload

    def generate_structured(
        self,
        *,
        role: str,
        prompt: str,
        response_model: type[TModel],
    ) -> TModel:
        if role != "originality_mechanism_planning":
            raise LLMInvocationError(f"Planner client does not support structured role={role}")

        last_error: LLMInvocationError | None = None
        for attempt in range(1, self._max_retries + 2):
            try:
                envelope = self._post_chat_completion(prompt=prompt, attempt=attempt)
                text, finish_reason = self._assistant_text(envelope)
                if finish_reason == "length":
                    raise LLMInvocationError("Originality planner output was truncated")
                output = response_model.model_validate(self._parse_plan_payload(text))
            except (LLMInvocationError, ValidationError) as exc:
                last_error = (
                    exc
                    if isinstance(exc, LLMInvocationError)
                    else LLMInvocationError(f"Originality planner schema validation failed: {exc}")
                )
                continue

            self.last_realization_result = RealizationResult(
                stage=role,
                status="retried" if attempt > 1 else "accepted",
                retry_reason=str(last_error) if attempt > 1 and last_error else None,
            )
            return output

        assert last_error is not None
        raise last_error

    def generate_text(self, *, role: str, prompt: str) -> str:
        raise LLMInvocationError(f"Planner client does not support text role={role}")


def build_originality_planner_client(
    settings: Settings,
) -> OpenAICompatiblePlannerClient | None:
    if not settings.originality_planner_base_url:
        return None
    if not settings.originality_planner_api_key:
        raise LLMInvocationError(
            "Configure DRAMALOOP_ORIGINALITY_PLANNER_API_KEY when "
            "DRAMALOOP_ORIGINALITY_PLANNER_BASE_URL is set"
        )
    return OpenAICompatiblePlannerClient(
        api_key=settings.originality_planner_api_key,
        model_name=settings.originality_planner_model_name,
        base_url=settings.originality_planner_base_url,
        timeout_seconds=settings.originality_planner_timeout_seconds,
        max_retries=settings.originality_planner_max_retries,
    )
