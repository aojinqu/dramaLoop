from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact



def build_draft_prompt(premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    tone_notes = "、".join(premise.tone_notes) or "都市情感、逆袭、短剧感"
    hard_constraints = "；".join(premise.hard_constraints) or "节奏快；结尾有回报"
    character_lines = "\n".join(
        f"- {card.name}（{card.role}）：身份={card.public_identity}；想要={card.core_desire}；害怕={card.core_fear}；口吻={card.voice_style}；人物走向={card.arc_target}"
        for card in characters.characters
    )
    beat_lines = "\n".join(
        f"- {beat.label}：{beat.summary}（作用：{beat.purpose}；张力：{beat.tension_level}/10）"
        for beat in outline.beats
    )
    return "\n".join(
        [
            "你是中文短剧感短篇小说写手，不是编剧，不是分镜师。",
            f"标题候选：{premise.title_candidate}",
            f"一句话梗概：{premise.logline}",
            f"核心冲突：{premise.core_conflict}",
            f"开场钩子承诺：{premise.hook_promise}",
            f"结尾回报承诺：{premise.ending_payoff_plan}",
            f"风格关键词：{tone_notes}",
            f"硬约束：{hard_constraints}",
            "任务：写一篇1800-2500字的连续中文短篇正文，整体要有都市情感短剧的钩子、反转、打脸和情绪回报，但成文必须自然成熟。",
            "输出硬性要求：",
            "1. 必须直接输出连续故事正文，不要写提纲、说明、分析或自我解释。",
            "2. 不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕。",
            "3. 不要使用 **SHE**、**HE**、人物名大写标签、人物名+冒号轮流对白、方括号舞台说明、镜头说明、FADE OUT 等脚本格式。",
            "4. 以叙事为主，只在关键冲突处穿插少量短对白，让对白服务于打脸、反转和情绪爆点。",
            "5. 开头两段内进入羞辱、背叛或利益冲突，随后持续升级矛盾，中后段给出明确反转，结尾给足回报。",
            "6. 语言要像自然中文短篇，不要像英文翻译腔，不要空喊口号，不要重复同义句。",
            "主要人物：",
            character_lines,
            "故事节拍：",
            beat_lines,
        ]
    )
