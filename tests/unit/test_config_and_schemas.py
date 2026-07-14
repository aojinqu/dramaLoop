from pathlib import Path

import pytest
from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.schemas.critique import CritiqueArtifact, DimensionCritique
from dramaloop.schemas.input import StoryRequest


def test_story_request_applies_defaults() -> None:
    request = StoryRequest(
        idea="她在婚礼上被抛弃后反手嫁给了宿敌",
        style=["都市情感", "狗血短剧感"],
        length="short",
    )

    assert request.max_iterations == 2
    assert request.constraints == []
    assert request.audience is None
    assert request.format == "single_story"
    assert request.episode_count == 12
    assert request.episode_min_words == 500
    assert request.episode_max_words == 800
    assert request.delivery_mode == "stream_and_final"


def test_story_request_rejects_long_form_length() -> None:
    with pytest.raises(ValidationError):
        StoryRequest(idea="x", style=["都市"], length="novel")


def test_critique_rejects_unknown_rewrite_target() -> None:
    with pytest.raises(ValidationError):
        CritiqueArtifact(
            dimension_scores={
                "hook_strength": DimensionCritique(score=7, reason="ok", evidence="line 1", improvement_advice="sharpen"),
                "character_consistency": DimensionCritique(score=7, reason="ok", evidence="line 2", improvement_advice="keep"),
                "conflict_intensity": DimensionCritique(score=6, reason="ok", evidence="line 3", improvement_advice="raise stakes"),
                "pacing": DimensionCritique(score=6, reason="ok", evidence="line 4", improvement_advice="trim"),
                "short_drama_feel": DimensionCritique(score=7, reason="ok", evidence="line 5", improvement_advice="push twist"),
                "ending_payoff": DimensionCritique(score=5, reason="ok", evidence="line 6", improvement_advice="pay off"),
                "language_fluency": DimensionCritique(score=8, reason="ok", evidence="line 7", improvement_advice="keep"),
            },
            overall_score=6.6,
            weakest_dimensions=["ending_payoff"],
            rewrite_target="full_rewrite",
            rewrite_plan={"scope": "ending", "must_fix": ["ending"], "keep": ["opening"]},
        )


def test_settings_defaults_use_repo_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings()

    assert settings.runs_dir == Path("runs")
    assert settings.evals_dir == Path("evals")
    assert settings.target_threshold == 7.5
    assert settings.minimum_dimension_threshold == 6
    assert settings.min_delta == 0.3
