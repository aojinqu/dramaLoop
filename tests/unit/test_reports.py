from pathlib import Path

from dramaloop.eval.report import build_single_run_report


def test_build_single_run_report_reads_scores(sample_run_dir: Path) -> None:
    report = build_single_run_report(sample_run_dir)

    assert report["run_id"] == "20260708-153000-demo"
    assert report["overall_scores"] == [6.0, 7.4]
    assert report["weakest_dimensions"] == ["ending_payoff", "pacing"]
