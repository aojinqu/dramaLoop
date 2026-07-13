from dramaloop.schemas.input import StoryRequest
from dramaloop.prompts.structured_json import build_json_contract


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
            "你是中文短剧故事前提规划师。",
            *build_json_contract(
                PREMISE_JSON_SCHEMA,
                extra_rules=[
                    "title_candidate 必须是简短的中文标题。",
                    "tone_notes 必须是数组，包含 2-4 个简短风格要点。",
                    "hard_constraints 必须始终是数组，即使只有一条约束也不能变成字符串。",
                ],
            ),
            f"故事想法：{request.idea}",
            f"风格标签：{', '.join(request.style)}",
            f"目标受众：{request.audience or 'general'}",
            f"额外约束：{', '.join(request.constraints) or 'none'}",
            "请把故事前提写得更适合中文短剧：开头要有钩子，冲突要明确，结尾回报要清楚，整体要具备可执行性。",
        ]
    )
