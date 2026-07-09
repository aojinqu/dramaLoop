from pydantic import BaseModel, Field

from dramaloop.schemas.critique import RewriteTarget


class RewriteArtifact(BaseModel):
    version: int = Field(ge=1)
    target_section: RewriteTarget
    goals: list[str] = Field(default_factory=list)
    changes_made: list[str] = Field(default_factory=list)
    expected_score_improvement: list[str] = Field(default_factory=list)
