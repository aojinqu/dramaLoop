import pytest

from dramaloop.config import Settings
from dramaloop.llm.base import LLMInvocationError
from dramaloop.llm.provider import AnthropicCompatibleLLMClient, build_llm_client
from dramaloop.schemas.premise import PremiseArtifact


def test_build_llm_client_returns_mock_for_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    client = build_llm_client(Settings())

    assert client.__class__.__name__ == "MockLLMClient"


def test_build_llm_client_requires_api_key_for_anthropic_compatible_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "anthropic-compatible")
    monkeypatch.setenv("DRAMALOOP_API_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")

    with pytest.raises(LLMInvocationError):
        build_llm_client(Settings())


def test_build_llm_client_passes_custom_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "anthropic-compatible")
    monkeypatch.setenv("DRAMALOOP_API_KEY", "test-key")
    monkeypatch.setenv("DRAMALOOP_BASE_URL", "https://api.deepseek.com/anthropic")
    monkeypatch.setenv("DRAMALOOP_MODEL_NAME", "deepseek-v4-flash")

    client = build_llm_client(Settings())

    assert isinstance(client, AnthropicCompatibleLLMClient)
    assert client._base_url == "https://api.deepseek.com/anthropic"


def test_normalize_payload_maps_common_premise_aliases() -> None:
    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)

    normalized = client._normalize_payload(
        "premise_refinement",
        {
            "title": "替嫁反击",
            "hook": "婚礼羞辱后立刻反击。",
            "ending": "公开反杀前任，完成逆袭。",
            "core_conflict": "两大家族对抗",
            "tone_notes": ["快节奏"],
            "hard_constraints": ["短篇"],
        },
    )

    artifact = PremiseArtifact.model_validate(normalized)

    assert artifact.title_candidate == "替嫁反击"
    assert artifact.hook_promise == "婚礼羞辱后立刻反击。"
    assert artifact.ending_payoff_plan == "公开反杀前任，完成逆袭。"
