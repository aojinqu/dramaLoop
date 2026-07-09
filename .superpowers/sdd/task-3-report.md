# Task 3 Report

## 实现了什么
- 在 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/storage/runs.py` 新增 `plan_run_id(runs_dir, idea, started_at)`，用于基于现有 `build_run_id` + `reserve_run_id` 预分配 run_id。
- 新建 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/runtime.py`：
  - `launch_run(store, request, settings)` 负责预分配 run_id、写入内存 store、后台启动真实 `run_story_pipeline`。
  - `stream_run_events(run_id, settings, store)` 负责轮询并 tail `events.jsonl`，将事件以 SSE 形式输出，并在发现 artifact 时额外发出 `artifact_ready` 事件；run 进入终态时发出 `run_completed` 或 `run_failed`。
- 修改 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py`：
  - `POST /api/runs` 改为异步调用真实后台 runtime，并返回带 `stream_url` 的 202 响应。
  - 新增 `GET /api/runs/{run_id}/stream`，通过 `StreamingResponse` 暴露 `text/event-stream`。
  - 对不存在的 `run_id` 在 stream 路由上直接返回 404，避免悬挂 SSE 连接。
- 修改 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/harness/orchestrator.py`：
  - `run_story_pipeline(...)` 新增可选参数 `run_id`，允许 web runtime 将预分配的 authoritative run_id 传入，避免后台再次重算 ID 导致 URL 与真实执行目录不一致。
- 新增 `/Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py`，验证真实后台 pipeline + SSE 可看到 `stage_started`、`stage_completed`、`artifact_ready`、`run_completed`。
- 扩展 `/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py`，补充 run_id 由 store 最终分配值返回的行为约束。

## 跑了哪些测试与结果
1. RED:
   - `uv run pytest /Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py::test_stream_endpoint_emits_stage_and_completion_events -v`
   - 结果：FAIL，返回内容为 `{"detail":"Not Found"}`，证明当时 stream endpoint 未实现。
2. RED:
   - `uv run pytest /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py::test_create_run_returns_store_assigned_run_id_when_background_is_not_running -v`
   - 结果：FAIL，第二次请求仍返回 `20260709-123456-story` 而不是 `20260709-123456-story-2`，证明返回给客户端的 run_id 不是 store 最终分配值。
3. GREEN:
   - `uv run pytest /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py::test_create_run_returns_store_assigned_run_id_when_background_is_not_running -v`
   - 结果：PASS。
4. GREEN:
   - `uv run pytest /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_app.py /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py /Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py -v`
   - 结果：全部 PASS，共 7 个测试通过。

## RED/GREEN 证据
- RED 证据 1：
  - 失败测试：`tests/integration/test_web_stream.py::test_stream_endpoint_emits_stage_and_completion_events`
  - 关键失败信息：`assert 'event: stage_started' in '{"detail":"Not Found"}'`
- RED 证据 2：
  - 失败测试：`tests/unit/test_web_runs_api.py::test_create_run_returns_store_assigned_run_id_when_background_is_not_running`
  - 关键失败信息：`assert '20260709-123456-story' == '20260709-123456-story-2'`
- GREEN 证据：
  - `tests/unit/test_web_app.py tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py` 全部通过。

## 改动文件清单
- 修改：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/storage/runs.py`
- 修改：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/harness/orchestrator.py`
- 新建：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/runtime.py`
- 修改：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py`
- 修改：`/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py`
- 新建：`/Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py`

## 自检与任何疑虑
- 已按 brief 范围实现后台真实 pipeline + SSE stream，没有扩展到前端代码。
- 为解决 code review 发现的高优先级问题，额外做了两个最小修正：
  1. web runtime 返回并复用 store 最终分配的 run_id，避免预分配 ID 与后台真实 run_id 漂移。
  2. stream endpoint 对未知 run_id 返回 404，避免无限悬挂连接。
- `/api/runs/{run_id}` 详情接口目前仍主要返回内存快照，不会随着 SSE 事件逐步更新 stage 列表；但 brief 本任务只要求后台启动真实 pipeline、SSE stream endpoint、tail events.jsonl，因此未继续扩展该接口逻辑。
- 测试输出仍有已有依赖警告：`StarletteDeprecationWarning`（`httpx` 与 `starlette.testclient`）。这不是本任务引入，也未影响通过结果。
