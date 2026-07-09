# Dramaloop MVP Spec

Date: 2026-07-08
Status: Draft for user review

## 1. Objective

Build a CLI-first system that turns a raw story idea into a short-drama-style short text through a staged agent harness and an iterative critique-rewrite loop. The system must save structured intermediate artifacts so runs are reproducible, inspectable, and reusable for future data accumulation.

## 2. Design principles

1. **Spec-driven**: stage contracts and artifact formats are defined before code.
2. **Schema-first**: structured artifacts are first-class outputs.
3. **Loop-first**: quality improvement comes from iteration, not one-shot prompting.
4. **Artifacts-first**: every meaningful step writes to disk.
5. **CLI-first**: prioritize backend and eval over frontend.
6. **Extensible by default**: reserve clean seams for future datasets, prompts, and model integrations.

## 3. Technology choices

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

## 4. Repository structure

Dramaloop uses a dual-layer repository structure: an application layer for the runnable Python system and an operating layer for durable project knowledge.

```text
brainWrite/
├─ README.md
├─ pyproject.toml
├─ .env.example
├─ src/dramaloop/
│  ├─ __init__.py
│  ├─ main.py
│  ├─ config.py
│  ├─ schemas/
│  │  ├─ input.py
│  │  ├─ premise.py
│  │  ├─ character.py
│  │  ├─ outline.py
│  │  ├─ critique.py
│  │  ├─ rewrite.py
│  │  └─ run.py
│  ├─ llm/
│  │  ├─ base.py
│  │  ├─ mock.py
│  │  └─ provider.py
│  ├─ prompts/
│  │  ├─ premise.py
│  │  ├─ characters.py
│  │  ├─ outline.py
│  │  ├─ draft.py
│  │  ├─ critique.py
│  │  └─ rewrite.py
│  ├─ harness/
│  │  ├─ context.py
│  │  ├─ stages.py
│  │  ├─ loop.py
│  │  └─ orchestrator.py
│  ├─ eval/
│  │  ├─ dimensions.py
│  │  ├─ scorer.py
│  │  └─ report.py
│  ├─ storage/
│  │  ├─ artifacts.py
│  │  └─ runs.py
│  └─ utils/
│     ├─ markdown.py
│     ├─ json_io.py
│     └─ logging.py
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ fixtures/
├─ docs/
│  └─ superpowers/
│     ├─ specs/
│     └─ plans/
├─ runs/
├─ artifacts/
├─ evals/
│  ├─ datasets/
│  └─ reports/
├─ examples/
│  ├─ inputs/
│  └─ outputs/
└─ project/
   ├─ spec/
   │  ├─ product.md
   │  ├─ architecture.md
   │  ├─ evaluation.md
   │  └─ conventions.md
   ├─ tasks/
   │  └─ <task-slug>/
   │     ├─ task.md
   │     ├─ implementation-notes.md
   │     └─ status.md
   └─ workspace/
      ├─ decisions.md
      ├─ learnings.md
      └─ backlog.md
```

## 5. Input contract

### StoryRequest

```yaml
idea: string
style:
  - string
length: short
audience: string | null
constraints:
  - string
max_iterations: int = 2
```

### Rules

- `idea` is required.
- `style` accepts one or more tags.
- MVP supports only `length=short`.
- `audience` is optional.
- `constraints` is optional and defaults to an empty list.
- `max_iterations` defaults to 2 and must be between 1 and 3 inclusive.

## 6. Stage sequence

The orchestrator executes these stages in order:

1. `premise_refinement`
2. `character_card_generation`
3. `story_outline_generation`
4. `draft_generation`
5. `critique_scoring`
6. `targeted_rewrite`
7. `final_assembly`

Stages 5 and 6 repeat inside the loop when additional iterations are allowed.

## 7. Stage contracts

### 7.1 premise_refinement

**Input**
- `StoryRequest`

**Output: PremiseArtifact**

```yaml
title_candidate: string
logline: string
core_conflict: string
hook_promise: string
ending_payoff_plan: string
tone_notes:
  - string
hard_constraints:
  - string
```

**Artifact file**
- `premise.json`

### 7.2 character_card_generation

**Input**
- `PremiseArtifact`

**Output: CharacterArtifact**

```yaml
characters:
  - name: string
    role: protagonist | antagonist | supporting
    public_identity: string
    core_desire: string
    core_fear: string
    hidden_secret: string | null
    conflict_links:
      - string
    voice_style: string
    arc_target: string
```

**Artifact file**
- `characters.json`

### 7.3 story_outline_generation

**Input**
- `PremiseArtifact`
- `CharacterArtifact`

**Output: OutlineArtifact**

```yaml
beats:
  - beat_id: string
    label: string
    purpose: string
    summary: string
    tension_level: int
    payoff_dependency: string | null
ending_type: string
```

**Rules**
- Must include a hook opening.
- Must include an inciting conflict.
- Must include escalation.
- Must include reversal or reveal.
- Must include an ending payoff.

**Artifact file**
- `outline.json`

### 7.4 draft_generation

**Input**
- `PremiseArtifact`
- `CharacterArtifact`
- `OutlineArtifact`

**Output**
- story draft in Markdown

**Artifact file**
- `draft_v1.md`

### 7.5 critique_scoring

**Input**
- current draft Markdown
- `PremiseArtifact`
- `CharacterArtifact`
- `OutlineArtifact`

**Output: CritiqueArtifact**

```yaml
dimension_scores:
  hook_strength:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  character_consistency:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  conflict_intensity:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  pacing:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  short_drama_feel:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  ending_payoff:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
  language_fluency:
    score: int
    reason: string
    evidence: string
    improvement_advice: string
overall_score: float
weakest_dimensions:
  - string
rewrite_target: string
rewrite_plan:
  scope: string
  must_fix:
    - string
  keep:
    - string
```

**Artifact file pattern**
- `critique_v{n}.json`

### 7.6 targeted_rewrite

**Input**
- current draft Markdown
- current critique artifact
- premise / characters / outline artifacts

**Output**
- revised draft Markdown
- rewrite metadata

**RewriteArtifact**

```yaml
version: int
target_section: string
goals:
  - string
changes_made:
  - string
expected_score_improvement:
  - string
```

**Artifact files**
- `rewrite_plan_v{n}.json`
- `draft_v{n+1}.md`

### 7.7 final_assembly

**Input**
- last accepted draft
- critique history
- run metadata

**Output artifacts**
- `final_story.md`
- `run_summary.md`

## 8. Evaluation dimensions

The MVP uses exactly these dimensions:

1. `hook_strength`
2. `character_consistency`
3. `conflict_intensity`
4. `pacing`
5. `short_drama_feel`
6. `ending_payoff`
7. `language_fluency`

### Scoring rules

- each score is an integer from 1 to 10
- each dimension requires reason, evidence, and improvement advice
- `overall_score` is a computed aggregate of dimension scores
- `weakest_dimensions` lists the lowest-scoring dimensions, ordered from weakest upward
- `rewrite_target` must be one of the allowed rewrite target enums

### Allowed rewrite targets

- `opening_hook`
- `character_motivation`
- `mid_conflict_escalation`
- `reversal_reveal`
- `ending_payoff`
- `prose_fluency`

## 9. Loop rules

### Defaults

- default `max_iterations = 2`
- allowed range: 1 to 3

### Execution flow

```text
draft_v1
-> critique_v1
-> rewrite_plan_v1
-> draft_v2
-> critique_v2
-> optional rewrite_plan_v2
-> optional draft_v3
-> optional critique_v3
-> final_story
```

### Rewrite policy

- do not perform blind full rewrites by default
- rewrite should focus on the selected `rewrite_target`
- adjacent text may be updated only when necessary to preserve coherence
- rewrite artifacts must summarize what was changed

### Early stop conditions

Stop when any of the following is true:

1. `overall_score >= target_threshold`
2. all required dimensions are above the minimum threshold
3. score improvement from the previous draft is below `min_delta`
4. critique states that additional rewrites are low-yield
5. the configured max iteration count is reached

### Default thresholds for MVP

- `target_threshold = 7.5`
- `minimum_dimension_threshold = 6`
- `min_delta = 0.3`

These defaults may be configurable, but they should be written into the manifest for every run.

## 10. Run directory spec

Each run creates a directory:

```text
runs/<timestamp>-<idea-slug>/
```

### Required files

```text
runs/<run_id>/
├─ request.json
├─ run_manifest.json
├─ events.jsonl
├─ premise.json
├─ characters.json
├─ outline.json
├─ draft_v1.md
├─ critique_v1.json
├─ rewrite_plan_v1.json
├─ draft_v2.md
├─ critique_v2.json
├─ final_story.md
└─ run_summary.md
```

If iteration 3 is used, also write:

- `rewrite_plan_v2.json`
- `draft_v3.md`
- `critique_v3.json`

### File requirements

#### request.json
Stores the validated user request and runtime settings.

#### run_manifest.json
Stores run metadata, including:

```json
{
  "run_id": "20260708-153000-fiance-revenge",
  "status": "completed",
  "started_at": "...",
  "finished_at": "...",
  "model_provider": "...",
  "model_name": "...",
  "max_iterations": 2,
  "completed_iterations": 2,
  "target_threshold": 7.5,
  "minimum_dimension_threshold": 6,
  "min_delta": 0.3,
  "final_artifact": "final_story.md"
}
```

#### events.jsonl
Appends one JSON object per run event. Minimum events:

- run started
- stage started
- stage completed
- artifact written
- run completed or failed

#### run_summary.md
Must include:

- input summary
- final story summary
- artifact index
- iteration score comparison table
- weakest dimension progression
- rewrite notes
- final stop reason

## 11. CLI spec

### `dramaloop run`

Starts a new generation run.

#### Input modes

1. YAML input file

```bash
dramaloop run --input examples/inputs/revenge_story.yaml
```

2. Direct CLI args

```bash
dramaloop run \
  --idea "被未婚夫当众退婚后，她转身嫁给了他的死对头" \
  --style "都市情感" \
  --style "逆袭" \
  --style "狗血短剧感" \
  --audience "女性向短剧用户" \
  --constraint "节奏快" \
  --constraint "结尾有回报"
```

#### Output behavior

- prints stage progress to terminal
- prints run path on success
- exits non-zero on failure

### `dramaloop inspect`

Displays a run summary and key paths.

```bash
dramaloop inspect runs/<run_id>
```

### `dramaloop eval`

Supports:

1. single run aggregation

```bash
dramaloop eval --run runs/<run_id>
```

2. dataset batch eval

```bash
dramaloop eval --dataset evals/datasets/mvp_cases.yaml
```

Batch eval must write:

- `evals/reports/<timestamp>-mvp-eval-report.json`
- `evals/reports/<timestamp>-mvp-eval-report.md`

## 12. Model abstraction spec

### Interface requirement

The business logic must depend on an abstract LLM client interface rather than a concrete SDK.

### Required MVP adapters

1. **real provider adapter**
   - used for actual generation
   - configuration comes from environment variables

2. **mock adapter**
   - deterministic outputs for tests
   - zero network dependency

### MVP rule

Prompt templates and orchestration code must not directly import provider SDK details outside the adapter layer.

## 13. Error handling requirements

The system must fail clearly and write run state whenever possible.

### Required failure behavior

- validation errors should stop before stage execution
- stage failures should mark `run_manifest.json` as failed
- partial artifacts should be preserved if already written
- events log should record the failing stage and error summary
- CLI should print the run path even on failure if the run directory exists

## 14. Testing requirements

### Unit tests

Cover:
- schema validation
- path and artifact naming
- run ID generation
- loop decision logic
- critique threshold helpers

### Integration tests

Cover:
- mocked end-to-end run
- expected artifact creation
- score trend capture in summary
- inspect and eval command behavior on fixture runs

### Fixture strategy

Store:
- example input YAMLs
- mock model outputs
- golden run directories where appropriate

## 15. Eval dataset spec

MVP should include a small dataset at:

```text
evals/datasets/mvp_cases.yaml
```

Recommended size:
- 5 to 10 cases

Each case should include:
- `idea`
- `style`
- `audience` (optional)
- `constraints` (optional)
- `notes` (optional evaluator expectations)

## 16. README requirements

README must show:

1. project motivation and system goal
2. the harness flow diagram
3. a sample run directory
4. score improvement across iterations
5. how the repo is organized into an application layer and an operating layer
6. key engineering highlights:
   - spec-driven design
   - agent orchestration
   - iterative loop
   - structured outputs
   - eval and data accumulation readiness
   - durable repo memory through `project/spec`, `project/tasks`, and `project/workspace`

## 17. Project operating layer requirements

The Trellis-inspired operating layer is part of the MVP repository design.

### `project/spec/`

Must contain split, durable project guidance for:

- product goals and MVP boundary
- system architecture
- evaluation rules
- repository conventions

### `project/tasks/`

Must support one folder per major implementation slice. Each folder should contain:

- `task.md`
- `implementation-notes.md`
- `status.md`

### `project/workspace/`

Must contain durable working notes for:

- design decisions
- learnings from implementation or evals
- future backlog

### Rules

- the operating layer supplements the application layer; it does not replace `src/dramaloop/`
- files in `project/spec/` should capture durable repo knowledge rather than one-off conversation notes
- files in `project/tasks/` should track execution context for meaningful implementation slices
- files in `project/workspace/` should capture reusable insights that help future iterations

## 18. Reserved future extensions

Explicitly deferred from MVP:

- scene-level decomposition
- stronger short-drama episode structure
- prompt package generation
- preference-data collection
- post-training data export
- video-model integration
- richer dashboards or UI
- richer task orchestration on top of the operating layer

## 19. Immediate next step

After user approval of this spec, write an implementation plan before scaffolding code.
