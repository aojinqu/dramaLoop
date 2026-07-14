from pathlib import Path

from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.episode_critique import EpisodeCritiqueArtifact
from dramaloop.schemas.season import EpisodeArtifact, SeasonBible
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def build_initial_continuity_state(season: SeasonBible) -> ContinuityState:
    return ContinuityState(
        current_episode=1,
        story_so_far_summary=f"《{season.title_candidate}》刚开始，主冲突是：{season.core_conflict}",
        character_states={},
        relationship_states={},
        open_threads=list(season.must_land_beats),
        resolved_threads=[],
        last_episode_hook="故事即将开始",
    )


def write_episode_artifacts(run_dir: Path, artifact: EpisodeArtifact) -> None:
    episodes_dir = run_dir / "episodes"
    write_markdown_artifact(episodes_dir / f"episode_{artifact.episode_number:02d}.md", artifact.markdown)
    write_json_artifact(episodes_dir / f"episode_{artifact.episode_number:02d}.json", artifact)


def write_episode_critique_artifact(run_dir: Path, critique: EpisodeCritiqueArtifact) -> None:
    episodes_dir = run_dir / "episodes"
    write_json_artifact(
        episodes_dir / f"episode_{critique.episode_number:02d}_critique.json",
        critique,
    )
