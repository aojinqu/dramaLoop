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

1. 在左侧输入 `idea`
2. 点击 `Launch Run`
3. 观察右上角的 stage timeline 与 event stream
4. run 完成后，在右下查看 final story、overall score、rewrite focus 与 artifacts

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
uv run dramaloop run --idea "她被退婚后反手嫁给宿敌" --style 都市情感 --format episodic_series --episode-count 12
uv run dramaloop inspect runs/<run_id>
uv run dramaloop eval --dataset evals/datasets/mvp_cases.yaml
```

## Harness 流程

`input -> premise -> characters -> outline -> draft -> critique -> rewrite -> final`

分集模式会切换为：

`input -> season -> episode_plan -> episodes -> final`

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

分集模式还会写出：
- `season_bible.json`
- `episode_plan.json`
- `continuity_state.json`
- `episodes/episode_01.md`
- `episodes/episode_01.json`
- `...`
- `episodes/episode_12.md`
- `episodes/episode_12.json`
- `final_story.md`
- `run_summary.md`
