from typing import Literal

from pydantic import BaseModel, Field


MemoryKind = Literal["raw_artifact", "episode", "semantic_fact", "procedural_skill"]
MemoryScope = Literal["run", "story", "episode", "stage"]


class MemoryRecord(BaseModel):
    id: str = Field(min_length=1)
    kind: MemoryKind
    scope: MemoryScope
    content: str = Field(min_length=1)
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    created_stage: str = Field(min_length=1)
    last_updated_stage: str | None = None


class RunMemory(BaseModel):
    run_id: str = Field(min_length=1)
    request_summary: str = Field(min_length=1)
    completed_stages: list[str] = Field(default_factory=list)
    raw_artifacts: list[MemoryRecord] = Field(default_factory=list)
    episode_memories: list[MemoryRecord] = Field(default_factory=list)
    semantic_facts: list[MemoryRecord] = Field(default_factory=list)
    unresolved_threads: list[MemoryRecord] = Field(default_factory=list)
    resolved_events: list[MemoryRecord] = Field(default_factory=list)
    critique_history: list[dict] = Field(default_factory=list)
    rewrite_targets: list[str] = Field(default_factory=list)
    memory_conflicts: list[dict] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    final_status: str = "running"
