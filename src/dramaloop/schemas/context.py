from pydantic import BaseModel, Field


class ContextItem(BaseModel):
    id: str = Field(min_length=1)
    kind: str = Field(min_length=1)
    content: str = Field(min_length=1)
    tokens_estimated: int = Field(ge=1)
    priority: int = 0
    reason: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    required: bool = False


class ContextPack(BaseModel):
    stage: str = Field(min_length=1)
    budget_tokens: int = Field(ge=1)
    selected_items: list[ContextItem] = Field(default_factory=list)
    dropped_items: list[ContextItem] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    selected_tokens: int = Field(default=0, ge=0)
    budget_overflow_tokens: int = Field(default=0, ge=0)
