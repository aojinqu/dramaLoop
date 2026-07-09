from dataclasses import dataclass, field

from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.critique import CritiqueArtifact
from dramaloop.schemas.input import StoryRequest
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.schemas.rewrite import RewriteArtifact
from dramaloop.schemas.run import RunPaths


@dataclass
class PipelineContext:
    request: StoryRequest
    run_paths: RunPaths
    premise: PremiseArtifact | None = None
    characters: CharacterArtifact | None = None
    outline: OutlineArtifact | None = None
    drafts: list[str] = field(default_factory=list)
    critiques: list[CritiqueArtifact] = field(default_factory=list)
    rewrites: list[RewriteArtifact] = field(default_factory=list)
