# Dramaloop

Dramaloop 是一个以 staged agent harness 和 critique-rewrite loop 为核心的短剧生成系统原型，支持单篇短剧感短文和分集连续短剧。

## 为什么做这个项目

这个项目重点展示：
- spec-driven development
- agent orchestration
- iterative loop optimization
- structured outputs
- eval 与 data accumulation readiness
- 通过 `project/spec`、`project/tasks`、`project/workspace` 实现 durable repo memory

## 仓库布局

- 应用层：`src/dramaloop/`、`tests/`、`runs/`、`evals/`、`examples/`
- 操作层：`project/spec/`、`project/tasks/`、`project/workspace/`
- 工程架构、可靠性与评测设计：`docs/engineering-overview.md`
- 真实工程方法实验与失败复盘：`docs/engineering-methods-evaluation.md`
- 小说 SFT、偏好训练与原创性提升调研：`docs/originality-improvement-research.md`

## 快速开始

```bash
uv sync --extra dev
cp .env.example .env
uv run dramaloop run --input examples/inputs/minimal_story.yaml
```

直接从一段 prompt 生成分集短剧：

```bash
uv run dramaloop run \
  --idea "一个普通人意外获得重来一次的机会，决定改写自己失败的人生" \
  --style 都市情感 \
  --format episodic_series \
  --episode-count 12
```

## Web Demo

### 本地开发

后端：
```bash
uv run dramaloop web --reload --host 127.0.0.1 --port 8000
```

前端：
```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

### 构建并由 FastAPI 托管前端

```bash
npm --prefix frontend run build
uv run dramaloop web --host 127.0.0.1 --port 8000
```

### 体验路径

1. 在左侧填写 prompt / 题材 / 集数 / 每集字数等参数
2. 点击 `开始生成`
3. 观察右上角阶段进度（整季规划 → 分集规划 → 逐集生成 → 最终合并）与事件流
4. 分集规划完成后默认暂停：可在「分集规划」里手动修改，再点「继续生成」
5. 生成中可随时「暂停 / 停止」（在当前集或阶段边界生效）
6. 停止或完成后，可在「分集正文」对某一集点「重生成本集」，再「继续生成」后续集
7. 在结果区切换查看整季规划、分集规划、分集正文与合并成稿

## API 配置文档

如果你准备接真实模型，先看：

- `docs/setup/deepseek-api-setup.md`

当前推荐方式：
- 使用 `anthropic-compatible` backend
- Claude 直接填 Anthropic 官方配置
- DeepSeek 使用 `DRAMALOOP_BASE_URL=https://api.deepseek.com/anthropic`

## 核心命令

```bash
uv run dramaloop run --input examples/inputs/minimal_story.yaml
uv run dramaloop run --idea "汛期泵站值班员失联，新调度员从叶轮异响中发现旧排水规则的漏洞" --style 职业悬疑 --format episodic_series --episode-count 2
uv run dramaloop inspect runs/<run_id>
uv run dramaloop eval --dataset evals/datasets/mvp_cases.yaml
DRAMALOOP_PROVIDER=mock uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml
DRAMALOOP_PROVIDER=mock uv run dramaloop eval --dataset evals/datasets/research_harness_cases.yaml
```

分集模式默认开启质量环（critique → 最多 1 次 rewrite）；可用 `enable_episode_critique=false` 关闭。评测指标见 `project/spec/evaluation.md`。

## Harness 流程

`input -> premise -> characters -> outline -> draft -> critique -> rewrite -> final`

分集模式会切换为：

`input -> season -> episode_plan -> episodes(+critique/rewrite) -> final`

模型调用外层由可配置的 research harness 包装：

`stage contract -> memory/skill -> context budget -> model -> realization -> trajectory regulation`

默认启用 `full_harness`。可通过 `DRAMALOOP_HARNESS_MODE` 选择
`baseline`、`contract_enabled`、`memory_skill_enabled`、
`memory_context_budgeted`、`realization_enabled`、
`trajectory_regulation_enabled` 或 `full_harness`。

stage context budget 默认使用模型上下文窗口的 40%，可通过
`DRAMALOOP_MODEL_CONTEXT_WINDOW_TOKENS` 和
`DRAMALOOP_STAGE_CONTEXT_BUDGET_RATIO` 调整。

## Run 输出

单篇模式会写出：
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

每次 run 还会写出：
- `run_memory.json`
- `stage_trace.jsonl`
- `memory_trace.jsonl`
- `context_trace.jsonl`
- `decision_trace.jsonl`
- `skill_trace.jsonl`
- `realization_trace.jsonl`
- `trajectory_trace.jsonl`
- `usage_trace.jsonl`

分集模式还会写出：
- `season_bible.json`
- `episode_plan.json`
- `continuity_state.json`
- `episodes/episode_01.md`
- `episodes/episode_01.json`
- `episodes/episode_01_critique.json`
- `...`
- `episodes/episode_12.md`
- `episodes/episode_12.json`
- `final_story.md`
- `run_summary.md`
- `human_actions.jsonl`（Web 上暂停 / 改 plan / 重生 / 取消等人工操作）

真实 research eval 默认使用 DeepSeek judge。通过
`DRAMALOOP_JUDGE_API_KEY`（或 `DEEPSEEK_API_KEY`）、
`DRAMALOOP_JUDGE_MODEL_NAME` 和 `DRAMALOOP_JUDGE_BASE_URL` 配置。
mock provider 不访问真实 judge。
