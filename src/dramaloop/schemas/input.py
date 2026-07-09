from typing import Literal

from pydantic import BaseModel, Field


class StoryRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    length: Literal["short"]
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)
