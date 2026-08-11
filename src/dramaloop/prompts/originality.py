from __future__ import annotations

from collections.abc import Sequence

from dramaloop.schemas.input import StoryRequest


PLANNER_SYSTEM_PROMPT = (
    "你是中文短剧原创机制规划器。你只输出合法 JSON object；字段名使用英文，"
    "字段内容使用中文。不写正文、不输出 Markdown、不解释。冲突必须来自具体职业、"
    "场域、制度、物件或人物关系；反转必须来自人物选择与既有信息。"
    "顶层字段必须且只能是 idea、genre、anti_cliche_constraints、"
    "novelty_mechanism、world_rules、character_arcs、mechanism_beats。"
    "novelty_mechanism 必须且只能包含 core_engine、conflict_source、"
    "reversal_logic、irreplaceable_details、why_it_cannot_be_swapped。"
    "character_arcs 每项必须且只能包含 name、role、desire、blind_spot、"
    "choice_pressure、arc_payoff。mechanism_beats 每项必须且只能包含 stage、"
    "pressure、choice、consequence、next_pressure，并且只能有三至五项。"
    "禁止输出 title、plan、nodes、plotOutline、mechanism_nodes 或其他替代字段。"
)

DEFAULT_ANTI_CLICHE_CONSTRAINTS = (
    "不得依赖未铺垫的身份揭露、万能证据或突然救场",
    "反转必须来自既有世界规则、人物选择及其后果",
    "职业、制度、场域、物件和人物关系必须具体且不可随意替换",
)


def planner_constraints(request: StoryRequest) -> list[str]:
    constraints = [*DEFAULT_ANTI_CLICHE_CONSTRAINTS, *request.constraints]
    return list(dict.fromkeys(item.strip() for item in constraints if item.strip()))


def render_planner_user_prompt(
    *,
    idea: str,
    genre: str,
    anti_cliche_constraints: Sequence[str],
) -> str:
    constraints = "；".join(anti_cliche_constraints)
    return (
        "请生成一个可由后续整季和分集规划执行的紧凑 OriginalityPlan。\n"
        f"故事创意：{idea}\n"
        f"题材：{genre}\n"
        f"约束与禁用套路：{constraints}\n"
        "只生成三至五个机制推进节点，不写正文或完整分集。\n"
        "必须严格使用系统消息规定的全部字段，不得使用同义替代字段。"
    )


def build_originality_plan_prompt(request: StoryRequest) -> str:
    return render_planner_user_prompt(
        idea=request.idea,
        genre="、".join(request.style),
        anti_cliche_constraints=planner_constraints(request),
    )
