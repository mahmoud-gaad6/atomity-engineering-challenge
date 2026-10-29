"""
scorer.py
=========
Criteria evaluation and weighted scoring engine for the G2 gate.

Enforces:
- Explicit observable anchors for scores: 0.0, 0.5, 1.0.
- Strict unknown handling: unknown criterion remains None and is NEVER converted to 0.
- Null weighted score propagation when any required criterion is unknown.
- Transparent weighted-sum calculation: score = sum(weight_i * criterion_i).
"""

from __future__ import annotations

from typing import Optional

from models import CaseMetadata, CriteriaScores, FreshnessResult
from policy import WeightConfig


def evaluate_criteria(
    metadata: CaseMetadata,
    freshness: FreshnessResult,
) -> CriteriaScores:
    """
    Map case attributes and temporal freshness to normalized criterion scores.

    Anchors:
    - evidence_support:
        1.0: Claim is directly supported by evidence without contradiction.
        0.5: Evidence provides partial or qualified support.
        0.0: Claim is unsupported or contradicted.
        None: Evidence support is unknown or cannot be assessed.

    - source_authority:
        1.0: Source is primary_authority.
        0.5: Source is secondary_authority or qualified authority.
        0.0: Source is competitor or lacks authority.
        None: Source authority is unknown.

    - temporal_validity:
        1.0: Freshness status is 'current' or validly 'future' (not superseded).
        0.5: Timing is partially applicable or requires qualification.
        0.0: Freshness status is 'stale' or superseded.
        None: Freshness status is 'unknown'.

    Parameters:
        metadata (CaseMetadata): The case evidence metadata.
        freshness (FreshnessResult): The evaluated temporal status.

    Returns:
        CriteriaScores: Scores for the 3 criteria (values in [0.0, 1.0] or None).
    """
    # -----------------------------------------------------------------------
    # 1. EVIDENCE SUPPORT ANCHOR
    # -----------------------------------------------------------------------
    evidence_score: Optional[float]
    if metadata.supported is True:
        if metadata.contradiction is True:
            # Contradicting evidence reduces support to 0.0 or requires review
            evidence_score = 0.0
        elif getattr(metadata, "partial_support", False):
            evidence_score = 0.5
        else:
            evidence_score = 1.0
    elif metadata.supported is False:
        evidence_score = 0.0
    else:
        evidence_score = None

    # -----------------------------------------------------------------------
    # 2. SOURCE AUTHORITY ANCHOR
    # -----------------------------------------------------------------------
    source_score: Optional[float]
    src_type = (metadata.source_type or "").strip().lower()

    if metadata.competitor_product_claim or src_type == "competitor":
        source_score = 0.0
    elif src_type == "primary_authority":
        source_score = 1.0
    elif src_type in ("secondary_authority", "industry_report", "academic"):
        source_score = 0.5
    elif not src_type:
        source_score = None
    else:
        # Default fallback for unrecognized non-authoritative source
        source_score = 0.0

    # -----------------------------------------------------------------------
    # 3. TEMPORAL VALIDITY ANCHOR
    # -----------------------------------------------------------------------
    temporal_score: Optional[float]
    if freshness.status == "unknown":
        temporal_score = None
    elif metadata.superseded or metadata.current_status == "superseded":
        temporal_score = 0.0
    elif freshness.status == "stale":
        temporal_score = 0.0
    elif freshness.status in ("current", "future"):
        temporal_score = 1.0
    else:
        temporal_score = None

    return CriteriaScores(
        evidence_support=evidence_score,
        source_authority=source_score,
        temporal_validity=temporal_score,
    )


def calculate_weighted_score(
    criteria: CriteriaScores,
    weights: WeightConfig,
) -> Optional[float]:
    """
    Calculate the transparent weighted sum score:
        score = sum(weight_i * criterion_i)

    Strict rule: If ANY criterion is None (unknown), this function MUST return None.
    Unknown values are never silently coerced to 0.0 or a default number.

    Parameters:
        criteria (CriteriaScores): Evaluated scores for each criterion.
        weights (WeightConfig): Validated weight configuration (sums to 1.0).

    Returns:
        Optional[float]: Weighted score rounded to 4 decimal places,
                         or None if any criterion is unknown.
    """
    # Guard: if any criterion is unknown, weighted score cannot be calculated
    if criteria.has_unknown:
        return None

    score = (
        (weights.evidence_support * criteria.evidence_support)
        + (weights.source_authority * criteria.source_authority)
        + (weights.temporal_validity * criteria.temporal_validity)
    )

    # Clamp and round to 4 decimal places for floating-point cleanliness
    score = max(0.0, min(1.0, score))
    return round(score, 4)
