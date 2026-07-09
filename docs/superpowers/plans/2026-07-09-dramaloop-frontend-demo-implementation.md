# Dramaloop 前端 Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在当前 Dramaloop 仓库内落地一个前后端一体化的单页 Web Demo，让用户能在页面中发起真实 run、通过 SSE 实时观看阶段进度，并看到最终故事、评分摘要与 artifacts。

**Architecture:** 保留现有 Python generation core，不重写 CLI pipeline，只在其外新增 FastAPI 风格 Web 层与 React + Vite + TypeScript 单页前端。后端负责创建 run、读取 `runs/` 产物并将 `events.jsonl` 映射成 SSE；前端负责单页表单、timeline、event stream、结果渲染与断线重连提示。

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Pydantic v2, Typer, React 18, Vite, TypeScript, Vitest, Testing Library, pytest, uv, npm

## Global Constraints

- 单页 Demo
- 前后端一体化接入当前 repo
- 页面发起真实生成 run
- 实时流式展示 run 生命周期
- 展示输入参数、阶段进度、事件流、评分摘要、rewrite focus、最终故事正文
- 提供 artifacts 的基础展示入口
- 选择：前后端一体，直接在当前 repo 内增加 Web 层
- 选择：SSE 优先的真实流式更新
- 选择：B 的信息架构 + A 的配色与气质
- 实现前先写 **spec** 和 **plan**
- spec 与 plan 都使用 **中文**
- spec 与 plan 都写入仓库并持久化保存
- 开发优先复用当前 generation core，不做无关重构
- 前端建议：React + Vite + TypeScript
- 后端建议：FastAPI 风格轻 Web 层

---

## File Map

### 后端
- `pyproject.toml` — 增加 FastAPI/Uvicorn 依赖，保留现有 Python 工具链
- `src/dramaloop/main.py` — 增加 `web` 命令，用于启动 Web 服务
- `src/dramaloop/web/__init__.py` — Web 模块导出
- `src/dramaloop/web/app.py` — FastAPI app factory、路由注册、静态资源挂载
- `src/dramaloop/web/schemas.py` — Web 请求体、详情响应体、SSE 事件数据模型
- `src/dramaloop/web/store.py` — 运行中 run 的内存态注册表与 stage snapshot 结构
- `src/dramaloop/web/runtime.py` — 后台启动 pipeline、tail `events.jsonl`、生成 SSE 消息
- `src/dramaloop/storage/runs.py` — 新增可预分配 run_id 的 helper，供 Web 层提前返回 `run_id`

### 前端
- `frontend/package.json` — Vite/React/TS/Vitest 脚本与依赖
- `frontend/tsconfig.json` — TypeScript 编译配置
- `frontend/vite.config.ts` — Vite 配置
- `frontend/index.html` — 前端入口 HTML
- `frontend/src/main.tsx` — React 启动入口
- `frontend/src/App.tsx` — 单页 Demo 总体状态与布局
- `frontend/src/api.ts` — `createRun` / `fetchRunDetail` / `connectRunStream` API 客户端
- `frontend/src/types.ts` — 前端 run/detail/event 类型定义
- `frontend/src/app.css` — “B 结构 + A 配色” 页面样式
- `frontend/src/components/RunForm.tsx` — 左侧输入表单
- `frontend/src/components/RunTimeline.tsx` — stage timeline 与状态条
- `frontend/src/components/EventFeed.tsx` — 实时事件流
- `frontend/src/components/ResultPanel.tsx` — 最终故事与 summary/artifacts 展示
- `frontend/src/__tests__/App.test.tsx` — 前端页面测试

### 测试与文档
- `tests/unit/test_web_app.py` — health、root、基础 app 启动测试
- `tests/unit/test_web_runs_api.py` — 创建 run 与详情接口测试
- `tests/integration/test_web_stream.py` — SSE 流式事件测试
- `README.md` — 补充 Web Demo 的开发与运行方式

---

### Task 1: 搭建 Web 后端壳子与启动命令

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/dramaloop/main.py`
- Create: `src/dramaloop/web/__init__.py`
- Create: `src/dramaloop/web/app.py`
- Test: `tests/unit/test_web_app.py`

**Interfaces:**
- Consumes: `Settings` from `src/dramaloop/config.py`
- Produces:
  - `create_app() -> FastAPI`
  - `dramaloop web --host <host> --port <port> --reload`

- [ ] **Step 1: 写失败测试，先钉住 health endpoint 和 web 命令入口**

`tests/unit/test_web_app.py`

```python
from fastapi.testclient import TestClient

from dramaloop.web.app import create_app



def test_health_endpoint_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行测试，确认当前仓库还没有 Web 层**

Run:

```bash
uv run pytest tests/unit/test_web_app.py::test_health_endpoint_returns_ok -v
```

Expected: FAIL，报错类似 `ModuleNotFoundError: No module named 'dramaloop.web'` 或 `No module named 'fastapi'`。

- [ ] **Step 3: 写最小可运行实现，补齐依赖、app factory 和 CLI 命令**

`pyproject.toml`

```toml
[project]
dependencies = [
  "anthropic>=0.57.1",
  "fastapi>=0.115.0",
  "pydantic>=2.11.0",
  "pydantic-settings>=2.10.1",
  "pyyaml>=6.0.2",
  "typer>=0.16.0",
  "uvicorn>=0.35.0",
]
```

`src/dramaloop/web/__init__.py`

```python
from dramaloop.web.app import create_app

__all__ = ["create_app"]
```

`src/dramaloop/web/app.py`

```python
from fastapi import FastAPI



def create_app() -> FastAPI:
    app = FastAPI(title="Dramaloop Web Demo")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

`src/dramaloop/main.py`

```python
@app.command()
def web(
    host: str = typer.Option(default="127.0.0.1"),
    port: int = typer.Option(default=8000),
    reload: bool = typer.Option(default=False),
) -> None:
    import uvicorn

    uvicorn.run(
        "dramaloop.web.app:create_app",
        host=host,
        port=port,
        reload=reload,
        factory=True,
    )
```

- [ ] **Step 4: 安装新依赖并重新运行测试**

Run:

```bash
uv sync --extra dev
uv run pytest tests/unit/test_web_app.py -v
```

Expected: PASS，`test_health_endpoint_returns_ok` 通过。

- [ ] **Step 5: 提交后端壳子**

```bash
git add pyproject.toml src/dramaloop/main.py src/dramaloop/web/__init__.py src/dramaloop/web/app.py tests/unit/test_web_app.py
git commit -m "feat: bootstrap dramaloop web app shell"
```

### Task 2: 实现创建 run 与详情接口的基础数据模型

**Files:**
- Create: `src/dramaloop/web/schemas.py`
- Create: `src/dramaloop/web/store.py`
- Modify: `src/dramaloop/web/app.py`
- Test: `tests/unit/test_web_runs_api.py`

**Interfaces:**
- Consumes:
  - `StoryRequest` from `src/dramaloop/schemas/input.py`
  - `create_app() -> FastAPI`
- Produces:
  - `class WebRunCreateRequest(BaseModel)`
  - `class WebRunCreated(BaseModel)`
  - `class WebRunDetail(BaseModel)`
  - `class WebRunStore`
  - `POST /api/runs`
  - `GET /api/runs/{run_id}`

- [ ] **Step 1: 写失败测试，钉住创建 run 与读取详情的返回格式**

`tests/unit/test_web_runs_api.py`

```python
from fastapi.testclient import TestClient

from dramaloop.web.app import create_app



def test_create_run_returns_run_id_and_detail_snapshot() -> None:
    client = TestClient(create_app())

    created = client.post(
        "/api/runs",
        json={
            "idea": "被未婚夫当众退婚后，她转身嫁给了他的死对头",
            "style": ["都市情感", "逆袭", "狗血短剧感"],
            "audience": "女性向短剧用户",
            "constraints": ["节奏快", "结尾有回报"],
            "max_iterations": 2,
        },
    )

    assert created.status_code == 202
    payload = created.json()
    assert payload["status"] == "running"
    assert payload["stream_url"] == f"/api/runs/{payload['run_id']}/stream"

    detail = client.get(f"/api/runs/{payload['run_id']}")

    assert detail.status_code == 200
    snapshot = detail.json()
    assert snapshot["request"]["idea"] == "被未婚夫当众退婚后，她转身嫁给了他的死对头"
    assert snapshot["status"] == "running"
    assert snapshot["stages"][0]["name"] == "premise_refinement"
```

- [ ] **Step 2: 运行测试，确认接口还不存在**

Run:

```bash
uv run pytest tests/unit/test_web_runs_api.py::test_create_run_returns_run_id_and_detail_snapshot -v
```

Expected: FAIL，`POST /api/runs` 返回 `404`。

- [ ] **Step 3: 实现请求/响应模型与内存态 store，并把接口挂到 app 上**

`src/dramaloop/web/schemas.py`

```python
from typing import Literal

from pydantic import BaseModel, Field


class WebRunCreateRequest(BaseModel):
    idea: str = Field(min_length=1)
    style: list[str] = Field(min_length=1)
    audience: str | None = None
    constraints: list[str] = Field(default_factory=list)
    max_iterations: int = Field(default=2, ge=1, le=3)


class WebStageSnapshot(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "failed"]


class WebRunCreated(BaseModel):
    run_id: str
    status: Literal["running"]
    stream_url: str


class WebRunDetail(BaseModel):
    run_id: str
    status: Literal["running", "completed", "failed"]
    request: WebRunCreateRequest
    stages: list[WebStageSnapshot]
    current_stage: str | None = None
    final_story: str | None = None
    overall_score: float | None = None
    rewrite_focus: str | None = None
    available_artifacts: list[str] = Field(default_factory=list)
```

`src/dramaloop/web/store.py`

```python
from dramaloop.web.schemas import WebRunCreateRequest, WebRunDetail, WebStageSnapshot


DEFAULT_STAGE_NAMES = [
    "premise_refinement",
    "character_card_generation",
    "story_outline_generation",
    "draft_generation",
    "critique_scoring",
    "targeted_rewrite",
    "final_assembly",
]


class WebRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, WebRunDetail] = {}

    def create(self, run_id: str, request: WebRunCreateRequest) -> WebRunDetail:
        detail = WebRunDetail(
            run_id=run_id,
            status="running",
            request=request,
            stages=[WebStageSnapshot(name=name, status="pending") for name in DEFAULT_STAGE_NAMES],
        )
        self._runs[run_id] = detail
        return detail

    def get(self, run_id: str) -> WebRunDetail | None:
        return self._runs.get(run_id)
```

`src/dramaloop/web/app.py`

```python
from datetime import datetime

from fastapi import FastAPI, HTTPException

from dramaloop.web.schemas import WebRunCreateRequest, WebRunCreated
from dramaloop.web.store import WebRunStore



def create_app() -> FastAPI:
    app = FastAPI(title="Dramaloop Web Demo")
    store = WebRunStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/runs", response_model=WebRunCreated, status_code=202)
    def create_run(request: WebRunCreateRequest) -> WebRunCreated:
        run_id = f"web-{datetime.now():%Y%m%d-%H%M%S}"
        store.create(run_id, request)
        return WebRunCreated(run_id=run_id, status="running", stream_url=f"/api/runs/{run_id}/stream")

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        detail = store.get(run_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="run not found")
        return detail

    app.state.run_store = store
    return app
```

- [ ] **Step 4: 跑后端 API 单测**

Run:

```bash
uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py -v
```

Expected: PASS。

- [ ] **Step 5: 提交 run API 基础模型**

```bash
git add src/dramaloop/web/schemas.py src/dramaloop/web/store.py src/dramaloop/web/app.py tests/unit/test_web_runs_api.py
git commit -m "feat: add dramaloop web run api skeleton"
```

### Task 3: 把真实 pipeline 接到后台执行，并用 SSE 暴露事件流

**Files:**
- Modify: `src/dramaloop/storage/runs.py`
- Create: `src/dramaloop/web/runtime.py`
- Modify: `src/dramaloop/web/app.py`
- Modify: `src/dramaloop/web/store.py`
- Test: `tests/integration/test_web_stream.py`

**Interfaces:**
- Consumes:
  - `run_story_pipeline(request: StoryRequest, settings: Settings, client: LLMClient, started_at: datetime | None = None) -> RunResult`
  - `build_run_id()` and `reserve_run_id()` from `src/dramaloop/storage/runs.py`
- Produces:
  - `plan_run_id(runs_dir: Path, idea: str, started_at: datetime) -> str`
  - `launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str`
  - `stream_run_events(run_id: str, settings: Settings, store: WebRunStore) -> AsyncIterator[str]`
  - `GET /api/runs/{run_id}/stream`

- [ ] **Step 1: 写失败集成测试，钉住 SSE 必须能看到真实 run 事件**

`tests/integration/test_web_stream.py`

```python
from fastapi.testclient import TestClient

from dramaloop.web.app import create_app



def test_stream_endpoint_emits_stage_and_completion_events(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("DRAMALOOP_PROVIDER", "mock")
    monkeypatch.setenv("DRAMALOOP_RUNS_DIR", str(tmp_path / "runs"))

    client = TestClient(create_app())
    created = client.post(
        "/api/runs",
        json={
            "idea": "被未婚夫当众退婚后，她转身嫁给了他的死对头",
            "style": ["都市情感", "逆袭", "狗血短剧感"],
            "audience": "女性向短剧用户",
            "constraints": ["节奏快", "结尾有回报"],
            "max_iterations": 2,
        },
    ).json()

    with client.stream("GET", created["stream_url"]) as response:
        chunks = list(response.iter_lines())

    text = "\n".join(line.decode() if isinstance(line, bytes) else line for line in chunks)
    assert "event: stage_started" in text
    assert "event: stage_completed" in text
    assert "event: artifact_ready" in text
    assert "event: run_completed" in text
```

- [ ] **Step 2: 运行集成测试，确认当前还没有 stream endpoint**

Run:

```bash
uv run pytest tests/integration/test_web_stream.py::test_stream_endpoint_emits_stage_and_completion_events -v
```

Expected: FAIL，`GET /api/runs/{run_id}/stream` 返回 `404`。

- [ ] **Step 3: 实现 run_id 预分配、后台启动真实 pipeline，以及 SSE tail `events.jsonl`**

`src/dramaloop/storage/runs.py`

```python
def plan_run_id(runs_dir: Path, idea: str, started_at: datetime) -> str:
    return reserve_run_id(runs_dir, build_run_id(idea, started_at))
```

`src/dramaloop/web/runtime.py`

```python
import asyncio
import json
from datetime import datetime

from dramaloop.config import Settings
from dramaloop.harness.orchestrator import run_story_pipeline
from dramaloop.llm.provider import build_llm_client
from dramaloop.schemas.input import StoryRequest
from dramaloop.storage.runs import plan_run_id
from dramaloop.web.schemas import WebRunCreateRequest
from dramaloop.web.store import WebRunStore


async def launch_run(store: WebRunStore, request: WebRunCreateRequest, settings: Settings) -> str:
    started_at = datetime.now()
    run_id = plan_run_id(settings.runs_dir, request.idea, started_at)
    store.create(run_id, request)

    async def _run() -> None:
        client = build_llm_client(settings)
        payload = StoryRequest(
            idea=request.idea,
            style=request.style,
            audience=request.audience,
            constraints=request.constraints,
            max_iterations=request.max_iterations,
            length="short",
        )
        await asyncio.to_thread(run_story_pipeline, payload, settings, client, started_at)

    asyncio.create_task(_run())
    return run_id


async def stream_run_events(run_id: str, settings: Settings):
    events_path = settings.runs_dir / run_id / "events.jsonl"
    manifest_path = settings.runs_dir / run_id / "run_manifest.json"
    sent = 0
    while True:
        if events_path.exists():
            lines = events_path.read_text(encoding="utf-8").splitlines()
            for raw in lines[sent:]:
                payload = json.loads(raw)
                sent += 1
                yield f"event: stage_{payload['event']}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if payload.get("artifact"):
                    artifact_payload = {"run_id": run_id, "artifact": payload["artifact"], "ts": payload.get("ts")}
                    yield f"event: artifact_ready\ndata: {json.dumps(artifact_payload, ensure_ascii=False)}\n\n"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            if manifest["status"] in {"completed", "failed"}:
                yield f"event: run_{manifest['status']}\ndata: {json.dumps({'run_id': run_id, 'status': manifest['status']}, ensure_ascii=False)}\n\n"
                break
        await asyncio.sleep(0.25)
```

`src/dramaloop/web/app.py`

```python
from fastapi.responses import StreamingResponse

from dramaloop.config import Settings
from dramaloop.web.runtime import launch_run, stream_run_events


@app.post("/api/runs", response_model=WebRunCreated, status_code=202)
async def create_run(request: WebRunCreateRequest) -> WebRunCreated:
    settings = Settings()
    run_id = await launch_run(store, request, settings)
    return WebRunCreated(run_id=run_id, status="running", stream_url=f"/api/runs/{run_id}/stream")


@app.get("/api/runs/{run_id}/stream")
async def get_run_stream(run_id: str) -> StreamingResponse:
    settings = Settings()
    return StreamingResponse(stream_run_events(run_id, settings), media_type="text/event-stream")
```

- [ ] **Step 4: 运行后端单测 + SSE 集成测试**

Run:

```bash
uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py -v
```

Expected: PASS，且 `test_stream_endpoint_emits_stage_and_completion_events` 使用 mock provider 跑通。

- [ ] **Step 5: 提交真实 run + SSE 桥接能力**

```bash
git add src/dramaloop/storage/runs.py src/dramaloop/web/runtime.py src/dramaloop/web/app.py src/dramaloop/web/store.py tests/integration/test_web_stream.py
git commit -m "feat: stream dramaloop run events over sse"
```

### Task 4: 搭建 React 单页骨架与基础布局

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/app.css`
- Create: `frontend/src/components/RunForm.tsx`
- Create: `frontend/src/components/RunTimeline.tsx`
- Create: `frontend/src/components/EventFeed.tsx`
- Create: `frontend/src/components/ResultPanel.tsx`
- Create: `frontend/src/types.ts`
- Test: `frontend/src/__tests__/App.test.tsx`

**Interfaces:**
- Consumes: `WebRunDetail`, `WebStageSnapshot` 前端类型定义
- Produces:
  - `RunForm` 左侧表单
  - `RunTimeline` 右上阶段视图
  - `EventFeed` 右上事件流
  - `ResultPanel` 右下故事与 artifacts 视图
  - `App` 单页整体布局

- [ ] **Step 1: 先写前端失败测试，钉住单页骨架的关键区域**

`frontend/src/__tests__/App.test.tsx`

```tsx
import { render, screen } from "@testing-library/react";
import App from "../App";


test("renders form, timeline, event feed, and result panels", () => {
  render(<App />);

  expect(screen.getByRole("heading", { name: /dramaloop web demo/i })).toBeInTheDocument();
  expect(screen.getByLabelText(/idea/i)).toBeInTheDocument();
  expect(screen.getByText(/stage timeline/i)).toBeInTheDocument();
  expect(screen.getByText(/event stream/i)).toBeInTheDocument();
  expect(screen.getByText(/final story/i)).toBeInTheDocument();
});
```

- [ ] **Step 2: 运行测试，确认 frontend 目录尚不存在**

Run:

```bash
npm --prefix frontend test -- --run
```

Expected: FAIL，报错类似 `ENOENT: no such file or directory, open 'frontend/package.json'`。

- [ ] **Step 3: 实现 Vite + React + TypeScript 骨架，并落实 B 结构 + A 配色**

`frontend/package.json`

```json
{
  "name": "dramaloop-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "test": "vitest"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "^6.6.3",
    "@testing-library/react": "^16.1.0",
    "@testing-library/user-event": "^14.6.1",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "typescript": "^5.6.3",
    "vite": "^5.4.10",
    "vitest": "^2.1.4"
  }
}
```

`frontend/src/App.tsx`

```tsx
import { EventFeed } from "./components/EventFeed";
import { ResultPanel } from "./components/ResultPanel";
import { RunForm } from "./components/RunForm";
import { RunTimeline } from "./components/RunTimeline";
import "./app.css";

export default function App() {
  return (
    <div className="page-shell">
      <aside className="left-panel">
        <h1>Dramaloop Web Demo</h1>
        <RunForm />
      </aside>
      <main className="right-panel">
        <section className="top-grid">
          <RunTimeline />
          <EventFeed />
        </section>
        <ResultPanel />
      </main>
    </div>
  );
}
```

`frontend/src/components/RunForm.tsx`

```tsx
export function RunForm() {
  return (
    <form className="panel">
      <label>
        Idea
        <textarea aria-label="Idea" name="idea" />
      </label>
      <label>
        Style tags
        <input name="style" placeholder="都市情感, 逆袭" />
      </label>
      <label>
        Audience
        <input name="audience" placeholder="女性向短剧用户" />
      </label>
      <label>
        Constraints
        <input name="constraints" placeholder="节奏快, 结尾有回报" />
      </label>
      <button type="submit">Launch Run</button>
    </form>
  );
}
```

- [ ] **Step 4: 安装前端依赖并运行前端单测**

Run:

```bash
npm --prefix frontend install
npm --prefix frontend test -- --run
```

Expected: PASS。

- [ ] **Step 5: 提交前端单页骨架**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/src/main.tsx frontend/src/App.tsx frontend/src/app.css frontend/src/components frontend/src/types.ts frontend/src/__tests__/App.test.tsx
git commit -m "feat: scaffold dramaloop frontend demo shell"
```

### Task 4 收口：补齐前端 lint 基线并完成任务归档

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/eslint.config.js`
- Modify: `.superpowers/sdd/task-4-report.md`
- Modify: `.superpowers/sdd/progress.md`

**Interfaces:**
- Consumes:
  - React + Vite + TypeScript 前端骨架
  - `npm --prefix frontend run lint`
- Produces:
  - 支持 TS / TSX 的最小 ESLint 基线
  - `react-hooks` / `jsx-a11y` lint 护栏
  - 忽略 `dist/`、`node_modules/`、`*.d.ts`、`*.tsbuildinfo`
  - Task 4 收口报告与 progress 记录

- [ ] **Step 1: 先审视现有前端配置缺口，确认 lint 基线只做最小收口**

检查当前：
- `frontend/package.json`
- `frontend/eslint.config.js`
- `frontend/src/**/*.tsx`

结论要求：
- 仅补齐 TypeScript parser、`react-hooks`、基础 `jsx-a11y`
- 不额外引入 Prettier、stylelint、type-aware lint 或更重工程化配置

- [ ] **Step 2: 以最小改动补齐前端 lint 配置**

要求：
- `frontend/package.json` 至少具备 `lint` script 与对应 lint 依赖
- `frontend/eslint.config.js` 支持 `ts` / `tsx`
- 忽略：`dist/**`、`node_modules/**`、`**/*.d.ts`、`**/*.tsbuildinfo`
- 保持前端当前单页骨架，不顺手扩展 Task 5 的 API / SSE 逻辑

- [ ] **Step 3: 运行 Task 4 收口验证**

Run:

```bash
npm --prefix frontend install
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: 全部 PASS。

- [ ] **Step 4: 更新 Task 4 报告并执行 task-scoped review**

要求：
- 更新 `.superpowers/sdd/task-4-report.md`，记录 lint 收口内容、验证命令与结果
- 对 Task 4 收口 diff 做 review，确认无 Critical / Important 问题残留

- [ ] **Step 5: review clean 后记录 progress 并提交 Task 4 收口 commit**

要求：
- 在 `.superpowers/sdd/progress.md` 追加 Task 4 完成记录
- 提交一个仅覆盖 Task 4 收口的 commit

### Task 5: 接通 API 与 SSE，渲染实时状态、故事结果，并补充运行文档

**Files:**
- Create: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/RunForm.tsx`
- Modify: `frontend/src/components/RunTimeline.tsx`
- Modify: `frontend/src/components/EventFeed.tsx`
- Modify: `frontend/src/components/ResultPanel.tsx`
- Modify: `src/dramaloop/web/app.py`
- Modify: `README.md`
- Test: `frontend/src/__tests__/App.test.tsx`

**Interfaces:**
- Consumes:
  - `POST /api/runs`
  - `GET /api/runs/{run_id}`
  - `GET /api/runs/{run_id}/stream`
- Produces:
  - `createRun(input: RunFormInput): Promise<WebRunCreated>`
  - `fetchRunDetail(runId: string): Promise<WebRunDetail>`
  - `connectRunStream(runId: string, handlers: StreamHandlers): EventSource`

- [ ] **Step 1: 先写失败前端测试，钉住“提交 -> 收到流 -> 渲染故事”的主路径**

在 `frontend/src/__tests__/App.test.tsx` 追加：

```tsx
import userEvent from "@testing-library/user-event";
import { render, screen, waitFor } from "@testing-library/react";
import App from "../App";
import * as api from "../api";

vi.mock("../api", () => ({
  createRun: vi.fn(),
  fetchRunDetail: vi.fn(),
  connectRunStream: vi.fn(),
}));


test("launches a run and renders streamed result", async () => {
  const createRun = vi.mocked(api.createRun);
  const fetchRunDetail = vi.mocked(api.fetchRunDetail);
  const connectRunStream = vi.mocked(api.connectRunStream);

  createRun.mockResolvedValue({
    run_id: "20260709-frontend-demo-story",
    status: "running",
    stream_url: "/api/runs/20260709-frontend-demo-story/stream",
  });

  fetchRunDetail.mockResolvedValue({
    run_id: "20260709-frontend-demo-story",
    status: "completed",
    request: {
      idea: "被未婚夫当众退婚后，她转身嫁给了他的死对头",
      style: ["都市情感", "逆袭"],
      audience: "女性向短剧用户",
      constraints: ["节奏快", "结尾有回报"],
      max_iterations: 2,
    },
    stages: [{ name: "premise_refinement", status: "completed" }],
    current_stage: "final_assembly",
    final_story: "婚礼进行到交换戒指的那一刻，周既白松开了她的手。",
    overall_score: 7.9,
    rewrite_focus: "ending_payoff",
    available_artifacts: ["run_summary.md", "rewrite_plan_v1.json", "events.jsonl"],
  });

  connectRunStream.mockImplementation((_runId, handlers) => {
    handlers.onMessage({ event: "stage_completed", data: { stage: "premise_refinement" } });
    handlers.onMessage({ event: "run_completed", data: { run_id: "20260709-frontend-demo-story" } });
    return { close() {} } as EventSource;
  });

  render(<App />);

  await userEvent.type(screen.getByLabelText(/idea/i), "被未婚夫当众退婚后，她转身嫁给了他的死对头");
  await userEvent.click(screen.getByRole("button", { name: /launch run/i }));

  await waitFor(() => {
    expect(screen.getByText(/婚礼进行到交换戒指的那一刻/)).toBeInTheDocument();
    expect(screen.getByText(/ending_payoff/)).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: 运行前端测试，确认当前页面还没有接 API**

Run:

```bash
npm --prefix frontend test -- --run
```

Expected: FAIL，提示 `createRun` / `connectRunStream` 未被调用，或页面没有渲染最终故事。

- [ ] **Step 3: 接通 API、SSE 与页面状态，并让 FastAPI 在构建产物存在时托管静态前端**

`frontend/src/api.ts`

```tsx
import type { WebRunCreated, WebRunDetail } from "./types";

export async function createRun(input: {
  idea: string;
  style: string[];
  audience: string;
  constraints: string[];
  max_iterations: number;
}): Promise<WebRunCreated> {
  const response = await fetch("/api/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  return response.json();
}

export async function fetchRunDetail(runId: string): Promise<WebRunDetail> {
  const response = await fetch(`/api/runs/${runId}`);
  return response.json();
}

export function connectRunStream(
  runId: string,
  handlers: {
    onMessage: (payload: { event: string; data: Record<string, unknown> }) => void;
    onError: () => void;
  },
): EventSource {
  const source = new EventSource(`/api/runs/${runId}/stream`);
  ["stage_started", "stage_completed", "artifact_ready", "run_completed", "run_failed"].forEach((eventName) => {
    source.addEventListener(eventName, (event) => {
      handlers.onMessage({ event: eventName, data: JSON.parse((event as MessageEvent).data) });
    });
  });
  source.onerror = handlers.onError;
  return source;
}
```

`frontend/src/App.tsx`

```tsx
import { useState } from "react";
import { connectRunStream, createRun, fetchRunDetail } from "./api";
import type { WebRunDetail } from "./types";

export default function App() {
  const [runId, setRunId] = useState<string | null>(null);
  const [detail, setDetail] = useState<WebRunDetail | null>(null);
  const [events, setEvents] = useState<Array<{ event: string; data: Record<string, unknown> }>>([]);
  const [streamState, setStreamState] = useState<"idle" | "streaming" | "reconnecting" | "failed">("idle");

  const handleLaunch = async (input: {
    idea: string;
    style: string[];
    audience: string;
    constraints: string[];
    max_iterations: number;
  }) => {
    const created = await createRun(input);
    setRunId(created.run_id);
    setStreamState("streaming");
    const source = connectRunStream(created.run_id, {
      onMessage: async (message) => {
        setEvents((current) => [...current, message]);
        if (message.event === "run_completed" || message.event === "run_failed") {
          const nextDetail = await fetchRunDetail(created.run_id);
          setDetail(nextDetail);
          source.close();
        }
      },
      onError: () => setStreamState("reconnecting"),
    });
  };

  return (
    <div className="page-shell">
      <aside className="left-panel">
        <h1>Dramaloop Web Demo</h1>
        <RunForm onSubmit={handleLaunch} />
      </aside>
      <main className="right-panel">
        <section className="top-grid">
          <RunTimeline detail={detail} streamState={streamState} />
          <EventFeed events={events} />
        </section>
        <ResultPanel detail={detail} runId={runId} />
      </main>
    </div>
  );
}
```

`src/dramaloop/web/app.py`

```python
from pathlib import Path

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
if dist_dir.exists():
    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(dist_dir / "index.html")
```

`README.md`

```md
## Web Demo

### 本地开发

后端：
```bash
uv run dramaloop web --reload --host 127.0.0.1 --port 8000
```

前端：
```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

### 构建并由 FastAPI 托管前端
```bash
npm --prefix frontend run build
uv run dramaloop web --host 127.0.0.1 --port 8000
```
```

- [ ] **Step 4: 跑后端 + 前端测试，并验证前端 build 可通过**

Run:

```bash
uv run pytest tests/unit/test_web_app.py tests/unit/test_web_runs_api.py tests/integration/test_web_stream.py -v
npm --prefix frontend test -- --run
npm --prefix frontend run build
```

Expected: 全部 PASS；`frontend/dist` 成功产出。

- [ ] **Step 5: 提交 API 集成、SSE 前端接线和文档**

```bash
git add frontend/src/api.ts frontend/src/App.tsx frontend/src/components/RunForm.tsx frontend/src/components/RunTimeline.tsx frontend/src/components/EventFeed.tsx frontend/src/components/ResultPanel.tsx frontend/src/__tests__/App.test.tsx src/dramaloop/web/app.py README.md
git commit -m "feat: ship dramaloop realtime web demo"
```

---

## 自检结论

### Spec coverage
- 单页 Demo：Task 4、Task 5
- 前后端一体接入：Task 1、Task 2、Task 5
- 页面发起真实 run：Task 2、Task 3、Task 5
- SSE 实时流式更新：Task 3、Task 5
- 展示输入、阶段进度、事件流、评分、rewrite focus、最终故事：Task 4、Task 5
- 复用现有 generation core：Task 3
- 中文 spec 与 plan 持久化：已通过 `docs/superpowers/specs/2026-07-09-dramaloop-frontend-demo-spec.md` 与本计划文件覆盖

### Placeholder scan
- 无 `TBD`、`TODO`、`implement later` 类占位语
- 所有任务都给出了明确文件路径、命令和最小代码片段

### Type consistency
- 后端请求模型统一使用 `WebRunCreateRequest`
- 后端详情模型统一使用 `WebRunDetail`
- 前端 API 客户端统一返回 `WebRunCreated` / `WebRunDetail`
- SSE 客户端统一消费 `{ event, data }`
