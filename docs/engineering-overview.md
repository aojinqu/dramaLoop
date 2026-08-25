# Dramaloop 工程级项目说明

## 1. 项目定位

Dramaloop 是一个面向短剧创作的多阶段 LLM Agent 系统。它不是将 Prompt
直接包装成一次模型调用，而是把创作过程拆成可配置、可校验、可恢复、可观测、
可评测的工程流水线。

系统同时支持：

- 单篇短剧：前提提炼、人物设计、大纲、初稿、批评、定向改写、成稿。
- 分集短剧：整季设定、分批分集规划、逐集生成、连续性校验、单集质量环、整季合并。
- CLI 与 Web：共享同一套 orchestrator、运行时控制和 artifact 协议。
- Mock 与真实模型：Mock 用于确定性回归，Anthropic-compatible provider 用于真实生成，
  DeepSeek 用作独立质量评审。

项目的工程目标是解决长流程生成中的四类问题：

1. 模型调用不可控：输入输出契约不明确，坏结构会污染下游。
2. 长上下文易漂移：人物、关系、伏笔和用户约束随集数增加而丢失。
3. 失败难复盘：只能看到最终文本，无法解释上下文选择和恢复决策。
4. 优化不可归因：无法判断质量变化来自模型、Prompt，还是某一层运行时策略。

## 2. 总体架构

```text
CLI / Web / API
      |
      v
Story Orchestrator / Episodic Orchestrator
      |
      v
Research Agent Harness Runtime
  - Stage Contract
  - Procedural Skill
  - Run Memory
  - Context Planner
  - Output Realization
  - Trajectory Regulation
      |
      v
LLM Provider (Mock / Anthropic-compatible)
      |
      v
Run Artifacts + Trace + Eval + Failure Mining
```

核心设计是让 harness 位于 orchestrator 与模型之间，同时位于模型输出与下游
stage 之间。业务流程负责“下一步做什么”，harness 负责“这一步以什么契约运行、
使用哪些上下文、输出能否被接受、失败后如何恢复”。

## 3. 核心模块

### 3.1 显式 Stage Contract

`src/dramaloop/harness/stage_graph.py` 为每个阶段定义：

- 输入和输出 Schema。
- required / optional context。
- 预期 artifact。
- contract rules、禁止行为和常见失败模式。

单篇与分集流程都通过同一个 registry 查找 stage 定义。Trace Eval 基于 registry
计算 stage completion 和 artifact completion，避免评测逻辑另写一套流程假设。

### 3.2 Run Memory

Run Memory 只服务当前 run 和当前故事，不保存跨用户长期记忆。

```text
RawArtifactMemory  -> 原始产物索引和摘要
EpisodeMemory      -> 每集或阶段的时间顺序摘要
SemanticStoryMemory -> 人物、关系、约束、伏笔等原子事实
ProceduralSkill    -> 来自规格和离线失败分析的流程规则
```

完整内容继续保存在 artifact 中，memory 只保存压缩内容与 `evidence_refs`。评测时不仅
检查引用是否非空，还验证引用路径确实指向当前 run 中的文件，避免“看似可追溯”的
悬空记忆。

### 3.3 Context Planner

`HarnessContextPlanner` 在每次模型调用前构造 `ContextPack`：

- 默认预算为模型上下文窗口的 40%。
- required context 始终保留，并记录预算溢出。
- optional context 按优先级选择，未选内容写入 dropped items。
- procedural skill 与 memory 共用同一预算。
- 同一上下文连续被丢弃时自动提升优先级。
- 连续性失败后，将 unresolved threads 强制注入下一次分集调用。

planner 与 runtime 分离，使上下文策略可以独立测试和演进，不需要修改 provider
或业务 orchestrator。

### 3.4 Output Realization

Output Realization 是模型输出进入下游前的质量门：

1. `accepted`：Schema 和契约均满足。
2. `repaired`：去除 Markdown wrapper，或从 JSON/YAML 中恢复结构。
3. `retried`：缺字段或未覆盖改写目标时，执行一次 targeted retry。
4. `blocked`：重试后仍违反 required contract，停止当前 stage。

结构化输出使用 Pydantic 校验；文本改写检查目标区域是否发生实质变化；分集正文
还要通过 hook 和 continuity gate。

### 3.5 Trajectory Regulation

Trajectory Regulation 处理跨步骤退化，而不是评价单次文本的文学质量：

- 改写最多执行一次，防止无界优化。
- 改写目标必须对齐 critique 的最低评分维度。
- stage 连续失败达到阈值后停止，并保留 partial memory。
- 连续性失败触发 unresolved-thread recovery context。
- required context 反复被预算丢弃时提升优先级。

每个 decision 都写入 trajectory 和 decision trace，报告可统计
`continue / rewrite / retry_stage / stop` 的动作分布。

## 4. 分集生成可靠性

分集模式采用“分批规划、合并生成”，避免一次规划整季导致 JSON 截断。逐集生成时：

1. 从 `season_bible.json` 和 `episode_plan.json` 读取本集目标。
2. 从 `continuity_state.json` 和 Run Memory 召回上一集收尾、未解决线索和人物状态。
3. 生成正文并检查开头是否承接上一集真实 hook。
4. 可选执行 critique 和一次定向 rewrite。
5. rewrite 若破坏连续性则回滚到改写前版本。
6. 更新 episode artifact、continuity state、memory 和 trace。

首次生成、暂停后继续、单集重生成共用同一 episode 执行路径。重生成某集时会使后续
集失效，避免旧后续集继续引用已经变化的剧情状态。

## 5. 可观测性与可复盘

每次 run 都写出业务产物和 harness 产物。

通用产物：

```text
request.json
run_manifest.json
events.jsonl
final_story.md
run_summary.md
```

Harness 产物：

```text
run_memory.json
stage_trace.jsonl
memory_trace.jsonl
context_trace.jsonl
decision_trace.jsonl
skill_trace.jsonl
realization_trace.jsonl
trajectory_trace.jsonl
```

这些文件分别回答：

- 实际执行了哪些 stage。
- 哪些 artifact 被压缩成了什么 memory。
- 每次模型调用选择和丢弃了哪些上下文。
- 哪条 procedural skill 被触发。
- 输出经历了接受、修复、重试还是阻断。
- 系统为什么继续、改写、重试或停止。

失败 run 同样写 partial memory 和 trace，因此 provider error、Schema error 与连续性
退化可以分开定位。

## 6. 评测体系

评测分为五层：

1. DeepSeek Judge：评分 hook、冲突、节奏、短剧感、人物一致性、连续性、
   上下文忠实度和改写有效性。
2. Pairwise：交换 A/B 顺序评审，降低位置偏差，统计 winner、tie 和维度胜率。
3. Trace Eval：计算 stage、Schema、context、memory、skill、realization、
   rewrite 和 artifact 指标。
4. Layer Ablation：对七种 harness mode 做逐层消融。
5. Failure Mining：把失败归类为 contract、skill、context、memory、realization、
   trajectory 或 quality 问题。

Dataset 中的 `expected_contracts` 会被逐项执行并写入 `contract_results`。结构契约使用
确定性 trace 指标，内容契约使用对应 judge 维度；未知契约直接判失败，不会被静默忽略。

第一版 research dataset 包含 5 类 case：

- 单篇基础生成。
- 分集连续性。
- 高约束人物关系。
- 长上下文预算。
- critique-rewrite 有效性。

每个 case 运行 7 种模式：

```text
baseline
contract_enabled
memory_skill_enabled
memory_context_budgeted
realization_enabled
trajectory_regulation_enabled
full_harness
```

## 7. 工程质量与验证

当前验证基线：

- Python 3.11+，Pydantic v2，Typer，FastAPI。
- `uv` 管理依赖与命令执行。
- Ruff 负责静态规范检查。
- mypy 负责类型检查。
- pytest 覆盖单元、集成、Web 流式和运行控制。

本次完整验证结果：

```text
pytest: 106 passed
ruff: passed
mypy: passed (77 source files)
mock research eval: 5 cases x 7 modes = 35 runs
run success rate: 100%
expected contract pass rate: 66.67%
invalid evidence refs: 0
```

Mock 评测用于验证结构、编排、trace 和报告，不代表真实模型的文学质量提升。真实质量
结论需要配置 DeepSeek judge，并结合多次运行、pairwise 结果和人工抽检判断。当前
Mock 输出的 originality 固定为 5，因此新增的 `originality_not_template` contract
会按预期失败，不能用 Mock 报告宣称原创性达标。

2026-08-03 的真实 DeepSeek Prompt A/B、loop 和三模式 ablation 结果见
[`engineering-methods-evaluation.md`](engineering-methods-evaluation.md)。该实验观察到
Prompt 与 loop 的局部收益，但没有观察到 full harness 相对 baseline 的总分净增益。

## 8. 关键工程取舍

### 文件系统优先

第一版使用 JSON / JSONL / YAML 和 run 目录，不引入数据库或向量库。这样更容易回放、
diff、归档和调试，也适合当前数据规模。

### 不修改模型权重

项目通过 runtime harness 改善可靠性和可评测性，不做 fine-tuning、DPO 或 RLHF。
这使每层收益可以通过 ablation 独立验证。

### 确定性规则与 LLM Judge 分工

Schema、artifact、evidence、stage completion 使用确定性检查；创作质量使用独立 judge。
系统不会用主观模型评分替代本可确定验证的工程事实。

### 原文与压缩记忆并存

压缩记忆用于上下文预算，原始 artifact 作为事实来源。Memory 发生冲突时记录 conflict，
不静默覆盖旧事实。

## 9. 运行方式

安装与基础生成：

```bash
uv sync --extra dev
uv run dramaloop run --input examples/inputs/minimal_story.yaml
```

分集生成：

```bash
uv run dramaloop run \
  --idea "一个普通人意外获得重来一次的机会，决定改写自己失败的人生" \
  --style 都市情感 \
  --format episodic_series \
  --episode-count 12
```

完整 research harness 结构评测：

```bash
DRAMALOOP_PROVIDER=mock \
uv run dramaloop eval --dataset evals/datasets/research_harness_cases.yaml
```

工程检查：

```bash
uv run pytest -q
uv run ruff check .
uv run mypy src
```

## 10. 项目边界与后续演进

当前不包含长期用户记忆、向量数据库、自动修改线上规则和训练式 memory policy。

后续工程演进方向：

- 使用真实模型重复执行 ablation，建立带方差和置信区间的质量基线。
- 将现有 provider token usage 与 latency 采集接入长期趋势报告和成本告警。
- 增加 run replay 命令，从 artifact 和 trace 复现单个失败 stage。
- 把 failure mining 报告转为待审核的 procedural skill 候选，而非自动上线规则。
- 为长季项目增加跨批次的 story fact 冲突检测与更细粒度的 continuity score。
