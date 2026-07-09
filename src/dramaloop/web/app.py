from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse

from dramaloop.config import Settings
from dramaloop.web.runtime import hydrate_run_detail, launch_run, stream_run_events
from dramaloop.web.schemas import WebRunCreateRequest, WebRunCreated, WebRunDetail
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
        return StreamingResponse(stream_run_events(run_id, settings, store), media_type="text/event-stream")

    app.state.run_store = store
    return app
