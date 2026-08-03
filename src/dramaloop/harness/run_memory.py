from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any

from pydantic import BaseModel

from dramaloop.harness.memory_compressor import extract_memory_records
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.memory import MemoryRecord, RunMemory
from dramaloop.storage.artifacts import write_json_artifact


def append_jsonl(path: Path, payload: BaseModel | dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(payload, BaseModel):
        body = payload.model_dump(mode="json", exclude_none=True)
    else:
        body = payload
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, ensure_ascii=False, separators=(",", ":")) + "\n")


class RunMemoryStore:
    def __init__(self, run_root: Path, run_id: str, request: StoryRequest) -> None:
        self.run_root = run_root
        self.memory_path = run_root / "run_memory.json"
        self.trace_path = run_root / "memory_trace.jsonl"
        if self.memory_path.exists():
            self.memory = RunMemory.model_validate_json(
                self.memory_path.read_text(encoding="utf-8")
            )
            self._sequence = len(self.memory.raw_artifacts)
            self.memory.final_status = "running"
            self.persist()
            return
        request_summary = (
            f"idea={request.idea}; format={request.format}; style={','.join(request.style)}; "
            f"constraints={';'.join(request.constraints)}"
        )
        self.memory = RunMemory(run_id=run_id, request_summary=request_summary)
        self._sequence = 0
        for index, constraint in enumerate(request.constraints, start=1):
            self.memory.semantic_facts.append(
                MemoryRecord(
                    id=f"request-constraint-{index}",
                    kind="semantic_fact",
                    scope="run",
                    content=f"user_constraint: {constraint}",
                    evidence_refs=["request.json"],
                    created_stage="run",
                )
            )
        self.persist()

    def complete_stage(self, stage: str) -> None:
        if stage not in self.memory.completed_stages:
            self.memory.completed_stages.append(stage)
            self.persist()

    def record_artifact(
        self,
        *,
        artifact_ref: str,
        payload: BaseModel | dict[str, Any] | str,
        stage: str,
    ) -> None:
        self._sequence += 1
        raw, episodes, facts = extract_memory_records(
            payload=payload,
            artifact_ref=artifact_ref,
            stage=stage,
            sequence=self._sequence,
        )
        self.memory.raw_artifacts.extend(raw)
        self._merge_records(self.memory.episode_memories, episodes, stage)
        self._merge_records(self.memory.semantic_facts, facts, stage)

        value = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
        if isinstance(value, dict):
            if "dimension_scores" in value:
                self.memory.critique_history.append(value)
            rewrite_target = value.get("rewrite_target") or value.get("target_section")
            if rewrite_target:
                self.memory.rewrite_targets.append(str(rewrite_target))
            open_threads = value.get("open_threads")
            if isinstance(open_threads, list):
                self.memory.unresolved_threads = [
                    MemoryRecord(
                        id=f"thread-{index + 1}",
                        kind="semantic_fact",
                        scope="story",
                        content=str(thread),
                        evidence_refs=[artifact_ref],
                        created_stage=stage,
                    )
                    for index, thread in enumerate(open_threads)
                ]
        append_jsonl(
            self.trace_path,
            {
                "ts": datetime.now().isoformat(),
                "event": "artifact_consolidated",
                "stage": stage,
                "artifact": artifact_ref,
                "raw_memory_ids": [item.id for item in raw],
                "episode_memory_ids": [item.id for item in episodes],
                "semantic_fact_ids": [item.id for item in facts],
            },
        )
        self.persist()

    def _merge_records(
        self,
        target: list[MemoryRecord],
        incoming: list[MemoryRecord],
        stage: str,
    ) -> None:
        by_id = {item.id: index for index, item in enumerate(target)}
        for record in incoming:
            if record.id not in by_id:
                target.append(record)
                continue
            current = target[by_id[record.id]]
            if current.content != record.content:
                self.memory.memory_conflicts.append(
                    {
                        "memory_id": record.id,
                        "existing": current.content,
                        "incoming": record.content,
                        "stage": stage,
                    }
                )
                append_jsonl(
                    self.trace_path,
                    {
                        "ts": datetime.now().isoformat(),
                        "event": "memory_conflict",
                        "stage": stage,
                        "memory_id": record.id,
                    },
                )
                continue
            target[by_id[record.id]] = record.model_copy(update={"last_updated_stage": stage})
            append_jsonl(
                self.trace_path,
                {
                    "ts": datetime.now().isoformat(),
                    "event": "memory_merged",
                    "stage": stage,
                    "memory_id": record.id,
                },
            )

    def finalize(self, status: str, *, failure_pattern: str | None = None) -> None:
        self.memory.final_status = status
        if failure_pattern and failure_pattern not in self.memory.failure_patterns:
            self.memory.failure_patterns.append(failure_pattern)
        self.persist()

    def invalidate_episodes_after(self, episode_number: int) -> None:
        def keep(record: MemoryRecord) -> bool:
            for evidence in record.evidence_refs:
                match = re.search(r"episodes/episode_(\d+)", evidence)
                if match and int(match.group(1)) > episode_number:
                    return False
            return True

        before = len(self.memory.raw_artifacts) + len(self.memory.episode_memories)
        self.memory.raw_artifacts = [record for record in self.memory.raw_artifacts if keep(record)]
        self.memory.episode_memories = [
            record for record in self.memory.episode_memories if keep(record)
        ]
        self.memory.semantic_facts = [
            record for record in self.memory.semantic_facts if keep(record)
        ]
        removed = before - (len(self.memory.raw_artifacts) + len(self.memory.episode_memories))
        append_jsonl(
            self.trace_path,
            {
                "ts": datetime.now().isoformat(),
                "event": "episode_memory_invalidated",
                "episode_number": episode_number,
                "removed_records": removed,
            },
        )
        self.persist()

    def persist(self) -> None:
        write_json_artifact(self.memory_path, self.memory)
