from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class RunManifest(BaseModel):
    run_id: str
    status: Literal["running", "paused", "completed", "failed", "cancelled"]
    started_at: str
    finished_at: str | None = None
    model_provider: str
    model_name: str
    format: Literal["single_story", "episodic_series"] = "single_story"
    max_iterations: int
    completed_iterations: int = 0
    total_episodes: int | None = None
    completed_episodes: int = 0
    current_episode: int | None = None
    target_threshold: float
    minimum_dimension_threshold: int
    min_delta: float
    final_artifact: str | None = None
    error_message: str | None = None


class RunEvent(BaseModel):
    ts: str
    stage: str
    event: str
    iteration: int | None = None
    artifact: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RunPaths:
    root: Path
    request_path: Path
    manifest_path: Path
    events_path: Path
    episodes_dir: Path


class RunResult(BaseModel):
    run_id: str
    run_dir: Path
    final_story_path: Path
    summary_path: Path
