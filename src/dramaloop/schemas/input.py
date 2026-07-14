from typing import Literal

from pydantic import BaseModel, Field, model_validator


class StoryRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    length: Literal["short"]
    format: Literal["single_story", "episodic_series"] = "single_story"
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)
    episode_count: int = Field(default=12, ge=1, le=12)
    episode_min_words: int = Field(default=500, ge=100)
    episode_max_words: int = Field(default=800, ge=100)
    delivery_mode: Literal["stream_and_final"] = "stream_and_final"
    enable_episode_critique: bool = True

    @model_validator(mode="after")
    def validate_episode_word_range(self) -> "StoryRequest":
        if self.episode_min_words > self.episode_max_words:
            raise ValueError("episode_min_words must be <= episode_max_words")
        return self
