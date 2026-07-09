from dramaloop.schemas.critique import CritiqueArtifact


def calculate_overall_score(critique: CritiqueArtifact) -> float:
    values = [dimension.score for dimension in critique.dimension_scores.values()]
    return round(sum(values) / len(values), 2)
