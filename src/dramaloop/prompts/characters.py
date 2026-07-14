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
                    "role 字段保留英文标识，例如 protagonist、antagonist、ally、supporting。",
                    "hidden_secret 可以是字符串或 null，但该字段必须始终存在。",
                ],
            ),
            f"标题候选：{premise.title_candidate}",
            f"一句话概括：{premise.logline}",
            f"核心冲突：{premise.core_conflict}",
            "请设计能最大化冲突、人物反差和后续回报空间的角色卡。",
        ]
    )
