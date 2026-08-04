import json
import os
import re
from typing import Any

from anthropic import Anthropic
from pydantic import ValidationError
import yaml

from dramaloop.config import Settings
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.schemas.realization import RealizationResult


class AnthropicCompatibleLLMClient(LLMClient):
    def __init__(self, api_key: str, model_name: str, base_url: str | None = None) -> None:
        self._base_url = base_url
        client_kwargs: dict[str, Any] = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = Anthropic(**client_kwargs)
        self._model_name = model_name
        self.last_realization_result: RealizationResult | None = None

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
        if role == "season_planning":
            normalized.setdefault("title_candidate", normalized.get("标题") or normalized.get("title") or normalized.get("片名"))
            normalized.setdefault(
                "series_logline",
                normalized.get("剧情主线") or normalized.get("整季logline") or normalized.get("logline") or normalized.get("主线"),
            )
            normalized.setdefault("core_conflict", normalized.get("核心冲突") or normalized.get("主冲突"))
            normalized.setdefault("target_episode_count", normalized.get("集数") or normalized.get("总集数") or normalized.get("episode_count"))
            normalized.setdefault("final_payoff", normalized.get("终局回报") or normalized.get("结局回报") or normalized.get("payoff"))
            normalized.setdefault("main_character_arcs", normalized.get("人物弧线") or normalized.get("角色弧线"))
            normalized.setdefault("must_land_beats", normalized.get("关键节点") or normalized.get("必须回收节点") or normalized.get("关键回收点"))
        if role == "episode_plan_generation":
            episodes = normalized.get("episodes") or normalized.get("分集")
            if isinstance(episodes, list):
                normalized["episodes"] = [self._normalize_episode_plan_item(item) for item in episodes]
        return normalized

    def _normalize_episode_plan_item(self, item: Any) -> Any:
        if not isinstance(item, dict):
            return item
        normalized = dict(item)
        normalized.setdefault("episode_number", normalized.get("集数") or normalized.get("episode") or normalized.get("episode_no"))
        normalized.setdefault("title", normalized.get("标题") or normalized.get("题目"))
        normalized.setdefault("opening_situation", normalized.get("开场局面") or normalized.get("开场") or normalized.get("opening"))
        normalized.setdefault("core_conflict", normalized.get("本集核心冲突") or normalized.get("核心冲突") or normalized.get("episode_conflict"))
        normalized.setdefault("must_happen", normalized.get("本集必须发生") or normalized.get("必须发生") or normalized.get("beats"))
        normalized.setdefault("hook_ending", normalized.get("本集结尾钩子") or normalized.get("结尾钩子") or normalized.get("hook"))
        normalized.setdefault("sets_up_next", normalized.get("下一集铺垫") or normalized.get("铺垫下一集") or normalized.get("next_setup"))
        return normalized

    def _structured_max_tokens(self, role: str) -> int:
        if role == "episode_plan_generation":
            return 6000
        if role in {"critique_scoring", "episode_critique_scoring"}:
            return 3000
        return 2000

    def _parse_structured_response_text(self, text: str) -> Any:
        content = text.strip()
        if not content:
            raise LLMInvocationError("Structured response was empty")

        parse_candidates = [content]

        fenced_match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.DOTALL | re.IGNORECASE)
        if fenced_match:
            parse_candidates.append(fenced_match.group(1).strip())

        decoder = json.JSONDecoder()
        first_json_start = min((index for index in (content.find("{"), content.find("[")) if index != -1), default=-1)
        if first_json_start != -1:
            parse_candidates.append(content[first_json_start:].strip())

        seen: set[str] = set()
        for candidate in parse_candidates:
            normalized_candidate = candidate.strip()
            if not normalized_candidate or normalized_candidate in seen:
                continue
            seen.add(normalized_candidate)
            try:
                return json.loads(normalized_candidate)
            except json.JSONDecodeError:
                try:
                    payload, _ = decoder.raw_decode(normalized_candidate)
                    return payload
                except json.JSONDecodeError:
                    continue

        try:
            yaml_payload = yaml.safe_load(content)
        except yaml.YAMLError:
            yaml_payload = None
        if isinstance(yaml_payload, (dict, list)):
            return yaml_payload

        snippet = content[:200].replace("\n", "\\n")
        raise LLMInvocationError(f"Structured response was not valid JSON: {snippet}")

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        max_tokens = self._structured_max_tokens(role)
        attempts: list[dict[str, Any]] = [
            {
                "max_tokens": max_tokens,
                "temperature": 0.4,
                "system": f"你是短剧生成系统中的 {role} 阶段。你必须只返回合法 JSON，不能输出任何 JSON 之外的内容。",
                "prompt": prompt,
            },
            {
                "max_tokens": max(max_tokens, 8000),
                "temperature": 0.2,
                "system": f"你是短剧生成系统中的 {role} 阶段。你上一次的结果未能被解析。你这一次必须只返回完整、闭合、合法的 JSON。",
                "prompt": prompt + "\n\n补充要求：如果上一次输出被截断，这一次请压缩措辞，但必须保证 JSON 完整闭合。",
            },
        ]

        last_error: LLMInvocationError | None = None
        for attempt_index, attempt in enumerate(attempts):
            response = self._client.messages.create(
                model=self._model_name,
                max_tokens=attempt["max_tokens"],
                temperature=attempt["temperature"],
                system=attempt["system"],
                messages=[{"role": "user", "content": attempt["prompt"]}],
            )
            text = "".join(
                getattr(block, "text", "")
                for block in response.content
                if getattr(block, "type", None) == "text"
            )
            try:
                payload = self._parse_structured_response_text(text)
                if isinstance(payload, dict):
                    payload = self._normalize_payload(role, payload)
                output = response_model.model_validate(payload)
            except (LLMInvocationError, ValidationError) as exc:
                stop_reason = getattr(response, "stop_reason", None)
                detail = f"{exc}"
                if stop_reason == "max_tokens":
                    detail = f"模型输出被 max_tokens 截断。{detail}"
                last_error = LLMInvocationError(f"Structured response for role={role} was not valid JSON. {detail}")
                continue

            content = text.strip()
            repaired = content.startswith("```") or not content.startswith(("{", "["))
            if attempt_index > 0:
                self.last_realization_result = RealizationResult(
                    stage=role,
                    status="retried",
                    retry_reason=str(last_error) if last_error else "first attempt failed",
                )
            elif repaired:
                self.last_realization_result = RealizationResult(
                    stage=role,
                    status="repaired",
                    repair_summary="removed response wrapper and recovered JSON payload",
                )
            else:
                self.last_realization_result = RealizationResult(
                    stage=role,
                    status="accepted",
                )
            return output

        assert last_error is not None
        raise last_error

    def generate_text(self, *, role: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=2500,
            temperature=0.8,
            system=f"你是短剧生成系统中的 {role} 阶段。",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            getattr(block, "text", "")
            for block in response.content
            if getattr(block, "type", None) == "text"
        )


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


def build_judge_client(settings: Settings) -> LLMClient:
    if settings.provider == "mock":
        return build_default_mock_client()
    api_key = settings.judge_api_key or os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise LLMInvocationError(
            "Configure DRAMALOOP_JUDGE_API_KEY or DEEPSEEK_API_KEY for the DeepSeek judge"
        )
    return AnthropicCompatibleLLMClient(
        api_key=api_key,
        model_name=settings.judge_model_name,
        base_url=settings.judge_base_url,
    )
