from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def build_episode_draft_prompt(
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    previous_summary: str | None,
    min_words: int,
    max_words: int,
    actual_total_episodes: int,
) -> str:
    must_happen = "；".join(episode.must_happen)
    continuity_rules: list[str] = []
    if episode.episode_number > 1:
        continuity_rules.extend(
            [
                "非第一集开篇必须直接承接上一集钩子或当前局面，写成连续剧情的串行续集。",
                "不要把故事重写成第1集，不要重新介绍前提设定或像初次登场一样重置人物关系与冲突状态。",
                "保持当前关系和冲突状态连续，推进本集计划事件，并在结尾落到本集钩子上。",
                f"开头前两句必须明确承接上一集实际收尾信号“{continuity.last_episode_hook}”，至少要点出其中一个关键人物、动作、物件或冲突结果。",
                "这种承接必须写进正文开头，不能只做抽象概述，也不能只在中段才补充。",
            ]
        )
    payoff_rule = (
        f"本集是本次生成请求的最终第{actual_total_episodes}集，可以完整回收整季最终回收：{season.final_payoff}。"
        if episode.episode_number == actual_total_episodes
        else f"整季最终回收“{season.final_payoff}”只允许在本次生成请求的最终第{actual_total_episodes}集完成，当前集不要提前写成整季完结。"
    )
    ending_scope_rule = (
        f"作为本次生成请求的最终第{actual_total_episodes}集，允许完成这一轮输出的收束，但仍只写当前这一集的正文。"
        if episode.episode_number == actual_total_episodes
        else "不要写成整部完结，只写当前这一集。"
    )
    return "\n".join(
        [
            "你是中文短剧分集写手。",
            f"这是一个共{actual_total_episodes}集的本次输出连续短剧，本集只是其中一集。",
            f"整季原始规划集数：{season.target_episode_count}集。",
            f"整季标题：{season.title_candidate}",
            f"整季主冲突：{season.core_conflict}",
            f"当前集数：第{episode.episode_number}集《{episode.title}》",
            f"上一集摘要：{previous_summary or '无，当前为第一集'}",
            f"当前连续性摘要：{continuity.story_so_far_summary}",
            f"上一集实际收尾信号：{continuity.last_episode_hook}",
            f"本集开场：{episode.opening_situation}",
            f"本集核心冲突：{episode.core_conflict}",
            f"本集必须发生：{must_happen}",
            f"本集计划结尾钩子：{episode.hook_ending}",
            (
                f"建议开头写法：承接“{continuity.last_episode_hook}”后，立刻进入“{episode.opening_situation}”。"
                if episode.episode_number > 1
                else f"建议开头写法：直接从“{episode.opening_situation}”切入冲突。"
            ),
            *continuity_rules,
            payoff_rule,
            f"请输出连续中文正文，严格控制在{min_words}-{max_words}字。",
            "本集结尾必须落在钩子上。",
            "使用当前故事独有的职业、场域、制度或物件细节推进冲突，避免把每集都写成拿到证据后公开打脸。",
            "反转应由人物选择和已出现的信息引发，不要临时加入神秘身份、大佬救场或万能录音。",
            ending_scope_rule,
        ]
    )
