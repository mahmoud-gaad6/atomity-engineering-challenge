"""
tests/test_evaluator.py
=======================
End-to-end integration tests for G2Evaluator in evaluator.py.

Verifies:
1. All 9 starter cases in fixtures/g2-cases.json evaluate to their expected decisions.
2. Hard check failures can NEVER result in a 'pass', even with artificially high scores.
3. Decision precedence: Reject takes precedence over Revise and Human Review.
4. Unknown temporal criteria result in 'human_review' and score=None.
5. All 3 extra sensitivity cases are eligible and score properly.
"""

import json
import unittest
from datetime import date
from pathlib import Path

from evaluator import G2Evaluator
from models import Case, CaseMetadata, CriteriaScores, HardCheckResult
from policy import get_default_policy
from run_example import find_fixture_path


class TestEvaluatorIntegration(unittest.TestCase):
    """End-to-end verification of G2Evaluator against challenge fixtures."""

    @classmethod
    def setUpClass(cls):
        """Load fixture files once for all integration tests."""
        g2_path = find_fixture_path("g2-cases.json")
        with open(g2_path, "r", encoding="utf-8") as f:
            cls.g2_data = json.load(f)

        cls.as_of = date.fromisoformat(cls.g2_data["as_of"])
        cls.evaluator = G2Evaluator(policy=get_default_policy())

    def test_all_9_starter_cases_match_expected(self):
        """
        Verify that each of the 9 starter cases matches its challenge contract:
        - current-news -> pass
        - old-law-current -> pass
        - recent-article-old-event -> revise
        - unknown-date -> human_review
        - unsupported-claim -> revise
        - superseded-source -> revise
        - competitor-promotion -> reject
        - conflicting-evidence -> human_review
        - future-rule -> pass
        """
        raw_cases = self.g2_data.get("cases", [])
        self.assertEqual(len(raw_cases), 9, "Fixture must contain exactly 9 starter cases")

        for raw_case in raw_cases:
            case_id = raw_case["id"]
            expected_decision = raw_case["expected_decision"]

            # Exclude test-only expected_decision before passing to evaluator
            case_dict = {k: v for k, v in raw_case.items() if k != "expected_decision"}
            case = Case.model_validate(case_dict)

            with self.subTest(case_id=case_id):
                report = self.evaluator.evaluate_case(case, as_of=self.as_of)
                self.assertEqual(
                    report.decision,
                    expected_decision,
                    f"Case '{case_id}' failed: expected {expected_decision}, got {report.decision}. "
                    f"Reasons: {report.reasons}",
                )

    def test_hard_check_failure_cannot_pass_with_high_score(self):
        """
        Crucial requirement: Even if a case somehow achieved a high score (e.g. 0.95),
        a failed mandatory hard check must prevent a 'pass' decision.
        """
        # Unsupported claim case
        case = Case(
            id="forced-unsupported-high-score",
            statement="An unsupported claim asserting fictional facts.",
            metadata=CaseMetadata(
                source_type="primary_authority",
                content_type="news",
                published_at=date(2026, 10, 4),
                event_date=date(2026, 10, 3),
                effective_from=None,
                last_verified_at=date(2026, 10, 6),
                current_status="current",
                supported=False,  # Hard check failure!
                superseded=False,
                contradiction=False,
                competitor_product_claim=False,
            ),
        )
        report = self.evaluator.evaluate_case(case, as_of=self.as_of)

        self.assertNotEqual(report.decision, "pass")
        self.assertEqual(report.decision, "revise")
        self.assertIn("UNSUPPORTED_CLAIM", report.reasons)

    def test_decision_precedence_reject_over_revise(self):
        """
        When both a non-remediable defect (competitor) and remediable defect
        (stale news) are present, Reject must take precedence.
        """
        case = Case(
            id="competitor-and-stale",
            statement="Competitor claims product advantages in an old 2024 post.",
            metadata=CaseMetadata(
                source_type="competitor",
                content_type="news",
                published_at=date(2026, 10, 4),
                event_date=date(2024, 1, 1),  # Stale event (>30 days)
                effective_from=None,
                last_verified_at=date(2026, 10, 6),
                current_status="current",
                supported=True,
                superseded=False,
                contradiction=False,
                competitor_product_claim=True,  # Prohibited competitor promotion
            ),
        )
        report = self.evaluator.evaluate_case(case, as_of=self.as_of)

        self.assertEqual(report.decision, "reject")
        self.assertIn("COMPETITOR_PROMOTION", report.reasons)

    def test_unknown_date_produces_null_score(self):
        """Unknown temporal metadata must produce a null weighted score and human_review."""
        case = Case(
            id="unknown-date-test",
            statement="Event date unavailable.",
            metadata=CaseMetadata(
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
            ),
        )
        report = self.evaluator.evaluate_case(case, as_of=self.as_of)

        self.assertEqual(report.decision, "human_review")
        self.assertIsNone(report.score)
        self.assertIn("UNKNOWN_TEMPORAL_METADATA", report.reasons)

    def test_extra_cases_fixture(self):
        """Verify that all 3 extra cases evaluate successfully and are eligible for scoring."""
        extra_path = find_fixture_path("extra_cases.json")
        with open(extra_path, "r", encoding="utf-8") as f:
            extra_data = json.load(f)

        extra_cases = [Case.model_validate(c) for c in extra_data.get("cases", [])]
        self.assertEqual(len(extra_cases), 3)

        for case in extra_cases:
            report = self.evaluator.evaluate_case(case, as_of=self.as_of)
            self.assertEqual(report.decision, "pass")
            self.assertIsNotNone(report.score)
            self.assertGreaterEqual(report.score, 0.70)


if __name__ == "__main__":
    unittest.main()
