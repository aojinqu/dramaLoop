from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dramaloop.config import Settings
from dramaloop.web.runtime import (
    cancel_run,
    hydrate_run_detail,
    launch_episode_regeneration,
    launch_run,
    pause_run,
    resume_run,
    stream_run_events,
    update_episode_plan,
)
from dramaloop.web.schemas import (
    WebControlResponse,
    WebEpisodePlanUpdateRequest,
    WebRunCreateRequest,
    WebRunCreated,
    WebRunDetail,
)
from dramaloop.web.store import WebRunStore



def create_app() -> FastAPI:
    app = FastAPI(title="Dramaloop Web Demo")
    store = WebRunStore()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/runs", response_model=WebRunCreated, status_code=202)
    async def create_run(request: WebRunCreateRequest) -> WebRunCreated:
        settings = Settings()
        run_id = await launch_run(store, request, settings)
        return WebRunCreated(run_id=run_id, status="running", stream_url=f"/api/runs/{run_id}/stream")

    @app.get("/api/runs/{run_id}", response_model=WebRunDetail)
    def get_run(run_id: str) -> WebRunDetail:
        settings = Settings()
        hydrated = hydrate_run_detail(run_id, settings, store)
        if hydrated is None:
            raise HTTPException(status_code=404, detail="run not found")
        return hydrated

    @app.get("/api/runs/{run_id}/stream")
    async def get_run_stream(run_id: str) -> StreamingResponse:
        settings = Settings()
        hydrated = hydrate_run_detail(run_id, settings, store)
        if hydrated is None:
            raise HTTPException(status_code=404, detail="run not found")
        return StreamingResponse(
            stream_run_events(run_id, settings, store),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.post("/api/runs/{run_id}/pause", response_model=WebControlResponse)
    def post_pause(run_id: str) -> WebControlResponse:
        settings = Settings()
        try:
            return pause_run(run_id, settings, store)
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/resume", response_model=WebControlResponse)
    async def post_resume(run_id: str) -> WebControlResponse:
        settings = Settings()
        try:
            return await resume_run(run_id, settings, store)
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/cancel", response_model=WebControlResponse)
    def post_cancel(run_id: str) -> WebControlResponse:
        settings = Settings()
        try:
            return cancel_run(run_id, settings, store)
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.put("/api/runs/{run_id}/episode-plan", response_model=WebRunDetail)
    def put_episode_plan(run_id: str, payload: WebEpisodePlanUpdateRequest) -> WebRunDetail:
        settings = Settings()
        try:
            return update_episode_plan(run_id, payload, settings, store)
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @app.post("/api/runs/{run_id}/episodes/{episode_number}/regenerate", response_model=WebControlResponse)
    async def post_regenerate(run_id: str, episode_number: int) -> WebControlResponse:
        settings = Settings()
        try:
            return await launch_episode_regeneration(run_id, episode_number, settings, store)
        except KeyError:
            raise HTTPException(status_code=404, detail="run not found") from None
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    assets_dir = dist_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

        @app.get("/", include_in_schema=False)
        def index() -> FileResponse:
            return FileResponse(dist_dir / "index.html")

    app.state.run_store = store
    return app
