from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.prompts.structured_json import build_json_contract


CHARACTER_JSON_SCHEMA = """{
  \"characters\": [
    {
      \"name\": \"角色名\",
      \"role\": \"protagonist\",
      \"public_identity\": \"公开身份\",
      \"core_desire\": \"核心欲望\",
      \"core_fear\": \"核心恐惧\",
      \"hidden_secret\": \"隐藏秘密或 null\",
      \"conflict_links\": [\"关联冲突对象\"],
      \"voice_style\": \"说话风格\",
      \"arc_target\": \"人物弧光\"
    }
  ]
}"""


def build_character_prompt(premise: PremiseArtifact) -> str:
    return "\n".join(
        [
            "你是中文短剧角色设计师。",
            *build_json_contract(
                CHARACTER_JSON_SCHEMA,
                extra_rules=[
                    "characters 必须是非空数组。",
                    "role 字段只能使用 protagonist、antagonist、supporting 三种英文标识。",
                    "hidden_secret 可以是字符串或 null，但该字段必须始终存在。",
                    "每个主要角色必须有与职业、生活经验或现实利益相关的独特行动逻辑，不能只写冷酷大佬、恶毒亲属、隐忍女主等标签。",
                    "至少设计一组非恋爱、非血缘的人物关系，并让冲突来自目标或价值观不兼容，而不只是误会。",
                    "角色的 voice_style 要能在不看姓名时被区分，禁止所有人都使用同一种金句式口吻。",
                ],
            ),
            f"标题候选：{premise.title_candidate}",
            f"一句话概括：{premise.logline}",
            f"核心冲突：{premise.core_conflict}",
            "请设计能最大化冲突、人物反差和后续回报空间的角色卡。",
        ]
    )
