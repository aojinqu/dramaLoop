from pydantic import BaseModel, Field


class EpisodeCritiqueArtifact(BaseModel):
    episode_number: int = Field(ge=1)
    overall_score: float
    dimension_scores: dict[str, float]
    weakest_dimensions: list[str] = Field(min_length=1)
    rewrite_needed: bool
    rewrite_target: str = Field(min_length=1)
    issues: list[str] = Field(default_factory=list)
