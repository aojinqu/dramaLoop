from dataclasses import dataclass, field

from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.context import ContextItem, ContextPack
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.memory import MemoryRecord
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.schemas.rewrite import RewriteArtifact
from dramaloop.schemas.run import RunPaths


@dataclass
class PipelineContext:
    request: StoryRequest
    run_paths: RunPaths
    premise: PremiseArtifact | None = None
    characters: CharacterArtifact | None = None
    outline: OutlineArtifact | None = None
    drafts: list[str] = field(default_factory=list)
    critiques: list[CritiqueArtifact] = field(default_factory=list)
    rewrites: list[RewriteArtifact] = field(default_factory=list)


def estimate_tokens(content: str) -> int:
    return max(1, (len(content) + 3) // 4)


def memory_to_context_item(memory: MemoryRecord, *, priority: int = 50) -> ContextItem:
    return ContextItem(
        id=memory.id,
        kind=memory.kind,
        content=memory.content,
        tokens_estimated=estimate_tokens(memory.content),
        priority=priority,
        reason=f"recalled {memory.kind} for current stage",
        evidence_refs=memory.evidence_refs,
    )


def build_context_pack(
    *,
    stage: str,
    budget_tokens: int,
    candidate_items: list[ContextItem],
    memories: list[MemoryRecord] | None = None,
) -> ContextPack:
    items = list(candidate_items)
    items.extend(memory_to_context_item(memory) for memory in memories or [])
    items.sort(key=lambda item: (not item.required, -item.priority, item.id))

    selected: list[ContextItem] = []
    dropped: list[ContextItem] = []
    used_tokens = 0
    for item in items:
        if item.required or used_tokens + item.tokens_estimated <= budget_tokens:
            selected.append(item)
            used_tokens += item.tokens_estimated
        else:
            dropped.append(
                item.model_copy(
                    update={"reason": f"{item.reason}; dropped because context budget was exhausted"}
                )
            )

    return ContextPack(
        stage=stage,
        budget_tokens=budget_tokens,
        selected_items=selected,
        dropped_items=dropped,
        memory_refs=[
            item.id
            for item in selected
            if item.kind in {"episode", "semantic_fact", "procedural_skill"}
        ],
        selected_tokens=used_tokens,
        budget_overflow_tokens=max(0, used_tokens - budget_tokens),
    )
