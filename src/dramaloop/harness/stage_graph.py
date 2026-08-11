from dramaloop.schemas.stage import StageSpec


_STAGES = (
    StageSpec(
        name="premise_refinement",
        input_schema="StoryRequest",
        output_schema="PremiseArtifact",
        required_context=["request"],
        artifact_outputs=["premise.json"],
        contract_rules=["preserve user constraints in hard constraints"],
        forbidden_behaviors=["replace the requested protagonist or premise"],
    ),
    StageSpec(
        name="character_card_generation",
        input_schema="PremiseArtifact",
        output_schema="CharacterArtifact",
        required_context=["premise"],
        optional_context=["request"],
        artifact_outputs=["characters.json"],
        contract_rules=["characters must support the premise conflict"],
    ),
    StageSpec(
        name="story_outline_generation",
        input_schema="OutlineInput",
        output_schema="OutlineArtifact",
        required_context=["premise", "characters"],
        optional_context=["request"],
        artifact_outputs=["outline.json"],
        contract_rules=["outline must preserve established character relationships"],
    ),
    StageSpec(
        name="draft_generation",
        input_schema="DraftInput",
        output_schema="Markdown",
        required_context=["premise", "characters", "outline"],
        optional_context=["semantic_facts"],
        artifact_outputs=["draft_v1.md"],
    ),
    StageSpec(
        name="critique_scoring",
        input_schema="CritiqueInput",
        output_schema="CritiqueArtifact",
        required_context=["draft", "premise", "characters", "outline"],
        artifact_outputs=["critique_v{iteration}.json"],
        contract_rules=["all configured quality dimensions must be scored"],
    ),
    StageSpec(
        name="targeted_rewrite",
        input_schema="RewriteInput",
        output_schema="RewriteOutput",
        required_context=["draft", "critique", "rewrite_target"],
        optional_context=["semantic_facts", "unresolved_threads"],
        artifact_outputs=["rewrite_plan_v{iteration}.json", "draft_v{next_iteration}.md"],
        contract_rules=[
            "rewrite must address the weakest critique dimensions",
            "rewrite must preserve established character relationships",
        ],
        forbidden_behaviors=["drop required user constraints"],
        common_failure_modes=["generic polish without fixing weak dimension"],
    ),
    StageSpec(
        name="originality_mechanism_planning",
        input_schema="StoryRequest",
        output_schema="OriginalityPlan",
        required_context=["request"],
        artifact_outputs=["originality_plan.json"],
        contract_rules=[
            "bind conflict to concrete profession, setting, institution, object, or relationship",
            "derive reversals from established rules and character choices",
        ],
        forbidden_behaviors=["write episode prose or replace schema fields"],
    ),
    StageSpec(
        name="season_planning",
        input_schema="StoryRequest",
        output_schema="SeasonBible",
        required_context=["request"],
        optional_context=["originality_plan"],
        artifact_outputs=["season_bible.json"],
        contract_rules=["realize the supplied originality plan when one is present"],
    ),
    StageSpec(
        name="episode_plan_generation",
        input_schema="EpisodePlanInput",
        output_schema="EpisodePlanArtifact",
        required_context=["season"],
        optional_context=["prior_episodes", "semantic_facts"],
        artifact_outputs=["episode_plan.json", "continuity_state.json"],
    ),
    StageSpec(
        name="episode_draft_generation",
        input_schema="EpisodeDraftInput",
        output_schema="Markdown",
        required_context=["season", "episode_plan", "continuity"],
        optional_context=["episode_memory", "semantic_facts", "unresolved_threads"],
        artifact_outputs=[
            "episodes/episode_{episode_number}.md",
            "episodes/episode_{episode_number}.json",
            "continuity_state.json",
        ],
        contract_rules=["carry at least one unresolved thread into the hook"],
        common_failure_modes=["episode restart", "continuity drift"],
    ),
    StageSpec(
        name="episode_critique_scoring",
        input_schema="EpisodeCritiqueInput",
        output_schema="EpisodeCritiqueArtifact",
        required_context=["episode_draft", "episode_plan", "continuity"],
        artifact_outputs=["episodes/episode_{episode_number}_critique.json"],
    ),
    StageSpec(
        name="episode_targeted_rewrite",
        input_schema="EpisodeRewriteInput",
        output_schema="Markdown",
        required_context=["episode_draft", "episode_critique", "rewrite_target"],
        optional_context=["unresolved_threads", "semantic_facts"],
        artifact_outputs=[
            "episodes/episode_{episode_number}.md",
            "episodes/episode_{episode_number}.json",
        ],
    ),
    StageSpec(
        name="final_assembly",
        input_schema="RunArtifacts",
        output_schema="Markdown",
        required_context=["completed_drafts"],
        artifact_outputs=["final_story.md", "run_summary.md"],
    ),
)

_REGISTRY = {stage.name: stage for stage in _STAGES}

_FORMAT_STAGES = {
    "single_story": (
        "premise_refinement",
        "character_card_generation",
        "story_outline_generation",
        "draft_generation",
        "critique_scoring",
        "targeted_rewrite",
        "final_assembly",
    ),
    "episodic_series": (
        "originality_mechanism_planning",
        "season_planning",
        "episode_plan_generation",
        "episode_draft_generation",
        "episode_critique_scoring",
        "episode_targeted_rewrite",
        "final_assembly",
    ),
}


def get_stage_spec(name: str) -> StageSpec:
    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"Unknown stage: {name}") from exc


def list_stage_specs() -> list[StageSpec]:
    return list(_STAGES)


def stage_names_for_format(format_name: str) -> list[str]:
    try:
        names = _FORMAT_STAGES[format_name]
    except KeyError as exc:
        raise KeyError(f"Unknown story format: {format_name}") from exc
    return [get_stage_spec(name).name for name in names]
