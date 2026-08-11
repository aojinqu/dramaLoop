# 仓库约定

## Artifacts
- 结构化产物使用 JSON
- 草稿和总结使用 Markdown
- eval 数据集使用 YAML

## Task 文件夹
每个主要实现切片都包含：
- `task.md`
- `implementation-notes.md`
- `status.md`

## Run 布局
所有 run 都必须保存 `request.json`、`run_manifest.json`、`events.jsonl`、
`final_story.md` 和 `run_summary.md`。

- 单篇模式保存 `premise.json`、`characters.json`、`outline.json`、
  `draft_v*.md`、`critique_v*.json` 和可选的 `rewrite_plan_v*.json`。
- 分集模式保存 `season_bible.json`、`episode_plan.json`、
  `continuity_state.json`、`episodes/episode_*.{json,md}` 和可选的
  `episodes/episode_*_critique.json`。
- 启用 harness 时保存 `run_memory.json` 以及 stage、memory、context、
  decision、skill、realization、trajectory trace。
