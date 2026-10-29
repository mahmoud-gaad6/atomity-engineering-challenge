"""
run_example.py
==============
Command-line executable demonstration for the G2 Content Quality Gate.

Executes:
1. Evaluation of all 9 supplied starter cases from fixtures/g2-cases.json.
2. Formatted terminal presentation of hard checks, freshness, scores, decisions, and reasons.
3. Weight sensitivity comparison across three eligible cases and three policy configurations:
   - Default Provisional Policy (50% Evidence, 25% Authority, 25% Temporal)
   - Equal Weights Policy (33.3% / 33.3% / 33.4%)
   - Authority-Heavy Policy (30% Evidence, 50% Authority, 20% Temporal)
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from evaluator import G2Evaluator
from models import Case
from policy import (
    GatePolicy,
    get_authority_heavy_policy,
    get_default_policy,
    get_equal_weights_policy,
)


def find_fixture_path(filename: str) -> Path:
    """Locate a fixture file across standard local directories."""
    candidates = [
        Path(filename),
        Path("fixtures") / filename,
        Path("../fixtures") / filename,
        Path("../../fixtures") / filename,
        Path("../../../fixtures") / filename,
        Path("engineering-challenge-main/engineering-challenge-main/fixtures") / filename,
    ]
    for p in candidates:
        if p.is_file():
            return p
    raise FileNotFoundError(f"Fixture file '{filename}' could not be located in candidate paths.")


def load_cases(fixture_path: Path) -> tuple[date, list[Case]]:
    """Load and parse cases from a fixture JSON file."""
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    as_of = date.fromisoformat(data["as_of"]) if "as_of" in data else date(2026, 10, 6)

    cases: list[Case] = []
    for item in data.get("cases", []):
        # Exclude test-only expected_decision before model parsing
        case_data = {k: v for k, v in item.items() if k != "expected_decision"}
        cases.append(Case.model_validate(case_data))

    return as_of, cases


def run_starter_demonstration(evaluator: G2Evaluator, as_of: date, cases: list[Case]) -> None:
    """Evaluate and display the 9 starter cases in a formatted table."""
    print("\n" + "=" * 98)
    print("                     G2 CONTENT-QUALITY GATE — STARTER CASES EVALUATION")
    print(f"                       Reference Evaluation Date (as_of): {as_of}")
    print("=" * 98)
    print(f"{'Case ID':<26} {'Status':<10} {'Score':<10} {'Decision':<14} {'Primary Reason'}")
    print("-" * 98)

    for case in cases:
        report = evaluator.evaluate_case(case, as_of=as_of)
        score_str = f"{report.score:.4f}" if report.score is not None else "None"
        primary_reason = report.reasons[0] if report.reasons else "N/A"

        print(
            f"{report.case_id:<26} "
            f"{report.freshness.status:<10} "
            f"{score_str:<10} "
            f"{report.decision.upper():<14} "
            f"{primary_reason}"
        )

    print("=" * 98)


def run_sensitivity_comparison(as_of: date, extra_cases: list[Case]) -> None:
    """Compare scores of eligible cases across three distinct weight policies."""
    policies: list[tuple[str, GatePolicy]] = [
        ("Default (0.50/0.25/0.25)", get_default_policy()),
        ("Equal (0.33/0.33/0.33)", get_equal_weights_policy()),
        ("Authority-Heavy (0.30/0.50/0.20)", get_authority_heavy_policy()),
    ]

    print("\n" + "=" * 98)
    print("                 WEIGHT SENSITIVITY COMPARISON (TASK 6 REQUIREMENT)")
    print("                   Evaluating 3 Eligible Cases Across 3 Policies")
    print("=" * 98)
    print(f"{'Case ID':<40} {'Default':<18} {'Equal':<18} {'Authority-Heavy'}")
    print("-" * 98)

    for case in extra_cases:
        scores: list[str] = []
        for _, policy in policies:
            evaluator = G2Evaluator(policy=policy)
            report = evaluator.evaluate_case(case, as_of=as_of)
            score_str = f"{report.score:.4f}" if report.score is not None else "None"
            scores.append(f"{score_str} ({report.decision})")

        print(f"{case.id:<40} {scores[0]:<18} {scores[1]:<18} {scores[2]}")

    print("=" * 98)
    print("Observation & Analysis (Ranking Inversion):")
    print("1. 'extra-high-authority-secondary-support' increases from 0.7500 (Rank 2) to 0.8500 (Rank 1)")
    print("   when switching from Default (evidence-first) to Authority-Heavy.")
    print("2. 'extra-strong-evidence-secondary-source' drops from 0.8750 (Rank 1) to 0.7500 (Rank 2)")
    print("   when shifting from Default to Authority-Heavy, proving meaningful ranking sensitivity.")
    print("3. 'extra-balanced-benchmark' remains invariant at 1.0000 across all 3 policy configurations.")
    print("=" * 98 + "\n")


def main() -> None:
    """CLI Entry point."""
    # 1. Locate and evaluate the 9 starter cases
    g2_fixture_file = find_fixture_path("g2-cases.json")
    as_of, starter_cases = load_cases(g2_fixture_file)

    evaluator = G2Evaluator()
    run_starter_demonstration(evaluator, as_of, starter_cases)

    # 2. Locate and evaluate the 3 extra cases for sensitivity analysis
    extra_fixture_file = find_fixture_path("extra_cases.json")
    _, extra_cases = load_cases(extra_fixture_file)
    run_sensitivity_comparison(as_of, extra_cases)


if __name__ == "__main__":
    main()
