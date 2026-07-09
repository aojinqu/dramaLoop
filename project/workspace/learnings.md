# 沉淀经验

- 对中文故事想法做 ASCII slug 时容易退化为 `story`，因此 run 目录必须支持自动追加后缀来避免 batch eval 冲突。
- 为了让项目更像生产系统原型，`events.jsonl`、`rewrite_plan_v1.json` 和 `run_summary.md` 必须直接体现 loop 的决策过程，而不只是保存最终稿。
- 稳定展示时应该把一个高质量 run 复制到 `examples/outputs/showcase-run/`，避免 README 依赖时间戳路径。
