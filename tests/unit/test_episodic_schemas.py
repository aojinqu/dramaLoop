from pathlib import Path

import pytest
from pydantic import ValidationError

from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunManifest
from dramaloop.schemas.season import EpisodeArtifact


def test_story_request_accepts_episodic_series_defaults() -> None:
    request = StoryRequest(
        idea="她被退婚后反手结婚",
        style=["都市情感"],
        length="short",
        format="episodic_series",
    )

    assert request.format == "episodic_series"
    assert request.episode_count == 12
    assert request.episode_min_words == 500
    assert request.episode_max_words == 800
    assert request.delivery_mode == "stream_and_final"


def test_story_request_rejects_inverted_episode_word_range() -> None:
    with pytest.raises(ValidationError):
        StoryRequest(
            idea="她被退婚后反手结婚",
            style=["都市情感"],
            length="short",
            format="episodic_series",
            episode_min_words=900,
            episode_max_words=800,
        )


def test_episode_artifact_requires_hook_and_summary() -> None:
    artifact = EpisodeArtifact(
        episode_number=1,
        title="婚礼反击",
        markdown="第1集正文",
        word_count=620,
        episode_summary="婚礼现场反手改嫁。",
        hook_delivered="顾承骁说他知道偷拍视频是谁放的。",
        qa_passed=True,
    )

    assert artifact.word_count == 620
    assert artifact.qa_passed is True


def test_continuity_state_tracks_open_threads() -> None:
    state = ContinuityState(
        current_episode=3,
        story_so_far_summary="女主已完成改嫁并开始反击。",
        character_states={"林晚": "从受辱转向主动布局"},
        relationship_states={"林晚->顾承骁": "互相试探"},
        open_threads=["偷拍视频来源未揭晓"],
        resolved_threads=["婚礼羞辱已反击"],
        last_episode_hook="顾承骁拿出了录音笔",
    )

    assert state.open_threads == ["偷拍视频来源未揭晓"]


def test_run_manifest_tracks_episodic_progress() -> None:
    manifest = RunManifest(
        run_id="20260709-story",
        status="running",
        started_at="2026-07-09T12:00:00",
        model_provider="mock",
        model_name="claude-sonnet-5",
        format="episodic_series",
        max_iterations=2,
        total_episodes=12,
        completed_episodes=3,
        current_episode=4,
        target_threshold=7.5,
        minimum_dimension_threshold=6,
        min_delta=0.3,
    )

    assert manifest.format == "episodic_series"
    assert manifest.completed_episodes == 3
    assert manifest.current_episode == 4
