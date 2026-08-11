# Implementation Notes

## Runtime Integration

`HarnessRuntime` 包装现有 `LLMClient`，orchestrator 只在模型调用和 artifact 写入边界接入。CLI、Web 和原有生成 stage 不需要改写。

## Memory

- 原文继续保存在 artifacts。
- `run_memory.json` 只保存摘要和 evidence refs。
- episode 与 semantic fact 在 stage/episode 边界做确定性 consolidation。
- 冲突记录到 `memory_conflicts`，不静默覆盖。

## Context

- stage budget 默认为模型窗口的 40%。
- required context 始终保留。
- memory 和 skill 进入同一个预算并写入 `context_trace.jsonl`。
- ablation mode 控制 contract、memory、budget、realization 和 regulation 的启用层级。
- `HarnessContextPlanner` 独立管理 context selection、重复丢弃提权和连续性恢复注入。

## Eval

- 真实 judge 使用独立 DeepSeek 配置。
- mock judge 用于结构测试。
- research dataset 运行 layer ablation，并生成 pairwise、trace 和 failure mining 报告。
- dataset 的 `expected_contracts` 会逐项评测，未知契约直接失败。
- semantic fact 的 evidence ref 必须指向当前 run 中真实存在的 artifact。
- JSON 和 Markdown 报告都包含 memory、trace、pairwise 与 regulation action 汇总。

## Episodic Execution

- 初次生成和继续生成复用统一 episode sequence。
- 单集重生成会使后续 episode artifact 和 memory 失效。
- 连续性失败会强制 unresolved threads 进入下一次 episode draft context。
