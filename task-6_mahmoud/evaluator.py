"""
evaluator.py
============
The main G2 Evaluator orchestrator.

Coordinates:
1. Hard check evaluation (hard_checks.py).
2. Freshness and temporal validity assessment (freshness.py).
3. Criteria scoring and weighted calculation (scorer.py).
4. Strict decision precedence (Reject -> Revise -> Human Review -> Pass).
5. Comprehensive EvaluationReport emission.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from freshness import evaluate_freshness
from hard_checks import run_hard_checks
from models import Case, EvaluationReport
from policy import GatePolicy, get_default_policy
from scorer import calculate_weighted_score, evaluate_criteria


class G2Evaluator:
    """
    Orchestrates G2 Content Quality Gate evaluation for candidate cases.
    """

    def __init__(self, policy: Optional[GatePolicy] = None):
        """
        Initialize the evaluator with a specific policy.
        Defaults to the standard provisional policy if none is provided.
        """
        self.policy = policy or get_default_policy()

    def evaluate_case(self, case: Case, as_of: date) -> EvaluationReport:
        """
        Evaluate a single case and return an authoritative EvaluationReport.

        Enforces strict Decision Precedence:
        1. REJECT: Prohibited/non-remediable violations (e.g. competitor promotion).
        2. REVISE: Remediable defects (unsupported claim, superseded source, stale news).
        3. HUMAN_REVIEW: Information gaps (missing date, contradiction, score < threshold).
        4. PASS: All hard checks passed, criteria >= floor, and score >= threshold.

        Parameters:
            case (Case): The input case to evaluate.
            as_of (date): Reference evaluation date (never datetime.today()).

        Returns:
            EvaluationReport: The comprehensive evaluation output report.
        """
        metadata = case.metadata

        # -------------------------------------------------------------------
        # Step 1: Run Hard Checks
        # -------------------------------------------------------------------
        hard_checks = run_hard_checks(metadata)

        # -------------------------------------------------------------------
        # Step 2: Evaluate Temporal Freshness
        # -------------------------------------------------------------------
        freshness = evaluate_freshness(
            metadata=metadata,
            as_of=as_of,
            news_max_event_age_days=self.policy.news_max_event_age_days,
        )

        # -------------------------------------------------------------------
        # Step 3: Score Required Criteria
        # -------------------------------------------------------------------
        criteria = evaluate_criteria(metadata, freshness)

        # -------------------------------------------------------------------
        # Step 4: Calculate Weighted Score (if eligible)
        # -------------------------------------------------------------------
        score: Optional[float] = None
        if not criteria.has_unknown:
            score = calculate_weighted_score(criteria, self.policy.weights)

        # -------------------------------------------------------------------
        # Step 5: Resolve Decision via Strict Precedence Hierarchy
        # -------------------------------------------------------------------
        decision: str
        reasons: list[str] = []

        # 1. REJECT PRECEDENCE
        # Competitor promotion is strictly prohibited and non-remediable.
        if not hard_checks.no_competitor_promotion:
            decision = "reject"
            reasons.append("COMPETITOR_PROMOTION")

        # 2. REVISE PRECEDENCE
        # Remediable problems: unsupported claim, superseded evidence, or stale news.
        elif not hard_checks.material_claim_supported:
            decision = "revise"
            reasons.append("UNSUPPORTED_CLAIM")

        elif not hard_checks.evidence_not_superseded:
            decision = "revise"
            reasons.append("EVIDENCE_SUPERSEDED")

        elif freshness.status == "stale":
            decision = "revise"
            reasons.append("STALE_EVENT_DATE")

        # 3. HUMAN REVIEW PRECEDENCE
        # Missing information, unknown criteria, contradiction, or below threshold.
        elif not hard_checks.no_contradiction:
            decision = "human_review"
            reasons.append("CONTRADICTING_EVIDENCE")

        elif freshness.status == "unknown" or criteria.has_unknown:
            decision = "human_review"
            reasons.append("UNKNOWN_TEMPORAL_METADATA")

        elif score is not None and score < self.policy.pass_threshold:
            decision = "human_review"
            reasons.append(
                f"WEIGHTED_SCORE_BELOW_THRESHOLD (score={score:.4f} < {self.policy.pass_threshold})"
            )

        # 4. PASS PRECEDENCE
        # All checks passed, all criteria known, floors met, and score >= threshold.
        else:
            decision = "pass"
            reasons.append("ALL_MANDATORY_CHECKS_PASSED")
            reasons.append("ALL_CRITERIA_KNOWN")
            reasons.append(f"THRESHOLD_MET (score={score:.4f} >= {self.policy.pass_threshold})")

        return EvaluationReport(
            case_id=case.id,
            gate="G2",
            policy_version=self.policy.policy_version,
            calibration_status=self.policy.calibration_status,
            hard_checks=hard_checks,
            freshness=freshness,
            criteria=criteria,
            weights=self.policy.weights.to_dict(),
            weights_version=self.policy.weights_version,
            score=score,
            decision=decision,
            reasons=reasons,
        )
