from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def build_episode_draft_prompt(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    previous_summary: str | None,
    min_words: int,
    max_words: int,
) -> str:
    must_happen = "；".join(episode.must_happen)
    return "\n".join(
        [
            "你是中文短剧分集写手。",
            f"整季标题：{season.title_candidate}",
            f"整季主冲突：{season.core_conflict}",
            f"当前集数：第{episode.episode_number}集《{episode.title}》",
            f"上一集摘要：{previous_summary or '无，当前为第一集'}",
            f"当前连续性摘要：{continuity.story_so_far_summary}",
            f"本集开场：{episode.opening_situation}",
            f"本集核心冲突：{episode.core_conflict}",
            f"本集必须发生：{must_happen}",
            f"本集结尾钩子：{episode.hook_ending}",
            f"请输出连续中文正文，严格控制在{min_words}-{max_words}字。",
            "本集结尾必须落在钩子上。",
            "不要写成整部完结，只写当前这一集。",
        ]
    )
