import json

from dramaloop.prompts.structured_json import build_json_contract
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.originality import OriginalityPlan


SEASON_JSON_SCHEMA = """{
  "title_candidate": "短剧标题",
  "series_logline": "一句话概括整季主线",
  "core_conflict": "整季核心冲突",
  "target_episode_count": 12,
  "final_payoff": "最终情绪与剧情回报",
  "main_character_arcs": ["主角弧线", "关键配角弧线"],
  "must_land_beats": ["必须回收的关键节点1", "必须回收的关键节点2"]
}"""


def build_season_prompt(
    request: StoryRequest,
    originality_plan: OriginalityPlan | None = None,
) -> str:
    lines = [
        "你是中文短剧整季规划师。",
    ]
    if originality_plan is not None:
        lines.extend(
            [
                "以下原创机制计划是上游已验证的强约束，必须落实到整季冲突、人物弧线和关键节点，"
                "不得退回可替换的通用套路：",
                json.dumps(
                    originality_plan.model_dump(mode="json"),
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
            ]
        )
    lines.extend(
        [
            *build_json_contract(
                SEASON_JSON_SCHEMA,
                extra_rules=[
                    f"target_episode_count must equal {request.episode_count}.",
                    "main_character_arcs must be an array with at least 1 item.",
                    "must_land_beats must be an array with at least 3 concrete beats.",
                    "All values should be concise Chinese text except the numeric episode count.",
                    "整季必须包含与具体职业、地域、制度或物件绑定的独特冲突机制。",
                    "除非用户明确要求，不要默认使用退婚改嫁、豪门继承、重生复仇、直播打脸或神秘大佬救场。",
                    "至少一条人物弧线必须来自价值观或职责冲突，而不是误会解除或恋爱确认。",
                ],
            ),
            f"故事想法：{request.idea}",
            f"风格标签：{', '.join(request.style)}",
            f"受众：{request.audience or 'general'}",
            f"额外约束：{', '.join(request.constraints) or 'none'}",
            f"目标：规划一部 {request.episode_count}集 的连续短剧。",
            f"每集要求：{request.episode_min_words}-{request.episode_max_words}字。",
            "请产出整季设定、主冲突、人物弧线和最终 payoff。",
        ]
    )
    return "\n".join(lines)
