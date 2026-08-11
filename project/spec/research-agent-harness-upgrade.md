ni# Research Agent Harness 生命周期架构规格

Date: 2026-08-02
Status: Implemented and verified
Reference: Life-Harness-style runtime interface adaptation

## 1. 目标

把 Dramaloop 改造成一个可观测、可复盘、可消融的 research agent harness。

本规格借鉴 Life-Harness 的核心思想：不改模型权重，不重写环境和主流程，而是在模型和任务流程之间增加一层可配置、可记录、可评测的 runtime harness。该 harness 从失败 run 中识别重复模式，并把这些模式沉淀为明确的运行时干预层。

第一期目标：

1. 把现有多阶段创作流程整理为显式 Stage Contract。
2. 为每次 run 写出可复盘的 memory、context、decision、realization、trajectory artifact。
3. 在每个 stage 调用前做 context budget 和 procedural skill 注入。
4. 在每个 stage 输出后做 schema 校验、格式修复和失败拦截。
5. 在多轮 critique / rewrite / episode 生成中做 trajectory regulation。
6. 增强 eval：DeepSeek judge baseline + pairwise + trace + layer ablation + failure mining。

不做：

- 不重写现有 CLI / Web / 分集生成主流程。
- 不做长期用户记忆。
- 不做人审功能，也不预留人工标注字段。
- 不做 fine-tuning、DPO、RLHF。
- 不把 eval 失败直接写成线上规则；第一期只做离线分析和显式配置。

## 2. 总体架构

Runtime harness 位于 orchestrator 和模型调用之间，也位于模型输出和下游 stage 之间。

```text
User Request
  -> Existing CLI / Web / Orchestrator
  -> Harness Runtime
       1. Stage Contract Layer
       2. Procedural Skill + Run Memory Layer
       3. Context Budget Layer
       4. Output Realization Layer
       5. Trajectory Regulation Layer
  -> Existing provider / model call
  -> Existing artifacts
  -> Eval + Failure Mining
```

各层职责：

| Harness Layer | Dramaloop 中的作用 | 第一版落点 |
| --- | --- | --- |
| Stage Contract | 明确每个创作阶段的输入、输出、上下文、产物和不变量 | `stage_graph.py` |
| Procedural Skill + Run Memory | 记录一次 run 的关键事实，并注入可复用创作流程规则 | `run_memory.py`、`skills.py` |
| Context Budget | 在预算内选择 stage 所需上下文，记录 dropped items | `context.py` |
| Output Realization | 校验和修复模型输出，避免坏结构进入下一阶段 | `realization.py` |
| Trajectory Regulation | 监控 rewrite、episode、continuity 的退化模式并触发恢复策略 | `trajectory.py` |
| Eval + Evolution | 用 trace、judge、ablation 和 failure mining 评估每层贡献 | `eval/*` |

运行原则：

- Harness 是可关闭的；默认不破坏现有输出路径。
- 每层都要写 trace，方便复盘和 ablation。
- 每层只处理自己能最早发现的问题。
- 对创作质量的判断走 DeepSeek judge 和 pairwise eval；对结构完整性走 deterministic trace eval。

## 3. Stage Contract Layer

当前流程已有多个阶段：`premise`、`characters`、`outline`、`draft`、`critique`、`rewrite`、`season`、`episode_plan`、`episode_draft` 等。

本层把这些阶段整理成显式 contract，作为后续 context、realization、trace eval 的基础。

建议新增：

- `src/dramaloop/harness/stage_graph.py`
- `src/dramaloop/schemas/stage.py`

核心结构：

```python
class StageSpec(BaseModel):
    name: str
    input_schema: str
    output_schema: str
    required_context: list[str]
    optional_context: list[str] = []
    artifact_outputs: list[str]
    contract_rules: list[str] = []
    forbidden_behaviors: list[str] = []
    common_failure_modes: list[str] = []
```

示例 contract：

```python
StageSpec(
    name="rewrite",
    input_schema="RewriteInput",
    output_schema="RewriteOutput",
    required_context=["draft", "critique", "rewrite_target"],
    optional_context=["story_facts", "unresolved_threads"],
    artifact_outputs=["final_story.md"],
    contract_rules=[
        "rewrite must address the weakest critique dimensions",
        "rewrite must preserve established character relationships",
    ],
    forbidden_behaviors=[
        "drop required user constraints",
        "change protagonist identity without explicit request",
    ],
    common_failure_modes=[
        "generic polish without fixing weak dimension",
        "continuity drift after rewrite",
    ],
)
```

实现要求：

- 每个 stage 都能查到输入、输出、上下文、产物和 contract rules。
- 现有 orchestrator 不需要大改，先在运行时引用 registry。
- eval 可以读取 registry 检查 stage 是否跑完整。
- stage trace 中记录实际进入和离开的 stage。

输出：

```text
runs/<run_id>/stage_trace.jsonl
```

验收标准：

- 单篇和分集生成都能写出完整 stage trace。
- 所有已知 stage 都在 registry 中有定义。
- trace eval 能基于 registry 判断 stage completion 和 artifact completion。

## 4. Memory System Layer

本层负责把一次 run 中产生的大量 artifacts 压缩成可复用、可追溯、可评测的记忆。第一期只做 run 内和 story 内记忆，不做跨用户长期记忆。

本层拆成四类 memory，避免把所有东西塞进一个 `RunMemory`：

1. `RawArtifactMemory`：原始产物索引，只保存路径、类型、stage、摘要，不复制全文。
2. `EpisodeMemory`：每集或每个主要阶段的时间顺序摘要。
3. `SemanticStoryMemory`：人物、关系、伏笔、约束、已解决事件等原子事实。
4. `ProceduralSkill`：从离线 eval 和失败恢复中沉淀的 harness 级流程规则，不包含用户私有长期记忆。

设计原则：

- 原文不丢：完整内容留在 artifacts，memory 中保存摘要和引用路径。
- 事实有证据：每条 semantic fact 必须带 `evidence_refs`，指向来源 artifact 或 episode。
- 压缩可逆：上下文中放压缩内容，但能通过路径回到原始产物。
- 少做 eager 总结：不要每个小输出都调用 LLM 压缩，优先在 stage 边界和 episode 边界 consolidation。
- 防止记忆漂移：新 memory 不能凭空改写已有事实；冲突必须记录为 conflict，而不是静默覆盖。

建议新增：

- `src/dramaloop/harness/run_memory.py`
- `src/dramaloop/harness/memory_compressor.py`
- `src/dramaloop/harness/memory_retriever.py`
- `src/dramaloop/harness/skills.py`
- `src/dramaloop/schemas/memory.py`
- `src/dramaloop/schemas/skill.py`
- `evals/skills/procedural_skills.yaml`

`MemoryRecord` 核心结构：

```python
class MemoryRecord(BaseModel):
    id: str
    kind: str  # raw_artifact / episode / semantic_fact / procedural_skill
    scope: str  # run / story / episode / stage
    content: str
    evidence_refs: list[str] = []
    confidence: float = 1.0
    created_stage: str
    last_updated_stage: str | None = None
```

`RunMemory` 核心结构：

```python
class RunMemory(BaseModel):
    run_id: str
    request_summary: str
    completed_stages: list[str]
    raw_artifacts: list[MemoryRecord]
    episode_memories: list[MemoryRecord]
    semantic_facts: list[MemoryRecord]
    unresolved_threads: list[MemoryRecord]
    resolved_events: list[MemoryRecord]
    critique_history: list[dict]
    rewrite_targets: list[str]
    memory_conflicts: list[dict] = []
    failure_patterns: list[str] = []
    final_status: str
```

`ProceduralSkill` 核心结构：

```python
class ProceduralSkill(BaseModel):
    id: str
    stage: str
    trigger: str
    guidance: str
    source: str
    priority: int = 0
```

示例 skill：

```yaml
- id: episodic-continuity-preserve-threads
  stage: episode_draft
  trigger: "episodic_series with unresolved_threads"
  guidance: "Before drafting the next episode, restate unresolved threads and carry at least one forward into the hook."
  source: "failure_mining: episodic-continuity-001"
  priority: 80
```

每次 run 写出：

```text
runs/<run_id>/run_memory.json
runs/<run_id>/memory_trace.jsonl
runs/<run_id>/decision_trace.jsonl
runs/<run_id>/skill_trace.jsonl
```

`memory_trace.jsonl` 记录：

- 从哪个 artifact 提取了哪些 memory。
- 哪些 memory 被合并、更新或标记冲突。
- 哪些原始内容被压缩成 episode summary。
- 哪些 semantic facts 被 context planner 召回。

`decision_trace.jsonl` 记录：

- 为什么触发 rewrite。
- 为什么跳过 rewrite。
- 为什么停止生成。
- 为什么某个阶段失败。
- 哪个 harness layer 触发了干预。

验收标准：

- 单篇和分集 run 都能写出 `run_memory.json`。
- 失败 run 也能写出 partial memory。
- 每条 semantic fact 都有 `evidence_refs`。
- memory 压缩后仍能追溯到原始 artifact。
- context planner 可以按 stage 召回 episode memory 和 semantic facts。
- skill 注入只来自显式 `procedural_skills.yaml` 或 eval 产物，不读取长期用户记忆。
- 不影响现有 `final_story.md`、`events.jsonl`、episode artifacts。

## 5. Context Budget Layer

每个 stage 调模型前，先构造 `ContextPack`。该层决定本次调用给模型看哪些事实、计划、critique、episode memory、semantic facts、procedural skills。

建议新增：

- `src/dramaloop/schemas/context.py`
- 扩展 `src/dramaloop/harness/context.py`

核心结构：

```python
class ContextItem(BaseModel):
    id: str
    kind: str
    content: str
    tokens_estimated: int
    priority: int
    reason: str
    evidence_refs: list[str] = []
    required: bool = False

class ContextPack(BaseModel):
    stage: str
    budget_tokens: int
    selected_items: list[ContextItem]
    dropped_items: list[ContextItem]
    memory_refs: list[str] = []
```

预算规则：

- 按模型上下文窗口比例推导，不写死固定 token。
- 第一版默认使用模型窗口的 40% 作为 stage context budget。
- `required_context` 必须进入。
- procedural skill 进入 context budget，并记录 reason。
- 超预算时优先保留当前 stage 的 required context、当前 episode plan、unresolved threads、rewrite target、高置信 semantic facts。
- episode 原文默认不直接进入上下文，优先进入 episode memory；只有需要修复连续性时再引用原文片段。
- semantic facts 进入上下文时必须保留 evidence refs，方便 judge 和 trace eval 检查是否幻觉。
- 被丢弃的内容要记录原因。

每次 stage 调用写出：

```text
runs/<run_id>/context_trace.jsonl
```

验收标准：

- 每个 stage 都能看到实际使用了哪些 context。
- report 能统计 context tokens、dropped items 数量。
- trace eval 能统计 `memory_recall_rate` 和 `unsupported_memory_rate`。
- eval 能比较 `baseline`、`memory_enabled`、`memory_context_budgeted`。

## 6. Output Realization Layer

Life-Harness 中的 Action Realization 负责把模型动作转成环境可执行动作。Dramaloop 中对应的是把模型输出转成下游 stage 可接受的结构化产物。

本层在模型输出后、写 artifact 或进入下一 stage 前运行。

建议新增：

- `src/dramaloop/harness/realization.py`
- `src/dramaloop/schemas/realization.py`

核心结构：

```python
class RealizationResult(BaseModel):
    stage: str
    status: str  # accepted / repaired / retried / blocked
    issues: list[str] = []
    repair_summary: str | None = None
    retry_reason: str | None = None
```

第一版处理范围：

- JSON / YAML 输出 parse 失败。
- stage output schema 缺字段。
- artifact 路径缺失或命名不符合 contract。
- rewrite 输出没有覆盖 rewrite target。
- episode draft 缺 hook、缺 continuity carry-over。
- critique 输出缺评分维度。

处理策略：

1. `accepted`：输出符合 schema 和 contract，直接进入下一阶段。
2. `repaired`：确定性格式问题，局部修复后继续。
3. `retried`：内容缺失但可通过一次 targeted retry 修复。
4. `blocked`：违反 required contract，停止该 stage 并记录失败。

输出：

```text
runs/<run_id>/realization_trace.jsonl
```

验收标准：

- mock provider 下能触发 parse repair、missing field retry、contract blocked 三类路径。
- `schema_valid_rate` 可从 realization trace 统计。
- realization 不改变创作主流程，只包装 stage 输出验收。

## 7. Trajectory Regulation Layer

本层关注多步交互中的退化模式，不评价单次输出的文学质量。

适用场景：

- critique 分数低但 rewrite 没有针对弱项。
- 多轮 rewrite 后分数不升反降。
- 分集生成重复相同冲突。
- episode plan 和 episode draft 逐步丢失用户约束。
- context budget 反复丢弃同一类关键事实。

建议新增：

- `src/dramaloop/harness/trajectory.py`
- `src/dramaloop/schemas/trajectory.py`

核心结构：

```python
class TrajectorySignal(BaseModel):
    stage: str
    signal_type: str
    severity: str
    evidence: list[str]
    recommended_action: str

class RegulationDecision(BaseModel):
    stage: str
    action: str  # continue / rewrite / retry_stage / stop
    reason: str
    signals: list[TrajectorySignal]
```

第一版 regulation rules：

- rewrite 最多触发一次，避免无限优化。
- 如果 critique 最弱维度没有进入 rewrite target，则强制修正 target。
- 如果 required context 连续被 dropped，则提升 priority。
- 如果分集连续性检测失败，则在下一集强制注入 unresolved threads。
- 如果 stage 连续 retry 失败，则停止并写 partial memory。

输出：

```text
runs/<run_id>/trajectory_trace.jsonl
```

验收标准：

- trace eval 能统计 `rewrite_target_alignment`。
- report 能看到 regulation action 分布。
- 失败 run 能说明停止原因，而不是只看到 provider error。

## 8. Eval + Harness Evolution

Eval 第一版分五层。

### 8.1 DeepSeek Judge Baseline

用 DeepSeek 作为默认真实 judge。

新增：

- `src/dramaloop/eval/judge.py`

评分维度：

- `hook_strength`
- `conflict_intensity`
- `pacing`
- `short_drama_feel`
- `character_consistency`
- `continuity`
- `context_fidelity`
- `rewrite_effectiveness`

输出：

```text
runs/<run_id>/eval/judge_baseline.json
```

### 8.2 Pairwise Eval

用于比较两个系统配置哪个更好。

新增：

- `src/dramaloop/eval/pairwise.py`

比较对象：

- `baseline` vs `contract_enabled`
- `contract_enabled` vs `memory_skill_enabled`
- `memory_skill_enabled` vs `memory_context_budgeted`
- `no_realization` vs `realization_enabled`
- `no_regulation` vs `trajectory_regulation_enabled`

要求：

- 同一个 case 跑 A/B 两个输出。
- DeepSeek judge 选择 winner / tie。
- A/B 顺序交换一次，降低位置偏差。
- 报告 win_rate、tie_rate、dimension_win_rate。

### 8.3 Trace Eval

不只看最终故事，还看过程是否合理。

新增：

- `src/dramaloop/eval/trace.py`

检查项：

- stage 是否都完成。
- schema 是否有效。
- 必需 context 是否进入。
- semantic facts 是否有证据来源。
- 压缩后的 episode memory 是否保留关键剧情推进。
- skill 是否按 trigger 注入。
- realization 是否过度修复或错误 block。
- rewrite 是否针对弱维度。
- artifacts 是否都写出。

核心指标：

- `stage_completion_rate`
- `schema_valid_rate`
- `required_context_recall`
- `memory_recall_rate`
- `memory_compression_ratio`
- `unsupported_memory_rate`
- `skill_trigger_precision`
- `realization_repair_rate`
- `realization_block_rate`
- `rewrite_target_alignment`
- `artifact_completion_rate`

### 8.4 Layer Ablation Eval

新增：

- `src/dramaloop/eval/ablation.py`
- `evals/datasets/research_harness_cases.yaml`

第一版 ablation modes：

1. `baseline`
2. `contract_enabled`
3. `memory_skill_enabled`
4. `memory_context_budgeted`
5. `realization_enabled`
6. `trajectory_regulation_enabled`
7. `full_harness`

报告比较：

- completion rate
- average judge score
- pairwise win rate
- continuity issue count
- memory recall rate
- memory compression ratio
- unsupported memory rate
- average tokens
- average latency
- layer intervention count

### 8.5 Failure Mining

新增：

- `src/dramaloop/eval/failure_mining.py`

输入：

```text
runs/<run_id>/*.jsonl
runs/<run_id>/run_memory.json
runs/<run_id>/eval/*.json
```

输出：

```text
evals/reports/<timestamp>-failure-patterns.md
evals/reports/<timestamp>-failure-patterns.json
```

失败分类：

- `contract_mismatch`：stage contract 不清或 required context 缺失。
- `skill_gap`：缺少可复用创作流程指导。
- `context_loss`：关键 story facts 或 constraints 被预算丢弃。
- `memory_drift`：压缩后的 memory 与原始 artifact 不一致。
- `memory_recall_gap`：需要的 episode memory 或 semantic facts 没有进入 context。
- `unsupported_memory`：memory 中出现无法追溯到 evidence refs 的事实。
- `realization_error`：输出结构、artifact、schema 不可用。
- `trajectory_degradation`：rewrite、分集连续性或多轮生成退化。
- `quality_gap`：结构正确但 DeepSeek judge 质量低。

第一期只生成报告，不自动改代码。

## 9. 数据集

新增 `evals/datasets/research_harness_cases.yaml`。

第一版放 5 个 case：

1. 单篇短剧基础生成。
2. 分集短剧连续性。
3. 高约束创作，比如必须保留指定人物关系。
4. 长上下文创作，测试 context budget。
5. 改写挑战，测试 critique-rewrite 是否真的修复弱点。

每个 case 包含：

```yaml
- id: episodic-continuity-001
  format: episodic_series
  idea: "..."
  style: ["都市情感"]
  constraints:
    - "..."
  expected_contracts:
    - preserve_character_relationships
    - carry_unresolved_threads
  ablation_modes:
    - baseline
    - contract_enabled
    - memory_skill_enabled
    - memory_context_budgeted
    - realization_enabled
    - trajectory_regulation_enabled
    - full_harness
```

## 10. 实施顺序

### Phase 1：先落 Contract 和 Artifacts

- 加 `StageSpec`。
- 加 `RunMemory`。
- 加 `MemoryRecord`。
- 写 `stage_trace.jsonl`。
- 写 `run_memory.json`。
- 写 `memory_trace.jsonl`。
- 写 `decision_trace.jsonl`。
- 保证不破坏现有 `final_story.md`、`events.jsonl`、episode artifacts。

### Phase 2：做 Memory Compression、Context 和 Skill

- 加 `memory_compressor.py`。
- 加 `memory_retriever.py`。
- 加 `ContextItem`。
- 加 `ContextPack`。
- 加 `ProceduralSkill`。
- 从 artifacts 提取 episode memory 和 semantic facts。
- 每个 stage 调用前构造 context pack。
- 按模型窗口 40% 控制预算。
- context pack 优先召回有 evidence refs 的 memory。
- 写 `context_trace.jsonl` 和 `skill_trace.jsonl`。

### Phase 3：做 Output Realization

- 加 realization schema。
- 接入 stage output validation。
- 支持 parse repair、missing field retry、contract blocked。
- 写 `realization_trace.jsonl`。

### Phase 4：做 Trajectory Regulation

- 加 trajectory signal 和 regulation decision。
- 接入 rewrite target alignment。
- 接入 continuity / repeated failure 检测。
- 写 `trajectory_trace.jsonl`。

### Phase 5：接 DeepSeek Judge 和 Eval

- 加 judge schema。
- 加 judge prompt。
- 生成 `judge_baseline.json`。
- 支持 pairwise eval。
- 支持 trace metrics。
- 支持 layer ablation。
- 新增 research harness dataset。

### Phase 6：做 Failure Mining

- 从 run artifacts 聚合失败模式。
- 输出 failure pattern report。
- 给下一轮 harness 改造提供输入。
- 第一版不自动改代码。

## 11. 最终验收

完成后应满足：

- `uv run dramaloop run ...` 正常生成，不破坏现有输出。
- 每次 run 都写出 `run_memory.json`、`memory_trace.jsonl`、`stage_trace.jsonl`、`context_trace.jsonl`、`decision_trace.jsonl`。
- `run_memory.json` 中的 semantic facts 都能追溯到 evidence refs。
- 启用 realization 后写出 `realization_trace.jsonl`。
- 启用 regulation 后写出 `trajectory_trace.jsonl`。
- `uv run dramaloop eval --dataset evals/datasets/research_harness_cases.yaml` 能生成 JSON 和 Markdown 报告。
- 报告能看到 DeepSeek judge 分数、pairwise 胜率、memory 指标、trace 指标、layer ablation 对比和 failure mining 分类。
- mock provider 下可以跑通结构测试；真实 DeepSeek judge 只用于离线质量评测。
- ablation report 能说明每个 harness layer 的干预次数和质量影响。
