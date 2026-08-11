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
            "任务：写一篇1800-2500字的连续中文短篇正文，要有短剧的钩子、升级、反转和情绪回报，但成文必须自然成熟且具有不可替换的故事细节。",
            "输出硬性要求：",
            "1. 必须直接输出连续故事正文，不要写提纲、说明、分析或自我解释。",
            "2. 不要使用 Beat 1/Beat 2、Scene、Act、小标题分幕。",
            "3. 不要使用 **SHE**、**HE**、人物名大写标签、人物名+冒号轮流对白、方括号舞台说明、镜头说明、FADE OUT 等脚本格式。",
            "4. 以叙事为主，只在关键冲突处穿插少量短对白，让对白服务于打脸、反转和情绪爆点。",
            "5. 开头两段内让人物面对一个具体且必须立刻处理的问题；问题可以来自工作、关系、制度、承诺或资源冲突，不要默认写公开羞辱。",
            "6. 语言要像自然中文短篇，不要像英文翻译腔，不要空喊口号，不要重复同义句。",
            "7. 至少使用三个来自当前设定的具体细节推动因果，例如专业动作、地方习俗、制度限制、旧物或空间结构；这些细节不能只作装饰。",
            "8. 反转必须来自人物此前的选择或已埋下的细节，不要用突然出现的录音、监控、身份或大佬救场代替因果。",
            "9. 除非输入明确要求，禁止复用婚礼退婚后改嫁宿敌、豪门继承争夺、直播公开打脸、重生预知复仇等现成骨架。",
            "10. 不要滥用“全场哗然、脸色惨白、众叛亲离”等通用反应；用具体人物的具体损失呈现回报。",
            "主要人物：",
            character_lines,
            "故事节拍：",
            beat_lines,
        ]
    )
