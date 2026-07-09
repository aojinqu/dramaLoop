from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


def build_rewrite_prompt(
    draft_markdown: str,
    critique: CritiqueArtifact,
    premise: PremiseArtifact,
    characters: CharacterArtifact,
    outline: OutlineArtifact,
) -> str:
    return "\n".join(
        [
            "You are the Rewriter for a short-drama fiction system.",
            f"Rewrite target: {critique.rewrite_target}",
            f"Core conflict: {premise.core_conflict}",
            f"Character count: {len(characters.characters)}",
            f"Beat count: {len(outline.beats)}",
            f"Must fix: {', '.join(critique.rewrite_plan.must_fix)}",
            f"Keep: {', '.join(critique.rewrite_plan.keep)}",
            "Rewrite only the weak section and adjacent lines needed for coherence.",
            draft_markdown,
        ]
    )
