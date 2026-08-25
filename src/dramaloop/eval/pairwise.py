from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from dramaloop.llm.base import LLMClient
from dramaloop.storage.artifacts import write_json_artifact


class PairwiseJudgment(BaseModel):
    winner: Literal["A", "B", "tie"]
    dimension_winners: dict[str, Literal["A", "B", "tie"]] = Field(default_factory=dict)
    rationale: str = Field(min_length=1)


def _prompt(story_a: str, story_b: str) -> str:
    return (
        "你是独立短剧评审。比较 A/B 两个输出，判断整体 winner，并按 hook_strength、"
        "conflict_intensity、pacing、short_drama_feel、character_consistency、continuity、"
        "context_fidelity、rewrite_effectiveness、originality 给出 dimension_winners。"
        "originality 优先比较冲突机制、场景、人物关系和关键意象是否具体且不可互换，"
        "对只替换名字的退婚改嫁、豪门打脸、直播翻盘等套式严格判负。"
        "winner 及每个维度只能是 A、B 或 tie。只返回符合 JSON Schema 的 JSON。\n\n"
        f"JSON Schema:\n{PairwiseJudgment.model_json_schema()}\n\n"
        f"A:\n{story_a}\n\nB:\n{story_b}"
    )


def compare_runs(
    run_a: Path,
    run_b: Path,
    client: LLMClient,
    *,
    output_path: Path | None = None,
) -> dict:
    story_a = (run_a / "final_story.md").read_text(encoding="utf-8")
    story_b = (run_b / "final_story.md").read_text(encoding="utf-8")
    forward = client.generate_structured(
        role="research_pairwise_judge",
        prompt=_prompt(story_a, story_b),
        response_model=PairwiseJudgment,
    )
    reverse = client.generate_structured(
        role="research_pairwise_judge",
        prompt=_prompt(story_b, story_a),
        response_model=PairwiseJudgment,
    )
    reverse_winner = {"A": "B", "B": "A", "tie": "tie"}[reverse.winner]
    winner = forward.winner if forward.winner == reverse_winner else "tie"

    dimensions = set(forward.dimension_winners) | set(reverse.dimension_winners)
    dimension_winners: dict[str, str] = {}
    for dimension in dimensions:
        first = forward.dimension_winners.get(dimension, "tie")
        second = {
            "A": "B",
            "B": "A",
            "tie": "tie",
        }[reverse.dimension_winners.get(dimension, "tie")]
        dimension_winners[dimension] = first if first == second else "tie"

    result = {
        "run_a": run_a.name,
        "run_b": run_b.name,
        "winner": winner,
        "dimension_winners": dimension_winners,
        "position_swapped": True,
        "judgments": [
            forward.model_dump(mode="json"),
            reverse.model_dump(mode="json"),
        ],
    }
    if output_path is not None:
        write_json_artifact(output_path, result)
    return result
