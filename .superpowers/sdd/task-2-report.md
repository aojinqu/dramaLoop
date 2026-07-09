# Task 2 Report: 创建 run 与详情接口的基础数据模型

## 实现了什么
- 新增 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/schemas.py`
  - `WebRunCreateRequest`
  - `WebStageSnapshot`
  - `WebRunCreated`
  - `WebRunDetail`
- 新增 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/store.py`
  - `DEFAULT_STAGE_NAMES`
  - `WebRunStore.create()` / `WebRunStore.get()`
  - 为同秒内重复 `run_id` 增加顺序后缀，并用 `Lock` 保证内存态写入不发生并发覆盖
- 修改 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py`
  - 挂载 `POST /api/runs`
  - 挂载 `GET /api/runs/{run_id}`
  - 在 `app.state.run_store` 暴露内存 store
- 新增 `/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py`
  - 覆盖创建 run 返回格式
  - 覆盖详情快照返回
  - 覆盖同秒内连续创建时 `run_id` 唯一性

## 跑了哪些测试与结果
1. RED 1
   - 命令：`uv run pytest tests/unit/test_web_runs_api.py::test_create_run_returns_run_id_and_detail_snapshot -v`
   - 结果：FAIL
   - 关键证据：`assert 404 == 202`
   - 说明：`POST /api/runs` 尚未实现，符合 brief 预期的 RED。

2. GREEN 1
   - 命令：`uv run pytest tests/unit/test_web_runs_api.py::test_create_run_returns_run_id_and_detail_snapshot -v`
   - 结果：PASS

3. RED 2
   - 命令：`uv run pytest tests/unit/test_web_runs_api.py::test_create_run_uses_unique_ids_within_same_second -v`
   - 结果：FAIL
   - 关键证据：`'web-20260709-123456' != 'web-20260709-123456'`
   - 说明：先让测试暴露同秒创建时 `run_id` 冲突问题，再补最小实现。

4. GREEN 2
   - 命令：`uv run pytest tests/unit/test_web_runs_api.py::test_create_run_uses_unique_ids_within_same_second -v`
   - 结果：PASS

5. 最终验证
   - 命令：`uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py -v`
   - 结果：PASS，`4 passed, 1 warning`
   - warning：来自 `fastapi.testclient`/`starlette` 的第三方依赖弃用提示，非本任务引入。

## RED/GREEN 证据
- RED：`POST /api/runs` 初始返回 `404 Not Found`，测试断言 `202` 失败。
- GREEN：完成最小 API skeleton 后，创建与详情测试通过。
- RED：新增唯一性测试后，同秒内两次创建得到相同 `run_id`，测试失败。
- GREEN：为 store 增加唯一化与锁保护后，唯一性测试与回归测试全部通过。

## 改动文件清单
- `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/schemas.py`
- `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/store.py`
- `/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py`
- `/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py`
- `/Users/bytedance/coderepo/brainWrite/.superpowers/sdd/task-2-report.md`

## 自检与任何疑虑
- 已严格限制在 brief 指定范围内：基础数据模型、内存 store、run 创建/详情 API skeleton、对应单测。
- 未扩展到真实 pipeline、SSE、后台任务或前端。
- `stream_url` 按 brief 原样返回，但当前任务未实现对应 stream 路由；这与 brief 的“仅 skeleton、不扩展 SSE”范围一致，因此保持为占位契约，不额外外溢实现。
- 已补一次代码审查复核，最终无 material issues。

## Fix 附录（Task 2 review follow-up）
- 修复 1：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/schemas.py` 中的 `WebRunCreateRequest` 改为复用 `/Users/bytedance/coderepo/brainWrite/src/dramaloop/schemas/input.py` 的 `StoryRequest`，并把 `length` 默认钉为 `"short"`，使 Web run 请求与 brief 指定契约保持一致。
- 修复 2：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/app.py` 中的 `GET /api/runs/{run_id}` 显式声明 `response_model=WebRunDetail`，同时补充返回类型标注。
- 配套调整：`/Users/bytedance/coderepo/brainWrite/src/dramaloop/web/store.py` 的 `create()` 入参同步改为 `StoryRequest`；`/Users/bytedance/coderepo/brainWrite/tests/unit/test_web_runs_api.py` 增加定向测试，覆盖默认 `length="short"` 和详情路由显式 `response_model`。

### Fix 验证命令与结果
1. 定向测试
   - 命令：`uv run pytest tests/unit/test_web_runs_api.py -v`
   - 结果：PASS，`3 passed, 1 warning`
   - 覆盖点：创建/详情回归、默认 `length="short"`、详情路由显式 `response_model=WebRunDetail`、同秒唯一 `run_id`。

2. 相关回归测试
   - 命令：`uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py -v`
   - 结果：PASS，`5 passed, 1 warning`
   - warning：仍为 `fastapi.testclient` / `starlette` 第三方依赖弃用提示，非本次 fix 引入。
