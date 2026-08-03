import json
from typing import Any

from pydantic import BaseModel

from dramaloop.schemas.memory import MemoryRecord


def _as_payload(payload: BaseModel | dict[str, Any] | str) -> dict[str, Any] | str:
    if isinstance(payload, BaseModel):
        return payload.model_dump(mode="json")
    return payload


def summarize_artifact(payload: BaseModel | dict[str, Any] | str, *, limit: int = 500) -> str:
    value = _as_payload(payload)
    if isinstance(value, str):
        compact = " ".join(value.split())
    else:
        compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    return compact if len(compact) <= limit else f"{compact[: limit - 3]}..."


def extract_memory_records(
    *,
    payload: BaseModel | dict[str, Any] | str,
    artifact_ref: str,
    stage: str,
    sequence: int,
) -> tuple[list[MemoryRecord], list[MemoryRecord], list[MemoryRecord]]:
    value = _as_payload(payload)
    raw = MemoryRecord(
        id=f"artifact-{sequence}",
        kind="raw_artifact",
        scope="stage",
        content=summarize_artifact(payload),
        evidence_refs=[artifact_ref],
        created_stage=stage,
    )
    episode_records: list[MemoryRecord] = []
    semantic_records: list[MemoryRecord] = []

    if isinstance(value, dict):
        episode_number = value.get("episode_number")
        episode_summary = value.get("episode_summary")
        if episode_number and episode_summary:
            episode_records.append(
                MemoryRecord(
                    id=f"episode-{episode_number}",
                    kind="episode",
                    scope="episode",
                    content=str(episode_summary),
                    evidence_refs=[artifact_ref],
                    created_stage=stage,
                )
            )

        fact_fields = (
            "core_conflict",
            "logline",
            "series_logline",
            "ending_payoff_plan",
            "final_payoff",
            "hook_delivered",
        )
        for field_name in fact_fields:
            content = value.get(field_name)
            if content:
                semantic_records.append(
                    MemoryRecord(
                        id=f"fact-{sequence}-{field_name}",
                        kind="semantic_fact",
                        scope="story",
                        content=f"{field_name}: {content}",
                        evidence_refs=[artifact_ref],
                        created_stage=stage,
                    )
                )

        for character in value.get("characters", []):
            if not isinstance(character, dict) or not character.get("name"):
                continue
            semantic_records.append(
                MemoryRecord(
                    id=f"fact-{sequence}-character-{len(semantic_records) + 1}",
                    kind="semantic_fact",
                    scope="story",
                    content=(
                        f"character: {character['name']}; role={character.get('role', '')}; "
                        f"desire={character.get('core_desire', '')}; "
                        f"links={','.join(character.get('conflict_links', []))}"
                    ),
                    evidence_refs=[artifact_ref],
                    created_stage=stage,
                )
            )

    return [raw], episode_records, semantic_records
