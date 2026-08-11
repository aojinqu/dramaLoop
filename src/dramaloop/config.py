from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from dramaloop.schemas.harness import HarnessMode


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRAMALOOP_", env_file=".env", extra="ignore")

    provider: Literal["mock", "anthropic-compatible"] = "mock"
    model_name: str = "claude-sonnet-5"
    api_key: str | None = None
    base_url: str | None = None
    judge_model_name: str = "deepseek-chat"
    judge_api_key: str | None = None
    judge_base_url: str = "https://api.deepseek.com/anthropic"
    runs_dir: Path = Path("runs")
    artifacts_dir: Path = Path("artifacts")
    evals_dir: Path = Path("evals")
    max_iterations_default: int = Field(default=2, ge=1, le=3)
    target_threshold: float = 7.5
    minimum_dimension_threshold: int = 6
    min_delta: float = 0.3
    harness_enabled: bool = True
    harness_mode: HarnessMode = "full_harness"
    model_context_window_tokens: int = Field(default=32768, ge=1024)
    stage_context_budget_ratio: float = Field(default=0.4, gt=0.0, le=1.0)
    procedural_skills_path: Path = Path("evals/skills/procedural_skills.yaml")
    enable_originality_plan: bool = False
    originality_planner_base_url: str | None = None
    originality_planner_api_key: str | None = None
    originality_planner_model_name: str = "originality-planner"
    originality_planner_timeout_seconds: float = Field(default=120.0, gt=0)
    originality_planner_max_retries: int = Field(default=1, ge=0, le=2)
    originality_planner_fallback_enabled: bool = True
