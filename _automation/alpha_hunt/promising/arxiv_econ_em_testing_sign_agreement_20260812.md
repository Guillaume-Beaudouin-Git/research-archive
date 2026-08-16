# Testing Sign Agreement

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.10294v1
**Captured**: 2026-08-12 02:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 565b845673b0ecc8070cecb0c4c7d7e6

## Summary
Proposes two new hypothesis tests for whether a finite collection of estimated parameters all share the same sign (all non-negative or all non-positive) under arbitrary dependence among the estimators. A "least favorable" test uses a worst-case critical value and is more powerful near sign-boundary cases; a "conditional" test first screens out clearly-signed components, then tests the remainder conditional on that screening, and is more powerful when effects are well separated from zero. Both control size uniformly and are validated in simulation.

## Why it might be useful
Maps directly onto a recurring project need: L25's two-sided requirement (a real directional edge must be positive on BOTH legs, not just net) and L37's beta-orthogonality/filter-sanity checks are, formally, sign-agreement tests across dependent estimated parameters (long-leg coefficient, short-leg coefficient). Current practice tests each leg's HAC t-stat separately; the paper's least-favorable test would give a single, formally correct test of "both legs share the required sign" instead of an ad hoc AND of two marginal tests — which matters because the legs are correlated (same underlying instrument). Second link: AMTP/multiple-testing discipline — sign-agreement testing across subgroups is exactly the heterogeneity problem cross-sectional strategies face (does the signal's sign agree across N >= 30 instruments), a candidate replacement for ad hoc quintile-monotonicity checks in TSMOM diagnostics.

## Extracted content
No code. No numeric performance claims (pure methodology paper).

## Action proposed
TEST_LATER — worth implementing the least-favorable sign-agreement test as a stricter replacement for the current two-sided-leg check (L25) next time a CFD two-sided candidate is evaluated; not urgent since no such candidate is currently in active research.
