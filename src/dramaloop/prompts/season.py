from dramaloop.schemas.input import StoryRequest


SEASON_JSON_SCHEMA = '''{
  "title_candidate": "短剧标题",
  "series_logline": "一句话概括整季主线",
  "core_conflict": "整季核心冲突",
  "target_episode_count": 12,
  "final_payoff": "最终情绪与剧情回报",
  "main_character_arcs": ["主角弧线", "关键配角弧线"],
  "must_land_beats": ["必须回收的关键节点1", "必须回收的关键节点2"]
}'''


def build_season_prompt(request: StoryRequest) -> str:
    return "\n".join(
        [
            "你是中文短剧整季规划师。",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            SEASON_JSON_SCHEMA,
            f"故事想法：{request.idea}",
            f"风格标签：{', '.join(request.style)}",
            f"受众：{request.audience or 'general'}",
            f"额外约束：{', '.join(request.constraints) or 'none'}",
            f"目标：规划一部 {request.episode_count}集 的连续短剧。",
            f"每集要求：{request.episode_min_words}-{request.episode_max_words}字。",
            "请产出整季设定、主冲突、人物弧线和最终 payoff。",
        ]
    )
