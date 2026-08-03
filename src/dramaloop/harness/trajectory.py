from dramaloop.schemas.trajectory import RegulationDecision, TrajectorySignal


_DIMENSION_TARGETS = {
    "hook_strength": "opening_hook",
    "character_consistency": "character_motivation",
    "conflict_intensity": "mid_conflict_escalation",
    "pacing": "mid_conflict_escalation",
    "short_drama_feel": "reversal_reveal",
    "ending_payoff": "ending_payoff",
    "language_fluency": "prose_fluency",
}


class TrajectoryRegulator:
    def __init__(self, *, max_rewrites: int = 1) -> None:
        self.max_rewrites = max_rewrites

    def target_for_dimension(self, dimension: str) -> str:
        return _DIMENSION_TARGETS.get(dimension, dimension)

    def align_rewrite_target(
        self,
        *,
        stage: str,
        weakest_dimensions: list[str],
        rewrite_target: str,
    ) -> RegulationDecision:
        weakest = weakest_dimensions[0] if weakest_dimensions else rewrite_target
        expected_target = self.target_for_dimension(weakest)
        if rewrite_target == expected_target:
            return RegulationDecision(
                stage=stage,
                action="continue",
                reason="rewrite target already matches weakest critique dimension",
            )
        signal = TrajectorySignal(
            stage=stage,
            signal_type="rewrite_target_mismatch",
            severity="warning",
            evidence=[f"weakest_dimension={weakest}", f"rewrite_target={rewrite_target}"],
            recommended_action=f"use target {weakest}",
        )
        return RegulationDecision(
            stage=stage,
            action="rewrite",
            reason="rewrite target aligned to weakest critique dimension",
            signals=[signal],
        )

    def decide_rewrite(
        self,
        *,
        stage: str,
        rewrite_needed: bool,
        rewrite_count: int,
    ) -> RegulationDecision:
        if not rewrite_needed:
            return RegulationDecision(
                stage=stage,
                action="continue",
                reason="critique does not require rewrite",
            )
        if rewrite_count >= self.max_rewrites:
            return RegulationDecision(
                stage=stage,
                action="stop",
                reason="maximum rewrite count reached",
                signals=[
                    TrajectorySignal(
                        stage=stage,
                        signal_type="rewrite_limit",
                        severity="info",
                        evidence=[f"rewrite_count={rewrite_count}"],
                        recommended_action="stop rewriting and preserve the best available draft",
                    )
                ],
            )
        return RegulationDecision(
            stage=stage,
            action="rewrite",
            reason="critique requires one targeted rewrite",
        )

    def decide_retry(
        self,
        *,
        stage: str,
        consecutive_failures: int,
        max_retries: int = 2,
    ) -> RegulationDecision:
        if consecutive_failures >= max_retries:
            return RegulationDecision(
                stage=stage,
                action="stop",
                reason="stage retry limit reached",
            )
        return RegulationDecision(
            stage=stage,
            action="retry_stage",
            reason="stage failure is recoverable",
        )
