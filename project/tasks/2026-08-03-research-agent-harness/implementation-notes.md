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

## Eval

- 真实 judge 使用独立 DeepSeek 配置。
- mock judge 用于结构测试。
- research dataset 运行 layer ablation，并生成 pairwise、trace 和 failure mining 报告。
