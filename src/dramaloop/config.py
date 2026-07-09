from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRAMALOOP_", env_file=".env", extra="ignore")

    provider: Literal["mock", "anthropic-compatible"] = "mock"
    model_name: str = "claude-sonnet-5"
    api_key: str | None = None
    base_url: str | None = None
    runs_dir: Path = Path("runs")
    artifacts_dir: Path = Path("artifacts")
    evals_dir: Path = Path("evals")
    max_iterations_default: int = Field(default=2, ge=1, le=3)
    target_threshold: float = 7.5
    minimum_dimension_threshold: int = 6
    min_delta: float = 0.3
