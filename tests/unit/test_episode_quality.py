from dramaloop.prompts.episode_critique import (
    build_episode_critique_prompt,
    build_episode_rewrite_prompt,
)
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.episode_critique import EpisodeCritiqueArtifact
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
        episode_number=2,
        title="危险闪婚",
        opening_situation="顾承骁公开接住女主抛出的婚约。",
        core_conflict="女主必须决定要不要借势反击。",
        must_happen=["闪婚协议", "前任破防"],
        hook_ending="顾承骁拿出了偷拍视频原件。",
        sets_up_next="下一集追查幕后黑手。",
    )


def _continuity() -> ContinuityState:
    return ContinuityState(
        current_episode=2,
        story_so_far_summary="婚礼上公开反击后，林晚被顾承骁带走。",
        character_states={"林晚": "刚完成反击"},
        relationship_states={},
        open_threads=["偷拍视频来源"],
        resolved_threads=[],
        last_episode_hook="顾承骁说他知道偷拍视频是谁放的。",
    )


def _critique(*, overall_score: float = 5.5) -> EpisodeCritiqueArtifact:
    return EpisodeCritiqueArtifact(
        episode_number=2,
        overall_score=overall_score,
        dimension_scores={
            "hook_strength": 5.0,
            "conflict_intensity": 6.0,
            "pacing": 5.5,
            "short_drama_feel": 6.0,
            "carryover": 7.0,
            "originality": 5.0,
        },
        weakest_dimensions=["hook_strength", "pacing"],
        rewrite_needed=True,
        rewrite_target="强化集末钩子并加快中段冲突推进。",
        issues=["结尾钩子偏软", "中段节奏拖沓"],
    )


def test_episode_critique_schema_accepts_required_dimensions() -> None:
    critique = _critique()

    assert critique.overall_score == 5.5
    assert set(critique.dimension_scores) >= {
        "hook_strength",
        "conflict_intensity",
        "pacing",
        "short_drama_feel",
        "carryover",
        "originality",
    }
    assert critique.rewrite_needed is True
    assert "钩子" in critique.rewrite_target


def test_episode_critique_prompt_requires_json_and_continuity_constraints() -> None:
    prompt = build_episode_critique_prompt(
        _season(),
        _episode(),
        _continuity(),
        "顾承骁把婚约文件拍在桌上，林晚盯着签名栏。",
    )

    assert "只返回一个合法的 JSON object" in prompt
    assert "短剧节奏" in prompt
    assert "集末钩子" in prompt or "结尾钩子" in prompt
    assert "承接" in prompt
    assert "禁止复述" in prompt or "不要复述" in prompt
    assert "carryover" in prompt
    assert "hook_strength" in prompt
    assert "rewrite_needed" in prompt


def test_episode_rewrite_prompt_targets_critique_and_keeps_must_happen() -> None:
    critique = _critique()
    prompt = build_episode_rewrite_prompt(
        _season(),
        _episode(),
        _continuity(),
        "顾承骁把婚约文件拍在桌上。",
        critique,
    )

    assert critique.rewrite_target in prompt
    assert "闪婚协议" in prompt
    assert "must_happen" in prompt or "必须发生" in prompt
    assert "只改" in prompt or "只修复" in prompt


def test_episode_critique_and_rewrite_stages_parse_via_mock() -> None:
    from dramaloop.harness.stages import run_episode_critique_stage, run_episode_rewrite_stage
    from dramaloop.llm.mock import MockLLMClient

    draft = "顾承骁把婚约文件拍在桌上，林晚盯着签名栏。"
    rewritten = draft + " 她终于提笔签字，顾承骁随即抽出偷拍视频原件。"
    client = MockLLMClient(
        structured_outputs={
            "episode_critique_scoring": {
                "episode_number": 2,
                "overall_score": 5.5,
                "dimension_scores": {
                    "hook_strength": 5.0,
                    "conflict_intensity": 6.0,
                    "pacing": 5.5,
                    "short_drama_feel": 6.0,
                    "carryover": 7.0,
                    "originality": 5.0,
                },
                "weakest_dimensions": ["hook_strength", "pacing"],
                "rewrite_needed": True,
                "rewrite_target": "强化集末钩子并加快中段冲突推进。",
                "issues": ["结尾钩子偏软"],
            }
        },
        text_outputs={"episode_targeted_rewrite": rewritten},
    )

    critique = run_episode_critique_stage(client, _season(), _episode(), _continuity(), draft)
    assert critique.rewrite_needed is True
    assert critique.overall_score < 7.0

    revised = run_episode_rewrite_stage(
        client, _season(), _episode(), _continuity(), draft, critique
    )
    assert revised != draft
    assert "偷拍视频原件" in revised
