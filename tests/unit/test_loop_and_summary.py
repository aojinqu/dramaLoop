from dramaloop.config import Settings
from dramaloop.eval.scorer import calculate_overall_score
from dramaloop.harness.loop import determine_stop_reason, should_continue_loop
from dramaloop.schemas.critique import CritiqueArtifact, DimensionCritique, RewritePlan
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.rewrite import RewriteArtifact
from dramaloop.utils.markdown import render_run_summary


def _critique(score_map: dict[str, int], target: str = "ending_payoff") -> CritiqueArtifact:
    return CritiqueArtifact(
        dimension_scores={
            name: DimensionCritique(score=value, reason="ok", evidence="proof", improvement_advice="improve")
            for name, value in score_map.items()
        },
        overall_score=round(sum(score_map.values()) / len(score_map), 2),
        weakest_dimensions=[min(score_map, key=score_map.get)],
        rewrite_target=target,
        rewrite_plan=RewritePlan(scope="ending", must_fix=["ending"], keep=["opening"]),
    )


def test_should_continue_loop_when_score_is_below_threshold() -> None:
    settings = Settings()
    critique = _critique(
        {
            "hook_strength": 6,
            "character_consistency": 7,
            "conflict_intensity": 6,
            "pacing": 6,
            "short_drama_feel": 6,
            "ending_payoff": 5,
            "language_fluency": 7,
        }
    )

    assert should_continue_loop(None, critique, settings, iteration=1, max_iterations=2) is True
    assert determine_stop_reason(None, critique, settings, iteration=1, max_iterations=2) is None


def test_should_stop_loop_when_gain_is_too_small() -> None:
    settings = Settings()
    critique = _critique(
        {
            "hook_strength": 7,
            "character_consistency": 7,
            "conflict_intensity": 7,
            "pacing": 7,
            "short_drama_feel": 7,
            "ending_payoff": 7,
            "language_fluency": 7,
        }
    )

    assert should_continue_loop(6.85, critique, settings, iteration=2, max_iterations=3) is False
    assert determine_stop_reason(6.85, critique, settings, iteration=2, max_iterations=3) == "minimum_dimension_threshold_reached"


def test_loop_does_not_stop_on_high_overall_when_originality_is_below_floor() -> None:
    settings = Settings()
    critique = _critique(
        {
            "hook_strength": 9,
            "character_consistency": 8,
            "conflict_intensity": 9,
            "pacing": 8,
            "short_drama_feel": 9,
            "ending_payoff": 8,
            "language_fluency": 8,
            "originality": 4,
        },
        target="originality_revision",
    )

    assert critique.overall_score >= settings.target_threshold
    assert should_continue_loop(None, critique, settings, iteration=1, max_iterations=2)


def test_render_run_summary_includes_score_table_and_rewrite_notes() -> None:
    request = StoryRequest(idea="她被退婚后闪婚死对头", style=["都市情感"], length="short")
    critique_history = [
        _critique(
            {
                "hook_strength": 6,
                "character_consistency": 7,
                "conflict_intensity": 6,
                "pacing": 5,
                "short_drama_feel": 6,
                "ending_payoff": 5,
                "language_fluency": 7,
            }
        ),
        _critique(
            {
                "hook_strength": 8,
                "character_consistency": 7,
                "conflict_intensity": 8,
                "pacing": 7,
                "short_drama_feel": 8,
                "ending_payoff": 7,
                "language_fluency": 7,
            },
            target="opening_hook",
        ),
    ]
    rewrite_history = [
        RewriteArtifact(
            version=1,
            target_section="ending_payoff",
            goals=["兑现回报"],
            changes_made=["补强结尾反杀"],
            expected_score_improvement=["ending_payoff", "short_drama_feel"],
        )
    ]

    markdown = render_run_summary(
        request=request,
        critique_history=critique_history,
        rewrite_history=rewrite_history,
        final_story_path="final_story.md",
        stop_reason="target_threshold_reached",
    )

    assert "| Version | Hook | Character | Conflict | Pacing | Drama Feel | Ending | Fluency | Originality | Overall |" in markdown
    assert "补强结尾反杀" in markdown
    assert "final_story.md" in markdown
    assert "Pacing -> ok" in markdown
    assert calculate_overall_score(critique_history[1]) > calculate_overall_score(critique_history[0])
