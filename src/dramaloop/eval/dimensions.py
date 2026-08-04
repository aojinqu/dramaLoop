from dramaloop.schemas.critique import DimensionName


def ordered_dimensions() -> list[DimensionName]:
    return [
        "hook_strength",
        "character_consistency",
        "conflict_intensity",
        "pacing",
        "short_drama_feel",
        "ending_payoff",
        "language_fluency",
    ]
