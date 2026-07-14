# 2026-07-14 Quality Loop + Agent Eval

## 目标
分集质量闭环（critique-rewrite）+ episodic agent 评测数据集与报告。

## 执行计划（给其他 AI）
完整可执行计划见：

**`docs/superpowers/plans/2026-07-14-quality-and-eval.md`**

## 建议开场 Prompt（复制给执行 AI）

```text
请按 docs/superpowers/plans/2026-07-14-quality-and-eval.md 逐任务实现。
先读计划里的「背景与现状」和 Global Constraints。
从 Task A1 开始，按 A1→A2→A3→B1→B2 顺序，用 checkbox 跟踪。
不要重做 pause/resume/cancel。优先 mock 可跑通的测试。
每完成一个 Task 跑对应 pytest。不要擅自 commit，除非我要求。
```

## 状态
- [ ] Track A 质量闭环
- [ ] Track B episodic eval
- [ ] Track A4/C1（可选）
