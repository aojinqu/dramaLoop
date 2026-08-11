import json

import pytest
from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.llm import originality_planner as planner_module
from dramaloop.llm.base import LLMInvocationError
from dramaloop.llm.originality_planner import (
    OpenAICompatiblePlannerClient,
    build_originality_planner_client,
)
from dramaloop.prompts.originality import (
    PLANNER_SYSTEM_PROMPT,
    build_originality_plan_prompt,
)
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.originality import OriginalityPlan


def _request() -> StoryRequest:
    return StoryRequest(
        idea="港口调度员发现一批救援物资的封签编号被系统重复使用",
        style=["职业悬疑"],
        length="short",
        format="episodic_series",
        constraints=["不得依赖万能监控"],
    )


def _valid_plan_payload() -> dict:
    return {
        "idea": "港口调度员必须在潮汐窗口关闭前找出被重复使用的救援物资封签",
        "genre": "职业悬疑",
        "anti_cliche_constraints": ["不得依赖万能监控"],
        "novelty_mechanism": {
            "core_engine": "潮汐窗口、泊位权限和纸质封签共同决定物资能否离港",
            "conflict_source": "调度员的岗位职责与港口审批制度迫使她在救援时效和追责之间选择",
            "reversal_logic": "她主动冻结泊位后留下的调度缺口，反向暴露了重复封签的使用顺序",
            "irreplaceable_details": [
                "港口调度员的职业职责",
                "潮汐泊位这一核心场域",
                "物资离港审批制度",
                "带压痕的纸质封签物件",
                "师徒关系共同保管的调度日志",
            ],
            "why_it_cannot_be_swapped": "移除潮汐、泊位权限或封签后，救援时限与追责选择都不再成立",
        },
        "world_rules": [
            "潮位低于警戒线后任何救援船都不得更换泊位",
            "纸质封签与系统编号不一致时调度员必须亲自冻结离港权限",
        ],
        "character_arcs": [
            {
                "name": "周岚",
                "role": "主角",
                "desire": "按时送出救援物资并保住调度资格",
                "blind_spot": "相信服从流程就能避免承担道德责任",
                "choice_pressure": "必须在冻结救援船和放过重复封签之间承担一方损失",
                "arc_payoff": "从执行流程转变为主动承担规则后果",
            }
        ],
        "mechanism_beats": [
            {
                "stage": "首次冻结",
                "pressure": "潮汐窗口只剩四十分钟",
                "choice": "周岚冻结救援船离港权限",
                "consequence": "物资延误责任落到她的工牌记录上",
                "next_pressure": "她必须在复核会上证明封签重复早于冻结操作",
            },
            {
                "stage": "日志交换",
                "pressure": "师父拒绝提交纸质调度日志",
                "choice": "周岚公开两人的共同保管责任",
                "consequence": "师父失去调度权限，师徒联盟破裂",
                "next_pressure": "她只能用泊位变化还原封签流向",
            },
            {
                "stage": "潮位回收",
                "pressure": "复核会要求恢复离港以减少损失",
                "choice": "周岚坚持等到潮位记录与封签压痕完成比对",
                "consequence": "重复封签按离港顺序锁定到内部审批人",
                "next_pressure": "她必须承担救援延误并重建调度规则",
            },
        ],
    }


def test_originality_plan_enforces_concrete_chinese_quality() -> None:
    payload = _valid_plan_payload()
    payload["novelty_mechanism"]["irreplaceable_details"] = [
        "独特机制",
        "精彩冲突",
        "复杂设定",
        "有趣反转",
    ]

    with pytest.raises(ValidationError, match="at least three"):
        OriginalityPlan.model_validate(payload)


def test_originality_prompt_matches_trained_schema_and_request() -> None:
    prompt = build_originality_plan_prompt(_request())

    assert "港口调度员" in prompt
    assert "不得依赖万能监控" in prompt
    assert "三至五个机制推进节点" in prompt
    assert "novelty_mechanism" in PLANNER_SYSTEM_PROMPT
    assert "mechanism_beats" in PLANNER_SYSTEM_PROMPT
    assert "禁止输出 title" in PLANNER_SYSTEM_PROMPT


def test_openai_planner_retries_invalid_json_and_records_usage(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    responses = [
        {
            "model": "originality-planner",
            "choices": [
                {
                    "message": {"content": "not-json"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        },
        {
            "model": "originality-planner",
            "choices": [
                {
                    "message": {"content": json.dumps(_valid_plan_payload(), ensure_ascii=False)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 300},
        },
    ]
    requests = []

    class _Response:
        def __init__(self, payload: dict) -> None:
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def read(self) -> bytes:
            return json.dumps(self.payload, ensure_ascii=False).encode("utf-8")

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return _Response(responses.pop(0))

    monkeypatch.setattr(planner_module, "urlopen", fake_urlopen)
    client = OpenAICompatiblePlannerClient(
        api_key="secret",
        model_name="originality-planner",
        base_url="https://planner.example/v1/",
        timeout_seconds=9,
        max_retries=1,
    )

    plan = client.generate_structured(
        role="originality_mechanism_planning",
        prompt=build_originality_plan_prompt(_request()),
        response_model=OriginalityPlan,
    )

    assert plan.genre == "职业悬疑"
    assert len(requests) == 2
    sent = json.loads(requests[0][0].data)
    assert sent["messages"][0]["content"] == PLANNER_SYSTEM_PROMPT
    assert sent["model"] == "originality-planner"
    assert requests[0][1] == 9
    usage = client.drain_usage_records()
    assert [record["attempt"] for record in usage] == [1, 2]
    assert usage[-1]["output_tokens"] == 300


def test_build_planner_client_requires_key_when_endpoint_is_configured() -> None:
    settings = Settings(
        originality_planner_base_url="https://planner.example/v1",
        originality_planner_api_key=None,
    )

    with pytest.raises(LLMInvocationError, match="ORIGINALITY_PLANNER_API_KEY"):
        build_originality_planner_client(settings)
