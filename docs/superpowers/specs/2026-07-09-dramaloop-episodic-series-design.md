# Dramaloop 分集短剧生成方案

## 1. 目标

把现在的“单篇 short story 生成”升级成“分集短剧生成”。

用户输入一个 idea 后，系统自动：

1. 生成整季故事总设定
2. 生成 12 集分集规划
3. 按顺序逐集生成正文
4. 每集生成完成后立即展示
5. 全部完成后输出合并版完整故事

本方案的默认形态：

- 形式：短剧分集
- 默认集数：12 集
- 每集字数：500-800 字
- 生成方式：先规划，再逐集串行生成
- 展示方式：边生成边展示 + 最后提供完整合并版

---

## 2. 当前问题

当前后端只有单篇模式：

- `StoryRequest.length` 只有 `short`
- 主流程是 premise → characters → outline → draft → critique/rewrite → final_story
- 没有分集规划、分集生成、连续性状态管理

所以现在系统不能稳定生成“第 1 集、第 2 集……连起来是一整个故事”的结果。

---

## 3. 设计原则

第一版只做够用、能跑、能持续扩展的方案。

原则：

1. 保留现有单篇模式，不直接删旧逻辑
2. 新增分集模式，不和单篇模式混在一起硬改
3. 每集独立落盘，避免中途失败全丢
4. 每集生成后做轻量检查
5. 前端优先支持“逐集可见”

---

## 4. 新模式

新增一个新格式：`episodic_series`。

请求语义改成两种：

- `single_story`：现有单篇模式
- `episodic_series`：新分集模式

分集模式默认参数：

- `episode_count = 12`
- `episode_min_words = 500`
- `episode_max_words = 800`
- `delivery_mode = stream_and_final`

第一版可以先把这些默认值写死或半写死，不要求前端一开始就全部可配置。

---

## 5. 新主流程

分集模式下，新流程如下：

### 5.1 Season Planning
先生成整季设定：

- 标题候选
- 整体 logline
- 主冲突
- 主要人物弧线
- 最终 payoff
- 全剧必须完成的关键节点

产物：`season_bible.json`

### 5.2 Episode Planning
基于整季设定，生成 12 集分集规划。

每集至少包含：

- 集数
- 本集标题
- 开场局面
- 本集核心冲突
- 本集必须发生的推进
- 本集结尾钩子
- 对下一集的铺垫

产物：`episode_plan.json`

### 5.3 Episode Generation Loop
按 1 → 12 串行生成。

每生成一集时，输入：

- `season_bible`
- 当前集的 `episode_plan`
- 上一集摘要
- 当前 `continuity_state`

输出：

- 当前集正文 markdown
- 当前集摘要
- continuity 更新

### 5.4 Episode QA
每集生成完成后做轻量检查：

- 字数是否在 500-800
- 是否承接上一集
- 是否有明确推进
- 是否有结尾钩子

如果失败：

- 优先只重试当前集 1 次
- 不重跑前面已经完成的集

### 5.5 Final Assembly
12 集全部完成后：

- 合并所有分集
- 输出 `final_story.md`
- 输出 `run_summary.md`

---

## 6. 核心数据结构

第一版只定义必要结构，不做过度设计。

### 6.1 SeasonBible
表示整部剧总设定。

建议字段：

- `title_candidate`
- `series_logline`
- `core_conflict`
- `target_episode_count`
- `final_payoff`
- `main_character_arcs`
- `must_land_beats`

### 6.2 EpisodePlanItem
表示单集规划。

建议字段：

- `episode_number`
- `title`
- `opening_situation`
- `core_conflict`
- `must_happen`
- `hook_ending`
- `sets_up_next`

### 6.3 ContinuityState
表示运行中的连续性状态。

建议字段：

- `current_episode`
- `story_so_far_summary`
- `character_states`
- `relationship_states`
- `open_threads`
- `resolved_threads`
- `last_episode_hook`

作用：

- 不用把前面所有正文每次都塞给模型
- 用结构化状态维持连续性

### 6.4 EpisodeArtifact
表示单集生成结果。

建议字段：

- `episode_number`
- `markdown`
- `word_count`
- `episode_summary`
- `hook_delivered`
- `qa_passed`

---

## 7. 目录结构

建议把 run 目录扩成下面这样：

```text
runs/<run_id>/
  request.json
  run_manifest.json
  events.jsonl
  season_bible.json
  episode_plan.json
  continuity_state.json
  episodes/
    episode_01.md
    episode_01.json
    episode_02.md
    episode_02.json
    ...
    episode_12.md
    episode_12.json
  final_story.md
  run_summary.md
```

这样做的好处：

- 每集单独可读
- 前端可逐集展示
- 某一集失败时更容易定位
- 后面支持“从第 N 集继续跑”也更自然

---

## 8. 后端模块调整

不建议继续把所有逻辑塞进现有单篇 orchestrator。

建议新增以下模块：

### 8.1 schema
新增：

- `src/dramaloop/schemas/season.py`
- `src/dramaloop/schemas/continuity.py`
- 视情况补充 `episode.py`

### 8.2 prompts
新增：

- `src/dramaloop/prompts/season.py`
- `src/dramaloop/prompts/episode_plan.py`
- `src/dramaloop/prompts/episode_draft.py`
- `src/dramaloop/prompts/episode_check.py`

### 8.3 harness
新增：

- `src/dramaloop/harness/episode_runner.py`
- `src/dramaloop/harness/episodic_orchestrator.py`

其中：

- 现有 `run_story_pipeline()` 继续服务单篇模式
- 新增 `run_episodic_pipeline()` 处理分集模式

---

## 9. API 设计

现有接口保留：

- `POST /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/stream`

这样前端接法不需要推翻重来。

### 9.1 请求字段
在现有请求上新增分集模式相关字段：

- `format`
- `episode_count`
- `episode_min_words`
- `episode_max_words`
- `delivery_mode`

第一版前端可以只暴露最少选项，甚至默认写死：

- `format = episodic_series`
- `episode_count = 12`
- `episode_min_words = 500`
- `episode_max_words = 800`
- `delivery_mode = stream_and_final`

### 9.2 详情响应
`WebRunDetail` 不能再只返回一个 `final_story`。

建议增加：

- `episodes`
- `completed_episode_count`
- `current_episode_number`
- `season_summary`
- `final_story`
- `available_artifacts`

其中 `episodes` 每项至少包含：

- `episode_number`
- `title`
- `status`
- `word_count`
- `hook_line`
- `content`

这样前端就能：

- 看到第几集完成了
- 点开看某一集正文
- 完成后再看合并版全文

---

## 10. SSE 事件设计

当前事件以 stage 为主，不够表达分集过程。

分集模式下建议增加：

### 10.1 整季规划事件
- `season_started`
- `season_completed`
- `episode_plan_ready`

### 10.2 分集事件
- `episode_started`
- `episode_completed`
- `episode_failed`
- `episode_artifact_ready`

### 10.3 收尾事件
- `final_assembly_started`
- `final_assembly_completed`

前端据此展示：

- 当前正在生成第几集
- 已完成多少集
- 哪一集已经可以看
- 完整版是否可读

---

## 11. 前端展示

第一版前端目标很明确：

### 11.1 实时区
显示：

- 当前 run 状态
- 当前生成到第几集
- 已完成集数 / 总集数
- 每集状态列表

### 11.2 分集阅读区
生成完一集就显示一集：

- 第 1 集完成后即可看
- 第 2 集完成后追加
- 一直到第 12 集

### 11.3 完整版阅读区
全部完成后展示：

- `final_story.md` 合并版

也就是：

- 过程里看分集
- 结束后看完整故事

---

## 12. 质量控制

第一版只做必要检查，不做复杂多轮评审。

### 12.1 规划检查
开始写第 1 集前，检查：

- 是否真的有 12 集计划
- 每集是否都有推进点
- 每集是否都有钩子
- 第 12 集是否有明确终局 payoff

如果不合格，先重做 `episode_plan`

### 12.2 单集检查
每集完成后检查：

- 500-800 字
- 和上一集是否能接上
- 是否有实质剧情推进
- 是否有结尾钩子

如不合格：

- 重试当前集 1 次

### 12.3 全季检查
全部完成后检查：

- 主线是否闭环
- 结尾是否回收主冲突
- 后半段是否明显失速

第一版全季检查先做轻量版即可，不通过时先记录问题，不强制自动全局返工。

---

## 13. 失败恢复

这是第一版就应该考虑的能力。

### 13.1 每集落盘
每生成完一集立刻写入：

- `episodes/episode_xx.md`
- `episodes/episode_xx.json`
- `continuity_state.json`

### 13.2 Manifest 记录进度
`run_manifest.json` 增加：

- 当前模式
- 总集数
- 已完成集数
- 当前第几集
- 最后失败在哪一集

### 13.3 续跑能力
后端结构上支持从失败集继续跑。

第一版可以先不做前端“继续生成”按钮，但后端目录和 manifest 设计要给这条路留口子。

---

## 14. MVP 范围

第一版只做这些：

1. 新增 `episodic_series` 模式
2. 默认 12 集
3. 每集 500-800 字
4. 先规划，再逐集串行生成
5. 每集生成后立即可展示
6. 最终输出 merged 完整版
7. 每集最基本 QA
8. 每集落盘

第一版不做：

1. 用户手改某一集后自动重写后续
2. 任意自由集数模板
3. 多季宇宙
4. 分支剧情
5. 复杂多轮单集 rewrite 系统

---

## 15. 实施建议

实际实现时，建议分 3 步：

### 第一步：后端打通
先完成：

- schema
- prompts
- episodic orchestrator
- run 产物落盘

目标：命令行或后端可完整跑出 12 集

### 第二步：Web 接口打通
再完成：

- `POST /api/runs` 支持新模式
- `GET /api/runs/{id}` 返回 episodes
- stream 支持 episode 级事件

目标：前端可以拿到分集数据

### 第三步：前端展示
最后完成：

- 分集列表
- 单集内容区
- 完整版内容区
- 进度显示

目标：用户能边看边等，并在结束后看到整部完整故事

---

## 16. 最终结论

本次采用的方案是：

- 新增 `episodic_series` 模式
- 默认 12 集短剧
- 每集 500-800 字
- 先整季规划，再逐集串行生成
- 前端边生成边展示分集
- 全部结束后输出完整合并版
- 第一版只做够用 MVP，不做复杂编辑与重算

这个方案比现有单篇流水线更符合短剧连续生成目标，也能为后续的“单集重生成”“人工改剧情再续写”保留扩展空间。
