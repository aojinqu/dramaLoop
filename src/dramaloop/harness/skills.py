from pathlib import Path

import yaml

from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.memory import RunMemory
from dramaloop.schemas.skill import ProceduralSkill


def load_procedural_skills(path: Path) -> list[ProceduralSkill]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [ProceduralSkill.model_validate(item) for item in payload]


def select_procedural_skills(
    skills: list[ProceduralSkill],
    *,
    stage: str,
    request: StoryRequest,
    memory: RunMemory,
) -> list[ProceduralSkill]:
    selected: list[ProceduralSkill] = []
    for skill in skills:
        if skill.stage != stage:
            continue
        trigger = skill.trigger.lower()
        if "episodic_series" in trigger and request.format != "episodic_series":
            continue
        if "unresolved_threads" in trigger and not memory.unresolved_threads:
            continue
        if "rewrite" in trigger and not memory.rewrite_targets and stage != "targeted_rewrite":
            continue
        selected.append(skill)
    return sorted(selected, key=lambda item: (-item.priority, item.id))
