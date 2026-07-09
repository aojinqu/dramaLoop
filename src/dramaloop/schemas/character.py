from typing import Literal

from pydantic import BaseModel, Field


class CharacterCard(BaseModel):
    name: str = Field(min_length=1)
    role: Literal["protagonist", "antagonist", "supporting"]
    public_identity: str = Field(min_length=1)
    core_desire: str = Field(min_length=1)
    core_fear: str = Field(min_length=1)
    hidden_secret: str | None = None
    conflict_links: list[str] = Field(default_factory=list)
    voice_style: str = Field(min_length=1)
    arc_target: str = Field(min_length=1)


class CharacterArtifact(BaseModel):
    characters: list[CharacterCard] = Field(min_length=1)
