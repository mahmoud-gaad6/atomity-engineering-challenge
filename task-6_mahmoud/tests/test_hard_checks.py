"""
tests/test_hard_checks.py
=========================
Unit tests for mandatory hard checks in hard_checks.py.
Compatible with both standard unittest and pytest.
"""

import unittest
from datetime import date
from hard_checks import run_hard_checks
from models import CaseMetadata


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


class TestHardChecks(unittest.TestCase):
    """Test suite for hard check logic."""

    def test_all_hard_checks_pass(self):
        """Verify that a standard valid case passes all hard checks."""
        meta = create_sample_metadata()
        result = run_hard_checks(meta)

        self.assertTrue(result.material_claim_supported)
        self.assertTrue(result.evidence_not_superseded)
        self.assertTrue(result.no_competitor_promotion)
        self.assertTrue(result.no_contradiction)
        self.assertTrue(result.all_passed)
        self.assertEqual(result.failure_reasons, [])

    def test_unsupported_claim_fails(self):
        """Verify failure when material claim lacks evidence support."""
        meta = create_sample_metadata(supported=False)
        result = run_hard_checks(meta)

        self.assertFalse(result.material_claim_supported)
        self.assertFalse(result.all_passed)
        self.assertIn("UNSUPPORTED_CLAIM", result.failure_reasons)

    def test_superseded_evidence_fails(self):
        """Verify failure when evidence has been superseded."""
        # Test both superseded flag and superseded current_status
        meta_flag = create_sample_metadata(superseded=True)
        self.assertFalse(run_hard_checks(meta_flag).evidence_not_superseded)

        meta_status = create_sample_metadata(current_status="superseded")
        result = run_hard_checks(meta_status)
        self.assertFalse(result.evidence_not_superseded)
        self.assertFalse(result.all_passed)
        self.assertIn("EVIDENCE_SUPERSEDED", result.failure_reasons)

    def test_competitor_promotion_fails(self):
        """Verify failure when content promotes competitor product."""
        meta = create_sample_metadata(competitor_product_claim=True)
        result = run_hard_checks(meta)

        self.assertFalse(result.no_competitor_promotion)
        self.assertFalse(result.all_passed)
        self.assertIn("COMPETITOR_PROMOTION", result.failure_reasons)

    def test_contradicting_evidence_fails(self):
        """Verify failure when evidence contains contradictions."""
        meta = create_sample_metadata(contradiction=True)
        result = run_hard_checks(meta)

        self.assertFalse(result.no_contradiction)
        self.assertFalse(result.all_passed)
        self.assertIn("CONTRADICTING_EVIDENCE", result.failure_reasons)


if __name__ == "__main__":
    unittest.main()
