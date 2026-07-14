from pydantic import BaseModel, Field


class ContinuityState(BaseModel):
    current_episode: int = Field(ge=1)
    story_so_far_summary: str = Field(min_length=1)
    character_states: dict[str, str] = Field(default_factory=dict)
    relationship_states: dict[str, str] = Field(default_factory=dict)
    open_threads: list[str] = Field(default_factory=list)
    resolved_threads: list[str] = Field(default_factory=list)
    last_episode_hook: str = Field(min_length=1)
