from threading import Lock

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
        self._lock = Lock()

    def create(self, run_id: str, request: WebRunCreateRequest) -> WebRunDetail:
        with self._lock:
            unique_run_id = run_id
            suffix = 2
            while unique_run_id in self._runs:
                unique_run_id = f"{run_id}-{suffix}"
                suffix += 1

            detail = WebRunDetail(
                run_id=unique_run_id,
                status="running",
                request=request,
                stages=[WebStageSnapshot(name=name, status="pending") for name in DEFAULT_STAGE_NAMES],
            )
            self._runs[unique_run_id] = detail
            return detail

    def get(self, run_id: str) -> WebRunDetail | None:
        return self._runs.get(run_id)
