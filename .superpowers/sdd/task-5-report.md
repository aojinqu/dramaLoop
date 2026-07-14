# Task 5 报告：接通 API 与 SSE，渲染实时状态、故事结果，并补充运行文档

## 目标

基于已确认的中文 spec / plan，完成 Dramaloop Web Demo 的 Task 5：

- 接通前端与后端 API
- 接通 SSE 事件流
- 在单页 Demo 中渲染实时运行状态
- 在 run 完成后渲染最终故事、评分摘要与 artifacts
- 补充 README 中的 Web Demo 运行文档

本次实现严格保持既有约束：
- 不改总体架构
- 不偏离单页 Demo
- 不改 SSE 优先方向
- 不重构 generation core

## TDD 过程

### RED
先按计划把“提交 -> 收到流 -> 渲染故事”的主路径测试写入：
- `frontend/src/__tests__/App.test.tsx`

新增测试约束：
- 点击 `Launch Run` 后必须调用 `createRun`
- 必须通过 `connectRunStream` 接收流事件
- 收到 `run_completed` 后必须拉取 `fetchRunDetail`
- 页面必须渲染最终故事正文
- 页面必须渲染 `rewrite_focus`

首先运行：

```bash
npm --prefix frontend test -- --run App.test.tsx
```

结果：FAIL。

失败原因符合预期：
- `frontend/src/api.ts` 尚不存在
- 测试文件无法解析 `../api`

这说明 RED 阶段确实钉住了“API / SSE 尚未接通”的真实缺口。

### GREEN
随后补齐最小实现：
- 新建 `frontend/src/api.ts`
- 更新 `frontend/src/App.tsx`
- 更新 `frontend/src/components/RunForm.tsx`
- 更新 `frontend/src/components/RunTimeline.tsx`
- 更新 `frontend/src/components/EventFeed.tsx`
- 更新 `frontend/src/components/ResultPanel.tsx`
- 更新 `frontend/src/types.ts`

第一次 GREEN 验证时，测试虽然功能通过，但出现：
- 未处理的异步 rejection
- 测试输出不干净

原因：
- 旧的“表单提交不会整页刷新”测试直接渲染 `App`，会误触发异步 `handleLaunch`

处理：
- 把该测试下沉到 `RunForm` 组件级别
- 改为验证 `fireEvent.submit(form)` 返回 `false`，从而证明 `preventDefault()` 已生效

随后再次运行：

```bash
npm --prefix frontend test -- --run App.test.tsx
```

结果：PASS，且输出干净。

## 实际改动

### 1. 前端 API 客户端：`frontend/src/api.ts`
新增最小 API / SSE 客户端：
- `createRun(input)`：提交 `POST /api/runs`
- `fetchRunDetail(runId)`：拉取 `GET /api/runs/{run_id}`
- `connectRunStream(runId, handlers)`：连接 `GET /api/runs/{run_id}/stream`

实现特点：
- 使用浏览器原生 `fetch`
- 使用原生 `EventSource`
- 对 `stage_started` / `stage_completed` / `artifact_ready` / `run_completed` / `run_failed` 做统一监听
- 保持最小实现，不引入额外状态管理库

### 2. 前端类型：`frontend/src/types.ts`
补齐前端运行时需要的类型：
- `RunFormInput`
- `WebRunCreated`
- `StreamMessage`
- 原有 `WebRunDetail` / `WebStageSnapshot`

让前端表单、API 客户端、SSE 事件与页面状态之间的契约一致。

### 3. RunForm：`frontend/src/components/RunForm.tsx`
将静态表单改为受控表单：
- 本地维护 `idea` / `style` / `audience` / `constraints`
- 提交时把逗号分隔字符串转换为数组
- 固定传递 `max_iterations: 2`
- 保持 `preventDefault()`，继续确保 SPA 交互

### 4. App 总控状态：`frontend/src/App.tsx`
把静态壳子升级为真正的单页运行页：
- 管理 `runId`
- 管理 `detail`
- 管理 `events`
- 管理 `streamState`
- 在提交后创建 run 并建立 SSE 连接
- 在收到 `stage_started` / `stage_completed` 时实时更新 timeline
- 在收到 `artifact_ready` 时实时更新 artifact 列表
- 在收到 `run_completed` / `run_failed` 时拉取最终详情
- 在 SSE 出错时进入 `reconnecting`，并通过 `fetchRunDetail` 做补偿刷新

这保证了页面不仅能在完成后展示结果，也能在流式过程中逐步更新。

### 5. RunTimeline：`frontend/src/components/RunTimeline.tsx`
将静态占位 timeline 改为数据驱动：
- 接收 `detail`
- 接收 `streamState`
- 默认仍保留 fallback stages，保证首屏壳子稳定
- 在流式过程中显示每个 stage 的 `pending/running/completed/failed`
- 当前 running stage 继续高亮

### 6. EventFeed：`frontend/src/components/EventFeed.tsx`
将静态事件列表改为数据驱动：
- 接收 `events`
- 优先展示真实流式事件
- 未开始前仍保留占位事件
- 对 `stage` / `artifact` 做轻量格式化，保持可读性

### 7. ResultPanel：`frontend/src/components/ResultPanel.tsx`
将静态结果面板改为“占位 + 真实结果”双模式：
- 接收 `detail`
- 接收 `runId`
- run 完成后渲染真实 `final_story`
- 渲染 `overall_score`
- 渲染 `rewrite_focus`
- 渲染 `available_artifacts`
- 在无真实结果前仍保留占位内容，保证首屏不会空掉

### 8. FastAPI 静态托管：`src/dramaloop/web/app.py`
在前端产物存在时由 FastAPI 托管静态页面：
- 如果 `frontend/dist/assets` 存在，则挂载 `/assets`
- 提供 `/` 返回 `frontend/dist/index.html`

这样支持：
- 本地前后端分离开发
- 前端 build 后由 FastAPI 直接托管 Demo 页面

### 9. README 文档：`README.md`
新增 Web Demo 章节，补充：
- 本地开发方式（后端 / 前端分别启动）
- 前端构建后由 FastAPI 托管的方式
- 基本体验路径说明

## review 后补充修正

在 Task 5 task-scoped review 过程中，又识别并修复了一个真实问题：

- 当用户已经发起真实 run，但 run 还未完成时，结果区仍会继续显示 Task 4 的占位故事和占位分数
- 这会误导用户把占位内容误认成当前 run 的真实成稿

处理方式：
- 为该场景新增失败测试：`does not show placeholder story while a real run is still running`
- 将 `ResultPanel` 改为三态展示：
  - 未发起 run：显示占位内容
  - 已发起 run 但未完成：显示 `Waiting for final story...` / `Waiting for run summary...`
  - run 完成：显示真实故事、真实分数与真实 rewrite focus

修正后重新验证：
- `frontend/src/__tests__/App.test.tsx`：4 tests passed
- 后端测试、前端全量测试、前端构建再次全部通过

## 测试命令与结果

### 1. RED 验证
```bash
npm --prefix frontend test -- --run App.test.tsx
```
结果：FAIL，报错 `Failed to resolve import "../api"`，因为 `frontend/src/api.ts` 尚不存在。

### 2. GREEN 主路径验证
```bash
npm --prefix frontend test -- --run App.test.tsx
```
结果：PASS，3 个测试通过，输出干净。

覆盖点包括：
- 单页壳子仍存在
- `RunForm` 提交不会触发原生导航
- 提交 run 后会渲染流式结果与最终故事

### 3. review 驱动的回归验证
```bash
npm --prefix frontend test -- --run App.test.tsx
```
结果：PASS，4 个测试通过。

新增覆盖点：
- 发起真实 run 后，在结果尚未完成前不会显示占位成稿与占位分数

### 4. Task 5 完整验证
```bash
uv sync --extra dev
uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py -v
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
结果：全部 PASS。

明细：
- 后端测试：13 passed
- 前端测试：4 passed
- 前端构建：PASS

补充说明：
- `pytest` 输出 1 条来自 `starlette.testclient` 的 deprecation warning
- 这不是本次改动引入的问题，也未阻塞验证

## 与计划对照

本次实现与 Task 5 计划一致：

- `frontend/src/api.ts`：已新增
- `frontend/src/App.tsx`：已接通 API 与 SSE 状态管理
- `frontend/src/components/RunForm.tsx`：已接入真实提交
- `frontend/src/components/RunTimeline.tsx`：已实时渲染状态
- `frontend/src/components/EventFeed.tsx`：已实时渲染事件流
- `frontend/src/components/ResultPanel.tsx`：已渲染故事、评分与 artifacts
- `src/dramaloop/web/app.py`：已补充前端静态托管
- `README.md`：已补充 Web Demo 运行说明
- `frontend/src/__tests__/App.test.tsx`：已扩展主路径测试

## 风险 / 后续

1. 当前前端仍是单页 Demo，不含历史 runs 与多页结构。
   - 这是符合 spec / plan 的。

2. SSE 出错后的恢复策略目前是：
   - UI 进入 `reconnecting`
   - 尝试 `fetchRunDetail` 补偿刷新
   - 若失败则转为 `failed`
   - 这符合首版 Demo 对“自动重连 + 状态补齐”的最小要求，但还不是更完整的长连接恢复机制。

3. ResultPanel 现在按“未发起 / 运行中 / 已完成”分态展示。
   - 这样避免了占位成稿误导，但仍保持了 Demo 首屏的完整度。

## 结论

Task 5 已完成并通过验证：

- 前端已接通 API 与 SSE
- 页面已能实时显示运行状态和事件流
- 页面已能渲染最终故事、评分摘要与 artifacts
- 运行中不再显示误导性的占位成稿与占位分数
- FastAPI 已支持托管前端构建产物
- README 已补充 Web Demo 运行方式
- 后端测试、前端测试、前端构建全部通过
