"""
tests/test_freshness.py
=======================
Unit tests for the temporal validity and freshness logic in freshness.py.
Covers news age calculation, regulatory applicability, unknown dates,
and future regulations against the fixed reference date (2026-10-06).
"""

import unittest
from datetime import date

from freshness import evaluate_freshness
from models import CaseMetadata


class TestFreshness(unittest.TestCase):
    """Test suite for evaluating temporal validity across news and regulations."""

    def setUp(self):
        """Standard fixture setup with the challenge's fixed reference date."""
        self.as_of = date(2026, 10, 6)

    def test_current_news(self):
        """Recent news event within 30-day window must be evaluated as 'current'."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="news",
            published_at=date(2026, 10, 4),
            event_date=date(2026, 10, 3),  # 3 days old relative to as_of
            effective_from=None,
            last_verified_at=date(2026, 10, 6),
            current_status="current",
            supported=True,
            superseded=False,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "current")
        self.assertEqual(result.date_type, "event_date")
        self.assertEqual(result.date_used, date(2026, 10, 3))
        self.assertEqual(result.age_days, 3)
        self.assertIn("within the allowable", result.reason)

    def test_stale_news_old_event(self):
        """Recent article reporting an old event (>30 days) must be evaluated as 'stale'."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="news",
            published_at=date(2026, 10, 5),
            event_date=date(2025, 1, 1),  # Well over 30 days old
            effective_from=None,
            last_verified_at=date(2026, 10, 6),
            current_status="current",
            supported=True,
            superseded=False,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "stale")
        self.assertEqual(result.date_type, "event_date")
        self.assertGreater(result.age_days, 30)
        self.assertIn("exceeding the 30-day threshold", result.reason)

    def test_unknown_event_date_news(self):
        """News with missing event date must result in 'unknown' without guessing."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="news",
            published_at=date(2026, 10, 4),
            event_date=None,  # Missing date
            effective_from=None,
            last_verified_at=date(2026, 10, 6),
            current_status="current",
            supported=True,
            superseded=False,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "unknown")
        self.assertIsNone(result.date_used)
        self.assertIsNone(result.age_days)
        self.assertIn("unavailable", result.reason)

    def test_old_regulation_still_current(self):
        """Old regulation that remains in force must be evaluated as 'current'."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="regulation",
            published_at=date(2021, 1, 1),
            event_date=date(2021, 1, 1),
            effective_from=date(2021, 6, 1),
            last_verified_at=date(2026, 10, 6),
            current_status="current",
            supported=True,
            superseded=False,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "current")
        self.assertEqual(result.date_type, "effective_from")
        self.assertEqual(result.date_used, date(2021, 6, 1))
        self.assertIn("in force", result.reason)

    def test_future_effective_regulation(self):
        """Regulation adopted with future effective date must be evaluated as 'future'."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="regulation",
            published_at=date(2026, 10, 4),
            event_date=date(2026, 10, 3),
            effective_from=date(2027, 1, 1),  # Future date relative to as_of
            last_verified_at=date(2026, 10, 6),
            current_status="adopted_not_applicable",
            supported=True,
            superseded=False,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "future")
        self.assertEqual(result.date_type, "effective_from")
        self.assertEqual(result.date_used, date(2027, 1, 1))
        self.assertIn("in the future", result.reason)

    def test_superseded_regulation(self):
        """Regulation replaced by a newer rule must be evaluated as 'stale'."""
        meta = CaseMetadata(
            source_type="primary_authority",
            content_type="regulation",
            published_at=date(2026, 10, 4),
            event_date=date(2026, 10, 3),
            effective_from=None,
            last_verified_at=date(2026, 10, 6),
            current_status="superseded",
            supported=True,
            superseded=True,
            contradiction=False,
            competitor_product_claim=False,
        )
        result = evaluate_freshness(meta, as_of=self.as_of)

        self.assertEqual(result.status, "stale")
        self.assertIn("superseded", result.reason)


if __name__ == "__main__":
    unittest.main()
