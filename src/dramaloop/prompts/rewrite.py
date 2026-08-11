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
            "你是中文短剧小说改写助手。",
            f"改写目标：{critique.rewrite_target}",
            f"核心冲突：{premise.core_conflict}",
            f"角色数量：{len(characters.characters)}",
            f"节拍数量：{len(outline.beats)}",
            f"必须修复：{'；'.join(critique.rewrite_plan.must_fix)}",
            f"必须保留：{'；'.join(critique.rewrite_plan.keep)}",
            "只改写薄弱段落及保证衔接所需的相邻句，不要无关地重写全文。",
            "若目标是 originality_revision，必须删除可互换的套路桥段，用既有职业、场域、物件和人物选择重建因果；不能只换措辞或增加形容词。",
            "只输出完整、连续的改写后正文，不要解释。",
            draft_markdown,
        ]
    )
