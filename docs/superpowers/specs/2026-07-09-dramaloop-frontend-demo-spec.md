# Dramaloop 前端 Demo 规格说明

日期：2026-07-09
状态：已确认，进入实现计划

## 1. 项目目标

在当前 Dramaloop 仓库内新增一个前后端一体化的 Web Demo，把现有 CLI-first 的短剧文本生成系统升级为一个可实时演示、可写入简历、可清晰讲述系统价值的产品化界面。

这个前端第一版的核心目标不是做完整平台，而是把现有能力包装成一个单页、可流式观察、可展示最终产物的 AI 写作系统 Demo。

## 2. 产品定位

Dramaloop 前端第一版定位为：

> 一个单页、SSE 实时更新的 AI 短剧文本生成控制台。

它既要体现 staged harness 的系统感，也要体现最终中文短篇文本的内容感。

## 3. 首版范围

### 3.1 In Scope

- 单页 Demo
- 前后端一体化接入当前 repo
- 页面发起真实生成 run
- 实时流式展示 run 生命周期
- 展示输入参数、阶段进度、事件流、评分摘要、rewrite focus、最终故事正文
- 提供 artifacts 的基础展示入口

### 3.2 Out of Scope

- 多页路由产品结构
- 多用户系统
- 历史 runs 后台
- 数据集 eval 管理台
- WebSocket 双向控制台
- 云端部署与权限系统

## 4. 方向选择结论

### 4.1 交互形态
- 选择：单页 Demo

### 4.2 接入方式
- 选择：前后端一体，直接在当前 repo 内增加 Web 层

### 4.3 实时通信
- 选择：SSE 优先的真实流式更新

### 4.4 视觉方向
- 选择：B 的信息架构 + A 的配色与气质
- 结论：采用“系统控制台的结构，内容工作台的气质”

## 5. 页面结构

页面采用左侧输入、右侧运行与结果的单页结构。

### 5.1 左侧输入控制区

负责：
- 填写 `idea`
- 填写 `style tags`
- 填写 `audience`
- 填写 `constraints`
- 发起生成

要求：
- 固定宽度
- CTA 清晰
- 视觉上更像创作配置面板，而非后台表单

### 5.2 右上实时运行区

负责：
- 展示当前 run 状态
- 展示 stage timeline
- 展示 event stream
- 展示当前 iteration 和 rewrite target
- 展示 critique 产出后的评分摘要

要求：
- 当前阶段必须清晰高亮
- 状态更新必须具备明显实时感
- event stream 不能压倒内容区

### 5.3 右下结果展示区

分为两部分：

#### 主列：Final Story
- 展示最终中文短篇正文
- 容器固定高度，内部滚动
- 长文本排版优先，保证可读性

#### 侧列：Summary / Artifacts
- overall score
- weakest dimensions
- rewrite focus
- artifacts：
  - `run_summary.md`
  - `rewrite_plan_v1.json`
  - `events.jsonl`

## 6. 视觉与交互要求

### 6.1 视觉基调
- 暖米色 / 纸感背景
- 深棕或深墨色文字
- 有清晰边框和模块层级
- 用少量状态色表达运行状态

### 6.2 避免事项
- 不要做成纯深色工程后台
- 不要做成 landing page
- 不要做成日志查看器
- 不要使用模板化紫色渐变和装饰性空 UI

### 6.3 产品记忆点

用户应能感知到：

> 一边看到系统分阶段运行，一边看到它最终写出一篇短剧感中文短篇。

## 7. 系统架构

### 7.1 保留现有 Generation Core
继续复用：
- `run_story_pipeline(...)`
- `runs/` artifact persistence
- critique-rewrite loop
- existing schemas
- prompt builders
- artifact writers

### 7.2 新增 Web Service Layer
职责：
- 接收前端请求
- 校验输入
- 启动异步 run
- 提供 run 查询接口
- 提供 SSE 事件流接口
- 将运行状态映射为前端事件

### 7.3 新增 Frontend SPA
职责：
- 提交 run
- 订阅 SSE
- 渲染页面状态与结果
- 处理重连与错误提示

## 8. API 设计

### 8.1 创建 run
`POST /api/runs`

请求体：
- `idea: string`
- `style: string[]`
- `audience: string | null`
- `constraints: string[]`
- `max_iterations: number`

返回：
- `run_id: string`
- `status: "running"`
- `stream_url: string`

### 8.2 订阅事件流
`GET /api/runs/{run_id}/stream`

事件类型建议：
- `run_created`
- `stage_started`
- `stage_completed`
- `artifact_ready`
- `critique_ready`
- `run_completed`
- `run_failed`

统一字段建议：
- `run_id`
- `event`
- `stage`
- `iteration`
- `artifact`
- `detail`
- `ts`

### 8.3 查询 run 详情
`GET /api/runs/{run_id}`

返回建议：
- request
- manifest
- current status
- stages summary
- critique summary
- rewrite summary
- final story
- available artifacts

## 9. 实时数据流

### 9.1 前端主路径
1. 用户填写表单
2. 用户点击 `Launch Run`
3. 前端请求 `POST /api/runs`
4. 后端返回 `run_id`
5. 前端连接 SSE
6. 页面按事件流更新 timeline、event feed、summary 和 final story
7. run 完成后进入 completed 状态

### 9.2 SSE 断开恢复
- 页面显示断连提示
- 自动重连
- 重连成功后请求 `GET /api/runs/{run_id}` 补齐状态

## 10. 错误处理

### 10.1 运行失败
来源包括：
- provider 配置错误
- key 缺失
- structured output 解析失败
- pipeline stage 报错

前端表现：
- 状态置为 failed
- event stream 标出失败阶段
- 保留已有产物
- 给出简短错误说明

### 10.2 长文本处理
- final story 容器固定高度
- 内部滚动
- 不能让左侧输入和上方运行区抖动

## 11. 技术选型

### 11.1 前端
建议：React + Vite + TypeScript

原因：
- 单页 Demo 起步快
- SSE 接入简单
- 后续扩展方便

### 11.2 后端
建议：FastAPI 风格轻 Web 层

原因：
- 与当前 Python 项目自然结合
- 适合 REST + SSE
- 易于复用现有 pipeline

## 12. 测试要求

### 12.1 后端测试
覆盖：
- 创建 run API
- run 详情 API
- SSE 事件格式
- 异常状态返回

### 12.2 前端测试
覆盖：
- 表单提交
- running 状态切换
- timeline 更新
- score / rewrite 信息展示
- final story 渲染
- SSE 重连提示

### 12.3 E2E
至少覆盖：
- 输入 revenge case
- 发起生成
- 看到阶段推进
- 看到 final story 和 summary

## 13. 实现要求

后续开发必须遵守以下约束：

1. 实现前先写 **spec** 和 **plan**
2. spec 与 plan 都使用 **中文**
3. spec 与 plan 都写入仓库并持久化保存
4. 开发优先复用当前 generation core，不做无关重构

## 14. 结论

前端第一版的最终方向是：

> 在当前 repo 内新增一体化 Web 层，构建一个单页、SSE 实时更新的 Dramaloop Demo；页面采用“控制台结构 + 编辑部配色”的视觉方向，在同一界面中同时呈现输入、系统运行过程、评分与最终故事成稿。