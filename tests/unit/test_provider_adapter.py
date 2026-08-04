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


def test_parse_structured_response_text_accepts_json_fence() -> None:
    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)

    payload = client._parse_structured_response_text(
        """```json
        {"episodes": [{"episode_number": 1, "title": "婚礼反击", "opening_situation": "婚礼现场", "core_conflict": "马上反击", "must_happen": ["提出改嫁"], "hook_ending": "他知道偷拍视频是谁放的", "sets_up_next": "进入下一集"}]}
        ```"""
    )

    artifact = EpisodePlanArtifact.model_validate(payload)

    assert artifact.episodes[0].episode_number == 1


def test_parse_structured_response_text_accepts_prefixed_json() -> None:
    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)

    payload = client._parse_structured_response_text(
        """好的，以下是分集规划：
        {"episodes": [{"episode_number": 1, "title": "婚礼反击", "opening_situation": "婚礼现场", "core_conflict": "马上反击", "must_happen": ["提出改嫁"], "hook_ending": "他知道偷拍视频是谁放的", "sets_up_next": "进入下一集"}]}
        """
    )

    artifact = EpisodePlanArtifact.model_validate(payload)

    assert artifact.episodes[0].title == "婚礼反击"


def test_generate_structured_retries_when_first_attempt_is_truncated() -> None:
    class _FakeBlock:
        def __init__(self, text: str) -> None:
            self.type = "text"
            self.text = text

    class _FakeResponse:
        def __init__(self, text: str, stop_reason: str | None = None) -> None:
            self.content = [_FakeBlock(text)]
            self.stop_reason = stop_reason

    class _FakeMessages:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                return _FakeResponse('{"episodes": [{"episode_number": 1, "title": "意外重来"', stop_reason="max_tokens")
            return _FakeResponse(
                '{"episodes": [{"episode_number": 1, "title": "意外重来", "opening_situation": "回到关键节点。", "core_conflict": "决定是否改命。", "must_happen": ["先验证重生", "试着改写错误"], "hook_ending": "他发现第一次改命带来代价。", "sets_up_next": "下一集进入第一次选择。"}]}'
            )

    class _FakeClient:
        def __init__(self) -> None:
            self.messages = _FakeMessages()

    client = AnthropicCompatibleLLMClient.__new__(AnthropicCompatibleLLMClient)
    client._client = _FakeClient()
    client._model_name = "fake-model"

    artifact = client.generate_structured(
        role="episode_plan_generation",
        prompt="生成分集规划",
        response_model=EpisodePlanArtifact,
    )

    assert artifact.episodes[0].title == "意外重来"
    assert client._client.messages.calls == 2
    assert client.last_realization_result is not None
    assert client.last_realization_result.status == "retried"
