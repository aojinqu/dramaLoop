from dramaloop.schemas.memory import MemoryRecord, RunMemory


def retrieve_stage_memories(
    memory: RunMemory,
    *,
    stage: str,
    limit: int = 12,
) -> list[MemoryRecord]:
    selected: list[MemoryRecord] = []
    if stage in {
        "draft_generation",
        "targeted_rewrite",
        "episode_plan_generation",
        "episode_draft_generation",
        "episode_targeted_rewrite",
    }:
        selected.extend(
            record
            for record in memory.semantic_facts
            if record.evidence_refs and record.confidence >= 0.5
        )
    if stage.startswith("episode_"):
        selected.extend(memory.episode_memories[-3:])
        selected.extend(memory.unresolved_threads)
    return selected[:limit]
