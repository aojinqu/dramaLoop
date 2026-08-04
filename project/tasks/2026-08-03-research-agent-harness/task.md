# Research Agent Harness Upgrade

Date: 2026-08-03
Spec: `project/spec/research-agent-harness-upgrade.md`

## Scope

- 显式 Stage Contract registry
- run/story/episode memory 与 evidence refs
- context budget 与 procedural skill 注入
- output realization 与 trajectory regulation
- DeepSeek judge、pairwise、trace、ablation 和 failure mining
- 单篇与分集 pipeline trace artifacts

## Acceptance

- 单篇和分集 mock run 保持原 artifact 输出
- 每次 run 写出 harness memory 与 trace
- 失败 run 写出 partial memory
- research harness dataset 生成 JSON/Markdown 报告
- ruff、mypy 和完整 pytest 通过
