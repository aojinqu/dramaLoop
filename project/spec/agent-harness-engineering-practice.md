# Agent Harness 工程化实践规格

## 背景

目标不是直接改造 `agent_harness` 仓库，而是将基于字节开源 Agent 框架 DeerFlow 的运行时分析、架构治理和评测设计，沉淀为可写入简历的工程级实践。

该实践面向多阶段 LLM Agent 场景，重点展示：
- 如何从 DeerFlow / LangGraph 的 Lead Agent、Tool、Middleware、Checkpointer、Subagent 设计中抽象工程化 Harness。
- 如何识别复杂 Agent 项目中的浅模块、重复编排、全局状态和弱评测问题。
- 如何设计可观测、可回放、可评测的 Agent run artifact 与 eval 闭环。

## 已识别的架构问题

### Agent 构建双轨

`agent_harness` 中生产路径主要在 `deerflow/client.py` 的 `DeerFlowClient._ensure_agent`，另一套较完整的 Agent 工厂在 `deerflow/agents/lead_agent/agent.py` 的 `make_lead_agent`。

风险：
- 生产路径与测试 / 设计路径可能不一致。
- Skill Domain 的工具隔离、MCP 过滤等逻辑可能没有完整进入生产路径。
- 后续评测如果绕过生产构建链路，得到的结果无法代表真实行为。

### HTTP Handler 巨石化

`handlers.py` 混合了 HTTP 适配、Ark SSE、业务 prompt 拼装、Lark 状态、Redis / Mongo 访问、rating、artifact 下载和错误处理。

风险：
- Interface 过宽，调用方和测试都需要理解过多细节。
- 业务 prompt 与运行时编排耦合，难以单独验证。
- 修改局部行为容易影响流式响应和线上运维逻辑。

### 全局状态与隐式依赖

项目大量依赖全局 config、MCP cache、sandbox / checkpointer singleton、ContextVar、类变量和进程内 subagent 任务表。

风险：
- 单测需要大量 monkeypatch 或 fake module。
- 多请求、多线程、多 pod 场景下状态语义不清。
- run 复现依赖环境，缺少显式上下文。

### 评测与运行时脱节

现有测试以消息转换、middleware、配置解析、HTTP 2xx smoke 为主，缺少 Harness 级 eval runner。

风险：
- 无法衡量 Agent 任务成功率、工具选择准确性、token / latency 成本、只读违规率和多轮稳定性。
- Skill 侧 eval 数据集没有统一接入 DeerFlow / Harness 生产路径。
- 缺少标准化 run artifact，问题复盘依赖日志搜索。

## 目标架构

### 统一 AgentFactory

提供单一 Agent 构建入口：

```text
AgentFactory.build(run_context) -> RunnableAgent
```

职责：
- 选择模型与 thinking / plan / subagent 配置。
- 装配 prompt、middleware、checkpointer、memory。
- 从 ToolRegistry 获取 domain-scoped tools。
- 保证生产、测试、eval 使用同一构建链路。

### 显式 RunContext

用 `RunContext` 聚合一次请求的关键上下文：

```text
thread_id
skill_domain
model
read_only
jwt / user identity
logid / trace_id
recursion_limit
eval_mode
```

收益：
- 减少散落在 handler、client、middleware 中的 kwargs。
- 降低对 ContextVar 和全局状态的依赖。
- eval runner 可以构造同一份上下文来复现生产行为。

### ToolRegistry

统一管理工具来源：
- builtin tools
- config tools
- MCP tools
- domain skill tools
- read-only allowlist / denylist

目标 Interface：

```text
ToolRegistry.list_tools(run_context) -> list[BaseTool]
```

收益：
- 工具暴露规则集中化。
- Domain 隔离和只读约束可单测。
- 避免工具拼装逻辑散落在 client、agent factory 和 handler 中。

### PromptContributor

将业务 prompt 注入从 handler 迁出，按 domain 注册：

```text
PromptContributor.contribute(run_context, messages) -> PromptPatch
```

收益：
- RMP、oncall、hornbill、创作类 prompt 可独立测试。
- HTTP 层只负责协议适配，不承担业务策略。

### Run Artifact

每次 Agent run 保存标准化产物：
- `run_manifest.json`
- `request.json`
- `events.jsonl`
- `tool_trace.jsonl`
- `usage.json`
- `artifacts/`
- `response.txt`
- `grading.json`
- `report.json`

收益：
- 支持失败复盘、回归对比、人工审核和 LLM judge。
- 简历中可表达为“把不可见的 Agent 执行链路转为可观测、可回放的工程产物”。

## 评测规格

### Dataset Schema

建议使用 `evals/harness_cases.yaml`：

```yaml
- id: sample-case-001
  skill_domain: writing
  headers:
    X-Read-Only: "true"
  messages:
    - role: user
      content: "生成一集短剧开头"
  expectations:
    - type: stage_completed
      stage: Writer
    - type: artifact_exists
      path_glob: "episodes/*.md"
    - type: llm_rubric
      criteria: "节奏、冲突、人物一致性、钩子"
  timeout_s: 300
  runs: 3
  tags: [writing, smoke]
```

### 指标

自动指标：
- `success_rate`
- `average_latency_ms`
- `average_total_tokens`
- `tool_call_count`
- `readonly_violation_count`
- `artifact_completion_rate`
- `continuity_gate_pass_rate`

模型 / 人工判定：
- 内容质量
- 人物一致性
- 情节承接
- 冲突强度
- 结尾 hook
- 是否满足用户约束

### 回归门禁

建议分层：
- L0：单元与契约测试，验证消息转换、工具隔离、只读 guard、stream 格式。
- L1：mock LLM / mock tools 离线 replay，验证编排确定性。
- L2：真实模型 smoke suite，验证端到端效果。
- L3：人工抽检与 LLM judge，对内容质量和复杂任务完成度做相对比较。

## 简历表达要点

可在简历中突出以下能力：
- 基于 DeerFlow 思路设计工程级 Agent Harness，而不是只写 prompt 或 Demo。
- 将多阶段 Agent 拆为统一 Stage Interface，使用 RunContext 管理运行上下文。
- 设计 ToolRegistry 和 Skill Domain 隔离，控制多工具 Agent 的误调用和副作用。
- 通过 run artifact、SSE event、tool trace 和 eval report 实现可观测、可回放和可评测。
- 使用 Critic / Rewriter / Continuity Guard 构建质量 loop，将长文本生成从一次性输出升级为可迭代流程。

## 当前简历落点

`resume-zh.tex` 中项目经历已调整为：

```text
基于 DeerFlow 的工程级 Agent Harness 与长文本生成评测系统
```

该标题能同时承载：
- DeerFlow / LangGraph 运行时理解
- Agent Harness 架构能力
- 长文本生成业务场景
- Eval / Observability / SFT 工程实践
