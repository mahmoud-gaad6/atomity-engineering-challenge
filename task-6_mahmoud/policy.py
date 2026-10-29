"""
policy.py
=========
G2 Gate policy configuration, weight definitions, and mathematical constraints.

Enforces:
- Non-negative weight validation (w_i >= 0).
- Unit sum constraint (sum(w_i) == 1.0 within floating point tolerance).
- Explicit provisional status marking (prototype-v1, uncalibrated).
- Preset configurations for sensitivity analysis (default, equal, authority-heavy).
"""

from __future__ import annotations

import math
from typing import Self

from pydantic import BaseModel, Field, model_validator


class WeightConfig(BaseModel):
    """
    Criterion weights configuration for the G2 evaluation gate.

    Attributes:
        evidence_support (float): Weight assigned to evidence grounding.
        source_authority (float): Weight assigned to institutional authority.
        temporal_validity (float): Weight assigned to temporal freshness.
    """
    evidence_support: float = Field(..., description="Weight for evidence support")
    source_authority: float = Field(..., description="Weight for source authority")
    temporal_validity: float = Field(..., description="Weight for temporal validity")

    @model_validator(mode="after")
    def validate_weights(self) -> Self:
        """
        Validate that all weights are non-negative and sum to 1.0.

        Raises:
            ValueError: If any weight is negative or if sum deviates from 1.0.
        """
        weights = [
            self.evidence_support,
            self.source_authority,
            self.temporal_validity,
        ]

        # 1. Non-negativity check
        for name, val in [
            ("evidence_support", self.evidence_support),
            ("source_authority", self.source_authority),
            ("temporal_validity", self.temporal_validity),
        ]:
            if val < 0.0:
                raise ValueError(f"Weight '{name}' cannot be negative, got {val}")

        # 2. Sum-to-one constraint check with floating point tolerance
        total = sum(weights)
        if not math.isclose(total, 1.0, rel_tol=1e-5, abs_tol=1e-5):
            raise ValueError(
                f"Weights must sum to 1.0, got sum = {total:.6f} "
                f"(evidence={self.evidence_support}, authority={self.source_authority}, "
                f"temporal={self.temporal_validity})"
            )

        return self

    def to_dict(self) -> dict[str, float]:
        """Convert weights to a standard dictionary format."""
        return {
            "evidence_support": self.evidence_support,
            "source_authority": self.source_authority,
            "temporal_validity": self.temporal_validity,
        }


class GatePolicy(BaseModel):
    """
    Evaluation policy governing thresholding, weight versions, and decision floors.
    """
    policy_version: str = "prototype-v1"
    weights_version: str = "provisional-v1"
    calibration_status: str = "uncalibrated"

    weights: WeightConfig
    pass_threshold: float = Field(
        default=0.70,
        ge=0.0,
        le=1.0,
        description="Minimum weighted score required for a pass decision",
    )
    min_criterion_floor: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
        description="Floor score required for each individual criterion to pass",
    )
    news_max_event_age_days: int = Field(
        default=30,
        ge=1,
        description="Maximum age in days for news events under the demo policy",
    )


# ---------------------------------------------------------------------------
# PRESET POLICY FACTORIES FOR SENSITIVITY COMPARISON
# ---------------------------------------------------------------------------

def get_default_policy() -> GatePolicy:
    """
    Default provisional policy: prioritizes evidence support (50%),
    with equal balance between authority (25%) and temporal validity (25%).
    """
    return GatePolicy(
        weights_version="provisional-default-v1",
        weights=WeightConfig(
            evidence_support=0.50,
            source_authority=0.25,
            temporal_validity=0.25,
        ),
        pass_threshold=0.70,
        min_criterion_floor=0.50,
        news_max_event_age_days=30,
    )


def get_equal_weights_policy() -> GatePolicy:
    """
    Baseline neutral policy: equal weights across all three criteria (1/3 each).
    """
    return GatePolicy(
        weights_version="provisional-equal-v1",
        weights=WeightConfig(
            evidence_support=1.0 / 3.0,
            source_authority=1.0 / 3.0,
            temporal_validity=1.0 - (2.0 / 3.0),  # Ensures exact sum to 1.0
        ),
        pass_threshold=0.70,
        min_criterion_floor=0.50,
        news_max_event_age_days=30,
    )


def get_authority_heavy_policy() -> GatePolicy:
    """
    Alternative policy: authority-heavy configuration (50% source authority,
    30% evidence support, 20% temporal validity).
    """
    return GatePolicy(
        weights_version="provisional-authority-heavy-v1",
        weights=WeightConfig(
            evidence_support=0.30,
            source_authority=0.50,
            temporal_validity=0.20,
        ),
        pass_threshold=0.70,
        min_criterion_floor=0.50,
        news_max_event_age_days=30,
    )
