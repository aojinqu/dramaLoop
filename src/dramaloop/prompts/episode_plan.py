from dramaloop.schemas.season import SeasonBible


EPISODE_PLAN_JSON_SCHEMA = '''{
  "episodes": [
    {
      "episode_number": 1,
      "title": "第1集标题",
      "opening_situation": "本集开场局面",
      "core_conflict": "本集核心冲突",
      "must_happen": ["本集必须发生的事件1", "本集必须发生的事件2"],
      "hook_ending": "本集结尾钩子",
      "sets_up_next": "如何铺垫下一集"
    }
  ]
}'''


def build_episode_plan_prompt(season: SeasonBible) -> str:
    return "\n".join(
        [
            "你是中文短剧分集规划师。",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            EPISODE_PLAN_JSON_SCHEMA,
            f"标题：{season.title_candidate}",
            f"整季 logline：{season.series_logline}",
            f"主冲突：{season.core_conflict}",
            f"总集数：{season.target_episode_count}",
            f"最终 payoff：{season.final_payoff}",
            f"人物弧线：{'；'.join(season.main_character_arcs)}",
            f"必须回收节点：{'；'.join(season.must_land_beats)}",
            "请输出逐集规划。每集都要有结尾钩子，最终回收主冲突和 payoff。",
        ]
    )
