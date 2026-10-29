# Task 6 — G2 Content-Quality Gate

> **Submission Directory:** `task-6_mahmoud`  
> **Challenge:** Evidence-to-Insight Engineering Challenge (Atomity)  
> **Selected Task:** Task 6 — One Content-Quality Gate (G2: Evidence and Current-Validity Assessment)

---

## 1. Executive Summary

This component implements the **G2 Content-Quality Gate**, an automated, deterministic quality checkpoint evaluated before content moves forward in the Evidence-to-Insight pipeline.

The G2 gate assesses **evidence support and temporal validity only**. In accordance with the challenge specification:
* It does **not** evaluate visual quality, typography, writing style, or audience engagement.
* It distinguishes between publication date, event date, effective date, and current applicability.
* It enforces mandatory hard checks before any weighted scoring takes place.
* It guarantees that a failed hard check cannot be bypassed by an otherwise high weighted score.
* It enforces strict unknown handling: missing criteria remain `None` and are **never** silently converted to `0.0`.
* It operates completely locally, deterministically, and without undisclosed credentials or external services.

---

## 2. Quick Start & Reviewer Verification

### Prerequisites
* Python 3.10+
* `pydantic >= 2.0`

### Run Automated Tests (30 Tests)
To execute the complete automated test suite across all units and fixtures:
```powershell
python -m unittest discover tests -v
```

### Run Executable Example & Sensitivity Analysis
To run the end-to-end command-line demonstration evaluating all 9 starter cases and displaying the weight sensitivity comparison:
```powershell
python run_example.py
```

---

## 3. Architecture & Evaluation Flow

The pipeline executes in a strict, unbranching sequential order:

```text
Input Case & Fixture (with fixed as_of: 2026-10-06)
                     │
                     ▼
       1. Strong Schema Validation (models.py)
                     │
                     ▼
       2. Mandatory Hard Checks (hard_checks.py)
          ├── Material claim supported
          ├── Evidence not superseded
          ├── No competitor product promotion
          └── No contradiction
                     │
                     ▼
       3. Freshness & Validity Engine (freshness.py)
          ├── News: (as_of - event_date) <= 30 days
          └── Regulations: in-force vs future vs superseded
                     │
                     ▼
       4. Criterion Anchoring & Scoring (scorer.py)
          ├── Evidence Support (0.0 / 0.5 / 1.0)
          ├── Source Authority (0.0 / 0.5 / 1.0)
          ├── Temporal Validity (0.0 / 0.5 / 1.0)
          └── Weighted Score = Σ(w_i * c_i)  [or None if any c_i is None]
                     │
                     ▼
       5. Strict Decision Precedence (evaluator.py)
          Reject ──► Revise ──► Human Review ──► Pass
                     │
                     ▼
             EvaluationReport
```

### Repository Structure
```text
task-6_mahmoud/
├── README.md               # This engineering design note & submission document
├── models.py               # Pydantic data contracts (Case, Metadata, Reports)
├── hard_checks.py          # Hard integrity constraints & failure extraction
├── freshness.py            # Temporal validity & news age / regulation engine
├── policy.py               # Weight configurations, mathematical validation & presets
├── scorer.py               # Observable criterion anchors & weighted sum calculation
├── evaluator.py            # G2Evaluator orchestrator enforcing decision precedence
├── run_example.py          # CLI executable demo & sensitivity analysis display
├── fixtures/
│   └── extra_cases.json    # 3 synthetic eligible test cases for sensitivity analysis
└── tests/
    ├── test_hard_checks.py # Unit tests for mandatory hard checks (5 tests)
    ├── test_freshness.py   # Unit tests for temporal freshness rules (6 tests)
    ├── test_weights.py     # Unit tests for weight invariants & validation (6 tests)
    ├── test_scorer.py      # Unit tests for anchors & scoring math (8 tests)
    └── test_evaluator.py   # End-to-end integration tests on all starter cases (5 tests)
```

---

## 4. Evaluation Rules & Anchors

### Mandatory Hard Checks (`hard_checks.py`)
Hard checks evaluate baseline integrity. A failure in any check guarantees that the case cannot receive a `pass` decision:
1. **Material claim supported:** `metadata.supported == True`.
2. **Evidence not superseded:** `metadata.superseded == False` and `metadata.current_status != "superseded"`.
3. **No competitor promotion:** `metadata.competitor_product_claim == False`.
4. **No contradiction:** `metadata.contradiction == False`.

### Freshness & Current Validity (`freshness.py`)
Evaluated relative to the fixed fixture date (`as_of: 2026-10-06`):
* **News Articles:** Evaluated strictly against `event_date` (never `published_at`).
  * If `event_date` is missing: status is `unknown`.
  * If `(as_of - event_date).days <= 30`: status is `current`.
  * If `(as_of - event_date).days > 30`: status is `stale` (even if publication is recent).
* **Regulations:** Publication age does not diminish legal validity.
  * Active in-force regulations remain `current`.
  * Regulations with `effective_from > as_of` or `current_status == "adopted_not_applicable"` are classified as `future` (adopted, but not yet applicable).
  * Regulations marked superseded are `stale`.

### Observable Criterion Anchors (`scorer.py`)
Each criterion maps to observable evidence anchors:

| Criterion | Score `1.0` | Score `0.5` | Score `0.0` | Score `None` |
| :--- | :--- | :--- | :--- | :--- |
| **Evidence Support** | Directly supported without contradiction. | Partial or qualified evidence support. | Unsupported or contradicted by sources. | Missing evidence support metadata. |
| **Source Authority** | Official primary authority (`primary_authority`). | Secondary authority, academic, or industry report. | Competitor source or product claim. | Source type is missing. |
| **Temporal Validity**| Status is `current` or validly `future` (not superseded). | Partially applicable or timing requires qualification. | Status is `stale` or superseded. | Status is `unknown` (missing event date). |

---

## 5. Decision Precedence Hierarchy

Decisions are resolved in a deterministic priority order so outcomes never conflict:

1. **`reject` (Rule 1 — Non-remediable violation):**
   * Triggered by prohibited competitor product promotion (`COMPETITOR_PROMOTION`).
2. **`revise` (Rule 2 — Remediable defect):**
   * Triggered by unsupported material claims (`UNSUPPORTED_CLAIM`).
   * Triggered by superseded evidence sources (`EVIDENCE_SUPERSEDED`).
   * Triggered by stale news under the demo policy (`STALE_EVENT_DATE`).
3. **`human_review` (Rule 3 — Information gap or uncertainty):**
   * Triggered by missing temporal metadata / unknown criteria (`UNKNOWN_TEMPORAL_METADATA`).
   * Triggered by conflicting evidence between authorities (`CONTRADICTING_EVIDENCE`).
   * Triggered when weighted score is below threshold (`WEIGHTED_SCORE_BELOW_THRESHOLD`).
4. **`pass` (Rule 4 — Eligible for next internal stage):**
   * All hard checks pass.
   * All criteria are known (no `None` values).
   * All individual criteria meet the floor of `0.50`.
   * Weighted score meets or exceeds the provisional threshold of `0.70`.

---

## 6. Policy Configurations & Weight Rationale

### Mathematical Constraints (`policy.py`)
All weight configurations strictly enforce:
$$\sum w_i = w_{\text{evidence}} + w_{\text{authority}} + w_{\text{temporal}} = 1.0 \quad (\pm 10^{-5})$$
$$w_i \ge 0.0 \quad \forall i$$

Configurations with negative weights or non-unit sums raise immediate validation errors.

### Weight Profiles
* **Default Provisional Policy (`0.50 / 0.25 / 0.25`):**  
  *Rationale:* **Evidence-First Principle.** A statement from an authoritative source is useless if it is not supported by actual evidence. Evidence grounding receives 50%, with the remaining 50% split equally between institutional authority and temporal validity.
* **Equal Weights Policy (`0.3333 / 0.3333 / 0.3334`):**  
  *Rationale:* Neutral baseline assigning equal weight to all three dimensions.
* **Authority-Heavy Policy (`0.30 / 0.50 / 0.20`):**  
  *Rationale:* Alternative model prioritizing institutional provenance and primary regulatory authorship over empirical proof nuances.

### Interpretation Warning
* The weighted score is an **uncalibrated quality index**, **not a statistical probability**.
* A score of `0.875` means the case performed well on the index; it does **not** mean "87.5% likely to be true."

---

## 7. Weight Sensitivity Comparison

Task 6 requires comparing at least three eligible cases across three weight configurations. We authored three synthetic eligible cases in `fixtures/extra_cases.json`:
1. `extra-high-authority-secondary-support`: High authority (1.0), partial evidence support (0.5), current (1.0).
2. `extra-strong-evidence-secondary-source`: Full evidence support (1.0), secondary authority (0.5), current (1.0).
3. `extra-balanced-benchmark`: Full evidence support (1.0), primary authority (1.0), current (1.0).

### Comparison Results

```text
==================================================================================================
                 WEIGHT SENSITIVITY COMPARISON (TASK 6 REQUIREMENT)
                   Evaluating 3 Eligible Cases Across 3 Policies
==================================================================================================
Case ID                                  Default            Equal              Authority-Heavy
--------------------------------------------------------------------------------------------------
extra-high-authority-secondary-support   0.7500 (pass)      0.8333 (pass)      0.8500 (pass)
extra-strong-evidence-secondary-source   0.8750 (pass)      0.8333 (pass)      0.7500 (pass)
extra-balanced-benchmark                 1.0000 (pass)      1.0000 (pass)      1.0000 (pass)
==================================================================================================
```

### Observations & Ranking Inversion:
* **Ranking Inversion:** Under the Default policy (evidence-first), `extra-strong-evidence-secondary-source` ranks #1 among the two non-benchmark cases ($0.8750 > 0.7500$). Under the Authority-Heavy policy, the ranking strictly inverts: `extra-high-authority-secondary-support` becomes #1 ($0.8500 > 0.7500$).
* **Invariant Benchmark:** `extra-balanced-benchmark` scores $1.0000$ across all configurations, confirming that balanced, flawless cases are unaffected by weight shifts.
* **Routing Stability:** All three cases remain above the `0.70` pass threshold, so routing remains `pass` across all three configurations.

---

## 8. Definition of Done Checklist

| Requirement | Implementation Verification | Status |
| :--- | :--- | :---: |
| 1. Load supplied `g2-cases.json` | Handled in `run_example.py` and `test_evaluator.py`. | **Done** |
| 2. Run evaluator using fixed `as_of` | Fixed reference date `2026-10-06` enforced; never uses system clock. | **Done** |
| 3. Validate every starter case | All 9 starter cases verified against expected decisions. | **Done** |
| 4. Inspect hard-check results | `HardCheckResult` captures all 4 checks and failure reason codes. | **Done** |
| 5. Inspect freshness reasoning | `FreshnessResult` provides transparent, human-readable rationale. | **Done** |
| 6. Inspect criterion scores | `CriteriaScores` stores explicit anchors for all three dimensions. | **Done** |
| 7. Inspect configured weights | Weights dictionary included in every `EvaluationReport`. | **Done** |
| 8. Inspect weighted score | Computed transparently; clamped to $[0.0, 1.0]$. | **Done** |
| 9. Inspect final decision and reasons | Report contains decision and machine-readable reason codes. | **Done** |
| 10. Hard failures cannot pass | Verified via `test_hard_check_failure_cannot_pass_with_high_score`. | **Done** |
| 11. Unknown criteria do not become zero | Verified via `test_unknown_criterion_propagates_none`. | **Done** |
| 12. Invalid weights rejected | Negative weights and sum $\neq 1.0$ verified via `test_weights.py`. | **Done** |
| 13. Three extra eligible cases | Provided in `fixtures/extra_cases.json`. | **Done** |
| 14. Weight sensitivity comparison | Displayed in `run_example.py` demonstrating ranking inversion. | **Done** |
| 15. All automated tests run locally | 30 unit and integration tests passing in $<0.01$s with 0 credentials. | **Done** |

---

## 9. Fixture Metadata Boundary & Known Limitations

1. **Metadata Trust Boundary:** The G2 gate trusts metadata flags (`supported`, `superseded`, `event_date`) as supplied by upstream pipeline stages (Tasks 1, 2, and 3). It is responsible for deterministic routing and scoring based on those flags, not for verifying real-world external truth.
2. **Deterministic Heuristic:** The component intentionally avoids LLM calls or learned weights to guarantee transparent, reproducible, and verifiable auditability.
3. **Provisional Calibration:** All threshold and weight configurations are explicitly designated `uncalibrated` and `provisional-v1`, as they reflect engineering judgment rather than empirically derived probability distributions.
