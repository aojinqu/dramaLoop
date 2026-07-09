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
        detail = store.create(run_id, request)
        return WebRunCreated(
            run_id=detail.run_id,
            status="running",
            stream_url=f"/api/runs/{detail.run_id}/stream",
        )

    @app.get("/api/runs/{run_id}")
    def get_run(run_id: str):
        detail = store.get(run_id)
        if detail is None:
            raise HTTPException(status_code=404, detail="run not found")
        return detail

    app.state.run_store = store
    return app
