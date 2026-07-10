from dramaloop.schemas.input import StoryRequest


def build_season_prompt(request: StoryRequest) -> str:
    return "\n".join(
        [
            "你是中文短剧整季规划师。",
            f"故事想法：{request.idea}",
            f"风格标签：{', '.join(request.style)}",
            f"目标：规划一部 {request.episode_count}集 的连续短剧。",
            f"每集要求：{request.episode_min_words}-{request.episode_max_words}字。",
            "请产出整季设定、主冲突、人物弧线和最终 payoff。",
        ]
    )
