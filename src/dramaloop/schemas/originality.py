from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


_CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
_GENERIC_ONLY_RE = re.compile(
    r"^(?:机制|冲突|反转|故事|设定|规则|细节)?"
    r"(?:很|非常|十分|特别)?"
    r"(?:独特|新颖|复杂|精彩|有趣|合理|巧妙)"
    r"(?:的)?(?:机制|冲突|反转|故事|设定|规则|细节)?[。！!？?]*$"
)
_BANNED_TROPES = (
    "豪门继承",
    "退婚改嫁",
    "直播打脸",
    "万能录音",
    "万能监控",
    "突然身份",
    "神秘身份",
    "大佬救场",
    "重生预知",
    "突然出现的遗嘱",
    "突然出现的亲子鉴定",
)
_NEGATION_MARKERS = ("禁止", "不得", "不能", "不靠", "不依赖", "避免", "拒绝")
_DETAIL_CATEGORY_HINTS = {
    "occupation": (
        "职业",
        "岗位",
        "工种",
        "职责",
        "执业",
        "医生",
        "护士",
        "律师",
        "教师",
        "记者",
        "工人",
        "技师",
        "审计",
        "调度员",
    ),
    "setting": (
        "场域",
        "场所",
        "车间",
        "医院",
        "学校",
        "法庭",
        "矿井",
        "码头",
        "剧场",
        "社区",
        "工地",
        "站台",
    ),
    "institution": (
        "制度",
        "条例",
        "规章",
        "流程",
        "配额",
        "考核",
        "合同",
        "审批",
        "轮班",
        "追责",
        "权限",
    ),
    "object": (
        "物件",
        "设备",
        "工具",
        "钥匙",
        "印章",
        "账本",
        "仪器",
        "工牌",
        "票据",
        "样本",
        "零件",
    ),
    "relationship": (
        "关系",
        "师徒",
        "母女",
        "父子",
        "姐妹",
        "兄弟",
        "同事",
        "搭档",
        "邻里",
        "债务",
        "监护",
    ),
}


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class NoveltyMechanism(StrictModel):
    core_engine: str = Field(min_length=2)
    conflict_source: str = Field(min_length=2)
    reversal_logic: str = Field(min_length=2)
    irreplaceable_details: list[str] = Field(min_length=4)
    why_it_cannot_be_swapped: str = Field(min_length=2)

    @field_validator("irreplaceable_details")
    @classmethod
    def details_must_be_distinct(cls, values: list[str]) -> list[str]:
        normalized = {"".join(value.split()) for value in values}
        if len(normalized) != len(values):
            raise ValueError("irreplaceable_details must not contain duplicates")
        return values


class CharacterArc(StrictModel):
    name: str = Field(min_length=1)
    role: str = Field(min_length=1)
    desire: str = Field(min_length=2)
    blind_spot: str = Field(min_length=2)
    choice_pressure: str = Field(min_length=2)
    arc_payoff: str = Field(min_length=2)


class MechanismBeat(StrictModel):
    stage: str = Field(min_length=1)
    pressure: str = Field(min_length=2)
    choice: str = Field(min_length=2)
    consequence: str = Field(min_length=2)
    next_pressure: str = Field(min_length=2)


class OriginalityPlan(StrictModel):
    idea: str = Field(min_length=2)
    genre: str = Field(min_length=1)
    anti_cliche_constraints: list[str] = Field(min_length=1)
    novelty_mechanism: NoveltyMechanism
    world_rules: list[str] = Field(min_length=2)
    character_arcs: list[CharacterArc] = Field(min_length=1)
    mechanism_beats: list[MechanismBeat] = Field(min_length=3, max_length=5)

    @model_validator(mode="after")
    def require_choice_pressure_and_causal_beat(self) -> "OriginalityPlan":
        if not any(arc.choice_pressure.strip() for arc in self.character_arcs):
            raise ValueError("at least one character arc must include choice_pressure")
        if not any(
            beat.choice.strip() and beat.consequence.strip() and beat.next_pressure.strip()
            for beat in self.mechanism_beats
        ):
            raise ValueError(
                "at least one mechanism beat must include choice, consequence, and next_pressure"
            )
        return self

    @model_validator(mode="after")
    def require_concrete_chinese_mechanism(self) -> "OriginalityPlan":
        errors = collect_quality_errors(self)
        if errors:
            raise ValueError("; ".join(errors))
        return self


def _iter_plan_strings(plan: OriginalityPlan) -> Iterable[tuple[str, str]]:
    def walk(value: Any, path: str) -> Iterable[tuple[str, str]]:
        if isinstance(value, str):
            yield path, value
        elif isinstance(value, list):
            for index, item in enumerate(value):
                yield from walk(item, f"{path}[{index}]")
        elif isinstance(value, dict):
            for key, item in value.items():
                yield from walk(item, f"{path}.{key}" if path else key)

    yield from walk(plan.model_dump(mode="python"), "")


def _contains_unnegated_trope(value: str, trope: str) -> bool:
    start = value.find(trope)
    while start >= 0:
        prefix = value[max(0, start - 8) : start]
        if not any(marker in prefix for marker in _NEGATION_MARKERS):
            return True
        start = value.find(trope, start + len(trope))
    return False


def collect_quality_errors(plan: OriginalityPlan) -> list[str]:
    errors: list[str] = []
    for path, value in _iter_plan_strings(plan):
        if not _CJK_RE.search(value):
            errors.append(f"{path} must contain Chinese content")
        if _GENERIC_ONLY_RE.fullmatch(value.replace(" ", "")):
            errors.append(f"{path} is generic and contains no mechanism")

    details = plan.novelty_mechanism.irreplaceable_details
    categories = {
        category
        for category, hints in _DETAIL_CATEGORY_HINTS.items()
        if any(any(hint in detail for hint in hints) for detail in details)
    }
    if len(categories) < 3:
        errors.append(
            "irreplaceable_details must explicitly cover at least three of "
            "occupation, setting, institution, object, and relationship"
        )

    stages = [beat.stage for beat in plan.mechanism_beats]
    if len(set(stages)) != len(stages):
        errors.append("mechanism_beats stages must be distinct")
    for index, beat in enumerate(plan.mechanism_beats):
        if beat.choice == beat.consequence:
            errors.append(f"mechanism_beats[{index}] choice and consequence must differ")
        if beat.consequence == beat.next_pressure:
            errors.append(f"mechanism_beats[{index}] consequence and next_pressure must differ")

    for path, value in _iter_plan_strings(plan):
        if path.startswith("anti_cliche_constraints"):
            continue
        for trope in _BANNED_TROPES:
            if _contains_unnegated_trope(value, trope):
                errors.append(f"{path} depends on banned trope: {trope}")
    return errors
