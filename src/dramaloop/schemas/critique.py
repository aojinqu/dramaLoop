from typing import Literal

from pydantic import BaseModel, Field

RewriteTarget = Literal[
    "opening_hook",
    "character_motivation",
    "mid_conflict_escalation",
    "reversal_reveal",
    "ending_payoff",
    "prose_fluency",
]

DimensionName = Literal[
    "hook_strength",
    "character_consistency",
    "conflict_intensity",
    "pacing",
    "short_drama_feel",
    "ending_payoff",
    "language_fluency",
]


class DimensionCritique(BaseModel):
    score: int = Field(ge=1, le=10)
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    improvement_advice: str = Field(min_length=1)


class RewritePlan(BaseModel):
    scope: str = Field(min_length=1)
    must_fix: list[str] = Field(default_factory=list)
    keep: list[str] = Field(default_factory=list)


class CritiqueArtifact(BaseModel):
    dimension_scores: dict[DimensionName, DimensionCritique]
    overall_score: float
    weakest_dimensions: list[DimensionName] = Field(min_length=1)
    rewrite_target: RewriteTarget
    rewrite_plan: RewritePlan
