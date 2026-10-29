"""
freshness.py
============
Temporal validity and freshness evaluation engine for the G2 quality gate.

Enforces clear distinctions between:
- Publication date vs Event date vs Effective date.
- News freshness threshold (demo policy: max 30 days old).
- Regulatory applicability (an old law remains valid if currently in force;
  a future-dated law is adopted but not yet applicable).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from models import CaseMetadata, FreshnessResult


def evaluate_freshness(
    metadata: CaseMetadata,
    as_of: date,
    news_max_event_age_days: int = 30,
) -> FreshnessResult:
    """
    Evaluate temporal validity and freshness for a given case.

    Parameters:
        metadata (CaseMetadata): The case metadata containing date attributes.
        as_of (date): Reference evaluation date (never datetime.today()).
        news_max_event_age_days (int): Maximum allowable age in days for news events.

    Returns:
        FreshnessResult: Detailed temporal evaluation result and rationale.
    """
    content_type = metadata.content_type.strip().lower()

    # -----------------------------------------------------------------------
    # 1. EVALUATION FOR NEWS ARTICLES
    # -----------------------------------------------------------------------
    if content_type == "news":
        # Missing event_date cannot be assessed reliably
        if metadata.event_date is None:
            return FreshnessResult(
                status="unknown",
                date_used=None,
                date_type=None,
                age_days=None,
                reason="Event date is unavailable; temporal validity cannot be established.",
            )

        age_days = (as_of - metadata.event_date).days

        if age_days > news_max_event_age_days:
            return FreshnessResult(
                status="stale",
                date_used=metadata.event_date,
                date_type="event_date",
                age_days=age_days,
                reason=(
                    f"News event occurred {age_days} days prior to reference date, "
                    f"exceeding the {news_max_event_age_days}-day threshold."
                ),
            )

        return FreshnessResult(
            status="current",
            date_used=metadata.event_date,
            date_type="event_date",
            age_days=age_days,
            reason=(
                f"News event is within the allowable {news_max_event_age_days}-day "
                f"window ({age_days} days old relative to reference date)."
            ),
        )

    # -----------------------------------------------------------------------
    # 2. EVALUATION FOR REGULATIONS / LEGAL INSTRUMENTS
    # -----------------------------------------------------------------------
    if content_type == "regulation":
        # Superseded regulations are automatically stale
        if metadata.superseded or metadata.current_status == "superseded":
            return FreshnessResult(
                status="stale",
                date_used=metadata.published_at,
                date_type="published_at",
                age_days=None,
                reason="Regulation has been marked as superseded by a newer authority.",
            )

        # Regulations adopted but with a future effective date
        is_future = (
            metadata.current_status == "adopted_not_applicable"
            or (metadata.effective_from is not None and metadata.effective_from > as_of)
        )
        if is_future:
            date_used = metadata.effective_from or metadata.published_at
            date_type = "effective_from" if metadata.effective_from else "published_at"
            return FreshnessResult(
                status="future",
                date_used=date_used,
                date_type=date_type,
                age_days=None,
                reason=(
                    "Regulation is adopted but not yet applicable as its effective "
                    f"date ({date_used}) is in the future."
                ),
            )

        # Active, in-force regulations remain current regardless of publication age
        return FreshnessResult(
            status="current",
            date_used=metadata.effective_from or metadata.published_at,
            date_type="effective_from" if metadata.effective_from else "published_at",
            age_days=None,
            reason=(
                "Regulation is active and currently in force. Publication date does "
                "not diminish legal validity."
            ),
        )

    # -----------------------------------------------------------------------
    # 3. FALLBACK FOR UNRECOGNIZED CONTENT TYPES
    # -----------------------------------------------------------------------
    return FreshnessResult(
        status="unknown",
        date_used=None,
        date_type=None,
        age_days=None,
        reason=f"Unrecognized content_type '{metadata.content_type}'.",
    )
