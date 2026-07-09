from pathlib import Path
from typing import Any

from pydantic import BaseModel

from dramaloop.schemas.run import RunEvent
from dramaloop.utils.json_io import dump_json


def write_json_artifact(path: Path, payload: BaseModel | dict[str, Any]) -> None:
    dump_json(path, payload)


def write_markdown_artifact(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def append_event(events_path: Path, event: RunEvent) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(event.model_dump_json(exclude_none=True) + "\n")
