# Dramaloop 前端 Demo 设计稿

日期：2026-07-09
状态：待用户 review

## 1. 设计背景

Dramaloop 当前是一个以 CLI 为主的短剧感短篇文本生成系统，核心价值在于：

- staged harness
- critique-rewrite loop
- 结构化 artifacts 持久化到 `runs/`
- 可解释的生成过程与评分过程

现阶段的问题不是生成核心不存在，而是缺少一个适合展示、演示和写入简历的产品化界面。

因此，前端第一阶段的目标不是把项目扩展成完整平台，而是把现有能力包装成一个**单页、可实时演示、可讲述系统价值的 Demo**。

---

## 2. 产品目标

前端第一版需要达成以下目标：

1. 让用户可以在页面中填写故事输入并发起一次生成
2. 让用户可以实时看到 run 的阶段推进和系统状态变化
3. 让用户可以在同一页面中看到最终成稿、评分摘要和 rewrite 信息
4. 让整个产品看起来像一个完整的 AI 写作系统，而不是命令行外壳
5. 让这个项目在简历、面试、现场演示中都更容易讲清楚

---

## 3. 第一版范围

### 3.1 In Scope

- 单页 Demo
- 前后端一体化接入当前 repo
- 前端提交一次生成请求
- 后端真实启动一条 run
- 实时流式更新 run 状态
- 页面展示：
  - 输入参数
  - 阶段进度
  - event stream
  - final story
  - score summary
  - rewrite focus
  - artifacts 简要入口

### 3.2 Out of Scope

- 多页路由产品
- 用户系统
- 多用户协作
- 历史 runs 管理后台
- 数据集 eval 后台
- 权限控制
- 云端部署体系
- WebSocket 双向交互控制台

第一版要强调的是：**能跑、能看、能讲**，而不是把所有产品能力一次做完。

---

## 4. 方向选择结论

### 4.1 产品形态

采用：**单页 Demo**

原因：
- 最适合 MVP 展示
- 路径最短
- 最容易把“输入 -> 运行 -> 实时反馈 -> 结果”压缩在一个心智模型内
- 更适合现场演示和简历讲述

### 4.2 系统接入方式

采用：**前后端一体，直接在当前 repo 内增加 Web 层**

原因：
- 最大化复用当前 Python pipeline
- 不需要先拆独立后端服务
- 可以保留当前 repo 的 staged harness、artifact persistence 和 run 目录结构

### 4.3 实时更新方式

采用：**SSE 优先的真实流式更新**

原因：
- 当前需求主要是后端单向推送 run 状态
- SSE 比 WebSocket 更轻量、更贴近第一版需求
- 更容易实现、更容易调试、更适合展示型产品

### 4.4 视觉方向

采用：**B 的信息架构 + A 的配色与气质**

即：
- 结构上采用“生成控制台 / Agent 控制室”
- 视觉上采用“编辑部 / 文学工作台”的暖色与内容产品感

最终设计关键词：

- 系统控制台的结构
- 内容工作台的气质
- 有实时感，但不冷
- 有产品感，但不后台
- 有文本可读性，但不做成纯阅读器

---

## 5. 页面结构设计

页面采用**左侧输入 + 右侧运行与结果**的单页结构。

### 5.1 左侧：输入控制区

职责：
- 填写 run 的输入参数
- 发起生成
- 显示本次 run 的基础配置

建议字段：
- `idea`
- `style tags`
- `audience`
- `constraints`
- `max_iterations`（可选，第一版可默认隐藏或折叠）

交互要求：
- 输入区固定宽度，避免 run 开始后布局抖动
- CTA 清晰明确，例如 `Launch Run`
- 表单风格像创作配置面板，而不是纯后台设置页

设计要求：
- 使用暖色底 + 清晰描边
- 让用户觉得这是一个“创作发起区”
- 表单长度控制在单屏可见范围内

### 5.2 右上：实时运行区

职责：
- 展示系统正在经历哪些阶段
- 告诉用户当前跑到哪里
- 强化 staged harness 的系统感

建议模块：
- 当前 run 状态
- stage timeline
- event stream
- 当前 iteration
- 当前 rewrite target
- critique 生成后的即时摘要

阶段展示建议：
- `premise_refinement`
- `character_card_generation`
- `story_outline_generation`
- `draft_generation`
- `critique_scoring`
- `targeted_rewrite`
- `final_assembly`

设计要求：
- 状态区必须一眼能扫
- 当前阶段高亮
- 已完成阶段弱高亮
- 未开始阶段低对比显示
- event stream 要有持续更新感，但不能像控制台日志一样压倒内容

### 5.3 右下：结果展示区

职责：
- 展示最终成稿
- 展示评分信息
- 展示系统不是黑盒的证据

建议拆分：

#### 主列：Final Story
- 展示最终中文短篇正文
- 是页面的内容主角
- 需要稳定的长文本排版
- 使用适合阅读的字体、行高、段间距
- 容器固定高度，内部滚动

#### 侧列：Summary / Artifacts
- overall score
- weakest dimensions
- rewrite focus
- artifacts 列表
  - `run_summary.md`
  - `rewrite_plan_v1.json`
  - `events.jsonl`

设计要求：
- 主列强调“成品感”
- 侧栏强调“系统解释性”
- 两者共同构成“既有内容价值，也有工程价值”的产品叙事

---

## 6. 视觉与交互设计

### 6.1 视觉基调

整体基调：
- 暖米色 / 浅纸感背景
- 深棕或深墨色文字
- 卡片边框明确，但不厚重
- 少量状态色用于表达运行状态

避免：
- 纯深色工程后台感
- 紫色渐变模板感
- 过度营销化 hero 视觉
- 卡片套卡片的堆叠感

### 6.2 页面气质

希望用户第一眼感受到：
- 这是一个在“写东西”的产品
- 但它不是简单文本框，而是一个有 agent flow 的生成系统

因此要保持两个平衡：

1. **系统感**
   - timeline
   - status chip
   - streaming event feed
   - score block

2. **内容感**
   - final story 阅读舒适
   - 暖色调
   - 文本区留白更克制
   - 不做冷冰冰 log viewer

### 6.3 记忆点

首版界面的记忆点不是炫技动画，而是：

> “你能一边看到系统跑 stages，一边看到它最后写出一篇短剧感中文短篇。”

这是 Dramaloop 与普通 prompt demo 的最大区别。

---

## 7. 系统架构设计

### 7.1 架构原则

前端接入不能破坏现有 CLI-first 架构，而应该在其上增加一层 Web 访问能力。

### 7.2 分层

#### A. Generation Core（保留现有）
继续复用：
- `run_story_pipeline(...)`
- `runs/` artifact persistence
- critique/rewrite loop
- existing schemas
- prompt builders
- artifact writers

#### B. Web Service Layer（新增）
新增轻量服务层，职责：
- 接收前端请求
- 校验输入
- 启动异步 run
- 暴露 run 查询接口
- 暴露 SSE 流式接口
- 将运行状态转换为前端可消费的事件格式

#### C. Frontend SPA（新增）
职责：
- 提交 run
- 订阅 SSE
- 渲染状态与结果
- 管理单页状态

---

## 8. 后端接口设计

### 8.1 创建 run

`POST /api/runs`

请求体建议：

```json
{
  "idea": "被未婚夫当众退婚后，她转身嫁给了他的死对头",
  "style": ["都市情感", "逆袭", "狗血短剧感"],
  "audience": "女性向短剧用户",
  "constraints": ["节奏快", "结尾有回报"],
  "max_iterations": 2
}
```

返回体建议：

```json
{
  "run_id": "20260709-frontend-demo-story",
  "status": "running",
  "stream_url": "/api/runs/20260709-frontend-demo-story/stream"
}
```

### 8.2 订阅 run 事件流

`GET /api/runs/{run_id}/stream`

用途：
- 通过 SSE 推送 run 生命周期事件
- 前端据此实时更新页面

建议事件类型：
- `run_created`
- `stage_started`
- `stage_completed`
- `artifact_ready`
- `critique_ready`
- `run_completed`
- `run_failed`

SSE 数据体建议统一包含：
- `run_id`
- `event`
- `stage`
- `iteration`
- `artifact`
- `detail`
- `ts`

### 8.3 查询 run 详情

`GET /api/runs/{run_id}`

返回建议包含：
- request
- manifest
- current status
- stages summary
- critique summary
- rewrite summary
- final story
- available artifacts

### 8.4 读取 artifact（可选）

`GET /api/runs/{run_id}/artifacts/{artifact_name}`

第一版如果 `GET /api/runs/{run_id}` 已经返回足够信息，则该接口可后置。

---

## 9. 实时数据流设计

### 9.1 运行主路径

前端交互流：

1. 用户填写表单
2. 点击 `Launch Run`
3. 前端调用 `POST /api/runs`
4. 后端返回 `run_id`
5. 前端立即建立 SSE 连接
6. 页面根据事件流更新阶段状态、event feed、评分摘要和最终成稿
7. run 完成后，页面进入 completed 状态

### 9.2 前端状态管理

前端至少维护以下状态：
- form state
- run request state
- run status state
- stage progress state
- event stream list
- score summary
- final story content
- error state
- reconnect state

### 9.3 SSE 的恢复策略

如果 SSE 中断：
- 页面显示 `stream disconnected, reconnecting...`
- 自动重连
- 重连成功后调用 `GET /api/runs/{run_id}` 补齐当前状态

---

## 10. 错误处理设计

### 10.1 运行失败

可能来源：
- provider 配置错误
- API key 缺失或失效
- structured output 解析失败
- pipeline 某 stage 报错

页面表现：
- 顶部状态切换为 failed
- event stream 显示失败阶段
- 保留已有结果，不清空页面
- 给出简洁错误说明

### 10.2 流中断

页面表现：
- 状态区提示断连
- 自动重连
- 如果最终失败，允许用户手动刷新 run 详情

### 10.3 长文本或大内容渲染问题

页面要求：
- final story 区域固定高度
- 内部滚动
- 左侧输入区与上方状态区高度稳定
- 页面在长文本下不整体抖动

---

## 11. 技术选型建议

### 11.1 前端

建议：**React + Vite + TypeScript**

原因：
- 单页 Demo 起步快
- SSE 接入简单
- 组件化管理方便
- 后续扩展历史 runs 或更多视图也顺手

### 11.2 后端

建议：**FastAPI 风格的轻 Web 层**

原因：
- 与当前 Python 项目自然结合
- 易于暴露 REST + SSE
- 适合把现有 pipeline 包装成 Web 服务

### 11.3 与 CLI 的关系

CLI 不废弃。

Web 层和 CLI 共享同一个 generation core，区别只是：
- CLI 直接执行 pipeline
- Web 层通过 API 与异步任务调度去调用 pipeline

这样可以保证：
- showcase 用 Web
- 开发与回归仍可继续用 CLI

---

## 12. 测试策略

### 12.1 后端测试

应覆盖：
- 创建 run API
- run 详情 API
- SSE 事件格式
- 异常时的错误状态返回

### 12.2 前端测试

应覆盖：
- 表单提交
- running 状态切换
- 阶段时间线更新
- critique/score 信息展示
- final story 渲染
- SSE 中断重连提示

### 12.3 E2E 测试

最少保留一条关键路径：
- 输入 revenge case
- 点击生成
- 看见阶段推进
- 最终看见 final story 与 summary

---

## 13. 为什么这版设计适合简历与展示

这版前端不是纯 UI 补丁，而是把 Dramaloop 从“命令行生成器”提升为“可被讲述的 AI 产品系统”。

它可以自然支持以下叙述：

- 我做了一个短剧文本生成系统
- 它不是一次性 prompt，而是 staged harness
- 它有 critique-rewrite loop
- 它有结构化 artifacts
- 它支持实时流式展示运行过程
- 它有可演示的前端产品形态

这会显著提升项目的完成度和简历表现力。

---

## 14. 后续扩展方向（不纳入首版）

后续可扩展但不在当前 MVP 内：
- 历史 runs 列表
- run 对比视图
- eval dataset 页面
- prompt 配置面板
- artifacts diff 视图
- rerun / fork run
- 多模板输入模式

---

## 15. 结论

前端第一版的最终设计结论是：

> 在当前 repo 内新增一体化 Web 层，构建一个单页、SSE 实时更新的 Dramaloop Demo；页面采用“控制台结构 + 编辑部配色”的视觉方向，在同一界面中同时呈现输入、系统运行过程、评分与最终故事成稿。

这是当前最适合 Dramaloop 的第一阶段产品化方向。