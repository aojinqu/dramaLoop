from pydantic import BaseModel, Field


class PremiseArtifact(BaseModel):
    title_candidate: str = Field(min_length=1)
    logline: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    hook_promise: str = Field(min_length=1)
    ending_payoff_plan: str = Field(min_length=1)
    tone_notes: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
