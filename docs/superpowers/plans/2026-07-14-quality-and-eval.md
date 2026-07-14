# Dramaloop 质量闭环 + Agent 评测 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Handoff note:** 本计划给「零上下文」执行者使用。先读完「背景与现状」再动代码。不要重写 Web UI / 控制流（pause/resume/cancel 已存在）。优先可验证的最小切片。

**Goal:** 让分集短剧生成具备「可评分 → 可改写」的质量闭环，并补齐 episodic agent 评测数据集与报告，使系统能证明「跑得好」而不只是「能跑完」。

**Architecture:** 复用单篇模式已有的 critique schema / prompts / loop 思想，在 `episodic_orchestrator` 的逐集生成后插入轻量 `episode_critique → optional rewrite`；评测层扩展现有 `dramaloop eval`，新增 episodic dataset 与成功/质量双轨指标，报告写入 `evals/reports/`。

**Tech Stack:** Python 3.12+、Pydantic、FastAPI（仅在需要暴露分数字段时最小改动）、现有 `uv` / `pytest` / `vitest` 工具链。前端改动可选且靠后。

## Global Constraints

- 不要破坏现有 CLI：`dramaloop run` / `inspect` / `eval` / `web`
- 不要重做 pause/resume/cancel/plan-edit/regenerate（已在 `harness/control.py` + `web/runtime.py`）
- 分集 critique 默认最多 **1 次 rewrite**（控制成本）；可用 request/settings 开关关闭
- 评测必须可在 `mock` LLM 下跑通单测；真实模型评测作为可选命令参数
- 代码风格：最小改动、复用现有 schema/prompt 模式，禁止无意义重构
- 提交信息简洁；仅在用户要求时 commit

---

## 背景与现状（执行前必读）

### 仓库关键路径

| 区域 | 路径 |
|------|------|
| 分集编排 | `src/dramaloop/harness/episodic_orchestrator.py` |
| 单篇编排 + critique loop | `src/dramaloop/harness/orchestrator.py`, `harness/loop.py` |
| 阶段 LLM 调用 | `src/dramaloop/harness/stages.py` |
| Critique schema | `src/dramaloop/schemas/critique.py` |
| Critique prompt | `src/dramaloop/prompts/critique.py` |
| 评估维度 | `src/dramaloop/eval/dimensions.py`, `project/spec/evaluation.md` |
| Dataset eval | `src/dramaloop/eval/report.py`, `evals/datasets/mvp_cases.yaml` |
| Web hydrate | `src/dramaloop/web/runtime.py`, `web/schemas.py` |
| 前端结果区 | `frontend/src/components/ResultPanel.tsx` |

### 当前缺口

1. **分集模式几乎没有质量闭环**：逐集生成后只有 continuity 规则门禁（重开篇/重复/完结感），`qa_passed=True` 基本是占位；单篇的 critique-rewrite **没有**接到 episodic。
2. **评测只覆盖 single_story**：`run_dataset_eval` 调用 `run_story_pipeline`；`mvp_cases.yaml` 仅 5 条且无 `format: episodic_series`。
3. **前端看不到质量信号**：分集 run 的 `overall_score` / `rewrite_focus` 通常为空。

### 成功定义

- 分集生成每集可产出 `episodes/episode_XX_critique.json`（及可选 rewrite 后正文）
- 低于阈值的集会触发一次定向 rewrite，事件写入 `events.jsonl`
- `uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml` 能跑 episodic 并出报告
- 报告含：完成率、连续性失败率、平均分、最弱维（至少在 mock 下结构正确）

---

## 文件规划（将创建 / 修改）

### 新建

| 文件 | 职责 |
|------|------|
| `src/dramaloop/prompts/episode_critique.py` | 分集 critique / rewrite prompt |
| `src/dramaloop/schemas/episode_critique.py` | 分集 critique 结构化结果（可薄封装现有 Critique） |
| `src/dramaloop/harness/episode_quality.py` | `run_episode_quality_loop(markdown, ...) -> (final_md, critique)` |
| `evals/datasets/episodic_mvp_cases.yaml` | 分集评测 case（建议 4–6 条，episode_count 用 2 或 3 降本） |
| `tests/unit/test_episode_quality.py` | 质量环单测 |
| `tests/unit/test_episodic_eval.py` | episodic eval 报告结构单测 |

### 修改

| 文件 | 改动 |
|------|------|
| `src/dramaloop/harness/stages.py` | 增加 `run_episode_critique_stage` / `run_episode_rewrite_stage` |
| `src/dramaloop/harness/episodic_orchestrator.py` | 在 `_persist_episode` 前接入 quality loop；写 critique artifact；事件 |
| `src/dramaloop/harness/episode_runner.py` | 可选：critique 文件写入 helper |
| `src/dramaloop/schemas/input.py` | 可选字段 `enable_episode_critique: bool = True` |
| `src/dramaloop/schemas/season.py` | `EpisodeArtifact` 增加 `overall_score` / `rewrite_applied` 等可选字段 |
| `src/dramaloop/llm/mock.py` | mock 返回 episode critique / rewrite |
| `src/dramaloop/llm/provider.py` | 若有 role 归一化，加上新 role |
| `src/dramaloop/eval/report.py` | 支持 episodic pipeline + 新指标聚合 |
| `src/dramaloop/eval/dimensions.py` | 可选增加 `carryover` / `episode_hook`（或复用现有 7 维） |
| `src/dramaloop/main.py` | eval 帮助文案；必要时 `--format` |
| `src/dramaloop/web/runtime.py` + `schemas.py` | hydrate 时汇总 episode scores 到 detail（可选 Task） |
| `frontend/...` | 展示每集分数（可选 Task，靠后） |
| `project/spec/evaluation.md` | 补 episodic 指标说明 |
| `README.md` | 一行评测/质量说明 |

---

## Track A — 分集 Critique-Rewrite 质量闭环

### Task A1: Episode critique schema + prompt

**Files:**
- Create: `src/dramaloop/schemas/episode_critique.py`
- Create: `src/dramaloop/prompts/episode_critique.py`
- Create: `tests/unit/test_episode_quality.py`（先写 schema/prompt 断言）
- Modify: `project/spec/evaluation.md`

- [x] **Step 1: 定义 schema**

建议字段（保持简单，可组合现有 `CritiqueArtifact`）：

```python
class EpisodeCritiqueArtifact(BaseModel):
    episode_number: int
    overall_score: float
    dimension_scores: dict[str, float]  # 至少含 hook_strength, conflict_intensity, pacing, short_drama_feel, carryover
    weakest_dimensions: list[str]
    rewrite_needed: bool
    rewrite_target: str  # 一句中文：本集应改什么
    issues: list[str]
```

阈值建议（写入 evaluation.md）：
- `rewrite_needed` 当 `overall_score < 7.0` 或任维 `< 6.0`

- [x] **Step 2: 写 prompt builder**

`build_episode_critique_prompt(season, episode_plan_item, continuity, markdown) -> str`  
要求模型输出 **严格 JSON**，强调：短剧节奏、集末钩子、与上一集承接、禁止复述上一集。

`build_episode_rewrite_prompt(..., critique) -> str`  
要求：只改 `rewrite_target` 指出的问题，保留必须发生情节 `must_happen`。

- [x] **Step 3: 单测 prompt 含关键约束词**

```bash
uv run pytest tests/unit/test_episode_quality.py -q
```

- [ ] **Step 4: Commit（仅当用户要求）**

---

### Task A2: Stage wrappers + mock LLM

**Files:**
- Modify: `src/dramaloop/harness/stages.py`
- Modify: `src/dramaloop/llm/mock.py`
- Modify: `src/dramaloop/llm/provider.py`（如需要）
- Test: `tests/unit/test_episode_quality.py`

- [x] **Step 1: 在 stages.py 增加**

```python
def run_episode_critique_stage(client, season, episode, continuity, markdown) -> EpisodeCritiqueArtifact: ...
def run_episode_rewrite_stage(client, season, episode, continuity, markdown, critique) -> str: ...
```

模式对齐现有 `run_episode_draft_stage`（role 字符串 + `client.complete_json` / `complete_text`）。

- [x] **Step 2: mock 返回**

- critique：可配置低分以触发 rewrite
- rewrite：返回与输入不同的 markdown（便于断言「发生了改写」）

- [x] **Step 3: 单测 mock 路径可解析**

```bash
uv run pytest tests/unit/test_episode_quality.py -q
```

---

### Task A3: 接入 episodic_orchestrator 质量环

**Files:**
- Create: `src/dramaloop/harness/episode_quality.py`
- Modify: `src/dramaloop/harness/episodic_orchestrator.py`
- Modify: `src/dramaloop/harness/episode_runner.py`（写 `episode_XX_critique.json`）
- Modify: `src/dramaloop/schemas/input.py`（`enable_episode_critique: bool = True`）
- Modify: `tests/unit/test_episodic_orchestrator.py`

**接入点：** `_generate_episode_markdown` 成功且通过 continuity gate **之后**、`_persist_episode` **之前**。

伪代码：

```python
markdown, hook_signal = _generate_episode_markdown(...)
if request.enable_episode_critique:
    markdown, critique = run_episode_quality_loop(...)  # critique + optional 1 rewrite
    write critique artifact
    record events: episode_critique_completed / episode_rewrite_completed
# then persist episode with updated markdown
```

**连续性注意：**
- rewrite 后建议 **再跑一次** `_detect_continuity_failures`；若失败，保留 rewrite 前版本或再 retry（选更简单策略并在实现笔记写明）。推荐：**rewrite 后若 continuity 失败 → 回退到 rewrite 前正文并记 event**。

**Artifacts 约定：**
- `episodes/episode_01_critique.json`
- 正文仍为 `episodes/episode_01.md` / `.json`（最终采用版本）

**Events 约定（写入 events.jsonl）：**
- `stage=episode_generation, event=completed` 保持兼容
- 额外：`stage=episode_critique, event=completed, iteration=N, detail=score=...`
- 若改写：`stage=episode_rewrite, event=completed, iteration=N`

- [x] **Step 1: 写失败单测** — mock 低分时断言出现 critique 文件且正文被改写
- [x] **Step 2: 实现 `run_episode_quality_loop`**
- [x] **Step 3: 接入 orchestrator**
- [x] **Step 4: 跑既有 episodic 单测 + 新测**

```bash
uv run pytest tests/unit/test_episodic_orchestrator.py tests/unit/test_episode_quality.py -q
```

- [x] **Step 5: 手动 smoke（mock）**

```bash
uv run dramaloop run --idea "测试质量环" --style 都市情感 --format episodic_series --episode-count 2
ls runs/<run_id>/episodes/
```

---

### Task A4: Web 暴露每集分数（可选但推荐）

**Files:**
- Modify: `src/dramaloop/web/schemas.py` — `WebEpisodeSnapshot` 增加 `overall_score: float | None`
- Modify: `src/dramaloop/web/runtime.py` — hydrate 时读 critique json
- Modify: `frontend/src/types.ts`, `ResultPanel.tsx` — 显示分数徽章
- Test: `tests/unit/test_web_runs_api.py` 扩展一条断言

- [x] hydrate 填 `overall_score`
- [x] 前端分集正文标题旁显示分数
- [x] 前端/后端测通过

---

## Track B — Episodic Agent 评测

### Task B1: Episodic dataset

**Files:**
- Create: `evals/datasets/episodic_mvp_cases.yaml`

每条 case 必须含：

```yaml
- idea: "..."
  style: [都市情感]
  length: short
  format: episodic_series
  episode_count: 2   # 评测用小集数
  episode_min_words: 200
  episode_max_words: 400
  constraints: [节奏快, 结尾有钩子]
  enable_episode_critique: true
```

建议 4–6 条，覆盖：逆袭 / 重生 / 悬疑 / 爽文。

- [x] 写 dataset
- [x] 用 `StoryRequest.model_validate` 在单测里校验每条可解析

---

### Task B2: Eval runner 支持 episodic + 双轨指标

**Files:**
- Modify: `src/dramaloop/eval/report.py`
- Create: `tests/unit/test_episodic_eval.py`
- Modify: `src/dramaloop/main.py`（如需）

**行为变更：**
- `run_dataset_eval` 按 case 的 `format` 分支：
  - `single_story` → `run_story_pipeline`（保持兼容）
  - `episodic_series` → `run_episodic_pipeline(..., controller=None)`（CLI 无 controller 即不暂停）

**每个 episodic report 至少包含：**

```python
{
  "run_id": "...",
  "status": "completed|failed|cancelled",
  "format": "episodic_series",
  "completed_episodes": 2,
  "total_episodes": 2,
  "success": true,  # status==completed and completed==total
  "continuity_failures": 0,  # 可从 events 统计 event=failed & stage=episode_generation
  "episode_scores": [7.2, 6.8],  # 从 critique artifacts 读取；无则 []
  "average_episode_score": 7.0,
  "weakest_dimensions": ["pacing"],
}
```

**聚合报告：**
- `case_count`
- `success_rate`
- `average_final_score`（episodic 用 average_episode_score；single 保持原逻辑）
- `average_completed_episode_ratio`

- [x] 写单测：用 mock + tmp_path 跑 1 条 episodic case，断言报告字段
- [x] 实现
- [x] 跑：

```bash
uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml
ls evals/reports/
```

---

### Task B3: 评测文档与 README

**Files:**
- Modify: `project/spec/evaluation.md`
- Modify: `README.md`
- Optional: `project/tasks/2026-07-14-quality-and-eval/implementation-notes.md`

写明：
- 分集质量环阈值
- episodic 指标含义
- 如何跑 mock eval / 真实模型 eval
- 已知限制（critique 是模型自评，需人工抽检校准）

---

## Track C — 人工反馈沉淀（轻量，可并行）

> 为后续偏好数据 / 金标服务，不做大系统。

### Task C1: 记录人审信号（最小）

**Files:**
- Modify: `src/dramaloop/web/runtime.py` — 核对 plan edit / regenerate / cancel 事件 detail
- Optional: 写 `runs/<id>/human_actions.jsonl` append-only

字段示例：`{ts, action, episode_number?, payload_summary}`

验收：手动改 plan 一次、重生一集，文件有对应行。

---

## 建议执行顺序

```
A1 → A2 → A3 → B1 → B2 → A4 → B3 → C1
```

- **A3 是质量核心**；没有 A3 不要先做大而全前端。
- **B2 依赖 A3** 才能填满 `episode_scores`；若 A3 未完成，B2 可先让 `episode_scores=[]` 但 `success_rate` 可用。

---

## 测试清单（全部完成后打勾）

```bash
# 单元
uv run pytest tests/unit/test_episode_quality.py tests/unit/test_episodic_orchestrator.py tests/unit/test_episodic_eval.py tests/unit/test_web_runs_api.py -q

# 分集 smoke（mock）
uv run dramaloop run --idea "婚礼反击短剧" --style 都市情感 --format episodic_series --episode-count 2

# 评测 smoke（mock）
uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml

# 前端（若做了 A4）
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

---

## 明确不在本计划范围

- 视频 / 分镜 / 多用户托管
- Token 级正文流式（LLM provider streaming）
- 训练数据全量导出流水线
- 替换现有 Web 控制流架构
- 为抬分而盲目堆超长 prompt

---

## 给执行 AI 的决策默认值（避免来回问）

1. Critique 维度：复用 `hook_strength, conflict_intensity, pacing, short_drama_feel`，新增 `carryover`（第 1 集可打 N/A 或固定 8）。
2. Rewrite：最多 1 次；`enable_episode_critique=false` 可关。
3. Continuity vs quality：先 continuity gate，再 critique；rewrite 后 continuity 失败则回退。
4. Eval 默认 `episode_count: 2` 降本。
5. Web/前端分数展示可在 A3+B2 之后做；若时间紧可跳过 A4/C1，但必须在 status 里标明。

---

## 完成时交付物

1. 代码：质量环 + episodic eval 可运行
2. 数据集：`evals/datasets/episodic_mvp_cases.yaml`
3. 至少一份 `evals/reports/*-mvp-eval-report.md`（mock）
4. 更新后的 `project/spec/evaluation.md` + README 片段
5. （可选）短实现笔记：`project/tasks/2026-07-14-quality-and-eval/implementation-notes.md`
