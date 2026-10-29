"""
models.py
=========
All Pydantic models for the G2 gate — both input (fixture) and output (reports).

Rule: any data that moves between modules must be defined here.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# INPUT MODELS  (loaded from g2-cases.json)
# ---------------------------------------------------------------------------

class DemoPolicy(BaseModel):
    """
    Evaluation rules embedded in the fixture.
    Example: news_max_event_age_days = 30
    """
    news_max_event_age_days: int
    regulation_rule: str
    unknown_required_temporal_metadata: str
    weights_and_threshold: str


class CaseMetadata(BaseModel):
    """
    Per-case data that the evaluator works on.

    Key flags:
    - event_date=None          → temporal info unknown → human_review
    - supported=False          → hard fail             → revise
    - superseded=True          → hard fail             → revise
    - competitor_product_claim → hard fail             → reject
    - contradiction=True       → hard fail             → human_review
    """
    source_type: str                        # "primary_authority" | "competitor"
    content_type: str                       # "news" | "regulation"
    published_at: date                      # date the article/document was published
    event_date: Optional[date] = None       # date the actual event occurred (may be null)
    effective_from: Optional[date] = None   # date a regulation becomes applicable (may be null)
    last_verified_at: Optional[date] = None
    current_status: str                     # "current" | "superseded" | "adopted_not_applicable"
    supported: bool                         # is the material claim backed by evidence?
    partial_support: bool = False           # does the evidence provide qualified/partial support?
    superseded: bool                        # has the source been replaced by a newer one?
    contradiction: bool                     # do sources disagree on this claim?
    competitor_product_claim: bool          # is this a competitor product promotion?


class Case(BaseModel):
    """
    A single evaluation case: id + statement + metadata.
    Note: expected_decision is intentionally excluded — strip it before parsing.
    """
    id: str
    statement: str
    metadata: CaseMetadata


class G2Fixture(BaseModel):
    """
    The full g2-cases.json file.
    as_of is the fixed reference date — never use today's date for freshness checks.
    """
    schema_version: str
    synthetic: bool
    as_of: date                 # e.g. "2026-10-06" — use this, not datetime.today()
    demo_policy: DemoPolicy
    cases: list[Case]


# ---------------------------------------------------------------------------
# INTERMEDIATE MODELS  (produced during evaluation, consumed by scorer)
# ---------------------------------------------------------------------------

class HardCheckResult(BaseModel):
    """
    Results of the mandatory hard checks.
    A single False here means the case cannot receive a 'pass' decision.
    """
    material_claim_supported: bool   # metadata.supported == True
    evidence_not_superseded: bool    # metadata.superseded == False
    no_competitor_promotion: bool    # metadata.competitor_product_claim == False
    no_contradiction: bool           # metadata.contradiction == False

    @property
    def all_passed(self) -> bool:
        """True only when every hard check passes."""
        return (
            self.material_claim_supported
            and self.evidence_not_superseded
            and self.no_competitor_promotion
            and self.no_contradiction
        )

    @property
    def failure_reasons(self) -> list[str]:
        """Return a list of reason codes for every failed check."""
        reasons: list[str] = []
        if not self.material_claim_supported:
            reasons.append("UNSUPPORTED_CLAIM")
        if not self.evidence_not_superseded:
            reasons.append("EVIDENCE_SUPERSEDED")
        if not self.no_competitor_promotion:
            reasons.append("COMPETITOR_PROMOTION")
        if not self.no_contradiction:
            reasons.append("CONTRADICTING_EVIDENCE")
        return reasons


class FreshnessResult(BaseModel):
    """
    Temporal validity assessment for a case.

    status values:
    - "current"  → evidence is recent and valid
    - "stale"    → news event is older than the policy threshold
    - "future"   → regulation adopted but not yet applicable
    - "unknown"  → required date is missing
    """
    status: str                          # current | stale | future | unknown
    date_used: Optional[date] = None     # which date was evaluated
    date_type: Optional[str] = None      # "event_date" | "effective_from" | None
    age_days: Optional[int] = None       # age of the event in days (news only)
    reason: str                          # human-readable explanation


class CriteriaScores(BaseModel):
    """
    Scores for the three G2 criteria.
    Each value is 0.0, 0.5, or 1.0 — or None if the criterion is unknown.

    IMPORTANT: unknown != 0.  Never convert None to 0 silently.
    """
    evidence_support: Optional[float] = None
    source_authority: Optional[float] = None
    temporal_validity: Optional[float] = None

    @field_validator(
        "evidence_support", "source_authority", "temporal_validity",
        mode="before",
    )
    @classmethod
    def _check_score_range(cls, v: float | None) -> float | None:
        """Reject any score outside [0, 1]."""
        if v is not None and not (0.0 <= v <= 1.0):
            raise ValueError(f"Score must be between 0.0 and 1.0, got {v!r}")
        return v

    @property
    def has_unknown(self) -> bool:
        """True if any criterion is unknown (None)."""
        return any(
            s is None
            for s in (self.evidence_support, self.source_authority, self.temporal_validity)
        )


# ---------------------------------------------------------------------------
# OUTPUT MODEL  (final evaluation report, one per case)
# ---------------------------------------------------------------------------

class EvaluationReport(BaseModel):
    """
    The final G2 evaluation report for a single case.
    This is what gets printed, saved, and reviewed.
    """
    case_id: str
    gate: str = "G2"
    policy_version: str = "prototype-v1"
    calibration_status: str = "uncalibrated"

    hard_checks: HardCheckResult
    freshness: FreshnessResult
    criteria: CriteriaScores

    weights: dict[str, float]          # weights actually used for scoring
    weights_version: str = "provisional-v1"

    score: Optional[float] = None      # None when any criterion is unknown
    decision: str                      # "pass" | "revise" | "reject" | "human_review"
    reasons: list[str]                 # list of reason codes explaining the decision
