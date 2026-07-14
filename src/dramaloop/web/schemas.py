from typing import Any, Literal

from pydantic import BaseModel, Field

from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.season import EpisodePlanItem


class WebRunCreateRequest(StoryRequest):
    length: Literal["short"] = "short"
    pause_after_plan: bool = True


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
    overall_score: float | None = None


class WebRunCreated(BaseModel):
    run_id: str
    status: Literal["running"]
    stream_url: str


class WebRunDetail(BaseModel):
    run_id: str
    status: Literal["running", "paused", "completed", "failed", "cancelled"]
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
    season_bible: dict[str, Any] | None = None
    episode_plan: dict[str, Any] | None = None
    available_artifacts: list[str] = Field(default_factory=list)
    control_phase: Literal["awaiting_plan_review", "between_episodes", "idle"] | None = None
    pause_after_plan: bool = True
    has_live_controller: bool = False


class WebEpisodePlanUpdateRequest(BaseModel):
    episodes: list[EpisodePlanItem]


class WebControlResponse(BaseModel):
    run_id: str
    status: Literal["running", "paused", "completed", "failed", "cancelled"]
    control_phase: Literal["awaiting_plan_review", "between_episodes", "idle"] | None = None
