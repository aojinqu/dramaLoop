from dramaloop.schemas.season import SeasonBible
from dramaloop.schemas.season import EpisodePlanItem
from dramaloop.prompts.structured_json import build_json_contract


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


def build_episode_plan_prompt(
    season: SeasonBible,
    *,
    start_episode: int = 1,
    end_episode: int | None = None,
    prior_episodes: list[EpisodePlanItem] | None = None,
) -> str:
    end_episode = end_episode or season.target_episode_count
    prior_episodes = prior_episodes or []
    expected_count = end_episode - start_episode + 1
    prior_context = (
        f"上一段已规划到第{prior_episodes[-1].episode_number}集《{prior_episodes[-1].title}》，"
        f"其结尾钩子为：{prior_episodes[-1].hook_ending}"
        if prior_episodes
        else "当前是第一段分集规划，无需承接前一段已规划内容。"
    )
    return "\n".join(
        [
            "你是中文短剧分集规划师。",
            *build_json_contract(
                EPISODE_PLAN_JSON_SCHEMA,
                extra_rules=[
                    f"episodes 必须刚好包含 {expected_count} 个条目。",
                    f"episode_number 必须从 {start_episode} 开始连续递增到 {end_episode}。",
                    "每一集都必须包含 schema 中展示的全部字段。",
                    "must_happen 必须是数组，且至少包含 2 个具体事件。",
                    "每个 episode item 内不要嵌套额外对象。",
                    "除 episode_number 外，分集规划内容都应使用中文。",
                ],
            ),
            f"标题：{season.title_candidate}",
            f"整季 logline：{season.series_logline}",
            f"主冲突：{season.core_conflict}",
            f"总集数：{season.target_episode_count}",
            f"本次只规划：第{start_episode}-{end_episode}集",
            f"最终 payoff：{season.final_payoff}",
            f"人物弧线：{'；'.join(season.main_character_arcs)}",
            f"必须回收节点：{'；'.join(season.must_land_beats)}",
            prior_context,
            "请只输出本次范围内的逐集规划。每集都要有结尾钩子，这一段的开头与上一段已规划内容保持连续，并为后续最终回收主冲突和 payoff 做铺垫。",
        ]
    )
