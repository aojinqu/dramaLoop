from dramaloop.prompts.episode_check import build_episode_check_prompt
from dramaloop.prompts.episode_draft import build_episode_draft_prompt
from dramaloop.prompts.episode_plan import build_episode_plan_prompt
from dramaloop.prompts.season import build_season_prompt
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def _season() -> SeasonBible:
    return SeasonBible(
        title_candidate="退婚反杀",
        series_logline="她被退婚后反手嫁给死对头，12 集内完成逆袭。",
        core_conflict="女主要在婚礼羞辱后拿回尊严并反杀前任。",
        target_episode_count=12,
        final_payoff="前任公开失势，女主赢回名声与主动权。",
        main_character_arcs=["林晚从受辱变成设局者"],
        must_land_beats=["婚礼羞辱", "闪婚联盟", "公开反杀"],
    )


def _episode() -> EpisodePlanItem:
    return EpisodePlanItem(
        episode_number=1,
        title="婚礼反击",
        opening_situation="婚礼现场，新郎带旧爱现身。",
        core_conflict="女主必须马上止损反击。",
        must_happen=["当众受辱", "反手提出改嫁"],
        hook_ending="顾承骁说他知道偷拍视频是谁放的。",
        sets_up_next="下一集进入危险闪婚。",
    )


def _continuity() -> ContinuityState:
    return ContinuityState(
        current_episode=1,
        story_so_far_summary="故事刚开始。",
        character_states={"林晚": "仍在受辱边缘"},
        relationship_states={},
        open_threads=["偷拍视频来源"],
        resolved_threads=[],
        last_episode_hook="婚礼开始前的大屏忽然亮了",
    )


def test_season_prompt_mentions_twelve_episode_series() -> None:
    request = StoryRequest(
        idea="她被退婚后反手嫁给死对头",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    prompt = build_season_prompt(request)

    assert "12集" in prompt
    assert "500-800字" in prompt


def test_episode_plan_prompt_mentions_hook_and_payoff() -> None:
    prompt = build_episode_plan_prompt(_season())

    assert "每集都要有结尾钩子" in prompt
    assert "最终回收" in prompt


def test_episode_draft_prompt_contains_word_range_and_hook_requirement() -> None:
    prompt = build_episode_draft_prompt(_season(), _episode(), _continuity(), None, 500, 800)

    assert "500-800字" in prompt
    assert "本集结尾必须落在钩子上" in prompt
    assert "不要写成整部完结" in prompt


def test_episode_check_prompt_requires_continuity_and_hook_validation() -> None:
    prompt = build_episode_check_prompt("第 1 集正文", _episode(), _continuity(), 500, 800)

    assert "是否承接上一集" in prompt
    assert "是否有结尾钩子" in prompt
    assert "qa_passed" in prompt
