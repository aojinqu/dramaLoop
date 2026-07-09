from typing import Any

from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel


DEFAULT_STRUCTURED_OUTPUTS: dict[str, list[dict[str, Any]]] = {
    "premise_refinement": [
        {
            "title_candidate": "替嫁反击",
            "logline": "她被退婚后转身嫁给死对头。",
            "core_conflict": "两大家族的旧怨与新婚关系相互引爆。",
            "hook_promise": "婚礼羞辱后立刻反击。",
            "ending_payoff_plan": "前任公开失势，她赢回尊严。",
            "tone_notes": ["快节奏", "爽感强"],
            "hard_constraints": ["短篇"],
        }
    ],
    "character_card_generation": [
        {
            "characters": [
                {
                    "name": "林晚",
                    "role": "protagonist",
                    "public_identity": "珠宝设计师",
                    "core_desire": "夺回尊严与事业",
                    "core_fear": "再次成为被选择的人",
                    "hidden_secret": None,
                    "conflict_links": ["顾承骁", "陆闻舟"],
                    "voice_style": "冷静锋利",
                    "arc_target": "从隐忍到掌控局面",
                }
            ]
        }
    ],
    "story_outline_generation": [
        {
            "beats": [
                {"beat_id": "b1", "label": "hook", "purpose": "抓人", "summary": "婚礼被退婚", "tension_level": 9, "payoff_dependency": None},
                {"beat_id": "b2", "label": "inciting", "purpose": "冲突", "summary": "她当场改嫁死对头", "tension_level": 9, "payoff_dependency": None},
                {"beat_id": "b3", "label": "escalation", "purpose": "升级", "summary": "前任家族全线封杀", "tension_level": 8, "payoff_dependency": "b5"},
                {"beat_id": "b4", "label": "reveal", "purpose": "反转", "summary": "新婚丈夫早就布局复仇", "tension_level": 9, "payoff_dependency": "b5"},
                {"beat_id": "b5", "label": "payoff", "purpose": "回报", "summary": "前任众叛亲离", "tension_level": 10, "payoff_dependency": None},
            ],
            "ending_type": "revenge payoff",
        }
    ],
    "critique_scoring": [
        {
            "dimension_scores": {
                "hook_strength": {"score": 6, "reason": "开头抓人但还不够猛", "evidence": "婚礼羞辱出现得快，但反击力度还可以更锋利", "improvement_advice": "让开场台词更有爆点"},
                "character_consistency": {"score": 7, "reason": "人物动机清晰", "evidence": "林晚始终围绕尊严和反击行动", "improvement_advice": "增加一处更强的内心决断"},
                "conflict_intensity": {"score": 7, "reason": "冲突已建立", "evidence": "退婚与改嫁形成正面对撞", "improvement_advice": "中段继续抬高外部压力"},
                "pacing": {"score": 6, "reason": "节奏还算顺", "evidence": "从婚礼到反击推进较快，但中段略短", "improvement_advice": "补一小段升级桥接"},
                "short_drama_feel": {"score": 7, "reason": "短剧感已出现", "evidence": "钩子、羞辱、反击都在位", "improvement_advice": "把结尾打脸拉得更狠"},
                "ending_payoff": {"score": 5, "reason": "结尾回报不足", "evidence": "目前只有反击起手，没有形成完整终局反杀", "improvement_advice": "增加一段更明确的公开反杀场景"},
                "language_fluency": {"score": 7, "reason": "语言基本流畅", "evidence": "句式简洁，易读", "improvement_advice": "增加一句更利落的收尾台词"},
            },
            "overall_score": 6.43,
            "weakest_dimensions": ["ending_payoff", "hook_strength"],
            "rewrite_target": "ending_payoff",
            "rewrite_plan": {"scope": "结尾两段", "must_fix": ["增加终局反杀", "补强公开羞辱的回报感"], "keep": ["婚礼开头", "改嫁钩子"]},
        },
        {
            "dimension_scores": {
                "hook_strength": {"score": 8, "reason": "开头明显更抓人", "evidence": "婚礼羞辱后立刻接改嫁动作", "improvement_advice": "继续保持开场锋利度"},
                "character_consistency": {"score": 7, "reason": "人物动机稳定", "evidence": "林晚的尊严诉求始终一致", "improvement_advice": "后续可再加一处心理描写"},
                "conflict_intensity": {"score": 8, "reason": "冲突强度够高", "evidence": "公开直播反杀抬升了冲突级别", "improvement_advice": "后续可以补更强的对手反扑"},
                "pacing": {"score": 7, "reason": "节奏更完整", "evidence": "开头-反击-结尾回报形成闭环", "improvement_advice": "中段桥接仍可略压缩"},
                "short_drama_feel": {"score": 8, "reason": "短剧感明显", "evidence": "羞辱、闪婚、直播反杀都很短剧", "improvement_advice": "后续可增加一层反转"},
                "ending_payoff": {"score": 7, "reason": "结尾已有明确回报", "evidence": "林晚在公开场合完成体面反击", "improvement_advice": "结尾再加一击会更爽"},
                "language_fluency": {"score": 7, "reason": "语言顺畅", "evidence": "关键台词简洁有力", "improvement_advice": "保持句式利落"},
            },
            "overall_score": 7.43,
            "weakest_dimensions": ["pacing"],
            "rewrite_target": "opening_hook",
            "rewrite_plan": {"scope": "开头一段", "must_fix": ["让第一句更锋利"], "keep": ["结尾直播反杀", "核心冲突关系"]},
        },
    ],
}

DEFAULT_TEXT_OUTPUTS: dict[str, list[str]] = {
    "draft_generation": [
        "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n\n顾承骁看了她三秒，抬手替她摘下头纱：\"林小姐，你敢嫁，我就敢让他们今天一起难堪。\"\n"
    ],
    "targeted_rewrite": [
        "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n\n顾承骁看了她三秒，抬手替她摘下头纱：\"林小姐，你敢嫁，我就敢让他们今天一起难堪。\"\n\n最后一场董事会直播里，顾承骁把陆闻舟转移资产的证据推上屏幕。林晚接过话筒，盯着那张瞬间惨白的脸，慢慢开口：\"你在婚礼上丢掉的，不只是我，是你陆家最后一点体面。\"\n\n直播弹幕刷得满屏都是，陆闻舟想解释，却被股东当场请出了会场。林晚终于把那口气，原封不动地还了回去。\n"
    ],
}


class MockLLMClient(LLMClient):
    def __init__(
        self,
        *,
        structured_outputs: dict[str, dict[str, Any] | list[dict[str, Any]]],
        text_outputs: dict[str, str | list[str]],
    ) -> None:
        self._structured_outputs = {
            role: list(payloads) if isinstance(payloads, list) else [payloads]
            for role, payloads in structured_outputs.items()
        }
        self._text_outputs = {
            role: list(payloads) if isinstance(payloads, list) else [payloads]
            for role, payloads in text_outputs.items()
        }

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        try:
            payloads = self._structured_outputs[role]
        except KeyError as exc:
            raise LLMInvocationError(f"Missing mock structured output for role={role}") from exc
        payload = payloads.pop(0) if len(payloads) > 1 else payloads[0]
        return response_model.model_validate(payload)

    def generate_text(self, *, role: str, prompt: str) -> str:
        try:
            payloads = self._text_outputs[role]
        except KeyError as exc:
            raise LLMInvocationError(f"Missing mock text output for role={role}") from exc
        return payloads.pop(0) if len(payloads) > 1 else payloads[0]


def build_default_mock_client() -> MockLLMClient:
    return MockLLMClient(structured_outputs=DEFAULT_STRUCTURED_OUTPUTS, text_outputs=DEFAULT_TEXT_OUTPUTS)
