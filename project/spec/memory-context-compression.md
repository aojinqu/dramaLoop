# 记忆系统与上下文压缩规格

Date: 2026-08-02
Status: Draft for implementation plan

## 1. 目标

为 Dramaloop 增加一套 run 内记忆系统和上下文压缩机制，让分集短剧生成在长流程中稳定记住人物、关系、伏笔、约束和改写目标，同时控制每次模型调用的 token 成本。

第一期目标：

1. 原始产物完整落盘，不丢信息。
2. 从 artifacts 中提取结构化记忆。
3. 把长文本压缩成 episode summary 和 semantic facts。
4. 每次 stage 调用前按预算组装 context pack。
5. 每条进入上下文的关键记忆都能追溯到原始证据。
6. 用 eval 衡量压缩是否省 token、是否丢事实、是否提升连续性。

不做：

- 不做跨用户长期记忆。
- 不做用户画像和个性化偏好记忆。
- 不接向量数据库。
- 不引入复杂多 agent 记忆协作。
- 不把压缩摘要当作唯一真相，原始 artifacts 始终保留。

## 2. 总体架构

第一期采用单 supervisor + 内部 memory/context tools。

```text
Existing Orchestrator
  -> MemoryExtractor
  -> MemoryCompressor
  -> MemoryStore
  -> MemoryRetriever
  -> ContextPlanner
  -> Model Call
  -> MemoryUpdater
  -> Trace / Eval
```

这些模块不是独立 agent，而是 supervisor 调用的内部工具模块。

## 3. 存储设计

存储继续使用本项目已有的文件系统 artifact 模式。

每次 run 新增：

```text
runs/<run_id>/
├─ run_memory.json
├─ memory/
│  ├─ raw_artifacts.jsonl
│  ├─ episode_memory.jsonl
│  ├─ semantic_facts.jsonl
│  ├─ memory_conflicts.jsonl
│  └─ compression_trace.jsonl
├─ context/
│  ├─ context_trace.jsonl
│  └─ packs/
│     ├─ 001_premise_refinement.json
│     ├─ 002_character_card_generation.json
│     └─ ...
└─ eval/
   └─ memory_context_report.json
```

项目级长期规则放在：

```text
evals/skills/procedural_skills.yaml
```

说明：

- `run_memory.json` 是聚合视图，方便 inspect 和 report。
- `memory/*.jsonl` 是增量日志，方便复盘每条记忆怎么产生。
- `context/packs/*.json` 保存每次模型调用真正看到的上下文。
- `procedural_skills.yaml` 只保存从 eval/failure mining 沉淀的流程规则，不保存用户私有信息。

## 4. 技术选型

第一期技术：

- Schema：Pydantic v2。
- 存储：本地 JSON / JSONL / YAML。
- 原文存储：继续复用 `runs/<run_id>/` artifacts。
- 压缩方式：结构化抽取 + 摘要压缩 + 证据引用。
- LLM：DeepSeek 可用于摘要压缩和 judge；mock provider 用于测试。
- Token 预算：按模型上下文窗口比例推导，默认 40%。
- Token 估算：第一期使用轻量估算器，按中英文字符长度近似；后续可替换为模型 tokenizer。

第一期不使用：

- 向量数据库。
- 知识图谱数据库。
- LLMLingua / token-level prompt compressor。
- 多 agent memory manager。
- 训练式 memory policy。

原因：

- 当前最重要的是让 memory 可追溯、可评测、可落地。
- 分集短剧的关键记忆主要是结构化事实和剧情摘要，不需要第一版就上向量检索。
- token-level compressor 更适合大规模 RAG；本项目第一期更需要 evidence-backed story memory。

## 5. 数据模型

### 5.1 MemoryRecord

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

### 5.2 RawArtifactMemory

只记录 artifact 元数据，不复制全文。

```python
class RawArtifactMemory(MemoryRecord):
    artifact_path: str
    artifact_type: str  # json / markdown / jsonl
    stage: str
    short_summary: str
```

### 5.3 EpisodeMemory

记录某一集或某个阶段的压缩摘要。

```python
class EpisodeMemory(MemoryRecord):
    episode_number: int | None = None
    title: str | None = None
    summary: str
    opening_state: str | None = None
    closing_state: str | None = None
    hook_signal: str | None = None
```

### 5.4 SemanticFact

记录可被后续 stage 复用的原子事实。

```python
class SemanticFact(MemoryRecord):
    fact_type: str  # character / relationship / constraint / thread / payoff
    subject: str
    predicate: str
    object: str
    status: str  # active / resolved / contradicted
```

### 5.5 ContextPack

```python
class ContextPack(BaseModel):
    stage: str
    call_index: int
    budget_tokens: int
    estimated_tokens: int
    selected_items: list[ContextItem]
    dropped_items: list[ContextItem]
    memory_refs: list[str]
```

### 5.6 ContextItem

```python
class ContextItem(BaseModel):
    id: str
    kind: str  # request / stage_input / episode_memory / semantic_fact / skill
    content: str
    tokens_estimated: int
    priority: int
    reason: str
    evidence_refs: list[str] = []
    required: bool = False
```

## 6. 写入路径

每个 stage 完成后执行 memory write path。

```text
stage output
  -> register raw artifact
  -> extract candidate facts
  -> update episode memory
  -> update semantic facts
  -> detect conflicts
  -> write memory trace
```

写入规则：

- 原始 artifact 先写入已有 run 目录。
- `RawArtifactMemory` 只记录路径和短摘要。
- `EpisodeMemory` 在 episode / stage 边界生成，不对每个小字段都压缩。
- `SemanticFact` 必须有 `evidence_refs`。
- 如果新事实和旧事实冲突，不覆盖旧事实，写入 `memory_conflicts.jsonl`。
- 失败 run 也必须写 partial memory。

## 7. 压缩策略

第一期采用三种压缩。

### 7.1 摘要压缩

把长正文压缩成 episode summary。

输入：

- episode markdown
- episode plan
- continuity state

输出：

- 本集发生了什么
- 本集开头承接了什么
- 本集推进了什么
- 本集结尾留下什么 hook

### 7.2 事实抽取

从正文和结构化 artifacts 中抽取 semantic facts。

例子：

```text
女主和男主是假结婚。
母亲病历是关键伏笔。
男主第 7 集发现真相。
第 8 集必须爆发误会。
```

这些事实进入 `semantic_facts.jsonl`。

### 7.3 可逆压缩

上下文里不塞全文，只塞摘要、事实和证据引用。

```text
Context 中放：
  - 第7集摘要
  - 当前第8集 plan
  - 未解决伏笔
  - evidence_refs: episodes/episode_07.md

不放：
  - 第1-7集全文
```

如果后续需要原文，系统可以通过 `evidence_refs` 回到 artifact。

## 8. 读取路径

每个 stage 调模型前执行 memory read path。

```text
stage spec
  -> required context
  -> retrieve memory
  -> rank by priority
  -> enforce token budget
  -> build context pack
  -> write context trace
```

不同 stage 的读取策略：

- `episode_draft`：优先读取当前 episode plan、上一集 summary、unresolved threads、人物关系。
- `critique`：优先读取 draft、rubric、用户约束、stage contract。
- `rewrite`：优先读取 critique weakest dimensions、rewrite target、原 draft、必须保留的 semantic facts。
- `final_assembly`：优先读取所有 episode summaries、resolved events、final payoff。

## 9. Context Budget 规则

预算计算：

```text
stage_budget = model_context_window * 0.4
```

第一版默认：

- 如果模型窗口未知，使用保守默认值。
- required context 不参与丢弃。
- optional context 按 priority 排序。
- 超预算时先丢低优先级 episode summaries，再丢低置信 semantic facts。
- 不允许丢弃当前 stage 的直接输入。

优先级建议：

```text
100: user request / hard constraints
90 : current stage input
80 : unresolved threads / rewrite target
70 : high-confidence semantic facts
60 : previous episode summary
50 : procedural skill
40 : older episode summary
```

## 10. 模块落点

新增文件：

```text
src/dramaloop/schemas/memory.py
src/dramaloop/schemas/context.py
src/dramaloop/harness/memory_store.py
src/dramaloop/harness/memory_extractor.py
src/dramaloop/harness/memory_compressor.py
src/dramaloop/harness/memory_retriever.py
src/dramaloop/harness/context_planner.py
```

修改文件：

```text
src/dramaloop/harness/orchestrator.py
src/dramaloop/harness/episodic_orchestrator.py
src/dramaloop/storage/runs.py
src/dramaloop/eval/report.py
```

新增 eval：

```text
src/dramaloop/eval/memory_context.py
evals/datasets/memory_context_cases.yaml
```

## 11. 评测指标

结构指标：

- `memory_write_success_rate`
- `context_pack_write_success_rate`
- `semantic_fact_evidence_rate`
- `unsupported_memory_count`

压缩指标：

- `memory_compression_ratio`
- `context_token_reduction_rate`
- `dropped_required_context_count`

质量指标：

- `memory_recall_rate`
- `continuity_issue_count`
- `constraint_preservation_rate`
- `rewrite_target_alignment`

成本指标：

- `average_context_tokens`
- `average_latency_ms`
- `average_llm_calls`

## 12. 验收标准

第一期完成后：

- 每个 run 都写出 `run_memory.json`。
- 每个 run 都写出 `memory/raw_artifacts.jsonl`、`memory/episode_memory.jsonl`、`memory/semantic_facts.jsonl`。
- 每次模型调用都写出一个 `context/packs/*.json`。
- 每条 semantic fact 都有 `evidence_refs`。
- 分集生成不会把前面所有正文塞进上下文。
- `episode_draft` 能按预算读取上一集 summary、未解决伏笔和关键人物关系。
- mock provider 下能跑通 memory/context 单测。
- `uv run dramaloop eval --dataset evals/datasets/memory_context_cases.yaml` 能输出 memory/context report。

## 13. 实施顺序

### Phase 1：存储和 schema

- 定义 memory/context schema。
- 扩展 run 目录结构。
- 写 `run_memory.json` 和 memory jsonl 文件。

### Phase 2：提取和压缩

- 实现 artifact registration。
- 实现 episode summary 压缩。
- 实现 semantic fact 抽取。
- 实现 conflict 记录。

### Phase 3：上下文组装

- 实现 memory retrieval。
- 实现 context priority 排序。
- 实现 budget enforcement。
- 写 `context_trace.jsonl` 和 `context/packs/*.json`。

### Phase 4：接入主流程

- 接入单篇 orchestrator。
- 接入分集 orchestrator。
- 保持现有 artifacts 不变。

### Phase 5：评测

- 增加 memory/context eval dataset。
- 统计压缩率、召回率、证据率、token 降低率。
- 输出 JSON 和 Markdown 报告。
