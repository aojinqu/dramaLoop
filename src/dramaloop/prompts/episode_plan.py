from dramaloop.schemas.season import SeasonBible


def build_episode_plan_prompt(season: SeasonBible) -> str:
    return "\n".join(
        [
            "你是中文短剧分集规划师。",
            f"标题：{season.title_candidate}",
            f"整季 logline：{season.series_logline}",
            f"主冲突：{season.core_conflict}",
            f"总集数：{season.target_episode_count}",
            "请输出逐集规划。每集都要有结尾钩子，最终回收主冲突和 payoff。",
        ]
    )
