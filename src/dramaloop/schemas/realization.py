from typing import Literal

from pydantic import BaseModel, Field


class RealizationResult(BaseModel):
    stage: str = Field(min_length=1)
    status: Literal["accepted", "repaired", "retried", "blocked"]
    issues: list[str] = Field(default_factory=list)
    repair_summary: str | None = None
    retry_reason: str | None = None
