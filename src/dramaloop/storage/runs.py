import re
from datetime import datetime
from pathlib import Path

from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunManifest, RunPaths
from dramaloop.utils.json_io import dump_json


ASCII_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _slugify_idea(idea: str) -> str:
    slug = "-".join(ASCII_TOKEN_RE.findall(idea.lower()))
    return slug or "story"


def build_run_id(idea: str, started_at: datetime) -> str:
    return f"{started_at:%Y%m%d-%H%M%S}-{_slugify_idea(idea)}"


def reserve_run_id(runs_dir: Path, run_id: str) -> str:
    candidate = run_id
    suffix = 2
    while (runs_dir / candidate).exists():
        candidate = f"{run_id}-{suffix}"
        suffix += 1
    return candidate


def plan_run_id(runs_dir: Path, idea: str, started_at: datetime) -> str:
    return reserve_run_id(runs_dir, build_run_id(idea, started_at))


def create_run_paths(runs_dir: Path, run_id: str) -> RunPaths:
    root = runs_dir / run_id
    root.mkdir(parents=True, exist_ok=False)
    return RunPaths(
        root=root,
        request_path=root / "request.json",
        manifest_path=root / "run_manifest.json",
        events_path=root / "events.jsonl",
    )


def initialize_run_files(run_paths: RunPaths, request: StoryRequest, manifest: RunManifest) -> None:
    dump_json(run_paths.request_path, request)
    dump_json(run_paths.manifest_path, manifest)
    run_paths.events_path.touch()
