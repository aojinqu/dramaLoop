# Implementation notes — quality + eval (2026-07-14)

## Decisions
- Continuity gate first, then episode critique; rewrite at most once.
- If rewrite breaks continuity, roll back to pre-rewrite markdown and log `episode_rewrite/failed`.
- Critique dimensions: hook_strength, conflict_intensity, pacing, short_drama_feel, carryover.
- Rewrite threshold: overall_score < 7.0 or any dimension < 6.0.
- Eval episodic cases use episode_count=2 for cost; mock provider required for CI-local runs.

## Artifacts
- `episodes/episode_XX_critique.json`
- Web hydrate exposes `episodes[].overall_score` and run-level average `overall_score`
- `human_actions.jsonl` for plan_edit / regenerate / pause / resume / cancel

## Known limits
- Model self-score is relative signal only; calibrate with human spot checks.
