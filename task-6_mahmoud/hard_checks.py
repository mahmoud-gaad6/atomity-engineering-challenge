"""
hard_checks.py
==============
Mandatory hard-check evaluation for the G2 gate.

Hard checks enforce baseline integrity constraints before any weighted scoring
can take place. A failure here guarantees that the case cannot pass.
"""

from __future__ import annotations

from models import CaseMetadata, HardCheckResult


def run_hard_checks(metadata: CaseMetadata) -> HardCheckResult:
    """
    Evaluate all mandatory hard checks for a single case against its metadata.

    Parameters:
        metadata (CaseMetadata): Input metadata containing evidence attributes.

    Returns:
        HardCheckResult: Object containing boolean results for each hard check,
                         along with automated helpers for pass/fail determination.
    """
    # 1. Material claim must be directly supported by evidence
    claim_supported = bool(metadata.supported)

    # 2. Evidence must not be superseded (check flag and status string)
    not_superseded = not (metadata.superseded or metadata.current_status == "superseded")

    # 3. Competitor product promotion is strictly barred
    no_competitor_promotion = not bool(metadata.competitor_product_claim)

    # 4. Evidence must be internally consistent and free from contradictions
    no_contradiction = not bool(metadata.contradiction)

    return HardCheckResult(
        material_claim_supported=claim_supported,
        evidence_not_superseded=not_superseded,
        no_competitor_promotion=no_competitor_promotion,
        no_contradiction=no_contradiction,
    )
