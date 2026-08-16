# Soft-Noncrossing Bayesian Panel Quantile Regression for Measuring Climate Tail Risk

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.04664v1
**Captured**: 2026-08-06 03:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: aec62f00d4726dc5605d892c078d1a81

## Summary
Develops a hierarchical Bayesian panel quantile regression where country-specific coefficient paths are smoothed across quantiles via Gaussian processes, with monotone Bernstein polynomials guaranteeing the quantile curves don't cross (with a proven bound on residual crossing probability). Applied to 33 countries 1979-2023, finds temperature shocks create a systemic, non-diversifiable downside risk to output growth concentrated in the lower tail, disproportionately affecting emerging markets, and the panel model cuts out-of-sample tail-risk forecast loss by roughly a third versus country-specific quantile regressions.

## Why it might be useful
The noncrossing-quantile machinery is relevant to any tail-risk modeling in the project's guardrail/DD-sizing stack — Strategy C's trailing_dd_simulator.py and the propfirm barrier/p(pass) work in `Portfolio/risk/` ultimately estimate tail quantiles of the P&L distribution (L24's finding that p(pass) depends on the shape, not just scale, of the daily distribution), and a soft-noncrossing panel quantile approach would let those estimates borrow strength across strategies/instruments the way this paper borrows strength across countries — useful if the barrier simulator is ever extended to jointly model A+B+C rather than one strategy at a time. Second link: a Bayesian alternative to the project's standard HAC/bootstrap machinery for tail inference, worth knowing about given the project's existing skepticism (L24, L54) toward MaxDD-based conditions that ignore distributional shape.

## Extracted content
No code. Numeric claim (author's): "reduces out-of-sample tail-risk forecast loss by roughly one-third relative to country-specific quantile regressions."

## Action proposed
REFERENCE.
