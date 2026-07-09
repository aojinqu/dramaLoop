from typing import Literal

from pydantic import BaseModel, Field


class WebRunCreateRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)


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
    request: WebRunCreateRequest
    stages: list[WebStageSnapshot]
    current_stage: str | None = None
    final_story: str | None = None
    overall_score: float | None = None
    rewrite_focus: str | None = None
    available_artifacts: list[str] = Field(default_factory=list)
