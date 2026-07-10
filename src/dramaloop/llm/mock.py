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
    "season_planning": [
        {
            "title_candidate": "退婚后我反嫁宿敌",
            "series_logline": "她在婚礼当天被抛弃后，反手嫁给宿敌，用12集完成反杀。",
            "core_conflict": "女主要在前任与家族的双重羞辱中拿回尊严和主动权。",
            "target_episode_count": 12,
            "final_payoff": "前任公开失势，女主赢回名声与感情主动权。",
            "main_character_arcs": ["林晚从受辱者变成设局者"],
            "must_land_beats": ["婚礼羞辱", "闪婚联盟", "公开反杀"],
        }
    ],
    "episode_plan_generation": [
        {
            "episodes": [
                {
                    "episode_number": 1,
                    "title": "婚礼反击",
                    "opening_situation": "婚礼现场，新郎带旧爱现身。",
                    "core_conflict": "女主必须马上止损反击。",
                    "must_happen": ["当众受辱", "提出改嫁"],
                    "hook_ending": "顾承骁说他知道偷拍视频是谁放的。",
                    "sets_up_next": "下一集进入危险闪婚。",
                },
                {
                    "episode_number": 2,
                    "title": "危险闪婚",
                    "opening_situation": "顾承骁公开接住女主抛出的婚约。",
                    "core_conflict": "女主必须决定要不要借势反击。",
                    "must_happen": ["闪婚协议", "前任破防"],
                    "hook_ending": "顾承骁拿出了偷拍视频原件。",
                    "sets_up_next": "下一集追查幕后黑手。",
                },
                {
                    "episode_number": 3,
                    "title": "幕后线索",
                    "opening_situation": "两人开始追查偷拍视频来源。",
                    "core_conflict": "女主发现背后还有家族内鬼。",
                    "must_happen": ["追线索", "锁定嫌疑人"],
                    "hook_ending": "偷拍视频里出现了女主父亲的名字。",
                    "sets_up_next": "下一集家族冲突升级。",
                },
                {
                    "episode_number": 4,
                    "title": "家族逼宫",
                    "opening_situation": "家族长辈要求女主低头息事宁人。",
                    "core_conflict": "女主必须在家族压力下坚持反击。",
                    "must_happen": ["公开对抗长辈", "顾承骁站队"],
                    "hook_ending": "前任宣布要抢走她最后的项目。",
                    "sets_up_next": "下一集进入项目争夺战。",
                },
                {
                    "episode_number": 5,
                    "title": "项目争夺",
                    "opening_situation": "女主核心项目被前任截胡。",
                    "core_conflict": "她必须在名利场中抢回主动权。",
                    "must_happen": ["反制截胡", "拿到关键证据"],
                    "hook_ending": "顾承骁承认他早就喜欢她。",
                    "sets_up_next": "下一集感情和利益同时失控。",
                },
                {
                    "episode_number": 6,
                    "title": "真假试探",
                    "opening_situation": "女主怀疑顾承骁靠近她另有目的。",
                    "core_conflict": "两人关系在合作与真心之间摇摆。",
                    "must_happen": ["感情试探", "误会升级"],
                    "hook_ending": "前任手里突然多出一份她的黑料。",
                    "sets_up_next": "下一集黑料危机引爆。",
                },
                {
                    "episode_number": 7,
                    "title": "黑料引爆",
                    "opening_situation": "前任公开放出女主黑料。",
                    "core_conflict": "女主必须在舆论崩盘前翻盘。",
                    "must_happen": ["舆论反击", "找出造谣源头"],
                    "hook_ending": "幕后金主终于露面。",
                    "sets_up_next": "下一集直面幕后势力。",
                },
                {
                    "episode_number": 8,
                    "title": "幕后现身",
                    "opening_situation": "幕后金主逼迫女主彻底退场。",
                    "core_conflict": "女主与顾承骁必须联手破局。",
                    "must_happen": ["正面谈判", "布下反杀局"],
                    "hook_ending": "女主发现父亲旧案另有真相。",
                    "sets_up_next": "下一集翻旧案。",
                },
                {
                    "episode_number": 9,
                    "title": "旧案翻出",
                    "opening_situation": "父亲旧案成为新的突破口。",
                    "core_conflict": "女主必须在真相和复仇间做选择。",
                    "must_happen": ["拼凑旧案", "确认内鬼身份"],
                    "hook_ending": "顾承骁被对手设计陷害。",
                    "sets_up_next": "下一集救人反击。",
                },
                {
                    "episode_number": 10,
                    "title": "双线反扑",
                    "opening_situation": "顾承骁陷入危机，女主被迫独自上场。",
                    "core_conflict": "女主必须同时救人和保住局面。",
                    "must_happen": ["救顾承骁", "埋终局证据"],
                    "hook_ending": "前任以为自己赢了。",
                    "sets_up_next": "下一集进入终局前夜。",
                },
                {
                    "episode_number": 11,
                    "title": "终局前夜",
                    "opening_situation": "所有证据与人脉都被推上桌面。",
                    "core_conflict": "女主必须赌上最后一局。",
                    "must_happen": ["召集盟友", "锁定直播反杀方案"],
                    "hook_ending": "直播开始前，证据突然消失。",
                    "sets_up_next": "下一集公开终局反杀。",
                },
                {
                    "episode_number": 12,
                    "title": "公开反杀",
                    "opening_situation": "女主走上公开直播的终局战场。",
                    "core_conflict": "她必须当众完成对前任和幕后势力的终局反杀。",
                    "must_happen": ["公开翻案", "前任失势", "情感 payoff 落地"],
                    "hook_ending": "风波结束后，顾承骁问她还愿不愿意继续这场婚姻。",
                    "sets_up_next": "整季收束。",
                },
            ]
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
    "episode_draft_generation": [
        "第1集正文。婚礼大屏亮起时，林晚看见未婚夫牵着旧爱走进来，整个宴会厅都安静了一瞬。她指尖发冷，却没有哭，只是在所有人的注视下慢慢转身，看向角落里的顾承骁。这个男人是前任最恨的死对头，也是全场唯一还带着笑的人。林晚提着婚纱一步步走到他面前，声音不高，却足够让满场宾客听清：‘顾总，你还缺一个新娘吗？’ 满堂哗然。前任脸色骤变，冲过来想抓她的手，却被顾承骁先一步挡开。顾承骁垂眼看着她，像是在确认她是不是一时赌气。几秒后，他抬手替她扶正头纱，低声道：‘你敢嫁，我就敢替你把这场羞辱翻过来。’ 下一秒，他当众宣布婚礼继续，只是新郎换人。前任彻底失控，旧爱也白了脸。林晚以为这已经够疯了，没想到走下台时，顾承骁忽然贴近她耳边，声音压得极低：‘我知道偷拍视频是谁放的。’"
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
