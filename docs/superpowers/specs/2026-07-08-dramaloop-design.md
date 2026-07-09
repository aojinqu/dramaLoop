# Dramaloop Design

Date: 2026-07-08
Status: Draft for user review

## 1. Overview

Dramaloop is a CLI-first production-system prototype for generating **short-drama-style short fiction** through a staged **agent harness** and an iterative **critique-rewrite loop**.

The project is intentionally not a one-shot prompt demo. Its MVP value comes from:

- explicit stage orchestration
- structured intermediate artifacts
- iterative quality improvement loops
- eval-friendly outputs
- data accumulation primitives for future expansion
- durable repo-level specs, tasks, and workspace notes inspired by Trellis-style repo memory

## 2. Product Goal

Given a user-provided story idea, style tags, optional audience, and optional constraints, the system should produce a short-drama-style short text that emphasizes:

- strong opening hook
- clear character motivations
- escalating conflict
- reversal or reveal
- emotionally satisfying ending payoff
- concise, readable prose

## 3. MVP Scope

### In scope

- CLI entrypoints for running and inspecting generation runs
- single orchestrator controlling a fixed multi-stage harness
- 2-3 iteration critique-rewrite loop, with 2 as the default
- structured artifacts written to disk at every stage
- per-dimension critique scoring and targeted rewrite planning
- local eval datasets and summary reports
- one real model provider adapter plus one mock adapter
- tests covering schema validation, loop logic, artifact creation, and mocked end-to-end flow

### Out of scope

- video generation APIs
- shot-by-shot screenplay or storyboard generation
- web UI or dashboard
- multi-user or hosted service deployment
- candidate beam search / large candidate pools
- preference learning pipeline implementation
- fine-tuning jobs or training pipelines

## 4. Why this project is resume-worthy

The project demonstrates:

- spec-driven development
- agent orchestration with explicit stage contracts
- iterative generation and evaluation loops
- structured outputs for downstream reuse
- reproducible run traces and artifacts
- eval-minded engineering instead of prompt-only experimentation

## 5. Approaches considered

### A. Single orchestrator with typed stage pipeline (recommended)

A central orchestrator executes each stage in order. Each stage has a fixed input/output contract enforced by Pydantic schemas. The loop controller uses critique results to select a narrow rewrite target and re-run only the necessary generation step.

**Pros**
- easiest to make reliable in an MVP
- cleanest architecture for testing and documentation
- strongest fit for structured artifacts and eval traces
- easiest to explain in a resume or interview

**Cons**
- less autonomous than a decentralized multi-agent system
- less flexible for open-ended planning behavior

### B. Multi-role collaborative agents

Planner, writer, critic, and editor agents coordinate more independently over shared context.

**Pros**
- stronger “agent system” flavor
- more flexible future evolution

**Cons**
- more prompt fragility
- more state-management overhead
- harder to stabilize and test as an MVP

### C. Candidate generation + judge-heavy selection system

Generate multiple candidates, run judges, then pick or merge the strongest.

**Pros**
- strong eval story
- natural path toward preference data

**Cons**
- weaker stage-by-stage production narrative
- more expensive and less focused for v1

## 6. Recommended design

Adopt **Approach A** as the base architecture, while expressing each stage through a role-specific prompt persona:

- Refiner
- Character Designer
- Outliner
- Drafter
- Critic
- Rewriter
- Assembler

Keep the business application in a focused Python package, but add a second, lighter-weight repo operating layer inspired by Trellis. This preserves clear orchestration while making both the runtime harness and the project’s persistent design/task memory visible.

## 7. System architecture

Dramaloop uses a **dual-layer architecture**.

### 7.1 Application layer

The application layer is the Python runtime responsible for generation, evaluation, and artifact persistence.

### Core application components

1. **CLI layer**
   - accepts user input and runtime options
   - launches runs and prints progress
   - inspects prior runs and eval reports

2. **Run manager**
   - creates a run directory
   - assigns run IDs
   - tracks manifest and event log

3. **Orchestrator**
   - executes stage sequence
   - stores artifacts after every stage
   - invokes loop controller after draft generation

4. **Loop controller**
   - compares critique scores to thresholds
   - identifies weakest dimensions
   - narrows rewrite target
   - decides whether to continue or stop early

5. **Stage executors**
   - build prompts from structured inputs
   - call the LLM client
   - validate structured outputs
   - emit typed artifacts

6. **LLM client abstraction**
   - real provider adapter for live generation
   - mock adapter for deterministic tests

7. **Artifact store**
   - writes JSON, YAML, Markdown, and JSONL outputs
   - standardizes naming and manifest tracking

8. **Eval subsystem**
   - defines scoring dimensions
   - generates critique artifacts
   - summarizes single-run and batch eval reports

### 7.2 Project operating layer

The operating layer is a lighter-weight, Trellis-inspired repo memory structure for durable project knowledge.

1. **`project/spec/`**
   - stores long-lived project guidance split by concern
   - keeps product goals, architecture, evaluation rules, and conventions separate

2. **`project/tasks/`**
   - stores task-scoped context for major implementation slices
   - keeps task goals, implementation notes, and status together

3. **`project/workspace/`**
   - stores evolving design decisions, learnings, and backlog notes
   - separates durable repo knowledge from transient conversation context

The operating layer does not replace the Python application architecture. It supports it by making the project easier to extend, explain, and iterate on over time.

## 8. Harness stages

The fixed MVP stage sequence is:

1. premise_refinement
2. character_card_generation
3. story_outline_generation
4. draft_generation
5. critique_scoring
6. targeted_rewrite
7. final_assembly

The first four stages build the initial story package. The next two stages form the loop. The final stage assembles the accepted output and summarizes the run.

## 9. Loop behavior

Default run flow:

1. generate `draft_v1`
2. critique and score it
3. identify the weakest dimension(s)
4. produce a targeted rewrite plan
5. rewrite only the weak portion or adjacent supporting text
6. critique again
7. stop early if thresholds are met or gains are too small

Default rewrite targets:

- opening_hook
- character_motivation
- mid_conflict_escalation
- reversal_reveal
- ending_payoff
- prose_fluency

This keeps the loop visible and disciplined instead of degenerating into repeated full rewrites.

## 10. Artifact strategy

Each run writes a full trace under `runs/<run_id>/`.

Minimum expected files:

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

These files are part of the product design, not incidental implementation detail.

## 11. Evaluation dimensions

The MVP uses seven fixed scoring dimensions:

- hook_strength
- character_consistency
- conflict_intensity
- pacing
- short_drama_feel
- ending_payoff
- language_fluency

Each dimension must capture:

- score
- reason
- evidence
- improvement advice

The critique output also includes:

- overall_score
- weakest_dimensions
- rewrite_target
- rewrite_plan

## 12. Technical stack

Recommended stack:

- Python 3.11+
- Typer for CLI
- Pydantic v2 for schemas
- pytest for testing
- Ruff for lint/format
- optional mypy for stricter interfaces
- JSON as primary structured artifact format
- Markdown for story outputs and summaries
- YAML for input cases and datasets
- `runs/`, `artifacts/`, and `evals/` kept in-repo for visibility
- `project/spec`, `project/tasks`, and `project/workspace` as a repo-level operating layer

### Why Python over TypeScript

Python is the stronger choice because this MVP is centered on agent orchestration, schema validation, iterative evaluation, local artifacts, and offline experimentation rather than frontend-heavy product work. It shortens the path to a stable CLI prototype and aligns better with future data and model experimentation.

## 13. Success criteria for MVP

The MVP is successful when:

1. a full run can execute from input to final story
2. every required artifact is written deterministically
3. the critique-rewrite loop runs at least once
4. most benchmark cases show score improvement from v1 to v2
5. the system is easy to explain as a production-style prototype

## 14. Future expansion reserved in design

These are intentionally deferred but should remain compatible with the architecture:

- scene-level story structure
- prompt package generation
- user preference data accumulation
- training-data export
- video-model integration
- richer eval dashboards
- richer task-context and spec-update workflows in the project operating layer

## 15. Implementation stance

Implementation should be spec-driven. The next step after user approval is to write a concrete implementation plan before scaffolding code.
