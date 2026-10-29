"""
tests/test_scorer.py
====================
Unit tests for criterion anchor evaluations and weighted scoring in scorer.py.
Verifies that:
- Explicit anchors (1.0, 0.5, 0.0) map accurately from case evidence.
- Unknown criteria evaluate to None (never coerced to 0.0).
- Weighted score evaluates to None whenever any criterion is unknown.
- Weighted sum mathematics are computed accurately and clamped to [0.0, 1.0].
"""

import unittest
from datetime import date

from models import CaseMetadata, CriteriaScores, FreshnessResult
from policy import WeightConfig, get_default_policy
from scorer import calculate_weighted_score, evaluate_criteria


def create_sample_metadata(**kwargs) -> CaseMetadata:
    """Helper to instantiate CaseMetadata with standard baseline defaults."""
    defaults = {
        "source_type": "primary_authority",
        "content_type": "news",
        "published_at": date(2026, 10, 4),
        "event_date": date(2026, 10, 3),
        "effective_from": None,
        "last_verified_at": date(2026, 10, 6),
        "current_status": "current",
        "supported": True,
        "superseded": False,
        "contradiction": False,
        "competitor_product_claim": False,
    }
    defaults.update(kwargs)
    return CaseMetadata(**defaults)


class TestScorer(unittest.TestCase):
    """Test suite for criteria score evaluation and weighted scoring calculation."""

    def setUp(self):
        """Standard fixture setup with default policy weights."""
        self.default_weights = get_default_policy().weights
        self.fresh_result = FreshnessResult(
            status="current",
            date_used=date(2026, 10, 3),
            date_type="event_date",
            age_days=3,
            reason="Fresh event",
        )

    def test_perfect_scores_and_weighted_sum(self):
        """A fully supported primary authority case must score 1.0 across all criteria."""
        meta = create_sample_metadata()
        criteria = evaluate_criteria(meta, self.fresh_result)

        self.assertEqual(criteria.evidence_support, 1.0)
        self.assertEqual(criteria.source_authority, 1.0)
        self.assertEqual(criteria.temporal_validity, 1.0)

        score = calculate_weighted_score(criteria, self.default_weights)
        self.assertEqual(score, 1.0)

    def test_unsupported_claim_anchor(self):
        """Unsupported claim must yield 0.0 for evidence support."""
        meta = create_sample_metadata(supported=False)
        criteria = evaluate_criteria(meta, self.fresh_result)

        self.assertEqual(criteria.evidence_support, 0.0)

    def test_contradiction_anchor(self):
        """Contradicting evidence must yield 0.0 for evidence support."""
        meta = create_sample_metadata(contradiction=True)
        criteria = evaluate_criteria(meta, self.fresh_result)

        self.assertEqual(criteria.evidence_support, 0.0)

    def test_competitor_source_anchor(self):
        """Competitor source or product promotion must yield 0.0 for source authority."""
        meta_competitor = create_sample_metadata(source_type="competitor")
        criteria_comp = evaluate_criteria(meta_competitor, self.fresh_result)
        self.assertEqual(criteria_comp.source_authority, 0.0)

        meta_claim = create_sample_metadata(competitor_product_claim=True)
        criteria_claim = evaluate_criteria(meta_claim, self.fresh_result)
        self.assertEqual(criteria_claim.source_authority, 0.0)

    def test_secondary_authority_anchor(self):
        """Secondary authority source must yield 0.5 for source authority."""
        meta = create_sample_metadata(source_type="secondary_authority")
        criteria = evaluate_criteria(meta, self.fresh_result)

        self.assertEqual(criteria.source_authority, 0.5)

    def test_stale_and_superseded_anchor(self):
        """Stale freshness or superseded evidence must yield 0.0 for temporal validity."""
        stale_fresh = FreshnessResult(
            status="stale",
            date_used=date(2025, 1, 1),
            date_type="event_date",
            age_days=100,
            reason="Old event",
        )
        meta = create_sample_metadata()
        criteria_stale = evaluate_criteria(meta, stale_fresh)
        self.assertEqual(criteria_stale.temporal_validity, 0.0)

        meta_superseded = create_sample_metadata(superseded=True)
        criteria_superseded = evaluate_criteria(meta_superseded, self.fresh_result)
        self.assertEqual(criteria_superseded.temporal_validity, 0.0)

    def test_unknown_criterion_propagates_none(self):
        """
        Critical requirement: An unknown criterion must evaluate to None,
        and calculate_weighted_score MUST return None, NOT 0.0.
        """
        unknown_fresh = FreshnessResult(
            status="unknown",
            date_used=None,
            date_type=None,
            age_days=None,
            reason="Missing date",
        )
        meta = create_sample_metadata(event_date=None)
        criteria = evaluate_criteria(meta, unknown_fresh)

        # 1. Temporal validity must be None (never 0.0)
        self.assertIsNone(criteria.temporal_validity)
        self.assertTrue(criteria.has_unknown)

        # 2. Weighted score must be None
        score = calculate_weighted_score(criteria, self.default_weights)
        self.assertIsNone(score)

    def test_weighted_score_math_precision(self):
        """Verify accurate calculation with non-trivial fractional criterion scores."""
        # evidence = 1.0, authority = 0.5, temporal = 1.0
        # weights = (0.50, 0.25, 0.25)
        # Expected: 0.50*1.0 + 0.25*0.5 + 0.25*1.0 = 0.50 + 0.125 + 0.25 = 0.875
        criteria = CriteriaScores(
            evidence_support=1.0,
            source_authority=0.5,
            temporal_validity=1.0,
        )
        score = calculate_weighted_score(criteria, self.default_weights)
        self.assertEqual(score, 0.875)


if __name__ == "__main__":
    unittest.main()
