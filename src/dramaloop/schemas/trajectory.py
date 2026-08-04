from typing import Literal

from pydantic import BaseModel, Field


class TrajectorySignal(BaseModel):
    stage: str = Field(min_length=1)
    signal_type: str = Field(min_length=1)
    severity: Literal["info", "warning", "error"]
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str = Field(min_length=1)


class RegulationDecision(BaseModel):
    stage: str = Field(min_length=1)
    action: Literal["continue", "rewrite", "retry_stage", "stop"]
    reason: str = Field(min_length=1)
    signals: list[TrajectorySignal] = Field(default_factory=list)
