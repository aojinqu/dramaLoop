from dramaloop.schemas.premise import PremiseArtifact


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
            "You are the Character Designer for a short-drama fiction system.",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            CHARACTER_JSON_SCHEMA,
            f"Title candidate: {premise.title_candidate}",
            f"Logline: {premise.logline}",
            f"Core conflict: {premise.core_conflict}",
            "Create character cards that maximize conflict, voice contrast, and payoff potential.",
        ]
    )
