from threading import Lock

from dramaloop.schemas.input import StoryRequest
from dramaloop.web.schemas import WebRunDetail, WebStageSnapshot


SINGLE_STAGE_NAMES = [
    "premise_refinement",
    "character_card_generation",
    "story_outline_generation",
    "draft_generation",
    "critique_scoring",
    "targeted_rewrite",
    "final_assembly",
]

EPISODIC_STAGE_NAMES = [
    "season_planning",
    "episode_plan_generation",
    "episode_generation",
    "final_assembly",
]


def stage_names_for_request(request: StoryRequest) -> list[str]:
    if request.format == "episodic_series":
        return EPISODIC_STAGE_NAMES
    return SINGLE_STAGE_NAMES


class WebRunStore:
    def __init__(self) -> None:
        self._runs: dict[str, WebRunDetail] = {}
        self._lock = Lock()

    def create(self, run_id: str, request: StoryRequest) -> WebRunDetail:
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
                stages=[WebStageSnapshot(name=name, status="pending") for name in stage_names_for_request(request)],
            )
            self._runs[unique_run_id] = detail
            return detail.model_copy(deep=True)

    def get(self, run_id: str) -> WebRunDetail | None:
        with self._lock:
            detail = self._runs.get(run_id)
            return detail.model_copy(deep=True) if detail is not None else None

    def replace(self, detail: WebRunDetail) -> WebRunDetail:
        with self._lock:
            stored = detail.model_copy(deep=True)
            self._runs[detail.run_id] = stored
            return stored.model_copy(deep=True)
