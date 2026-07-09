from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact


CRITIQUE_JSON_SCHEMA = """{
  \"dimension_scores\": {
    \"hook_strength\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"character_consistency\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"conflict_intensity\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"pacing\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"short_drama_feel\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"ending_payoff\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    },
    \"language_fluency\": {
      \"score\": 7,
      \"reason\": \"原因\",
      \"evidence\": \"证据\",
      \"improvement_advice\": \"改进建议\"
    }
  },
  \"overall_score\": 7.0,
  \"weakest_dimensions\": [\"ending_payoff\"],
  \"rewrite_target\": \"ending_payoff\",
  \"rewrite_plan\": {
    \"scope\": \"结尾两段\",
    \"must_fix\": [\"增加终局反杀\"],
    \"keep\": [\"婚礼开头\"]
  }
}"""


def build_critique_prompt(draft_markdown: str, premise: PremiseArtifact, characters: CharacterArtifact, outline: OutlineArtifact) -> str:
    return "\n".join(
        [
            "You are the Critic for a short-drama fiction system.",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            CRITIQUE_JSON_SCHEMA,
            f"Logline: {premise.logline}",
            f"Character count: {len(characters.characters)}",
            f"Beat count: {len(outline.beats)}",
            "Score the draft on hook_strength, character_consistency, conflict_intensity, pacing, short_drama_feel, ending_payoff, and language_fluency.",
            "Return the weakest dimensions, a rewrite target, and a rewrite plan.",
            draft_markdown,
        ]
    )
