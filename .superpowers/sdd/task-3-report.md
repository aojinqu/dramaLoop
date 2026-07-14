# Task 3 报告：把真实 pipeline 接到后台执行，并用 SSE 暴露事件流

## 目标

基于当前工作树已有未提交改动，完成并验证 Task 3：

- Web 层创建 run 时预分配 `run_id`
- 后台启动真实 `run_story_pipeline(...)`
- 保持一体化 Web 层与 SSE 桥接，复用现有 generation core
- 提供 `GET /api/runs/{run_id}/stream`，向前端暴露真实事件流
- 运行与 Task 3 相关的后端测试并修复到通过

## 实际改动

### 1. `/Users/bytedance/coderepo/brainWrite/src/dramaloop/storage/runs.py`
- 新增 `plan_run_id(runs_dir, idea, started_at)`。
- 复用现有 `build_run_id(...)` 与 `reserve_run_id(...)`，让 Web 层能在后台任务真正创建目录之前先规划可用 `run_id`。

### 2. `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/runtime.py`
- 新增 `launch_run(store, request, settings)`：
  - 预分配 `run_id`
  - 把 run 注册到内存 store
  - 构造 `StoryRequest`
  - 通过 `asyncio.create_task(...)` + `asyncio.to_thread(...)` 启动真实 `run_story_pipeline(...)`
- 新增 `stream_run_events(run_id, settings, store)`：
  - 轮询并 tail `events.jsonl`
  - 将落盘事件转成 SSE 输出
  - 检测到 artifact 时附加发出 `artifact_ready`
  - 检测到 manifest 终态时发出 `run_completed` 或 `run_failed`
  - 在结束前把最终 `status` 同步回 store

### 3. `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py`
- `POST /api/runs` 改为异步调用 `launch_run(...)`，返回 202 与 `stream_url`。
- 新增 `GET /api/runs/{run_id}/stream`，用 `StreamingResponse(..., media_type="text/event-stream")` 暴露 SSE。
- `GET /api/runs/{run_id}` 与 stream 路由都会先做磁盘态 hydration，不再要求 run 必须仍存在于内存 store 中。
- 因此在服务重启后，只要 `runs/<run_id>/` 下仍有 `request.json` / `events.jsonl` / `run_manifest.json`，详情查询与 SSE 订阅仍可恢复。

### 4. `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/store.py`
- 维持轻量内存注册表角色。
- `create(...)` 在内存侧对 run_id 做去重，确保同秒多次创建时也能返回唯一 id。
- `get(...)` / `replace(...)` 通过深拷贝隔离返回值与内部状态，避免 hydration 过程把半成品状态泄漏回共享内存对象。
- 这与磁盘侧 `plan_run_id(...)` 形成兜底，避免客户端拿到与最终 store 不一致的 id。

### 5. `/Users/bytedance/coderepo/brainWrite/src/dramaloop/harness/orchestrator.py`
- `run_story_pipeline(...)` 新增可选参数 `run_id`。
- Web runtime 可以把预分配的 authoritative run_id 传入，避免后台再次重算 id 导致 URL 与真实执行目录漂移。
- pipeline 在执行过程中会把阶段开始、完成、产物写入 `events.jsonl`，并在结束时写回 `run_manifest.json`，作为 SSE bridge 的真实事件来源。

### 6. `/Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py`
- 集成测试验证：
  - `POST /api/runs` 创建真实 run
  - `GET /api/runs/{run_id}/stream` 能收到真实事件流
  - SSE 文本中包含 `stage_started`、`stage_completed`、`artifact_ready`、`run_completed`

### 7. `/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py`
- 覆盖创建 run、详情读取、默认 `length=short`、同秒唯一 run id 等行为。
- 增加“后台任务未真正执行时，也必须返回 store 最终分配 run_id”的测试约束。
- 新增服务重启/丢失 store 会员关系后的磁盘恢复测试，验证 `GET /api/runs/{run_id}` 与 `/stream` 都能直接从 `runs/<run_id>/` 恢复。
- 新增 SSE 终态收尾测试，验证 manifest 先进入终态时，stream 仍会 drain 完尾部事件再发出 `run_completed`。

## 测试命令与结果

### 1. Task 3 相关后端测试
命令：

```bash
uv run pytest /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_app.py /Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py /Users/bytedance/coderepo/brainWrite/tests/integration/test_web_stream.py -v
```

结果：
- 13 个测试全部通过。
- 覆盖点包括：
  - health endpoint
  - web CLI 启动工厂
  - 创建 run API
  - run 详情 API
  - 默认 `length=short`
  - 同秒 run_id 去重
  - 后台初始化失败时的 failed persistence
  - partial JSON 写入容错
  - 服务重启后的磁盘恢复查询
  - 服务重启后的磁盘恢复 SSE
  - SSE 终态前 drain 尾部事件
  - SSE 真实事件流输出

测试摘要：
- `tests/unit/test_web_app.py`：PASS
- `tests/unit/test_web_runs_api.py`：PASS
- `tests/integration/test_web_stream.py`：PASS

备注：测试中存在已有 `StarletteDeprecationWarning`，但不影响 Task 3 功能通过。

## 与计划差异

整体方向与计划一致，主要差异如下：

1. `run_story_pipeline(...)` 除计划中的后台接线外，实际补充了 `run_id` 参数。
   - 这是为了让 Web 层预分配的 `run_id` 与最终真实 run 目录保持一致。
   - 属于 Task 3 落地所需的最小接口补强。

2. `WebRunStore.create(...)` 额外做了内存态唯一性兜底。
   - 计划主要强调磁盘侧 `reserve_run_id(...)`。
   - 实际实现中补上了“后台任务未跑起来时，连续请求仍要返回不同 run_id”的场景。

3. 当前 `GET /api/runs/{run_id}` 详情接口不再只是轻量内存快照。
   - 为了修复 task-scoped review 提出的 correctness 问题，已补充从磁盘恢复 `request` / `status` / `stages` / `final_story` / critique 摘要的 hydration。
   - 这仍然服务于 Task 3 的“真实后台执行 + SSE 暴露事件流 + 可恢复查询”，没有扩展到 Task 4/5 的前端展示逻辑。

4. `stream_run_events(...)` 在发现 manifest 进入终态后，会再检查一次 `events.jsonl` 是否还有未发送尾部事件。
   - 这样可以避免 terminal event 过早发出，漏掉最后的 artifact/stage 事件。
   - 属于 review 后补上的 correctness 修复。

## 风险 / 后续

1. 当前 SSE bridge 基于轮询 tail `events.jsonl` 与 `run_manifest.json`。
   - 对本地 demo 与当前任务范围是合适的。
   - 若后续 run 数量或并发提高，可考虑更高效的事件分发方式。

2. 当前 detail hydration 已能覆盖 Task 3 所需的 run 恢复与结果摘要。
   - 如果后续前端需要更细粒度的 timeline/reconnect 体验，可继续补充更明确的 stage 映射与增量更新策略。

3. `artifact_ready` 当前是根据事件中的 `artifact` 字段即时映射出来的。
   - 已满足当前 UI 订阅需求。
   - 若后续前端需要区分 artifact 类型或摘要字段，可以扩展 SSE 事件 schema。

## 结论

当前工作树中的 Task 3 实现已完成并通过 review 修复：

- Web 层可创建真实 run
- 真实 pipeline 在后台执行
- SSE endpoint 可暴露真实阶段事件与完成事件
- 服务重启后仍可从磁盘恢复 run 详情与 SSE 订阅
- terminal manifest 不会导致 SSE 提前丢失尾部事件
- Task 3 相关后端测试已全部通过
