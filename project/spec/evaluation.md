# 评估规格

## 评估维度
- hook_strength
- character_consistency
- conflict_intensity
- pacing
- short_drama_feel
- ending_payoff
- language_fluency

## 默认阈值
- target_threshold = 7.5
- minimum_dimension_threshold = 6
- min_delta = 0.3

## 分集（episodic）质量环

### 分集 critique 维度
- hook_strength
- conflict_intensity
- pacing
- short_drama_feel
- carryover（第 1 集可打 N/A 语义分，建议固定 8）

### 分集 rewrite 阈值
- `rewrite_needed` 当 `overall_score < 7.0` 或任维 `< 6.0`
- 默认最多 1 次定向 rewrite；可用 `enable_episode_critique=false` 关闭

### Episodic 评测指标
- `success`：`status == completed` 且 `completed_episodes == total_episodes`
- `continuity_failures`：events 中 `stage=episode_generation` 且 `event=failed` 的次数
- `episode_scores`：从 `episodes/episode_XX_critique.json` 读取的 overall_score 列表
- `average_episode_score`：episode_scores 均值
- 聚合：`success_rate`、`average_final_score`（episodic 用 average_episode_score）、`average_completed_episode_ratio`

### 如何跑评测
```bash
# mock（推荐本地/CI）
DRAMALOOP_PROVIDER=mock uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml

# 单篇既有集
DRAMALOOP_PROVIDER=mock uv run dramaloop eval --dataset evals/datasets/mvp_cases.yaml

# 真实模型：在 .env 配置 anthropic-compatible 后去掉 DRAMALOOP_PROVIDER=mock
uv run dramaloop eval --dataset evals/datasets/episodic_mvp_cases.yaml
```
报告写入 `evals/reports/*-mvp-eval-report.{json,md}`。

### 已知限制
- Critique / rewrite 是模型自评，分数只作相对信号；上线前需人工抽检校准。
- mock 下分数固定可复现，不代表真实模型质量。
