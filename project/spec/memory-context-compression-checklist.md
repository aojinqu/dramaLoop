# 记忆系统与上下文压缩规格检查清单

Date: 2026-08-02
Feature: `project/spec/memory-context-compression.md`

## 内容质量

- [x] 明确目标：run 内记忆系统和上下文压缩
- [x] 明确非目标：不做跨用户长期记忆、不接向量库、不做多 agent memory
- [x] 明确总体架构：单 supervisor + 内部 memory/context tools
- [x] 明确存储位置：`runs/<run_id>/memory/`、`runs/<run_id>/context/`
- [x] 明确技术选型：Pydantic v2、JSON/JSONL/YAML、DeepSeek、mock provider

## 存储完整性

- [x] 定义 `run_memory.json`
- [x] 定义 `raw_artifacts.jsonl`
- [x] 定义 `episode_memory.jsonl`
- [x] 定义 `semantic_facts.jsonl`
- [x] 定义 `memory_conflicts.jsonl`
- [x] 定义 `compression_trace.jsonl`
- [x] 定义 `context_trace.jsonl`
- [x] 定义 `context/packs/*.json`

## 压缩方案

- [x] 支持摘要压缩
- [x] 支持事实抽取
- [x] 支持可逆压缩
- [x] 所有关键事实必须带 `evidence_refs`
- [x] 明确不使用 token-level prompt compressor

## 实施准备度

- [x] 新增文件列表明确
- [x] 修改文件列表明确
- [x] 评测指标明确
- [x] 验收标准明确
- [x] 可进入 implementation plan 阶段
