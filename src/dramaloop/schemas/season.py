from pydantic import BaseModel, Field


class SeasonBible(BaseModel):
    title_candidate: str = Field(min_length=1)
    series_logline: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    target_episode_count: int = Field(ge=1)
    final_payoff: str = Field(min_length=1)
    main_character_arcs: list[str] = Field(min_length=1)
    must_land_beats: list[str] = Field(min_length=1)


class EpisodePlanItem(BaseModel):
    episode_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    opening_situation: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    must_happen: list[str] = Field(min_length=1)
    hook_ending: str = Field(min_length=1)
    sets_up_next: str = Field(min_length=1)


class EpisodePlanArtifact(BaseModel):
    episodes: list[EpisodePlanItem] = Field(min_length=1)


class EpisodeArtifact(BaseModel):
    episode_number: int = Field(ge=1)
    title: str = Field(min_length=1)
    markdown: str = Field(min_length=1)
    word_count: int = Field(ge=1)
    episode_summary: str = Field(min_length=1)
    hook_delivered: str = Field(min_length=1)
    qa_passed: bool
    overall_score: float | None = None
    rewrite_applied: bool = False
