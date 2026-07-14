from dramaloop.harness.stages import run_episode_critique_stage, run_episode_rewrite_stage
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.episode_critique import EpisodeCritiqueArtifact
from dramaloop.schemas.season import EpisodePlanItem, SeasonBible


def run_episode_quality_loop(
    client: LLMClient,
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    markdown: str,
) -> tuple[str, EpisodeCritiqueArtifact, bool]:
    """Critique an episode and optionally apply one targeted rewrite.

    Returns (final_markdown, critique, rewrite_applied).
    """
    critique = run_episode_critique_stage(client, season, episode, continuity, markdown)
    if not critique.rewrite_needed:
        return markdown, critique, False
    rewritten = run_episode_rewrite_stage(client, season, episode, continuity, markdown, critique)
    return rewritten, critique, True
