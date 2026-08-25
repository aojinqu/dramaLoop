from dataclasses import dataclass
from difflib import SequenceMatcher
from fnmatch import fnmatch
import json
import re
from typing import Callable, Generic, Literal, TypeVar

import yaml
from pydantic import BaseModel, ValidationError

from dramaloop.harness.stage_graph import get_stage_spec
from dramaloop.schemas.realization import RealizationResult


TOutput = TypeVar("TOutput", bound=BaseModel)


@dataclass(frozen=True)
class RealizedOutput(Generic[TOutput]):
    result: RealizationResult
    output: TOutput | None


def _parse_json(raw_output: str) -> tuple[object, bool]:
    content = raw_output.strip()
    repaired = False
    fenced = re.fullmatch(r"```(?:json|yaml)?\s*(.*?)\s*```", content, flags=re.DOTALL)
    if fenced:
        content = fenced.group(1).strip()
        repaired = True
    try:
        return json.loads(content), repaired
    except json.JSONDecodeError:
        start = min(
            (position for position in (content.find("{"), content.find("[")) if position >= 0),
            default=-1,
        )
        if start >= 0:
            decoder = json.JSONDecoder()
            try:
                payload, _ = decoder.raw_decode(content[start:])
                return payload, True
            except json.JSONDecodeError:
                pass
        try:
            payload = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise json.JSONDecodeError("invalid JSON or YAML", content, 0) from exc
        if not isinstance(payload, (dict, list)):
            raise
        return payload, True


def _validate_raw(
    stage: str,
    raw_output: str,
    response_model: type[TOutput],
) -> RealizedOutput[TOutput]:
    try:
        payload, repaired = _parse_json(raw_output)
        output = response_model.model_validate(payload)
    except (json.JSONDecodeError, ValidationError, TypeError, ValueError) as exc:
        return RealizedOutput(
            result=RealizationResult(
                stage=stage,
                status="blocked",
                issues=[str(exc)],
            ),
            output=None,
        )
    status: Literal["accepted", "repaired"] = "repaired" if repaired else "accepted"
    return RealizedOutput(
        result=RealizationResult(
            stage=stage,
            status=status,
            repair_summary="removed response wrapper and recovered JSON payload"
            if repaired
            else None,
        ),
        output=output,
    )


def realize_structured_output(
    stage: str,
    raw_output: str,
    response_model: type[TOutput],
    *,
    retry: Callable[[str], str] | None = None,
) -> RealizedOutput[TOutput]:
    first = _validate_raw(stage, raw_output, response_model)
    if first.output is not None or retry is None:
        return first

    retry_reason = "; ".join(first.result.issues)
    second = _validate_raw(stage, retry(retry_reason), response_model)
    if second.output is None:
        return RealizedOutput(
            result=second.result.model_copy(
                update={
                    "issues": [*first.result.issues, *second.result.issues],
                    "retry_reason": retry_reason,
                }
            ),
            output=None,
        )
    return RealizedOutput(
        result=second.result.model_copy(
            update={
                "status": "retried",
                "retry_reason": retry_reason,
                "issues": first.result.issues,
            }
        ),
        output=second.output,
    )


def validate_text_output(
    stage: str,
    output: str,
    *,
    required_terms: list[str] | None = None,
) -> RealizationResult:
    issues: list[str] = []
    if not output.strip():
        issues.append("text output was empty")
    missing = [term for term in required_terms or [] if term and term not in output]
    if missing:
        issues.append(f"required contract terms were not covered: {', '.join(missing)}")
    return RealizationResult(
        stage=stage,
        status="blocked" if issues else "accepted",
        issues=issues,
    )


def validate_artifact_output(stage: str, artifact_ref: str) -> RealizationResult:
    spec = get_stage_spec(stage)
    patterns = [re.sub(r"\{[^}]+\}", "*", pattern) for pattern in spec.artifact_outputs]
    valid = any(fnmatch(artifact_ref, pattern) for pattern in patterns)
    return RealizationResult(
        stage=stage,
        status="accepted" if valid else "blocked",
        issues=[]
        if valid
        else [f"artifact {artifact_ref} does not match stage contract: {', '.join(patterns)}"],
    )


def validate_structured_contract(stage: str, output: BaseModel) -> RealizationResult:
    payload = output.model_dump(mode="json")
    issues: list[str] = []
    if stage == "critique_scoring":
        required_dimensions = {
            "hook_strength",
            "character_consistency",
            "conflict_intensity",
            "pacing",
            "short_drama_feel",
            "ending_payoff",
            "language_fluency",
            "originality",
        }
        missing = required_dimensions - set(payload.get("dimension_scores", {}))
        if missing:
            issues.append(f"critique dimensions missing: {', '.join(sorted(missing))}")
    elif stage == "episode_critique_scoring":
        required_dimensions = {
            "hook_strength",
            "conflict_intensity",
            "pacing",
            "short_drama_feel",
            "carryover",
            "originality",
        }
        missing = required_dimensions - set(payload.get("dimension_scores", {}))
        if missing:
            issues.append(f"episode critique dimensions missing: {', '.join(sorted(missing))}")
    return RealizationResult(
        stage=stage,
        status="blocked" if issues else "accepted",
        issues=issues,
    )


def validate_rewrite_coverage(
    original: str,
    revised: str,
    *,
    rewrite_target: str,
) -> RealizationResult:
    issues: list[str] = []
    if not revised.strip() or revised.strip() == original.strip():
        issues.append("rewrite did not change the draft")
    else:
        segment_size = max(80, min(len(original), len(revised)) // 3)
        if rewrite_target == "opening_hook":
            before_segment = original[:segment_size]
            after_segment = revised[:segment_size]
        elif rewrite_target == "ending_payoff":
            before_segment = original[-segment_size:]
            after_segment = revised[-segment_size:]
        elif rewrite_target in {
            "mid_conflict_escalation",
            "reversal_reveal",
            "character_motivation",
        }:
            before_start = max(0, (len(original) - segment_size) // 2)
            after_start = max(0, (len(revised) - segment_size) // 2)
            before_segment = original[before_start : before_start + segment_size]
            after_segment = revised[after_start : after_start + segment_size]
        else:
            before_segment = original
            after_segment = revised
        similarity = SequenceMatcher(None, before_segment, after_segment).ratio()
        if similarity >= 0.98:
            issues.append(f"rewrite did not materially change target {rewrite_target}")
    return RealizationResult(
        stage="targeted_rewrite",
        status="blocked" if issues else "accepted",
        issues=issues,
    )
