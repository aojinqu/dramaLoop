from pydantic import BaseModel, Field


class StoryBeat(BaseModel):
    beat_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tension_level: int = Field(ge=1, le=10)
    payoff_dependency: str | None = None


class OutlineArtifact(BaseModel):
    beats: list[StoryBeat] = Field(min_length=5)
    ending_type: str = Field(min_length=1)
