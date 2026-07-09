from dramaloop.schemas.input import StoryRequest


PREMISE_JSON_SCHEMA = """{
  \"title_candidate\": \"短标题\",
  \"logline\": \"一句话概括故事\",
  \"core_conflict\": \"主冲突\",
  \"hook_promise\": \"开头钩子承诺\",
  \"ending_payoff_plan\": \"结尾回报设计\",
  \"tone_notes\": [\"风格要点1\", \"风格要点2\"],
  \"hard_constraints\": [\"必须满足的约束1\"]
}"""


def build_premise_prompt(request: StoryRequest) -> str:
    return "\n".join(
        [
            "You are the Premise Refiner for a short-drama fiction system.",
            "Return valid JSON only. Do not wrap it in markdown fences. Use the exact field names below.",
            "Required JSON schema:",
            PREMISE_JSON_SCHEMA,
            f"Idea: {request.idea}",
            f"Style tags: {', '.join(request.style)}",
            f"Audience: {request.audience or 'general'}",
            f"Constraints: {', '.join(request.constraints) or 'none'}",
            "Make the premise punchy, dramatic, and executable for a short-drama style story with a strong hook and a clear ending payoff.",
        ]
    )
