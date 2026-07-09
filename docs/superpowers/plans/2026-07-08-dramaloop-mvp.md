# Dramaloop MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI-first short-drama text generation system with a staged agent harness, a critique-rewrite loop, persisted run artifacts, and a Trellis-inspired project operating layer.

**Architecture:** Dramaloop uses a dual-layer architecture. The application layer lives in `src/dramaloop/` and owns generation, critique, rewriting, evals, and CLI behavior. The project operating layer lives under `project/` and stores durable specs, task folders, and workspace notes so the repo itself becomes a persistent engineering memory instead of a one-off prototype.

**Tech Stack:** Python 3.11+, Typer, Pydantic v2, pydantic-settings, pytest, Ruff, optional mypy, JSON, Markdown, YAML, uv

## Global Constraints

- Language: **Python 3.11+**
- CLI: **Typer**
- Schema validation: **Pydantic v2**
- Config: `pydantic-settings`
- Testing: **pytest**
- Lint/format: **Ruff**
- Optional type-checking: **mypy**
- Structured artifact format: **JSON**
- Human-readable output format: **Markdown**
- Input/eval dataset format: **YAML**
- Package/runtime workflow: **uv**
- MVP supports only `length=short`
- `max_iterations` defaults to 2 and must be between 1 and 3 inclusive
- Allowed rewrite targets: `opening_hook`, `character_motivation`, `mid_conflict_escalation`, `reversal_reveal`, `ending_payoff`, `prose_fluency`
- Default thresholds for MVP: `target_threshold = 7.5`, `minimum_dimension_threshold = 6`, `min_delta = 0.3`
- Business logic must depend on an abstract LLM client interface rather than a concrete SDK
- The system must fail clearly and write run state whenever possible
- Prompt templates and orchestration code must not directly import provider SDK details outside the adapter layer
- The operating layer supplements the application layer; it does not replace `src/dramaloop/`
- Files in `project/spec/` must capture durable repo knowledge rather than one-off conversation notes
- Files in `project/tasks/` must track execution context for meaningful implementation slices
- Files in `project/workspace/` must capture reusable insights that help future iterations

---

## Execution Order Note

Because the repository currently has no Python bootstrap yet, execute tasks in this order:

1. Task 2: Bootstrap the Python package and CLI shell
2. Task 1: Seed the Trellis-inspired project operating layer
3. Tasks 3-10 in numeric order

This preserves the intended architecture while ensuring that the first pytest-based verification runs in a bootstrapped environment.

## File Map

### Application layer

- `pyproject.toml` — project metadata, dependencies, scripts, pytest, Ruff configuration
- `.env.example` — runtime configuration examples for providers and output directories
- `src/dramaloop/__init__.py` — package version constant
- `src/dramaloop/main.py` — Typer CLI entrypoints for `run`, `inspect`, and `eval`
- `src/dramaloop/config.py` — settings model and threshold defaults
- `src/dramaloop/schemas/input.py` — `StoryRequest`
- `src/dramaloop/schemas/premise.py` — `PremiseArtifact`
- `src/dramaloop/schemas/character.py` — `CharacterCard`, `CharacterArtifact`
- `src/dramaloop/schemas/outline.py` — `StoryBeat`, `OutlineArtifact`
- `src/dramaloop/schemas/critique.py` — dimension schema, rewrite-target enum, `CritiqueArtifact`
- `src/dramaloop/schemas/rewrite.py` — `RewriteArtifact`
- `src/dramaloop/schemas/run.py` — `RunManifest`, `RunEvent`, `RunPaths`, `RunResult`
- `src/dramaloop/llm/base.py` — `LLMClient` protocol and common exceptions
- `src/dramaloop/llm/mock.py` — deterministic mock client and default mock payloads
- `src/dramaloop/llm/provider.py` — Anthropic adapter and `build_llm_client(settings)` factory
- `src/dramaloop/prompts/premise.py` — premise refinement prompt builder
- `src/dramaloop/prompts/characters.py` — character-card prompt builder
- `src/dramaloop/prompts/outline.py` — story outline prompt builder
- `src/dramaloop/prompts/draft.py` — draft generation prompt builder
- `src/dramaloop/prompts/critique.py` — critique prompt builder
- `src/dramaloop/prompts/rewrite.py` — rewrite prompt builder
- `src/dramaloop/harness/context.py` — `PipelineContext` dataclass for a run-in-progress
- `src/dramaloop/harness/stages.py` — typed stage functions for all seven stages
- `src/dramaloop/harness/loop.py` — loop continuation and stop-reason helpers
- `src/dramaloop/harness/orchestrator.py` — end-to-end pipeline execution and failure handling
- `src/dramaloop/storage/runs.py` — run ID generation, run path creation, manifest bootstrap
- `src/dramaloop/storage/artifacts.py` — JSON, Markdown, and JSONL writers/readers
- `src/dramaloop/eval/dimensions.py` — ordered dimension names and display labels
- `src/dramaloop/eval/scorer.py` — score aggregation helpers
- `src/dramaloop/eval/report.py` — single-run reporting and dataset batch eval
- `src/dramaloop/utils/json_io.py` — reusable JSON serialization helpers
- `src/dramaloop/utils/markdown.py` — `run_summary.md` renderer
- `src/dramaloop/utils/logging.py` — terminal progress helpers
- `README.md` — quickstart, architecture overview, run outputs, repo layout
- `examples/inputs/revenge_story.yaml` — sample run input
- `examples/outputs/README.md` — stable copied output examples
- `artifacts/README.md` — curated artifact sample guidance
- `evals/datasets/mvp_cases.yaml` — small benchmark dataset

### Project operating layer

- `project/spec/product.md` — long-lived product goal and MVP boundary
- `project/spec/architecture.md` — durable architecture notes for the dual-layer system
- `project/spec/evaluation.md` — scoring dimensions, loop thresholds, eval rules
- `project/spec/conventions.md` — repo conventions, artifact naming, task folder expectations
- `project/tasks/2026-07-08-mvp-bootstrap/task.md` — task goal and linked spec sections for the first implementation slice
- `project/tasks/2026-07-08-mvp-bootstrap/implementation-notes.md` — slice-specific implementation notes
- `project/tasks/2026-07-08-mvp-bootstrap/status.md` — task status and verification notes
- `project/workspace/decisions.md` — durable design decisions
- `project/workspace/learnings.md` — implementation/eval lessons learned
- `project/workspace/backlog.md` — deferred work and future slices

### Tests

- `tests/unit/test_repo_layout.py`
- `tests/unit/test_cli_smoke.py`
- `tests/unit/test_config_and_schemas.py`
- `tests/unit/test_storage.py`
- `tests/unit/test_mock_llm.py`
- `tests/unit/test_stage_builders.py`
- `tests/unit/test_loop_and_summary.py`
- `tests/unit/test_provider_adapter.py`
- `tests/unit/test_reports.py`
- `tests/integration/test_run_command.py`
- `tests/integration/test_inspect_eval_commands.py`
- `tests/fixtures/sample_run/`

---

### Task 1: Seed the Trellis-inspired project operating layer

**Files:**
- Create: `project/spec/product.md`
- Create: `project/spec/architecture.md`
- Create: `project/spec/evaluation.md`
- Create: `project/spec/conventions.md`
- Create: `project/tasks/2026-07-08-mvp-bootstrap/task.md`
- Create: `project/tasks/2026-07-08-mvp-bootstrap/implementation-notes.md`
- Create: `project/tasks/2026-07-08-mvp-bootstrap/status.md`
- Create: `project/workspace/decisions.md`
- Create: `project/workspace/learnings.md`
- Create: `project/workspace/backlog.md`
- Test: `tests/unit/test_repo_layout.py`

**Interfaces:**
- Consumes: approved design/spec docs under `docs/superpowers/specs/`
- Produces:
  - durable repo memory files under `project/spec/`, `project/tasks/`, and `project/workspace/`
  - `tests/unit/test_repo_layout.py` verifying the operating-layer skeleton exists

- [ ] **Step 1: Write the failing repo-layout test**

```python
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


REQUIRED_PATHS = [
    "project/spec/product.md",
    "project/spec/architecture.md",
    "project/spec/evaluation.md",
    "project/spec/conventions.md",
    "project/tasks/2026-07-08-mvp-bootstrap/task.md",
    "project/tasks/2026-07-08-mvp-bootstrap/implementation-notes.md",
    "project/tasks/2026-07-08-mvp-bootstrap/status.md",
    "project/workspace/decisions.md",
    "project/workspace/learnings.md",
    "project/workspace/backlog.md",
]


def test_project_operating_layer_files_exist() -> None:
    missing = [relative_path for relative_path in REQUIRED_PATHS if not (ROOT / relative_path).exists()]

    assert missing == []
```

- [ ] **Step 2: Run the repo-layout test to confirm the operating layer is missing**

Run: `uv run pytest tests/unit/test_repo_layout.py -v`
Expected: FAIL with missing paths listed in the assertion output

- [ ] **Step 3: Create the operating-layer files with initial durable content**

`project/spec/product.md`
```md
# Product Spec

## Goal
Build a CLI-first short-drama text generation system that turns a story idea into a structured, iteratively improved short story.

## MVP Boundary
- fixed seven-stage harness
- 2-iteration default critique-rewrite loop
- structured artifacts persisted to `runs/`
- CLI commands: `run`, `inspect`, `eval`

## Non-Goals
- video generation
- storyboard output
- web UI
- hosted multi-user deployment
```

`project/spec/architecture.md`
```md
# Architecture Spec

## Dual-Layer Model
- Application layer: `src/dramaloop/`
- Operating layer: `project/`

## Application Responsibilities
- generation stages
- critique-rewrite loop
- run artifact persistence
- eval reporting

## Operating Layer Responsibilities
- durable specs
- task-scoped execution context
- decisions, learnings, and backlog
```

`project/spec/evaluation.md`
```md
# Evaluation Spec

## Dimensions
- hook_strength
- character_consistency
- conflict_intensity
- pacing
- short_drama_feel
- ending_payoff
- language_fluency

## Default Thresholds
- target_threshold = 7.5
- minimum_dimension_threshold = 6
- min_delta = 0.3
```

`project/spec/conventions.md`
```md
# Repository Conventions

## Artifacts
- structured artifacts use JSON
- drafts and summaries use Markdown
- eval datasets use YAML

## Task Folders
Each major implementation slice gets:
- `task.md`
- `implementation-notes.md`
- `status.md`

## Run Layout
Every run must persist request, manifest, events, premise, characters, outline, draft(s), critique(s), final story, and run summary.
```

`project/tasks/2026-07-08-mvp-bootstrap/task.md`
```md
# MVP Bootstrap Task

## Goal
Implement the first end-to-end Dramaloop MVP slice.

## Linked Specs
- `docs/superpowers/specs/2026-07-08-dramaloop-design.md`
- `docs/superpowers/specs/2026-07-08-dramaloop-spec.md`
```

`project/tasks/2026-07-08-mvp-bootstrap/implementation-notes.md`
```md
# Implementation Notes

- start with mock-backed pipeline
- keep stages typed and small
- persist every artifact
```

`project/tasks/2026-07-08-mvp-bootstrap/status.md`
```md
# Status

- state: planned
- owner: current session
- next milestone: bootstrap package and CLI
```

`project/workspace/decisions.md`
```md
# Decisions

- Python over TypeScript for faster agent/eval prototyping
- dual-layer repo architecture inspired by Trellis
```

`project/workspace/learnings.md`
```md
# Learnings

- reserved for durable lessons from implementation and eval runs
```

`project/workspace/backlog.md`
```md
# Backlog

- scene-level decomposition
- prompt package generation
- training-data export
- video-model integration
```

- [ ] **Step 4: Run the repo-layout test again**

Run: `uv run pytest tests/unit/test_repo_layout.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the operating-layer skeleton**

```bash
git add project tests/unit/test_repo_layout.py
git commit -m "feat: add project operating layer skeleton"
```

---

### Task 2: Bootstrap the Python package and CLI shell

**Files:**
- Create: `pyproject.toml`
- Create: `src/dramaloop/__init__.py`
- Create: `src/dramaloop/main.py`
- Test: `tests/unit/test_cli_smoke.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `app: typer.Typer`
  - CLI commands named `run`, `inspect`, and `eval`
  - `__version__: str`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from typer.testing import CliRunner

from dramaloop.main import app


runner = CliRunner()


def test_cli_help_lists_core_commands() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "run" in result.stdout
    assert "inspect" in result.stdout
    assert "eval" in result.stdout
```

- [ ] **Step 2: Run the smoke test to verify the package is not wired yet**

Run: `uv run pytest tests/unit/test_cli_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'dramaloop'`

- [ ] **Step 3: Add project metadata and the minimal Typer app**

`pyproject.toml`
```toml
[project]
name = "dramaloop"
version = "0.1.0"
description = "CLI-first short-drama story generation harness"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
  "anthropic>=0.57.1",
  "pydantic>=2.11.0",
  "pydantic-settings>=2.10.1",
  "pyyaml>=6.0.2",
  "typer>=0.16.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.4.0",
  "ruff>=0.12.0",
  "mypy>=1.16.0",
]

[project.scripts]
dramaloop = "dramaloop.main:app"

[build-system]
requires = ["hatchling>=1.25.0"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
pythonpath = ["src"]

[tool.ruff]
line-length = 100

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

`src/dramaloop/__init__.py`
```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

`src/dramaloop/main.py`
```python
import typer


app = typer.Typer(no_args_is_help=True, help="Dramaloop short-drama generation CLI")


@app.command()
def run() -> None:
    """Run a new generation pipeline."""
    raise typer.Exit(code=0)


@app.command()
def inspect() -> None:
    """Inspect a previous run."""
    raise typer.Exit(code=0)


@app.command(name="eval")
def eval_command() -> None:
    """Aggregate one run or a dataset of runs."""
    raise typer.Exit(code=0)
```

- [ ] **Step 4: Run the smoke test again**

Run: `uv run pytest tests/unit/test_cli_smoke.py -v`
Expected: PASS with `1 passed`

- [ ] **Step 5: Commit the bootstrap**

```bash
git add pyproject.toml src/dramaloop/__init__.py src/dramaloop/main.py tests/unit/test_cli_smoke.py
git commit -m "feat: bootstrap dramaloop cli"
```

---

### Task 3: Define settings and all Pydantic schemas

**Files:**
- Create: `src/dramaloop/config.py`
- Create: `src/dramaloop/schemas/input.py`
- Create: `src/dramaloop/schemas/premise.py`
- Create: `src/dramaloop/schemas/character.py`
- Create: `src/dramaloop/schemas/outline.py`
- Create: `src/dramaloop/schemas/critique.py`
- Create: `src/dramaloop/schemas/rewrite.py`
- Create: `src/dramaloop/schemas/run.py`
- Test: `tests/unit/test_config_and_schemas.py`

**Interfaces:**
- Consumes: none
- Produces:
  - `Settings`
  - `StoryRequest`
  - `PremiseArtifact`
  - `CharacterCard`, `CharacterArtifact`
  - `StoryBeat`, `OutlineArtifact`
  - `DimensionCritique`, `RewritePlan`, `CritiqueArtifact`, `RewriteTarget`
  - `RewriteArtifact`
  - `RunManifest`, `RunEvent`, `RunPaths`, `RunResult`

- [ ] **Step 1: Write failing tests for request validation, critique targets, and settings defaults**

```python
from pathlib import Path

import pytest
from pydantic import ValidationError

from dramaloop.config import Settings
from dramaloop.schemas.critique import CritiqueArtifact, DimensionCritique
from dramaloop.schemas.input import StoryRequest


def test_story_request_applies_defaults() -> None:
    request = StoryRequest(
        idea="她在婚礼上被抛弃后反手嫁给了宿敌",
        style=["都市情感", "狗血短剧感"],
        length="short",
    )

    assert request.max_iterations == 2
    assert request.constraints == []
    assert request.audience is None


def test_story_request_rejects_long_form_length() -> None:
    with pytest.raises(ValidationError):
        StoryRequest(idea="x", style=["都市"], length="novel")


def test_critique_rejects_unknown_rewrite_target() -> None:
    with pytest.raises(ValidationError):
        CritiqueArtifact(
            dimension_scores={
                "hook_strength": DimensionCritique(score=7, reason="ok", evidence="line 1", improvement_advice="sharpen"),
                "character_consistency": DimensionCritique(score=7, reason="ok", evidence="line 2", improvement_advice="keep"),
                "conflict_intensity": DimensionCritique(score=6, reason="ok", evidence="line 3", improvement_advice="raise stakes"),
                "pacing": DimensionCritique(score=6, reason="ok", evidence="line 4", improvement_advice="trim"),
                "short_drama_feel": DimensionCritique(score=7, reason="ok", evidence="line 5", improvement_advice="push twist"),
                "ending_payoff": DimensionCritique(score=5, reason="ok", evidence="line 6", improvement_advice="pay off"),
                "language_fluency": DimensionCritique(score=8, reason="ok", evidence="line 7", improvement_advice="keep"),
            },
            overall_score=6.6,
            weakest_dimensions=["ending_payoff"],
            rewrite_target="full_rewrite",
            rewrite_plan={"scope": "ending", "must_fix": ["ending"], "keep": ["opening"]},
        )


def test_settings_defaults_use_repo_relative_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings()

    assert settings.runs_dir == Path("runs")
    assert settings.evals_dir == Path("evals")
    assert settings.target_threshold == 7.5
    assert settings.minimum_dimension_threshold == 6
    assert settings.min_delta == 0.3
```

- [ ] **Step 2: Run the schema tests to verify the models do not exist yet**

Run: `uv run pytest tests/unit/test_config_and_schemas.py -v`
Expected: FAIL with import errors for `dramaloop.config` or `dramaloop.schemas.*`

- [ ] **Step 3: Implement the settings model and core schemas**

`src/dramaloop/config.py`
```python
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DRAMALOOP_", env_file=".env", extra="ignore")

    provider: Literal["mock", "anthropic"] = "mock"
    model_name: str = "claude-sonnet-5"
    runs_dir: Path = Path("runs")
    artifacts_dir: Path = Path("artifacts")
    evals_dir: Path = Path("evals")
    max_iterations_default: int = Field(default=2, ge=1, le=3)
    target_threshold: float = 7.5
    minimum_dimension_threshold: int = 6
    min_delta: float = 0.3
```

`src/dramaloop/schemas/input.py`
```python
from typing import Literal

from pydantic import BaseModel, Field


class StoryRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    length: Literal["short"]
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)
```

`src/dramaloop/schemas/premise.py`
```python
from pydantic import BaseModel, Field


class PremiseArtifact(BaseModel):
    title_candidate: str = Field(min_length=1)
    logline: str = Field(min_length=1)
    core_conflict: str = Field(min_length=1)
    hook_promise: str = Field(min_length=1)
    ending_payoff_plan: str = Field(min_length=1)
    tone_notes: list[str] = Field(default_factory=list)
    hard_constraints: list[str] = Field(default_factory=list)
```

`src/dramaloop/schemas/character.py`
```python
from typing import Literal

from pydantic import BaseModel, Field


class CharacterCard(BaseModel):
    name: str = Field(min_length=1)
    role: Literal["protagonist", "antagonist", "supporting"]
    public_identity: str = Field(min_length=1)
    core_desire: str = Field(min_length=1)
    core_fear: str = Field(min_length=1)
    hidden_secret: str | None = None
    conflict_links: list[str] = Field(default_factory=list)
    voice_style: str = Field(min_length=1)
    arc_target: str = Field(min_length=1)


class CharacterArtifact(BaseModel):
    characters: list[CharacterCard] = Field(min_length=1)
```

`src/dramaloop/schemas/outline.py`
```python
from pydantic import BaseModel, Field


class StoryBeat(BaseModel):
    beat_id: str = Field(min_length=1)
    label: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    tension_level: int = Field(ge=1, le=10)
    payoff_dependency: str | None = None


class OutlineArtifact(BaseModel):
    beats: list[StoryBeat] = Field(min_length=5)
    ending_type: str = Field(min_length=1)
```

`src/dramaloop/schemas/critique.py`
```python
from typing import Literal

from pydantic import BaseModel, Field

RewriteTarget = Literal[
    "opening_hook",
    "character_motivation",
    "mid_conflict_escalation",
    "reversal_reveal",
    "ending_payoff",
    "prose_fluency",
]

DimensionName = Literal[
    "hook_strength",
    "character_consistency",
    "conflict_intensity",
    "pacing",
    "short_drama_feel",
    "ending_payoff",
    "language_fluency",
]


class DimensionCritique(BaseModel):
    score: int = Field(ge=1, le=10)
    reason: str = Field(min_length=1)
    evidence: str = Field(min_length=1)
    improvement_advice: str = Field(min_length=1)


class RewritePlan(BaseModel):
    scope: str = Field(min_length=1)
    must_fix: list[str] = Field(default_factory=list)
    keep: list[str] = Field(default_factory=list)


class CritiqueArtifact(BaseModel):
    dimension_scores: dict[DimensionName, DimensionCritique]
    overall_score: float
    weakest_dimensions: list[DimensionName] = Field(min_length=1)
    rewrite_target: RewriteTarget
    rewrite_plan: RewritePlan
```

`src/dramaloop/schemas/rewrite.py`
```python
from pydantic import BaseModel, Field

from dramaloop.schemas.critique import RewriteTarget


class RewriteArtifact(BaseModel):
    version: int = Field(ge=1)
    target_section: RewriteTarget
    goals: list[str] = Field(default_factory=list)
    changes_made: list[str] = Field(default_factory=list)
    expected_score_improvement: list[str] = Field(default_factory=list)
```

`src/dramaloop/schemas/run.py`
```python
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class RunManifest(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"]
    started_at: str
    finished_at: str | None = None
    model_provider: str
    model_name: str
    max_iterations: int
    completed_iterations: int = 0
    target_threshold: float
    minimum_dimension_threshold: int
    min_delta: float
    final_artifact: str | None = None
    error_message: str | None = None


class RunEvent(BaseModel):
    ts: str
    stage: str
    event: str
    iteration: int | None = None
    artifact: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class RunPaths:
    root: Path
    request_path: Path
    manifest_path: Path
    events_path: Path


class RunResult(BaseModel):
    run_id: str
    run_dir: Path
    final_story_path: Path
    summary_path: Path
```

- [ ] **Step 4: Run the schema tests again**

Run: `uv run pytest tests/unit/test_config_and_schemas.py -v`
Expected: PASS with `4 passed`

- [ ] **Step 5: Commit the settings and schemas**

```bash
git add src/dramaloop/config.py src/dramaloop/schemas tests/unit/test_config_and_schemas.py
git commit -m "feat: add dramaloop settings and schemas"
```

---

### Task 4: Implement run storage, artifact writers, and event logging

**Files:**
- Create: `src/dramaloop/storage/runs.py`
- Create: `src/dramaloop/storage/artifacts.py`
- Create: `src/dramaloop/utils/json_io.py`
- Create: `src/dramaloop/utils/logging.py`
- Test: `tests/unit/test_storage.py`

**Interfaces:**
- Consumes:
  - `StoryRequest`
  - `RunManifest`, `RunEvent`, `RunPaths`
- Produces:
  - `build_run_id(idea: str, started_at: datetime) -> str`
  - `create_run_paths(runs_dir: Path, run_id: str) -> RunPaths`
  - `initialize_run_files(run_paths: RunPaths, request: StoryRequest, manifest: RunManifest) -> None`
  - `write_json_artifact(path: Path, payload: BaseModel | dict) -> None`
  - `write_markdown_artifact(path: Path, body: str) -> None`
  - `append_event(events_path: Path, event: RunEvent) -> None`
  - `console_step(message: str) -> str`

- [ ] **Step 1: Write failing tests for run IDs, bootstrap files, and JSONL events**

```python
from datetime import datetime
from pathlib import Path

from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent, RunManifest
from dramaloop.storage.artifacts import append_event, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files


def test_build_run_id_uses_timestamp_and_ascii_slug_fallback() -> None:
    run_id = build_run_id("被未婚夫退婚后她嫁给死对头", datetime(2026, 7, 8, 15, 30, 0))

    assert run_id == "20260708-153000-story"


def test_initialize_run_files_writes_request_manifest_and_events_file(tmp_path: Path) -> None:
    request = StoryRequest(idea="x", style=["都市"], length="short")
    manifest = RunManifest(
        run_id="20260708-153000-story",
        status="running",
        started_at="2026-07-08T15:30:00",
        model_provider="mock",
        model_name="mock-model",
        max_iterations=2,
        target_threshold=7.5,
        minimum_dimension_threshold=6,
        min_delta=0.3,
    )

    run_paths = create_run_paths(tmp_path, manifest.run_id)
    initialize_run_files(run_paths, request, manifest)

    assert run_paths.request_path.exists()
    assert run_paths.manifest_path.exists()
    assert run_paths.events_path.exists()


def test_append_event_writes_one_json_object_per_line(tmp_path: Path) -> None:
    events_path = tmp_path / "events.jsonl"
    append_event(
        events_path,
        RunEvent(ts="2026-07-08T15:30:00", stage="premise_refinement", event="completed", artifact="premise.json"),
    )

    assert events_path.read_text(encoding="utf-8").strip().endswith('"artifact":"premise.json"}')


def test_write_markdown_artifact_creates_parent_directory(tmp_path: Path) -> None:
    markdown_path = tmp_path / "nested" / "draft_v1.md"
    write_markdown_artifact(markdown_path, "# Draft\n")

    assert markdown_path.read_text(encoding="utf-8") == "# Draft\n"
```

- [ ] **Step 2: Run the storage tests to verify the storage layer is missing**

Run: `uv run pytest tests/unit/test_storage.py -v`
Expected: FAIL with import errors for `dramaloop.storage.*`

- [ ] **Step 3: Implement run helpers, JSON writers, and logging helpers**

`src/dramaloop/utils/json_io.py`
```python
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def dump_json(path: Path, payload: BaseModel | dict[str, Any] | list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
```

`src/dramaloop/storage/runs.py`
```python
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


def create_run_paths(runs_dir: Path, run_id: str) -> RunPaths:
    root = runs_dir / run_id
    root.mkdir(parents=True, exist_ok=True)
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
```

`src/dramaloop/storage/artifacts.py`
```python
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
        handle.write(event.model_dump_json() + "\n")
```

`src/dramaloop/utils/logging.py`
```python
def console_step(message: str) -> str:
    return f"[dramaloop] {message}"
```

- [ ] **Step 4: Run the storage tests again**

Run: `uv run pytest tests/unit/test_storage.py -v`
Expected: PASS with `4 passed`

- [ ] **Step 5: Commit the storage layer**

```bash
git add src/dramaloop/storage src/dramaloop/utils tests/unit/test_storage.py
git commit -m "feat: add run storage and artifact writers"
```

---

### Task 5: Add the LLM abstraction and deterministic mock client

**Files:**
- Create: `src/dramaloop/llm/base.py`
- Create: `src/dramaloop/llm/mock.py`
- Test: `tests/unit/test_mock_llm.py`

**Interfaces:**
- Consumes: schema models from `src/dramaloop/schemas/*`
- Produces:
  - `class LLMClient(Protocol)`
  - `class LLMInvocationError(RuntimeError)`
  - `MockLLMClient(structured_outputs: dict[str, dict], text_outputs: dict[str, str])`
  - `build_default_mock_client() -> MockLLMClient`
  - `MockLLMClient.generate_structured(role: str, prompt: str, response_model: type[TModel]) -> TModel`
  - `MockLLMClient.generate_text(role: str, prompt: str) -> str`

- [ ] **Step 1: Write failing tests for structured and text mock outputs**

```python
from dramaloop.llm.mock import MockLLMClient, build_default_mock_client
from dramaloop.schemas.premise import PremiseArtifact


def test_mock_client_returns_validated_structured_model() -> None:
    client = MockLLMClient(
        structured_outputs={
            "premise_refinement": {
                "title_candidate": "替嫁反击",
                "logline": "她被退婚后嫁给死对头反击前任。",
                "core_conflict": "前任和新婚丈夫的权力对抗把她卷到中心。",
                "hook_promise": "婚礼背叛后立即反击。",
                "ending_payoff_plan": "前任失去一切，她赢回尊严与爱。",
                "tone_notes": ["快节奏"],
                "hard_constraints": ["短篇"],
            }
        },
        text_outputs={},
    )

    artifact = client.generate_structured(
        role="premise_refinement",
        prompt="refine premise",
        response_model=PremiseArtifact,
    )

    assert artifact.title_candidate == "替嫁反击"


def test_default_mock_client_can_generate_text() -> None:
    client = build_default_mock_client()

    assert "替嫁反击" in client.generate_text(role="draft_generation", prompt="write draft")
```

- [ ] **Step 2: Run the mock LLM tests to verify the client layer is missing**

Run: `uv run pytest tests/unit/test_mock_llm.py -v`
Expected: FAIL with import errors for `dramaloop.llm.mock`

- [ ] **Step 3: Implement the protocol, exception, and mock client**

`src/dramaloop/llm/base.py`
```python
from typing import Protocol, TypeVar

from pydantic import BaseModel

TModel = TypeVar("TModel", bound=BaseModel)


class LLMInvocationError(RuntimeError):
    pass


class LLMClient(Protocol):
    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        ...

    def generate_text(self, *, role: str, prompt: str) -> str:
        ...
```

`src/dramaloop/llm/mock.py`
```python
from typing import Any

from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel


DEFAULT_STRUCTURED_OUTPUTS: dict[str, dict[str, Any]] = {
    "premise_refinement": {
        "title_candidate": "替嫁反击",
        "logline": "她被退婚后转身嫁给死对头。",
        "core_conflict": "两大家族的旧怨与新婚关系相互引爆。",
        "hook_promise": "婚礼羞辱后立刻反击。",
        "ending_payoff_plan": "前任公开失势，她赢回尊严。",
        "tone_notes": ["快节奏", "爽感强"],
        "hard_constraints": ["短篇"],
    },
    "character_card_generation": {
        "characters": [
            {
                "name": "林晚",
                "role": "protagonist",
                "public_identity": "珠宝设计师",
                "core_desire": "夺回尊严与事业",
                "core_fear": "再次成为被选择的人",
                "hidden_secret": None,
                "conflict_links": ["顾承骁", "陆闻舟"],
                "voice_style": "冷静锋利",
                "arc_target": "从隐忍到掌控局面",
            }
        ]
    },
    "story_outline_generation": {
        "beats": [
            {"beat_id": "b1", "label": "hook", "purpose": "抓人", "summary": "婚礼被退婚", "tension_level": 9, "payoff_dependency": None},
            {"beat_id": "b2", "label": "inciting", "purpose": "冲突", "summary": "她当场改嫁死对头", "tension_level": 9, "payoff_dependency": None},
            {"beat_id": "b3", "label": "escalation", "purpose": "升级", "summary": "前任家族全线封杀", "tension_level": 8, "payoff_dependency": "b5"},
            {"beat_id": "b4", "label": "reveal", "purpose": "反转", "summary": "新婚丈夫早就布局复仇", "tension_level": 9, "payoff_dependency": "b5"},
            {"beat_id": "b5", "label": "payoff", "purpose": "回报", "summary": "前任众叛亲离", "tension_level": 10, "payoff_dependency": None},
        ],
        "ending_type": "revenge payoff",
    },
    "critique_scoring": {
        "dimension_scores": {
            "hook_strength": {"score": 8, "reason": "开头快", "evidence": "第一段就是婚礼羞辱", "improvement_advice": "继续保持"},
            "character_consistency": {"score": 7, "reason": "人物动机清晰", "evidence": "林晚始终围绕尊严", "improvement_advice": "增加内心动作"},
            "conflict_intensity": {"score": 8, "reason": "冲突够强", "evidence": "家族对抗持续升级", "improvement_advice": "中段再推高"},
            "pacing": {"score": 7, "reason": "节奏稳定", "evidence": "段落推进紧凑", "improvement_advice": "删掉一处解释"},
            "short_drama_feel": {"score": 8, "reason": "短剧感明显", "evidence": "钩子-反击-反转齐全", "improvement_advice": "增强结尾爆点"},
            "ending_payoff": {"score": 7, "reason": "结尾有回报", "evidence": "前任公开失势", "improvement_advice": "加一记更狠的反杀"},
            "language_fluency": {"score": 7, "reason": "可读性好", "evidence": "句式通顺", "improvement_advice": "增加一句更利落台词"},
        },
        "overall_score": 7.43,
        "weakest_dimensions": ["ending_payoff"],
        "rewrite_target": "ending_payoff",
        "rewrite_plan": {"scope": "结尾两段", "must_fix": ["增加终局反杀"], "keep": ["婚礼开头", "中段反转"]},
    },
}

DEFAULT_TEXT_OUTPUTS = {
    "draft_generation": "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n",
    "targeted_rewrite": "# 替嫁反击\n\n婚礼大屏亮起时，林晚看见了陆闻舟牵着别人的手。\n\n她没有哭，只当着所有宾客的面，转头看向陆闻舟最大的死对头顾承骁：\"顾总，你还缺新娘吗？\"\n\n最后一场董事会直播里，顾承骁把陆闻舟转移资产的证据推上屏幕。林晚接过话筒，只说了一句：\"你在婚礼上丢掉的，不只是我，是你陆家最后一点体面。\"\n",
}


class MockLLMClient(LLMClient):
    def __init__(self, *, structured_outputs: dict[str, dict[str, Any]], text_outputs: dict[str, str]) -> None:
        self._structured_outputs = structured_outputs
        self._text_outputs = text_outputs

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        try:
            payload = self._structured_outputs[role]
        except KeyError as exc:
            raise LLMInvocationError(f"Missing mock structured output for role={role}") from exc
        return response_model.model_validate(payload)

    def generate_text(self, *, role: str, prompt: str) -> str:
        try:
            return self._text_outputs[role]
        except KeyError as exc:
            raise LLMInvocationError(f"Missing mock text output for role={role}") from exc


def build_default_mock_client() -> MockLLMClient:
    return MockLLMClient(structured_outputs=DEFAULT_STRUCTURED_OUTPUTS, text_outputs=DEFAULT_TEXT_OUTPUTS)
```

- [ ] **Step 4: Run the mock-client tests again**

Run: `uv run pytest tests/unit/test_mock_llm.py -v`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit the LLM abstraction and mock client**

```bash
git add src/dramaloop/llm tests/unit/test_mock_llm.py
git commit -m "feat: add llm protocol and mock client"
```

---

### Task 6: Implement premise, character, and outline prompt builders and stage functions

**Files:**
- Create: `src/dramaloop/prompts/premise.py`
- Create: `src/dramaloop/prompts/characters.py`
- Create: `src/dramaloop/prompts/outline.py`
- Create: `src/dramaloop/harness/stages.py`
- Test: `tests/unit/test_stage_builders.py`

**Interfaces:**
- Consumes:
  - `LLMClient`
  - `StoryRequest`, `PremiseArtifact`, `CharacterArtifact`, `OutlineArtifact`
- Produces:
  - `build_premise_prompt(request: StoryRequest) -> str`
  - `build_character_prompt(premise: PremiseArtifact) -> str`
  - `build_outline_prompt(premise: PremiseArtifact, characters: CharacterArtifact) -> str`
  - `run_premise_stage(client: LLMClient, request: StoryRequest) -> PremiseArtifact`
  - `run_character_stage(client: LLMClient, premise: PremiseArtifact) -> CharacterArtifact`
  - `run_outline_stage(client: LLMClient, premise: PremiseArtifact, characters: CharacterArtifact) -> OutlineArtifact`

- [ ] **Step 1: Write failing tests for prompt content and typed stage outputs**

```python
from dramaloop.harness.stages import run_character_stage, run_outline_stage, run_premise_stage
from dramaloop.llm.mock import build_default_mock_client
from dramaloop.prompts.premise import build_premise_prompt
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.input import StoryRequest


def test_premise_prompt_mentions_hook_and_ending_payoff() -> None:
    request = StoryRequest(idea="她被退婚后反手结婚", style=["都市情感"], length="short")
    prompt = build_premise_prompt(request)

    assert "hook" in prompt.lower()
    assert "ending payoff" in prompt.lower()


def test_stage_chain_returns_typed_outputs() -> None:
    client = build_default_mock_client()
    request = StoryRequest(idea="她被退婚后反手结婚", style=["都市情感"], length="short")

    premise = run_premise_stage(client, request)
    characters = run_character_stage(client, premise)
    outline = run_outline_stage(client, premise, characters)

    assert premise.title_candidate == "替嫁反击"
    assert isinstance(characters, CharacterArtifact)
    assert outline.ending_type == "revenge payoff"
```

- [ ] **Step 2: Run the stage-builder tests to confirm the modules are missing**

Run: `uv run pytest tests/unit/test_stage_builders.py -v`
Expected: FAIL with import errors for `dramaloop.prompts.*` or `dramaloop.harness.stages`

- [ ] **Step 3: Implement the prompt builders and the first three stage functions**

`src/dramaloop/prompts/premise.py`
```python
from dramaloop.schemas.input import StoryRequest


def build_premise_prompt(request: StoryRequest) -> str:
    return "\n".join(
        [
            "You are the Premise Refiner for a short-drama fiction system.",
            f"Idea: {request.idea}",
            f"Style tags: {', '.join(request.style)}",
            f"Audience: {request.audience or 'general'}",
            f"Constraints: {', '.join(request.constraints) or 'none'}",
            "Produce a structured premise with a strong hook, core conflict, and ending payoff.",
        ]
    )
```

`src/dramaloop/prompts/characters.py`
```python
from dramaloop.schemas.premise import PremiseArtifact


def build_character_prompt(premise: PremiseArtifact) -> str:
    return "\n".join(
        [
            "You are the Character Designer for a short-drama fiction system.",
            f"Logline: {premise.logline}",
            f"Core conflict: {premise.core_conflict}",
            "Create character cards that maximize conflict, voice contrast, and payoff potential.",
        ]
    )
```

`src/dramaloop/prompts/outline.py`
```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.premise import PremiseArtifact


def build_outline_prompt(premise: PremiseArtifact, characters: CharacterArtifact) -> str:
    names = ", ".join(character.name for character in characters.characters)
    return "\n".join(
        [
            "You are the Outliner for a short-drama fiction system.",
            f"Logline: {premise.logline}",
            f"Characters: {names}",
            "Return at least five beats covering hook, inciting conflict, escalation, reversal, and ending payoff.",
        ]
    )
```

`src/dramaloop/harness/stages.py`
```python
from dramaloop.llm.base import LLMClient
from dramaloop.prompts.characters import build_character_prompt
from dramaloop.prompts.outline import build_outline_prompt
from dramaloop.prompts.premise import build_premise_prompt
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


def run_premise_stage(client: LLMClient, request: StoryRequest) -> PremiseArtifact:
    return client.generate_structured(
        role="premise_refinement",
        prompt=build_premise_prompt(request),
        response_model=PremiseArtifact,
    )


def run_character_stage(client: LLMClient, premise: PremiseArtifact) -> CharacterArtifact:
    return client.generate_structured(
        role="character_card_generation",
        prompt=build_character_prompt(premise),
        response_model=CharacterArtifact,
    )


def run_outline_stage(client: LLMClient, premise: PremiseArtifact, characters: CharacterArtifact) -> OutlineArtifact:
    return client.generate_structured(
        role="story_outline_generation",
        prompt=build_outline_prompt(premise, characters),
        response_model=OutlineArtifact,
    )
```

- [ ] **Step 4: Run the stage-builder tests again**

Run: `uv run pytest tests/unit/test_stage_builders.py -v`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit the first stage pipeline**

```bash
git add src/dramaloop/prompts src/dramaloop/harness/stages.py tests/unit/test_stage_builders.py
git commit -m "feat: add premise character and outline stages"
```

---

### Task 7: Implement draft, critique, rewrite, loop policy, and summary rendering

**Files:**
- Create: `src/dramaloop/prompts/draft.py`
- Create: `src/dramaloop/prompts/critique.py`
- Create: `src/dramaloop/prompts/rewrite.py`
- Create: `src/dramaloop/harness/loop.py`
- Create: `src/dramaloop/eval/dimensions.py`
- Create: `src/dramaloop/eval/scorer.py`
- Create: `src/dramaloop/utils/markdown.py`
- Modify: `src/dramaloop/harness/stages.py`
- Test: `tests/unit/test_loop_and_summary.py`

**Interfaces:**
- Consumes:
  - `LLMClient`
  - `PremiseArtifact`, `CharacterArtifact`, `OutlineArtifact`, `CritiqueArtifact`, `RewriteArtifact`
  - `Settings`
- Produces:
  - `build_draft_prompt(...) -> str`
  - `build_critique_prompt(...) -> str`
  - `build_rewrite_prompt(...) -> str`
  - `ordered_dimensions() -> list[str]`
  - `calculate_overall_score(critique: CritiqueArtifact) -> float`
  - `determine_stop_reason(previous_overall_score: float | None, current_critique: CritiqueArtifact, settings: Settings, iteration: int, max_iterations: int) -> str | None`
  - `should_continue_loop(...) -> bool`
  - `render_run_summary(...) -> str`
  - `run_draft_stage(...) -> str`
  - `run_critique_stage(...) -> CritiqueArtifact`
  - `run_rewrite_stage(...) -> tuple[RewriteArtifact, str]`

- [ ] **Step 1: Write failing tests for loop policy and summary rendering**

```python
from dramaloop.config import Settings
from dramaloop.eval.scorer import calculate_overall_score
from dramaloop.harness.loop import determine_stop_reason, should_continue_loop
from dramaloop.schemas.critique import CritiqueArtifact, DimensionCritique, RewritePlan
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.rewrite import RewriteArtifact
from dramaloop.utils.markdown import render_run_summary


def _critique(score_map: dict[str, int], target: str = "ending_payoff") -> CritiqueArtifact:
    return CritiqueArtifact(
        dimension_scores={
            name: DimensionCritique(score=value, reason="ok", evidence="proof", improvement_advice="improve")
            for name, value in score_map.items()
        },
        overall_score=round(sum(score_map.values()) / len(score_map), 2),
        weakest_dimensions=[min(score_map, key=score_map.get)],
        rewrite_target=target,
        rewrite_plan=RewritePlan(scope="ending", must_fix=["ending"], keep=["opening"]),
    )


def test_should_continue_loop_when_score_is_below_threshold() -> None:
    settings = Settings()
    critique = _critique(
        {
            "hook_strength": 6,
            "character_consistency": 7,
            "conflict_intensity": 6,
            "pacing": 6,
            "short_drama_feel": 6,
            "ending_payoff": 5,
            "language_fluency": 7,
        }
    )

    assert should_continue_loop(None, critique, settings, iteration=1, max_iterations=2) is True
    assert determine_stop_reason(None, critique, settings, iteration=1, max_iterations=2) is None


def test_should_stop_loop_when_gain_is_too_small() -> None:
    settings = Settings()
    critique = _critique(
        {
            "hook_strength": 7,
            "character_consistency": 7,
            "conflict_intensity": 7,
            "pacing": 7,
            "short_drama_feel": 7,
            "ending_payoff": 7,
            "language_fluency": 7,
        }
    )

    assert should_continue_loop(6.85, critique, settings, iteration=2, max_iterations=3) is False
    assert determine_stop_reason(6.85, critique, settings, iteration=2, max_iterations=3) == "improvement_below_min_delta"


def test_render_run_summary_includes_score_table_and_rewrite_notes() -> None:
    request = StoryRequest(idea="她被退婚后闪婚死对头", style=["都市情感"], length="short")
    critique_history = [
        _critique(
            {
                "hook_strength": 6,
                "character_consistency": 7,
                "conflict_intensity": 6,
                "pacing": 5,
                "short_drama_feel": 6,
                "ending_payoff": 5,
                "language_fluency": 7,
            }
        ),
        _critique(
            {
                "hook_strength": 8,
                "character_consistency": 7,
                "conflict_intensity": 8,
                "pacing": 7,
                "short_drama_feel": 8,
                "ending_payoff": 7,
                "language_fluency": 7,
            },
            target="opening_hook",
        ),
    ]
    rewrite_history = [
        RewriteArtifact(
            version=1,
            target_section="ending_payoff",
            goals=["兑现回报"],
            changes_made=["补强结尾反杀"],
            expected_score_improvement=["ending_payoff", "short_drama_feel"],
        )
    ]

    markdown = render_run_summary(
        request=request,
        critique_history=critique_history,
        rewrite_history=rewrite_history,
        final_story_path="final_story.md",
        stop_reason="target_threshold_reached",
    )

    assert "| Version | Hook | Character | Conflict | Pacing | Drama Feel | Ending | Fluency | Overall |" in markdown
    assert "补强结尾反杀" in markdown
    assert "final_story.md" in markdown
    assert calculate_overall_score(critique_history[1]) > calculate_overall_score(critique_history[0])
```

- [ ] **Step 2: Run the loop and summary tests to confirm the helpers are missing**

Run: `uv run pytest tests/unit/test_loop_and_summary.py -v`
Expected: FAIL with import errors for `dramaloop.harness.loop` or `dramaloop.utils.markdown`

- [ ] **Step 3: Implement prompt builders, later stage functions, loop helpers, and summary rendering**

`src/dramaloop/prompts/draft.py`
```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


def build_draft_prompt(premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    return "\n".join(
        [
            "You are the Drafter for a short-drama fiction system.",
            f"Title candidate: {premise.title_candidate}",
            f"Logline: {premise.logline}",
            f"Character count: {len(characters.characters)}",
            f"Beat count: {len(outline.beats)}",
            "Write a short, punchy story with a strong hook and a satisfying payoff.",
        ]
    )
```

`src/dramaloop/prompts/critique.py`
```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


def build_critique_prompt(draft_markdown: str, premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    return "\n".join(
        [
            "You are the Critic for a short-drama fiction system.",
            f"Logline: {premise.logline}",
            f"Character count: {len(characters.characters)}",
            f"Beat count: {len(outline.beats)}",
            "Score the draft on hook_strength, character_consistency, conflict_intensity, pacing, short_drama_feel, ending_payoff, and language_fluency.",
            "Return the weakest dimensions, a rewrite target, and a rewrite plan.",
            draft_markdown,
        ]
    )
```

`src/dramaloop/prompts/rewrite.py`
```python
from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


def build_rewrite_prompt(
    draft_markdown: str,
    critique: CritiqueArtifact,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
) -> str:
    return "\n".join(
        [
            "You are the Rewriter for a short-drama fiction system.",
            f"Rewrite target: {critique.rewrite_target}",
            f"Core conflict: {premise.core_conflict}",
            f"Character count: {len(characters.characters)}",
            f"Beat count: {len(outline.beats)}",
            f"Must fix: {', '.join(critique.rewrite_plan.must_fix)}",
            f"Keep: {', '.join(critique.rewrite_plan.keep)}",
            "Rewrite only the weak section and adjacent lines needed for coherence.",
            draft_markdown,
        ]
    )
```

`src/dramaloop/eval/dimensions.py`
```python
def ordered_dimensions() -> list[str]:
    return [
        "hook_strength",
        "character_consistency",
        "conflict_intensity",
        "pacing",
        "short_drama_feel",
        "ending_payoff",
        "language_fluency",
    ]
```

`src/dramaloop/eval/scorer.py`
```python
from dramaloop.schemas.critique import CritiqueArtifact


def calculate_overall_score(critique: CritiqueArtifact) -> float:
    values = [dimension.score for dimension in critique.dimension_scores.values()]
    return round(sum(values) / len(values), 2)
```

`src/dramaloop/harness/loop.py`
```python
from dramaloop.config import Settings
from dramaloop.schemas.critique import CritiqueArtifact


def determine_stop_reason(
    previous_overall_score: float | None,
    current_critique: CritiqueArtifact,
    settings: Settings,
    iteration: int,
    max_iterations: int,
) -> str | None:
    if current_critique.overall_score >= settings.target_threshold:
        return "target_threshold_reached"
    if all(score.score >= settings.minimum_dimension_threshold for score in current_critique.dimension_scores.values()):
        return "minimum_dimension_threshold_reached"
    if previous_overall_score is not None and current_critique.overall_score - previous_overall_score < settings.min_delta:
        return "improvement_below_min_delta"
    if iteration >= max_iterations:
        return "max_iterations_reached"
    return None


def should_continue_loop(
    previous_overall_score: float | None,
    current_critique: CritiqueArtifact,
    settings: Settings,
    iteration: int,
    max_iterations: int,
) -> bool:
    return determine_stop_reason(previous_overall_score, current_critique, settings, iteration, max_iterations) is None
```

`src/dramaloop/utils/markdown.py`
```python
from dramaloop.eval.dimensions import ordered_dimensions
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.rewrite import RewriteArtifact


def render_run_summary(
    *,
    request: StoryRequest,
    critique_history: list[CritiqueArtifact],
    rewrite_history: list[RewriteArtifact],
    final_story_path: str,
    stop_reason: str,
) -> str:
    header = "| Version | Hook | Character | Conflict | Pacing | Drama Feel | Ending | Fluency | Overall |"
    divider = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    rows = []
    for index, critique in enumerate(critique_history, start=1):
        values = [str(critique.dimension_scores[name].score) for name in ordered_dimensions()]
        rows.append(f"| v{index} | {' | '.join(values)} | {critique.overall_score:.2f} |")
    rewrite_lines = [f"- v{item.version}: {', '.join(item.changes_made)}" for item in rewrite_history] or ["- none"]
    return "\n".join(
        [
            "# Run Summary",
            "",
            "## Input",
            f"- Idea: {request.idea}",
            f"- Style: {', '.join(request.style)}",
            f"- Audience: {request.audience or 'general'}",
            "",
            "## Iteration Score Trend",
            header,
            divider,
            *rows,
            "",
            "## Rewrite Notes",
            *rewrite_lines,
            "",
            f"## Final Story\n- Path: {final_story_path}",
            f"\n## Stop Reason\n- {stop_reason}",
        ]
    )
```

Append to `src/dramaloop/harness/stages.py`
```python
from dramaloop.prompts.critique import build_critique_prompt
from dramaloop.prompts.draft import build_draft_prompt
from dramaloop.prompts.rewrite import build_rewrite_prompt
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.rewrite import RewriteArtifact


def run_draft_stage(client: LLMClient, premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    return client.generate_text(
        role="draft_generation",
        prompt=build_draft_prompt(premise, characters, outline),
    )


def run_critique_stage(
    client: LLMClient,
    draft_markdown: str,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
) -> CritiqueArtifact:
    return client.generate_structured(
        role="critique_scoring",
        prompt=build_critique_prompt(draft_markdown, premise, characters, outline),
        response_model=CritiqueArtifact,
    )


def run_rewrite_stage(
    client: LLMClient,
    draft_markdown: str,
    critique: CritiqueArtifact,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
    next_version: int,
) -> tuple[RewriteArtifact, str]:
    revised_draft = client.generate_text(
        role="targeted_rewrite",
        prompt=build_rewrite_prompt(draft_markdown, critique, premise, characters, outline),
    )
    rewrite_artifact = RewriteArtifact(
        version=next_version - 1,
        target_section=critique.rewrite_target,
        goals=critique.rewrite_plan.must_fix,
        changes_made=critique.rewrite_plan.must_fix,
        expected_score_improvement=critique.weakest_dimensions,
    )
    return rewrite_artifact, revised_draft
```

- [ ] **Step 4: Run the loop and summary tests again**

Run: `uv run pytest tests/unit/test_loop_and_summary.py -v`
Expected: PASS with `3 passed`

- [ ] **Step 5: Commit the loop-ready stage set**

```bash
git add src/dramaloop/prompts src/dramaloop/harness src/dramaloop/eval src/dramaloop/utils/markdown.py tests/unit/test_loop_and_summary.py
git commit -m "feat: add critique rewrite loop and summary renderer"
```

---

### Task 8: Implement the real provider adapter and client factory

**Files:**
- Create: `src/dramaloop/llm/provider.py`
- Test: `tests/unit/test_provider_adapter.py`

**Interfaces:**
- Consumes:
  - `Settings`
  - `LLMClient`, `LLMInvocationError`, `TModel`
  - `build_default_mock_client()`
- Produces:
  - `AnthropicLLMClient(api_key: str, model_name: str)`
  - `build_llm_client(settings: Settings) -> LLMClient`

- [ ] **Step 1: Write failing tests for provider selection and Anthropic key validation**

```python
import pytest

from dramaloop.config import Settings
from dramaloop.llm.base import LLMInvocationError
from dramaloop.llm.provider import build_llm_client


def test_build_llm_client_returns_mock_for_mock_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    client = build_llm_client(Settings())

    assert client.__class__.__name__ == "MockLLMClient"


def test_build_llm_client_requires_api_key_for_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(LLMInvocationError):
        build_llm_client(Settings())
```

- [ ] **Step 2: Run the provider tests to verify the adapter is missing**

Run: `uv run pytest tests/unit/test_provider_adapter.py -v`
Expected: FAIL with import errors for `dramaloop.llm.provider`

- [ ] **Step 3: Implement the Anthropic adapter and provider factory**

`src/dramaloop/llm/provider.py`
```python
import json
import os

from anthropic import Anthropic

from dramaloop.config import Settings
from dramaloop.llm.base import LLMClient, LLMInvocationError, TModel
from dramaloop.llm.mock import build_default_mock_client


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str, model_name: str) -> None:
        self._client = Anthropic(api_key=api_key)
        self._model_name = model_name

    def generate_structured(self, *, role: str, prompt: str, response_model: type[TModel]) -> TModel:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=2000,
            temperature=0.7,
            system=f"You are the {role} stage in a structured short-drama generation system. Return valid JSON only.",
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", None) == "text")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMInvocationError(f"Structured response for role={role} was not valid JSON") from exc
        return response_model.model_validate(payload)

    def generate_text(self, *, role: str, prompt: str) -> str:
        response = self._client.messages.create(
            model=self._model_name,
            max_tokens=2500,
            temperature=0.8,
            system=f"You are the {role} stage in a short-drama generation system.",
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(block.text for block in response.content if getattr(block, "type", None) == "text")


def build_llm_client(settings: Settings) -> LLMClient:
    if settings.provider == "mock":
        return build_default_mock_client()
    if settings.provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMInvocationError("ANTHROPIC_API_KEY is required when DRAMALOOP_PROVIDER=anthropic")
        return AnthropicLLMClient(api_key=api_key, model_name=settings.model_name)
    raise LLMInvocationError(f"Unsupported provider: {settings.provider}")
```

- [ ] **Step 4: Run the provider tests again**

Run: `uv run pytest tests/unit/test_provider_adapter.py -v`
Expected: PASS with `2 passed`

- [ ] **Step 5: Commit the provider adapter**

```bash
git add src/dramaloop/llm/provider.py tests/unit/test_provider_adapter.py
git commit -m "feat: add anthropic adapter and client factory"
```

---

### Task 9: Build the orchestrator and the `dramaloop run` command

**Files:**
- Create: `src/dramaloop/harness/context.py`
- Create: `src/dramaloop/harness/orchestrator.py`
- Modify: `src/dramaloop/main.py`
- Test: `tests/integration/test_run_command.py`

**Interfaces:**
- Consumes:
  - all stage functions from `src/dramaloop/harness/stages.py`
  - `determine_stop_reason`, `should_continue_loop`
  - storage helpers from `src/dramaloop/storage/*`
  - `Settings`
  - `build_llm_client(settings)`
- Produces:
  - `PipelineContext`
  - `build_running_manifest(run_id: str, settings: Settings, request: StoryRequest, started_at: datetime) -> RunManifest`
  - `run_story_pipeline(request: StoryRequest, settings: Settings, client: LLMClient, started_at: datetime | None = None) -> RunResult`
  - CLI `run` command that accepts `--input` or direct args

- [ ] **Step 1: Write the failing integration tests for a successful run and a failed manifest update**

```python
from pathlib import Path

from typer.testing import CliRunner

from dramaloop.llm.base import LLMInvocationError
from dramaloop.main import app


runner = CliRunner()


class ExplodingClient:
    def generate_structured(self, *, role: str, prompt: str, response_model):
        raise LLMInvocationError("boom")

    def generate_text(self, *, role: str, prompt: str) -> str:
        raise LLMInvocationError("boom")


def test_run_command_creates_required_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    result = runner.invoke(
        app,
        [
            "run",
            "--idea",
            "她被退婚后嫁给死对头",
            "--style",
            "都市情感",
            "--style",
            "逆袭",
        ],
    )

    assert result.exit_code == 0
    created_runs = list((tmp_path / "runs").iterdir())
    assert len(created_runs) == 1
    run_dir = created_runs[0]
    assert (run_dir / "premise.json").exists()
    assert (run_dir / "characters.json").exists()
    assert (run_dir / "outline.json").exists()
    assert (run_dir / "draft_v1.md").exists()
    assert (run_dir / "critique_v1.json").exists()
    assert (run_dir / "final_story.md").exists()
    assert (run_dir / "run_summary.md").exists()


def test_run_command_marks_manifest_failed_when_stage_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setattr("dramaloop.main.build_llm_client", lambda settings: ExplodingClient())

    result = runner.invoke(app, ["run", "--idea", "x", "--style", "都市情感"])

    assert result.exit_code != 0
    created_runs = list((tmp_path / "runs").iterdir())
    assert len(created_runs) == 1
    assert '"status": "failed"' in (created_runs[0] / "run_manifest.json").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the run-command integration tests to confirm the command is still empty**

Run: `uv run pytest tests/integration/test_run_command.py -v`
Expected: FAIL because `run` accepts no options and no run directory is created

- [ ] **Step 3: Implement the context model, orchestrator, and real `run` command**

`src/dramaloop/harness/context.py`
```python
from dataclasses import dataclass, field

from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
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
```

`src/dramaloop/harness/orchestrator.py`
```python
from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.context import PipelineContext
from dramaloop.harness.loop import determine_stop_reason, should_continue_loop
from dramaloop.harness.stages import (
    run_character_stage,
    run_critique_stage,
    run_draft_stage,
    run_outline_stage,
    run_premise_stage,
    run_rewrite_stage,
)
from dramaloop.llm.base import LLMClient
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunEvent, RunManifest, RunResult
from dramaloop.storage.artifacts import append_event, write_json_artifact, write_markdown_artifact
from dramaloop.storage.runs import build_run_id, create_run_paths, initialize_run_files
from dramaloop.utils.markdown import render_run_summary


def build_running_manifest(run_id: str, settings: Settings, request: StoryRequest, started_at: datetime) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        status="running",
        started_at=started_at.isoformat(),
        model_provider=settings.provider,
        model_name=settings.model_name,
        max_iterations=request.max_iterations,
        target_threshold=settings.target_threshold,
        minimum_dimension_threshold=settings.minimum_dimension_threshold,
        min_delta=settings.min_delta,
    )


def _record_stage_event(run_events_path, stage: str, event: str, *, iteration: int | None = None, artifact: str | None = None, detail: str | None = None) -> None:
    append_event(
        run_events_path,
        RunEvent(
            ts=datetime.now().isoformat(),
            stage=stage,
            event=event,
            iteration=iteration,
            artifact=artifact,
            detail=detail,
        ),
    )


def run_story_pipeline(request: StoryRequest, settings: Settings, client: LLMClient, started_at: datetime | None = None) -> RunResult:
    started_at = started_at or datetime.now()
    run_id = build_run_id(request.idea, started_at)
    run_paths = create_run_paths(settings.runs_dir, run_id)
    manifest = build_running_manifest(run_id, settings, request, started_at)
    initialize_run_files(run_paths, request, manifest)
    context = PipelineContext(request=request, run_paths=run_paths)
    stop_reason = "max_iterations_reached"

    try:
        _record_stage_event(run_paths.events_path, "run", "started")

        _record_stage_event(run_paths.events_path, "premise_refinement", "started")
        context.premise = run_premise_stage(client, request)
        write_json_artifact(run_paths.root / "premise.json", context.premise)
        _record_stage_event(run_paths.events_path, "premise_refinement", "completed", artifact="premise.json")

        _record_stage_event(run_paths.events_path, "character_card_generation", "started")
        context.characters = run_character_stage(client, context.premise)
        write_json_artifact(run_paths.root / "characters.json", context.characters)
        _record_stage_event(run_paths.events_path, "character_card_generation", "completed", artifact="characters.json")

        _record_stage_event(run_paths.events_path, "story_outline_generation", "started")
        context.outline = run_outline_stage(client, context.premise, context.characters)
        write_json_artifact(run_paths.root / "outline.json", context.outline)
        _record_stage_event(run_paths.events_path, "story_outline_generation", "completed", artifact="outline.json")

        _record_stage_event(run_paths.events_path, "draft_generation", "started", iteration=1)
        draft = run_draft_stage(client, context.premise, context.characters, context.outline)
        context.drafts.append(draft)
        write_markdown_artifact(run_paths.root / "draft_v1.md", draft)
        _record_stage_event(run_paths.events_path, "draft_generation", "completed", iteration=1, artifact="draft_v1.md")

        previous_score = None
        current_iteration = 1
        while True:
            _record_stage_event(run_paths.events_path, "critique_scoring", "started", iteration=current_iteration)
            critique = run_critique_stage(client, context.drafts[-1], context.premise, context.characters, context.outline)
            context.critiques.append(critique)
            write_json_artifact(run_paths.root / f"critique_v{current_iteration}.json", critique)
            _record_stage_event(run_paths.events_path, "critique_scoring", "completed", iteration=current_iteration, artifact=f"critique_v{current_iteration}.json")

            stop_reason = determine_stop_reason(previous_score, critique, settings, current_iteration, request.max_iterations) or stop_reason
            if not should_continue_loop(previous_score, critique, settings, current_iteration, request.max_iterations):
                break

            _record_stage_event(run_paths.events_path, "targeted_rewrite", "started", iteration=current_iteration)
            rewrite_artifact, next_draft = run_rewrite_stage(
                client,
                context.drafts[-1],
                critique,
                context.premise,
                context.characters,
                context.outline,
                next_version=current_iteration + 1,
            )
            context.rewrites.append(rewrite_artifact)
            write_json_artifact(run_paths.root / f"rewrite_plan_v{current_iteration}.json", rewrite_artifact)
            context.drafts.append(next_draft)
            write_markdown_artifact(run_paths.root / f"draft_v{current_iteration + 1}.md", next_draft)
            _record_stage_event(run_paths.events_path, "targeted_rewrite", "completed", iteration=current_iteration, artifact=f"draft_v{current_iteration + 1}.md")
            previous_score = critique.overall_score
            current_iteration += 1

        final_story_path = run_paths.root / "final_story.md"
        write_markdown_artifact(final_story_path, context.drafts[-1])
        summary_path = run_paths.root / "run_summary.md"
        write_markdown_artifact(
            summary_path,
            render_run_summary(
                request=request,
                critique_history=context.critiques,
                rewrite_history=context.rewrites,
                final_story_path="final_story.md",
                stop_reason=stop_reason,
            ),
        )
        manifest.status = "completed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.completed_iterations = len(context.critiques)
        manifest.final_artifact = "final_story.md"
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "completed", artifact="final_story.md")
        return RunResult(run_id=run_id, run_dir=run_paths.root, final_story_path=final_story_path, summary_path=summary_path)
    except Exception as exc:
        manifest.status = "failed"
        manifest.finished_at = datetime.now().isoformat()
        manifest.error_message = str(exc)
        write_json_artifact(run_paths.manifest_path, manifest)
        _record_stage_event(run_paths.events_path, "run", "failed", detail=str(exc))
        raise
```

Modify `src/dramaloop/main.py`
```python
from pathlib import Path

import typer
import yaml

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest


app = typer.Typer(no_args_is_help=True, help="Dramaloop short-drama generation CLI")


def _load_request(
    input_path: Path | None,
    idea: str | None,
    style: list[str],
    audience: str | None,
    constraint: list[str],
) -> StoryRequest:
    if input_path is not None:
        payload = yaml.safe_load(input_path.read_text(encoding="utf-8"))
        return StoryRequest.model_validate(payload)
    if idea is None or not style:
        raise typer.BadParameter("Provide --input or provide --idea with at least one --style")
    return StoryRequest(idea=idea, style=style, length="short", audience=audience, constraints=constraint)


@app.command()
def run(
    input: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False),
    idea: str | None = typer.Option(default=None),
    style: list[str] = typer.Option(default_factory=list),
    audience: str | None = typer.Option(default=None),
    constraint: list[str] = typer.Option(default_factory=list),
) -> None:
    settings = Settings()
    request = _load_request(input, idea, style, audience, constraint)
    client = build_llm_client(settings)
    result = run_story_pipeline(request, settings, client)
    typer.echo(str(result.run_dir))
```

- [ ] **Step 4: Run the run-command integration tests again**

Run: `uv run pytest tests/integration/test_run_command.py -v`
Expected: PASS with both tests green

- [ ] **Step 5: Commit the orchestrator and run command**

```bash
git add src/dramaloop/harness src/dramaloop/main.py tests/integration/test_run_command.py
git commit -m "feat: add orchestrator and run command"
```

---

### Task 10: Implement inspect/eval reporting, dataset fixtures, and public docs

**Files:**
- Create: `src/dramaloop/eval/report.py`
- Modify: `src/dramaloop/main.py`
- Create: `evals/datasets/mvp_cases.yaml`
- Create: `.env.example`
- Create: `README.md`
- Create: `examples/inputs/revenge_story.yaml`
- Create: `examples/outputs/README.md`
- Create: `artifacts/README.md`
- Create: `tests/fixtures/sample_run/request.json`
- Create: `tests/fixtures/sample_run/run_manifest.json`
- Create: `tests/fixtures/sample_run/critique_v1.json`
- Create: `tests/fixtures/sample_run/critique_v2.json`
- Create: `tests/fixtures/sample_run/run_summary.md`
- Test: `tests/unit/test_reports.py`
- Test: `tests/integration/test_inspect_eval_commands.py`

**Interfaces:**
- Consumes:
  - `RunManifest`, `CritiqueArtifact`, `StoryRequest`
  - `run_story_pipeline`
  - `build_llm_client(settings)`
- Produces:
  - `build_single_run_report(run_dir: Path) -> dict`
  - `run_dataset_eval(dataset_path: Path, settings: Settings) -> dict`
  - CLI `inspect(run_dir: Path) -> None`
  - CLI `eval_command(run: Path | None, dataset: Path | None) -> None`

- [ ] **Step 1: Write failing tests for single-run reports and CLI inspect/eval behavior**

```python
from pathlib import Path

from typer.testing import CliRunner

from dramaloop.eval.report import build_single_run_report
from dramaloop.main import app


runner = CliRunner()


def test_build_single_run_report_reads_scores(sample_run_dir: Path) -> None:
    report = build_single_run_report(sample_run_dir)

    assert report["run_id"] == "20260708-153000-demo"
    assert report["overall_scores"] == [6.0, 7.4]
    assert report["weakest_dimensions"] == ["ending_payoff", "pacing"]


def test_inspect_command_prints_summary_table(sample_run_dir: Path) -> None:
    result = runner.invoke(app, ["inspect", str(sample_run_dir)])

    assert result.exit_code == 0
    assert "20260708-153000-demo" in result.stdout
    assert "overall_scores" in result.stdout


def test_eval_command_supports_dataset_runs(tmp_path: Path, monkeypatch) -> None:
    dataset_path = tmp_path / "cases.yaml"
    dataset_path.write_text(
        """
- idea: 她在婚礼被抛弃后改嫁死对头
  style: [都市情感, 逆袭]
  length: short
- idea: 她被继妹算计后直播翻盘
  style: [狗血短剧感, 爽文]
  length: short
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))
    monkeypatch.setenv("DRAMALOOP_EVALS_DIR", str(tmp_path / "evals"))

    result = runner.invoke(app, ["eval", "--dataset", str(dataset_path)])

    assert result.exit_code == 0
    reports = list((tmp_path / "evals" / "reports").glob("*.json"))
    assert len(reports) == 1
```

- [ ] **Step 2: Run the report and inspect/eval tests to confirm these features are not implemented yet**

Run: `uv run pytest tests/unit/test_reports.py tests/integration/test_inspect_eval_commands.py -v`
Expected: FAIL with missing report helpers, missing fixture files, and empty `inspect` / `eval` behavior

- [ ] **Step 3: Implement reporting, CLI inspect/eval, datasets, fixtures, and docs**

`src/dramaloop/eval/report.py`
```python
from datetime import datetime
from pathlib import Path

import yaml

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.run import RunManifest
from dramaloop.storage.artifacts import write_json_artifact, write_markdown_artifact


def build_single_run_report(run_dir: Path) -> dict:
    manifest = RunManifest.model_validate_json((run_dir / "run_manifest.json").read_text(encoding="utf-8"))
    critiques = [
        CritiqueArtifact.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted(run_dir.glob("critique_v*.json"))
    ]
    return {
        "run_id": manifest.run_id,
        "status": manifest.status,
        "overall_scores": [item.overall_score for item in critiques],
        "weakest_dimensions": [item.weakest_dimensions[0] for item in critiques],
    }


def run_dataset_eval(dataset_path: Path, settings: Settings) -> dict:
    cases = yaml.safe_load(dataset_path.read_text(encoding="utf-8"))
    reports = []
    for case in cases:
        request = StoryRequest.model_validate(case)
        result = run_story_pipeline(request, settings, build_llm_client(settings))
        reports.append(build_single_run_report(result.run_dir))
    aggregate = {
        "case_count": len(reports),
        "average_final_score": round(sum(item["overall_scores"][-1] for item in reports) / len(reports), 2),
        "reports": reports,
    }
    reports_dir = settings.evals_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    write_json_artifact(reports_dir / f"{stamp}-mvp-eval-report.json", aggregate)
    write_markdown_artifact(
        reports_dir / f"{stamp}-mvp-eval-report.md",
        "\n".join(["# MVP Eval Report", f"- case_count: {aggregate['case_count']}", f"- average_final_score: {aggregate['average_final_score']}"]),
    )
    return aggregate
```

Append to `src/dramaloop/main.py`
```python
from dramaloop.eval.report import build_single_run_report, run_dataset_eval


@app.command()
def inspect(run_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True)) -> None:
    typer.echo(build_single_run_report(run_dir))


@app.command(name="eval")
def eval_command(
    run: Path | None = typer.Option(default=None, exists=True, file_okay=False, dir_okay=True),
    dataset: Path | None = typer.Option(default=None, exists=True, file_okay=True, dir_okay=False),
) -> None:
    settings = Settings()
    if run is not None:
        typer.echo(build_single_run_report(run))
        raise typer.Exit(code=0)
    if dataset is None:
        raise typer.BadParameter("Provide --run or --dataset")
    typer.echo(run_dataset_eval(dataset, settings))
```

`.env.example`
```bash
DRAMALOOP_PROVIDER=mock
DRAMALOOP_MODEL_NAME=claude-sonnet-5
DRAMALOOP_RUNS_DIR=runs
DRAMALOOP_EVALS_DIR=evals
ANTHROPIC_API_KEY=
```

`evals/datasets/mvp_cases.yaml`
```yaml
- idea: 她在婚礼被抛弃后改嫁死对头
  style: [都市情感, 逆袭]
  length: short
  audience: 女性向短剧用户
  constraints: [节奏快, 结尾有回报]
- idea: 她被继妹算计后直播翻盘
  style: [狗血短剧感, 爽文]
  length: short
  audience: 女性向爽文用户
  constraints: [反转强, 结尾打脸]
- idea: 她被豪门扫地出门后凭一份录音翻盘
  style: [都市情感, 悬疑]
  length: short
  constraints: [开头抓人]
- idea: 她被全网网暴后揭开真相
  style: [逆袭, 爽文]
  length: short
  constraints: [中段升级]
- idea: 她替妹妹相亲却钓到真大佬
  style: [都市情感, 狗血短剧感]
  length: short
  constraints: [反转, 回报]
```

`examples/inputs/revenge_story.yaml`
```yaml
idea: 被未婚夫当众退婚后，她转身嫁给了他的死对头
style: [都市情感, 逆袭, 狗血短剧感]
length: short
audience: 女性向短剧用户
constraints: [节奏快, 结尾有回报]
max_iterations: 2
```

`examples/outputs/README.md`
```md
# Example Outputs

Store copied example outputs here when you want stable demo material without depending on timestamped `runs/` paths.
```

`artifacts/README.md`
```md
# Artifacts

Curated artifact samples live here after successful runs are copied out of `runs/` for documentation, demos, or regression comparisons.
```

`README.md`
```md
# Dramaloop

Dramaloop is a CLI-first short-drama short-text generation system prototype built around a staged agent harness and a critique-rewrite loop.

## Why it exists

This project demonstrates:
- spec-driven development
- agent orchestration
- iterative loop optimization
- structured outputs
- eval and data accumulation readiness
- durable repo memory through `project/spec`, `project/tasks`, and `project/workspace`

## Repo layout

- application layer: `src/dramaloop/`, `tests/`, `runs/`, `evals/`, `examples/`
- operating layer: `project/spec/`, `project/tasks/`, `project/workspace/`

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env
uv run dramaloop run --input examples/inputs/revenge_story.yaml
```

## Core commands

```bash
uv run dramaloop run --input examples/inputs/revenge_story.yaml
uv run dramaloop inspect runs/<run_id>
uv run dramaloop eval --dataset evals/datasets/mvp_cases.yaml
```

## Harness flow

`input -> premise -> characters -> outline -> draft -> critique -> rewrite -> final`

## Run outputs

Each run writes:
- `request.json`
- `run_manifest.json`
- `events.jsonl`
- `premise.json`
- `characters.json`
- `outline.json`
- `draft_v1.md`
- `critique_v1.json`
- `rewrite_plan_v1.json`
- `draft_v2.md`
- `critique_v2.json`
- `final_story.md`
- `run_summary.md`
```

Fixture files under `tests/fixtures/sample_run/`
```json
// request.json
{
  "idea": "demo",
  "style": ["都市情感"],
  "length": "short",
  "audience": null,
  "constraints": [],
  "max_iterations": 2
}
```

```json
// run_manifest.json
{
  "run_id": "20260708-153000-demo",
  "status": "completed",
  "started_at": "2026-07-08T15:30:00",
  "finished_at": "2026-07-08T15:31:00",
  "model_provider": "mock",
  "model_name": "mock-model",
  "max_iterations": 2,
  "completed_iterations": 2,
  "target_threshold": 7.5,
  "minimum_dimension_threshold": 6,
  "min_delta": 0.3,
  "final_artifact": "final_story.md",
  "error_message": null
}
```

```json
// critique_v1.json
{
  "dimension_scores": {
    "hook_strength": {"score": 6, "reason": "ok", "evidence": "a", "improvement_advice": "x"},
    "character_consistency": {"score": 7, "reason": "ok", "evidence": "b", "improvement_advice": "x"},
    "conflict_intensity": {"score": 6, "reason": "ok", "evidence": "c", "improvement_advice": "x"},
    "pacing": {"score": 5, "reason": "ok", "evidence": "d", "improvement_advice": "x"},
    "short_drama_feel": {"score": 6, "reason": "ok", "evidence": "e", "improvement_advice": "x"},
    "ending_payoff": {"score": 5, "reason": "ok", "evidence": "f", "improvement_advice": "x"},
    "language_fluency": {"score": 7, "reason": "ok", "evidence": "g", "improvement_advice": "x"}
  },
  "overall_score": 6.0,
  "weakest_dimensions": ["ending_payoff", "pacing"],
  "rewrite_target": "ending_payoff",
  "rewrite_plan": {"scope": "ending", "must_fix": ["pay off"], "keep": ["hook"]}
}
```

```json
// critique_v2.json
{
  "dimension_scores": {
    "hook_strength": {"score": 8, "reason": "ok", "evidence": "a", "improvement_advice": "x"},
    "character_consistency": {"score": 7, "reason": "ok", "evidence": "b", "improvement_advice": "x"},
    "conflict_intensity": {"score": 8, "reason": "ok", "evidence": "c", "improvement_advice": "x"},
    "pacing": {"score": 7, "reason": "ok", "evidence": "d", "improvement_advice": "x"},
    "short_drama_feel": {"score": 8, "reason": "ok", "evidence": "e", "improvement_advice": "x"},
    "ending_payoff": {"score": 7, "reason": "ok", "evidence": "f", "improvement_advice": "x"},
    "language_fluency": {"score": 7, "reason": "ok", "evidence": "g", "improvement_advice": "x"}
  },
  "overall_score": 7.4,
  "weakest_dimensions": ["pacing"],
  "rewrite_target": "opening_hook",
  "rewrite_plan": {"scope": "opening", "must_fix": ["sharpen hook"], "keep": ["ending"]}
}
```

```md
<!-- run_summary.md -->
# Run Summary

Fixture summary.
```

- [ ] **Step 4: Run the report and inspect/eval tests again, then run the full suite**

Run: `uv run pytest tests/unit/test_reports.py tests/integration/test_inspect_eval_commands.py -v`
Expected: PASS with dataset report files created under the configured eval directory

Run: `uv run pytest -v`
Expected: PASS with all unit and integration tests green

- [ ] **Step 5: Commit reporting and public docs**

```bash
git add src/dramaloop/eval src/dramaloop/main.py .env.example README.md examples/inputs/revenge_story.yaml examples/outputs/README.md artifacts/README.md evals/datasets tests/unit/test_reports.py tests/integration/test_inspect_eval_commands.py tests/fixtures/sample_run
git commit -m "feat: add inspect eval and public docs"
```

---

## Self-Review

### Spec coverage

- Objective, design principles, and tech stack: Tasks 2-3 and Task 10 README/docs
- Dual-layer repository structure: Task 1 plus Task 10 README
- Input contract and schema rules: Task 3
- Stage sequence and stage contracts: Tasks 6-7
- Evaluation dimensions and rewrite targets: Tasks 3, 7, and 10
- Loop rules and thresholds: Tasks 3 and 7
- Run directory spec and required files: Tasks 4 and 9
- CLI spec (`run`, `inspect`, `eval`): Tasks 2, 9, and 10
- Model abstraction with mock + real adapter: Tasks 5 and 8
- Error handling requirements: Task 9 and Task 8 API-key validation
- Testing requirements: every task includes explicit unit/integration tests; full suite in Task 10
- Eval dataset spec: Task 10
- README requirements: Task 10
- Project operating layer requirements: Task 1 and Task 10

### Placeholder scan

- No `TBD`, `TODO`, or “implement later” placeholders remain
- Every code-changing step includes explicit code or file content blocks
- Every verification step includes exact commands and expected outcomes

### Type consistency

- `Settings`, `StoryRequest`, `CritiqueArtifact`, `RewriteArtifact`, `RunManifest`, `RunResult`, `LLMClient`, `build_llm_client(settings)`, and all stage function names are consistent across tasks
- The plan no longer depends on circular imports between `main.py` and the provider factory
- The `run` failure-path test now uses an exploding client monkeypatch instead of an invalid provider literal
