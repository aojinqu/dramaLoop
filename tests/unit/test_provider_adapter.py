import pytest

from dramaloop.config import Settings
from dramaloop.llm.base import LLMInvocationError
from dramaloop.llm.provider import AnthropicCompatibleLLMClient, build_llm_client
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.schemas.season import EpisodePlanArtifact, SeasonBible


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


def test_normalize_payload_maps_common_season_aliases() -> None:
    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)

    normalized = client._normalize_payload(
        "season_planning",
        {
            "标题": "退婚后我反嫁宿敌",
            "剧情主线": "她在婚礼当天被抛弃后，反手嫁给宿敌，用12集完成反杀。",
            "核心冲突": "女主要在前任与家族的双重羞辱中拿回尊严和主动权。",
            "集数": 12,
            "终局回报": "前任公开失势，女主赢回名声与感情主动权。",
            "人物弧线": ["林晚从受辱者变成设局者"],
            "关键节点": ["婚礼羞辱", "闪婚联盟", "公开反杀"],
        },
    )

    artifact = SeasonBible.model_validate(normalized)

    assert artifact.title_candidate == "退婚后我反嫁宿敌"
    assert artifact.target_episode_count == 12
    assert artifact.must_land_beats == ["婚礼羞辱", "闪婚联盟", "公开反杀"]


def test_normalize_payload_maps_common_episode_plan_aliases() -> None:
    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)

    normalized = client._normalize_payload(
        "episode_plan_generation",
        {
            "分集": [
                {
                    "集数": 1,
                    "标题": "婚礼反击",
                    "开场局面": "婚礼现场，新郎带旧爱现身。",
                    "本集核心冲突": "女主必须马上止损反击。",
                    "本集必须发生": ["当众受辱", "提出改嫁"],
                    "本集结尾钩子": "顾承骁说他知道偷拍视频是谁放的。",
                    "下一集铺垫": "下一集进入危险闪婚。",
                }
            ]
        },
    )

    artifact = EpisodePlanArtifact.model_validate(normalized)

    assert artifact.episodes[0].episode_number == 1
    assert artifact.episodes[0].hook_ending == "顾承骁说他知道偷拍视频是谁放的。"
