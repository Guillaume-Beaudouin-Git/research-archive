# Identifying Treatment and Spillover Effects with Control-Based and Forecast-Based Counterfactuals

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.20156v1
**Captured**: 2026-07-23 01:00 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 1979043c2c3e258ba7f5b3ae7f439e2f

## Summary
The paper compares two families of methods for estimating causal treatment effects when
treating one unit can spill over and contaminate the outcomes of supposedly-untreated
"control" units. Control-based counterfactual methods (matching, difference-in-differences)
need genuinely uncontaminated controls to work, which breaks down when spillovers are
widespread or hard to characterize. Forecast-based counterfactual methods (interrupted
time-series, machine-learning control methods that predict what would have happened absent
treatment) sidestep that requirement by forecasting the counterfactual path directly instead
of relying on a clean control group. Through simulation and an empirical example the authors
show forecast-based methods are more credible when spillovers are pervasive or poorly
understood, at least over short horizons.

## Why it might be useful
This is a causal-inference identification paper for treatment-effect / event-study designs,
not a trading strategy. It doesn't bear on Strategy A, B, or C's known gaps (beta-dominance,
insufficient walk-forward folds, and vehicle unavailability respectively — none are
causal-identification problems). The repo doesn't currently run synthetic-control or
interrupted-time-series style event studies, so the forecast-based-counterfactual angle is
background only rather than a live methodology gap; the closest conceptual neighbor in the
toolkit is block-bootstrap inference under trade clustering, which this paper does not
address. No concrete implementation path exists today.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for
further extraction.

## Action proposed
REFERENCE — general causal-identification theory with no active strategy or feasibility-gate
tie; the repo runs no event-study/spillover-inference pipeline that would consume this.
