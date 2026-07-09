from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.premise import PremiseArtifact


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
            "You are the Outliner for a short-drama fiction system.",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            OUTLINE_JSON_SCHEMA,
            f"Title candidate: {premise.title_candidate}",
            f"Logline: {premise.logline}",
            f"Characters: {names}",
            "Return at least five beats covering hook, inciting conflict, escalation, reversal, and ending payoff.",
        ]
    )
