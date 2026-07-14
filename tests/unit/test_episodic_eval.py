from pathlib import Path

import yaml

from dramaloop.config import Settings
from dramaloop.eval.report import run_dataset_eval
from dramaloop.schemas.input import StoryRequest


DATASET_PATH = Path(__file__).resolve().parents[2] / "evals" / "datasets" / "episodic_mvp_cases.yaml"


def test_episodic_mvp_cases_are_valid_story_requests() -> None:
    cases = yaml.safe_load(DATASET_PATH.read_text(encoding="utf-8"))
    assert 4 <= len(cases) <= 6
    for case in cases:
        request = StoryRequest.model_validate(case)
        assert request.format == "episodic_series"
        assert request.episode_count in {2, 3}
        assert request.enable_episode_critique is True


def test_run_dataset_eval_episodic_report_fields(tmp_path: Path) -> None:
    settings = Settings(
        runs_dir=tmp_path / "runs",
        evals_dir=tmp_path / "evals",
        provider="mock",
    )
    cases = [
        {
            "idea": "她被退婚后反手嫁给宿敌",
            "style": ["都市情感"],
            "length": "short",
            "format": "episodic_series",
            "episode_count": 2,
            "episode_min_words": 200,
            "episode_max_words": 400,
            "constraints": ["节奏快", "结尾有钩子"],
            "enable_episode_critique": True,
        }
    ]
    dataset_path = tmp_path / "one_episodic_case.yaml"
    dataset_path.write_text(yaml.safe_dump(cases, allow_unicode=True), encoding="utf-8")

    aggregate = run_dataset_eval(dataset_path, settings)
    report = aggregate["reports"][0]

    assert aggregate["case_count"] == 1
    assert "success_rate" in aggregate
    assert "average_completed_episode_ratio" in aggregate
    assert report["format"] == "episodic_series"
    assert report["status"] == "completed"
    assert report["completed_episodes"] == 2
    assert report["total_episodes"] == 2
    assert report["success"] is True
    assert report["continuity_failures"] == 0
    assert isinstance(report["episode_scores"], list)
    assert len(report["episode_scores"]) == 2
    assert isinstance(report["average_episode_score"], float)
    assert isinstance(report["weakest_dimensions"], list)
