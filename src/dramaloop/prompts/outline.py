from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.prompts.structured_json import build_json_contract


OUTLINE_JSON_SCHEMA = """{
  \"beats\": [
    {
      \"beat_id\": \"b1\",
      \"label\": \"hook\",
      \"purpose\": \"抓人目的\",
      \"summary\": \"这一拍发生了什么\",
      \"tension_level\": 9,
      \"payoff_dependency\": null
    }
  ],
  \"ending_type\": \"revenge payoff\"
}"""


def build_outline_prompt(premise: PremiseArtifact, characters: CharacterArtifact) -> str:
    names = ", ".join(character.name for character in characters.characters)
    return "\n".join(
        [
            "你是中文短剧大纲设计师。",
            *build_json_contract(
                OUTLINE_JSON_SCHEMA,
                extra_rules=[
                    "beats 至少包含 5 个条目。",
                    "beat_id 必须写成 b1、b2、b3 这种形式。",
                    "tension_level 必须是 1 到 10 的整数。",
                    "ending_type 必须是简短字符串，不能是对象。",
                ],
            ),
            f"标题候选：{premise.title_candidate}",
            f"一句话概括：{premise.logline}",
            f"主要角色：{names}",
            "请至少输出 5 个 beats，覆盖 hook、冲突引爆、升级、反转和结尾回报。",
        ]
    )
