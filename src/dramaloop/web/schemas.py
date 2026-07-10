from typing import Literal

from pydantic import BaseModel, Field

from dramaloop.schemas.input import StoryRequest


class WebRunCreateRequest(StoryRequest):
    length: Literal["short"] = "short"


class WebStageSnapshot(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]


class WebEpisodeSnapshot(BaseModel):
    episode_number: int
    title: str
    status: Literal["pending", "running", "completed", "failed"]
    word_count: int | None = None
    hook_line: str | None = None
    content: str | None = None


class WebRunCreated(BaseModel):
    run_id: str
    status: Literal["running"]
    stream_url: str


class WebRunDetail(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"]
    request: StoryRequest
    stages: list[WebStageSnapshot]
    current_stage: str | None = None
    current_episode_number: int | None = None
    completed_episode_count: int = 0
    episodes: list[WebEpisodeSnapshot] = Field(default_factory=list)
    final_story: str | None = None
    overall_score: float | None = None
    rewrite_focus: str | None = None
    season_summary: str | None = None
    available_artifacts: list[str] = Field(default_factory=list)
