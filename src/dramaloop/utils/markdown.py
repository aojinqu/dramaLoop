from dramaloop.eval.dimensions import ordered_dimensions
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.rewrite import RewriteArtifact


def _dimension_label(name: str) -> str:
    return {
        "hook_strength": "Hook",
        "character_consistency": "Character",
        "conflict_intensity": "Conflict",
        "pacing": "Pacing",
        "short_drama_feel": "Drama Feel",
        "ending_payoff": "Ending",
        "language_fluency": "Fluency",
        "originality": "Originality",
    }[name]


def _stop_reason_label(stop_reason: str) -> str:
    return {
        "target_threshold_reached": "达到目标总分阈值",
        "minimum_dimension_threshold_reached": "所有关键维度达到最低阈值",
        "improvement_below_min_delta": "继续改写的收益低于最小提升阈值",
        "max_iterations_reached": "达到最大迭代轮数",
    }.get(stop_reason, stop_reason)


def render_run_summary(
    *,
    request: StoryRequest,
    critique_history: list[CritiqueArtifact],
    rewrite_history: list[RewriteArtifact],
    final_story_path: str,
    stop_reason: str,
) -> str:
    labels = [_dimension_label(name) for name in ordered_dimensions()]
    header = f"| Version | {' | '.join(labels)} | Overall |"
    divider = f"| {' | '.join(['---'] * (len(labels) + 2))} |"
    rows = []
    for index, critique in enumerate(critique_history, start=1):
        values = [
            str(critique.dimension_scores[name].score)
            if name in critique.dimension_scores
            else "-"
            for name in ordered_dimensions()
        ]
        rows.append(f"| v{index} | {' | '.join(values)} | {critique.overall_score:.2f} |")

    weakest_lines = []
    for index, critique in enumerate(critique_history, start=1):
        weakest = critique.weakest_dimensions[0]
        reason = critique.dimension_scores[weakest].reason
        weakest_lines.append(f"- v{index}: {_dimension_label(weakest)} -> {reason}")

    rewrite_lines = [
        f"- v{item.version}: target={item.target_section}; changes={', '.join(item.changes_made)}"
        for item in rewrite_history
    ] or ["- none"]

    return "\n".join(
        [
            "# Run Summary",
            "",
            "## Input",
            f"- Idea: {request.idea}",
            f"- Style: {', '.join(request.style)}",
            f"- Audience: {request.audience or 'general'}",
            f"- Constraints: {', '.join(request.constraints) or 'none'}",
            "",
            "## Iteration Score Trend",
            header,
            divider,
            *rows,
            "",
            "## Weakest Dimensions",
            *weakest_lines,
            "",
            "## Rewrite Notes",
            *rewrite_lines,
            "",
            "## Final Story",
            f"- Path: {final_story_path}",
            "",
            "## Stop Reason",
            f"- {_stop_reason_label(stop_reason)}",
        ]
    )
