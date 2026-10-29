"""
tests/test_weights.py
=====================
Unit tests for policy configurations and weight mathematical validation.
Verifies that:
- Non-negative constraint is strictly enforced (rejects negative weights).
- Unit sum constraint is strictly enforced (rejects sum != 1.0).
- Numerical tolerance allows legitimate floating-point values.
- All preset sensitivity configurations instantiate valid policies.
"""

import math
import unittest
from pydantic import ValidationError

from policy import (
    WeightConfig,
    get_authority_heavy_policy,
    get_default_policy,
    get_equal_weights_policy,
)


class TestWeightsValidation(unittest.TestCase):
    """Test suite for weight configuration constraints."""

    def test_valid_weights(self):
        """Standard valid weights summing to 1.0 must be accepted."""
        config = WeightConfig(
            evidence_support=0.50,
            source_authority=0.25,
            temporal_validity=0.25,
        )
        self.assertEqual(config.evidence_support, 0.50)
        self.assertEqual(config.source_authority, 0.25)
        self.assertEqual(config.temporal_validity, 0.25)
        self.assertEqual(
            config.to_dict(),
            {
                "evidence_support": 0.50,
                "source_authority": 0.25,
                "temporal_validity": 0.25,
            },
        )

    def test_negative_weight_rejected(self):
        """Configurations containing negative weights must raise ValidationError/ValueError."""
        with self.assertRaises(ValidationError) as ctx:
            WeightConfig(
                evidence_support=0.8,
                source_authority=0.3,
                temporal_validity=-0.1,  # Negative weight
            )
        self.assertIn("cannot be negative", str(ctx.exception))

    def test_weight_sum_greater_than_one_rejected(self):
        """Weights summing to more than 1.0 must be rejected."""
        with self.assertRaises(ValidationError) as ctx:
            WeightConfig(
                evidence_support=0.5,
                source_authority=0.4,
                temporal_validity=0.3,  # Sum = 1.2
            )
        self.assertIn("must sum to 1.0", str(ctx.exception))

    def test_weight_sum_less_than_one_rejected(self):
        """Weights summing to less than 1.0 must be rejected."""
        with self.assertRaises(ValidationError) as ctx:
            WeightConfig(
                evidence_support=0.3,
                source_authority=0.3,
                temporal_validity=0.2,  # Sum = 0.8
            )
        self.assertIn("must sum to 1.0", str(ctx.exception))

    def test_floating_point_tolerance(self):
        """Weights with repeating float divisions must pass within numerical tolerance."""
        w1 = 1.0 / 3.0
        w2 = 1.0 / 3.0
        w3 = 1.0 - (w1 + w2)
        config = WeightConfig(
            evidence_support=w1,
            source_authority=w2,
            temporal_validity=w3,
        )
        total = sum(config.to_dict().values())
        self.assertTrue(math.isclose(total, 1.0, rel_tol=1e-5))

    def test_preset_sensitivity_policies(self):
        """All preset sensitivity policies must be valid and conform to constraints."""
        policies = [
            ("default", get_default_policy()),
            ("equal", get_equal_weights_policy()),
            ("authority_heavy", get_authority_heavy_policy()),
        ]

        for name, policy in policies:
            with self.subTest(policy_name=name):
                # Verify non-empty version strings
                self.assertTrue(policy.weights_version)
                self.assertEqual(policy.calibration_status, "uncalibrated")

                # Verify thresholds
                self.assertEqual(policy.pass_threshold, 0.70)
                self.assertEqual(policy.min_criterion_floor, 0.50)

                # Verify weights sum to 1.0
                weights_dict = policy.weights.to_dict()
                total = sum(weights_dict.values())
                self.assertTrue(
                    math.isclose(total, 1.0, rel_tol=1e-5),
                    f"Policy '{name}' weights sum to {total}, expected 1.0",
                )


if __name__ == "__main__":
    unittest.main()
