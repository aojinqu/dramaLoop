from dramaloop.schemas.character import CharacterArtifact
from dramaloop.schemas.outline import OutlineArtifact
from dramaloop.schemas.premise import PremiseArtifact
from dramaloop.prompts.structured_json import build_json_contract


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
            "你是中文短剧文本审稿与打分助手。",
            *build_json_contract(
                CRITIQUE_JSON_SCHEMA,
                extra_rules=[
                    "dimension_scores 必须且只能包含这些 key：hook_strength、character_consistency、conflict_intensity、pacing、short_drama_feel、ending_payoff、language_fluency。",
                    "每个 score 都必须是 1 到 10 的整数。",
                    "weakest_dimensions 必须是已有维度 key 组成的数组。",
                    "rewrite_plan.must_fix 和 rewrite_plan.keep 都必须是数组。",
                ],
            ),
            f"一句话概括：{premise.logline}",
            f"角色数量：{len(characters.characters)}",
            f"大纲节拍数：{len(outline.beats)}",
            "请对草稿在 hook_strength、character_consistency、conflict_intensity、pacing、short_drama_feel、ending_payoff、language_fluency 这些维度上进行打分。",
            "同时输出 weakest_dimensions、rewrite_target 和 rewrite_plan。",
            draft_markdown,
        ]
    )
