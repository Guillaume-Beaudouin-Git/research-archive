# Conformalized Lee Inference

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.02898v1
**Captured**: 2026-07-07 02:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 83081b7ed644b178f4d2af702d6c7562

## Summary

The paper tackles prediction in randomized experiments where treatment changes who gets observed at all (one-sided sample selection) — the standard example being outcomes only measured for units that "survive" to be seen. It shows plain conformal prediction intervals under-cover in this setting because treated-and-selected units aren't comparable to control-and-selected units. Their fix, "conformalized Lee inference," trains and calibrates on the treated-selected group, then widens the interval by exactly the amount implied by the observed selection gap between treatment and control, producing valid individual treatment-effect intervals for units that are always observed regardless of treatment. Simulations confirm the adjustment restores nominal coverage where naive conformal prediction falls short.

## Why it might be useful

The mechanism — correcting inference when the sample you observe was itself shaped by a decision (treatment/selection) — is conceptually the same problem the DSR/AMTP correction machinery in CLAUDE.md exists to solve: a strategy that "survived" to be reported (out of the 321-test global ledger, or the 10 modifications budget per hypothesis) is a selected sample, and L20 (DSR mandatory for N_modifications≥2) is exactly a coverage-restoring correction in that same spirit, just for Sharpe ratios instead of treatment effects. It doesn't give a new tool to bolt on directly — nothing in the current pipeline does treated/control conformal prediction — but it's a useful cross-check that the selection-correction discipline already enforced (DSR, AMTP, walk-forward ≥5 folds) is solving the right class of problem, not an ad-hoc one.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt beyond the qualitative coverage comparison (naive conformal under-covers under selection shift; Lee-adjusted achieves nominal coverage). Full paper needed for the interval-construction algorithm.

## Action proposed

REFERENCE

Conceptual validation of the existing DSR/AMTP selection-correction discipline, not a new applicable technique — no treatment/selection structure exists in any active strategy's data.
