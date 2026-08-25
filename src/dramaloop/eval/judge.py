from pathlib import Path

from pydantic import BaseModel, Field, computed_field

from dramaloop.llm.base import LLMClient
from dramaloop.storage.artifacts import write_json_artifact


class JudgeDimensions(BaseModel):
    hook_strength: float = Field(ge=1, le=10)
    conflict_intensity: float = Field(ge=1, le=10)
    pacing: float = Field(ge=1, le=10)
    short_drama_feel: float = Field(ge=1, le=10)
    character_consistency: float = Field(ge=1, le=10)
    continuity: float = Field(ge=1, le=10)
    context_fidelity: float = Field(ge=1, le=10)
    rewrite_effectiveness: float = Field(ge=1, le=10)
    originality: float = Field(ge=1, le=10)


class JudgeResult(BaseModel):
    dimensions: JudgeDimensions
    rationale: str = Field(min_length=1)

    @computed_field
    def average_score(self) -> float:
        values = list(self.dimensions.model_dump().values())
        return round(sum(values) / len(values), 2)


def _build_judge_prompt(story: str, context_trace: str) -> str:
    schema = JudgeResult.model_json_schema()
    return (
        "你是独立的短剧质量评审。请按 1-10 分评估九个维度，只根据给出的故事和运行上下文作答。"
        "context_fidelity 检查故事是否保留用户约束，rewrite_effectiveness 检查改写是否针对弱项；"
        "originality 检查核心冲突机制、人物关系、场景与关键意象是否具有不可替换的具体性。"
        "若故事只是复用退婚改嫁、豪门打脸、直播翻盘、重生复仇等常见骨架并替换名字，"
        "或依赖大佬救场、证据大屏、全场哗然等快捷桥段，应在 originality 上严格扣分；"
        "若没有改写，按最终文本是否结构完整评分。只返回符合 JSON Schema 的 JSON。\n\n"
        f"JSON Schema:\n{schema}\n\n"
        f"故事：\n{story}\n\n"
        f"上下文轨迹：\n{context_trace[-6000:]}"
    )


def run_judge(run_dir: Path, client: LLMClient) -> JudgeResult:
    story = (run_dir / "final_story.md").read_text(encoding="utf-8")
    context_path = run_dir / "context_trace.jsonl"
    context_trace = context_path.read_text(encoding="utf-8") if context_path.exists() else ""
    result = client.generate_structured(
        role="research_judge",
        prompt=_build_judge_prompt(story, context_trace),
        response_model=JudgeResult,
    )
    write_json_artifact(run_dir / "eval" / "judge_baseline.json", result)
    return result
