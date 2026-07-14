from dramaloop.prompts.structured_json import build_json_contract
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.episode_critique import EpisodeCritiqueArtifact
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


EPISODE_CRITIQUE_JSON_SCHEMA = """{
  \"episode_number\": 2,
  \"overall_score\": 7.0,
  \"dimension_scores\": {
    \"hook_strength\": 7.0,
    \"conflict_intensity\": 7.0,
    \"pacing\": 7.0,
    \"short_drama_feel\": 7.0,
    \"carryover\": 8.0
  },
  \"weakest_dimensions\": [\"pacing\"],
  \"rewrite_needed\": false,
  \"rewrite_target\": \"本集应强化中段冲突推进。\",
  \"issues\": [\"中段略慢\"]
}"""


def build_episode_critique_prompt(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    markdown: str,
) -> str:
    return "\n".join(
        [
            "你是中文短剧分集审稿助手。",
            *build_json_contract(
                EPISODE_CRITIQUE_JSON_SCHEMA,
                extra_rules=[
                    "dimension_scores 必须且只能包含这些 key：hook_strength、conflict_intensity、pacing、short_drama_feel、carryover。",
                    "每个维度分数都是 1 到 10 的数字。",
                    "第 1 集的 carryover 可给 8.0（无上一集可承接）。",
                    "当 overall_score < 7.0 或任维 < 6.0 时，rewrite_needed 必须为 true。",
                    "rewrite_target 必须是一句中文，说明本集应改什么。",
                    "weakest_dimensions 必须是已有维度 key 组成的数组。",
                    "issues 必须是数组。",
                ],
            ),
            f"整季标题：{season.title_candidate}",
            f"整季主冲突：{season.core_conflict}",
            f"当前集数：第{episode.episode_number}集《{episode.title}》",
            f"本集核心冲突：{episode.core_conflict}",
            f"本集必须发生：{'；'.join(episode.must_happen)}",
            f"本集计划结尾钩子：{episode.hook_ending}",
            f"上一集实际收尾信号：{continuity.last_episode_hook}",
            f"当前连续性摘要：{continuity.story_so_far_summary}",
            "请重点评估：短剧节奏、集末钩子、与上一集承接；禁止复述上一集剧情。",
            "输出 overall_score、dimension_scores、weakest_dimensions、rewrite_needed、rewrite_target、issues。",
            markdown,
        ]
    )


def build_episode_rewrite_prompt(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    markdown: str,
    critique: EpisodeCritiqueArtifact,
) -> str:
    must_happen = "；".join(episode.must_happen)
    return "\n".join(
        [
            "你是中文短剧分集改写助手。",
            f"整季标题：{season.title_candidate}",
            f"当前集数：第{episode.episode_number}集《{episode.title}》",
            f"只改 rewrite_target 指出的问题：{critique.rewrite_target}",
            f"必须保留本集 must_happen（必须发生情节）：{must_happen}",
            f"上一集实际收尾信号：{continuity.last_episode_hook}",
            f"本集计划结尾钩子：{episode.hook_ending}",
            f"已知问题：{'；'.join(critique.issues) if critique.issues else '无'}",
            "不要重写整集无关段落；不要复述上一集；保持短剧节奏与集末钩子。",
            "只输出改写后的连续中文正文，不要解释。",
            markdown,
        ]
    )
