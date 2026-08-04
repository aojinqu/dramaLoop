# Research Agent Harness 改造规格检查清单

Date: 2026-08-02
Feature: `project/spec/research-agent-harness-upgrade.md`

## 内容质量

- [x] Spec 已改为 Life-Harness-style 生命周期架构
- [x] 覆盖目标：research harness
- [x] 覆盖 Stage Contract Layer
- [x] 覆盖 Procedural Skill + Run Memory Layer
- [x] 覆盖 Context Budget Layer
- [x] 覆盖 Output Realization Layer
- [x] 覆盖 Trajectory Regulation Layer
- [x] 覆盖 Eval + Harness Evolution
- [x] 明确非目标：不做人审、不做长期用户记忆、不重写主流程

## 需求完整性

- [x] 默认真实 judge 已定为 DeepSeek
- [x] 人审策略已定为第一期不做、不预留字段
- [x] context budget 已定为按模型窗口比例推导
- [x] 第一版默认 stage context budget 为模型窗口 40%
- [x] dataset 设计明确为 5 个 research harness cases
- [x] ablation modes 已扩展为 layer-level modes
- [x] failure mining 只生成报告，不自动改代码
- [x] 最终验收命令明确

## 评测方案质量

- [x] DeepSeek judge baseline 明确
- [x] Pairwise eval 明确
- [x] Trace eval 明确
- [x] Layer ablation eval 明确
- [x] Failure mining 分类明确
- [x] Mock provider 和真实 DeepSeek judge 边界明确

## 下一阶段准备度

- [x] 可进入 implementation plan 阶段
- [x] 已无 `[NEEDS CLARIFICATION]`
