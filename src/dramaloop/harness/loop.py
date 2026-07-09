from dramaloop.config import Settings
from dramaloop.schemas.critique import CritiqueArtifact


def determine_stop_reason(
    previous_overall_score: float | None,
    current_critique: CritiqueArtifact,
    settings: Settings,
    iteration: int,
    max_iterations: int,
) -> str | None:
    if current_critique.overall_score >= settings.target_threshold:
        return "target_threshold_reached"
    if all(score.score >= settings.minimum_dimension_threshold for score in current_critique.dimension_scores.values()):
        return "minimum_dimension_threshold_reached"
    if previous_overall_score is not None and current_critique.overall_score - previous_overall_score < settings.min_delta:
        return "improvement_below_min_delta"
    if iteration >= max_iterations:
        return "max_iterations_reached"
    return None


def should_continue_loop(
    previous_overall_score: float | None,
    current_critique: CritiqueArtifact,
    settings: Settings,
    iteration: int,
    max_iterations: int,
) -> bool:
    return determine_stop_reason(previous_overall_score, current_critique, settings, iteration, max_iterations) is None
