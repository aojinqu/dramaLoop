from typing import Literal

from pydantic import BaseModel, Field

from dramaloop.schemas.input import StoryRequest


class WebRunCreateRequest(StoryRequest):
    length: Literal["short"] = "short"


class WebStageSnapshot(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]


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
    final_story: str | None = None
    overall_score: float | None = None
    rewrite_focus: str | None = None
    available_artifacts: list[str] = Field(default_factory=list)
