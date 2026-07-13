from dramaloop.llm.base import LLMClient
from dramaloop.prompts.characters import build_character_prompt
from dramaloop.prompts.critique import build_critique_prompt
from dramaloop.prompts.draft import build_draft_prompt
from dramaloop.prompts.episode_draft import build_episode_draft_prompt
from dramaloop.prompts.episode_plan import build_episode_plan_prompt
from dramaloop.prompts.outline import build_outline_prompt
from dramaloop.prompts.premise import build_premise_prompt
from dramaloop.prompts.rewrite import build_rewrite_prompt
from dramaloop.prompts.season import build_season_prompt
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.continuity import ContinuityState
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.schemas.rewrite import RewriteArtifact
from dramaloop.schemas.season import EpisodePlanArtifact, EpisodePlanItem, SeasonBible


def run_premise_stage(client: LLMClient, request: StoryRequest) -> PremiseArtifact:
    return client.generate_structured(
        role="premise_refinement",
        prompt=build_premise_prompt(request),
        response_model=PremiseArtifact,
    )


def run_season_stage(client: LLMClient, request: StoryRequest) -> SeasonBible:
    return client.generate_structured(
        role="season_planning",
        prompt=build_season_prompt(request),
        response_model=SeasonBible,
    )


def run_character_stage(client: LLMClient, premise: PremiseArtifact) -> CharacterArtifact:
    return client.generate_structured(
        role="character_card_generation",
        prompt=build_character_prompt(premise),
        response_model=CharacterArtifact,
    )


def run_outline_stage(client: LLMClient, premise: PremiseArtifact, characters: CharacterArtifact) -> OutlineArtifact:
    return client.generate_structured(
        role="story_outline_generation",
        prompt=build_outline_prompt(premise, characters),
        response_model=OutlineArtifact,
    )


def run_episode_plan_stage(
    client: LLMClient,
    season: SeasonBible,
    *,
    start_episode: int = 1,
    end_episode: int | None = None,
    prior_episodes: list[EpisodePlanItem] | None = None,
) -> EpisodePlanArtifact:
    return client.generate_structured(
        role="episode_plan_generation",
        prompt=build_episode_plan_prompt(
            season,
            start_episode=start_episode,
            end_episode=end_episode,
            prior_episodes=prior_episodes,
        ),
        response_model=EpisodePlanArtifact,
    )


def run_draft_stage(client: LLMClient, premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    return client.generate_text(
        role="draft_generation",
        prompt=build_draft_prompt(premise, characters, outline),
    )


def run_episode_draft_stage(
    client: LLMClient,
    season: SeasonBible,
    episode: EpisodePlanItem,
    continuity: ContinuityState,
    previous_summary: str | None,
    min_words: int,
    max_words: int,
    actual_total_episodes: int,
) -> str:
    return client.generate_text(
        role="episode_draft_generation",
        prompt=build_episode_draft_prompt(
            season,
            episode,
            continuity,
            previous_summary,
            min_words,
            max_words,
            actual_total_episodes,
        ),
    )


def run_critique_stage(
    client: LLMClient,
    draft_markdown: str,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
) -> CritiqueArtifact:
    return client.generate_structured(
        role="critique_scoring",
        prompt=build_critique_prompt(draft_markdown, premise, characters, outline),
        response_model=CritiqueArtifact,
    )


def run_rewrite_stage(
    client: LLMClient,
    draft_markdown: str,
    critique: CritiqueArtifact,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
    next_version: int,
) -> tuple[RewriteArtifact, str]:
    revised_draft = client.generate_text(
        role="targeted_rewrite",
        prompt=build_rewrite_prompt(draft_markdown, critique, premise, characters, outline),
    )
    rewrite_artifact = RewriteArtifact(
        version=next_version - 1,
        target_section=critique.rewrite_target,
        goals=critique.rewrite_plan.must_fix,
        changes_made=critique.rewrite_plan.must_fix,
        expected_score_improvement=critique.weakest_dimensions,
    )
    return rewrite_artifact, revised_draft
