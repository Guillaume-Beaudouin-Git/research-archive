# Estimating Supply Incrementality in Two-sided Marketplaces: A Causal Machine Learning Approach

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.30999v1
**Captured**: 2026-07-01 02:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 4512d6da5c69bd89efc81e2e67e9477b

## Summary

The paper estimates how much additional bookings result from adding listing supply on a two-sided marketplace (Airbnb), combining double/debiased machine learning (DML) with a hierarchical Bayesian layer that uses geospatial product-similarity measures as informative priors across market segments. The claimed contribution is a causal-ML estimator that borrows strength across segments while still producing segment-specific incrementality estimates, validated with strong out-of-sample performance. The application domain (marketplace supply economics) is unrelated to trading, but the estimator design — DML plus hierarchical shrinkage across a segmented universe — is a general causal-inference technique.

## Why it might be useful

The methodological pattern (hierarchical/shrinkage estimation across segments, validated out-of-sample) is the same class of problem as pooling per-instrument or per-rule estimates across a small, correlated universe — directly adjacent to the pooling-estimator question raised in the same run's companion item (`quantocracy_one_of_these_things_is_not_like_the_others_or_is_i_20260701.md`, re: Strategy D3+D5 combination) and to the Commodities XS cross-sectional IC scan (`Commodities/research/active/xs_basis_tsmom/`, N≤279, 24 continuous contracts across sectors) where a hierarchical prior by commodity-sector cluster could stabilize per-contract Sharpe estimates that are individually noisy. There is no direct edge or signal here — it's a technique reference, not a trading hypothesis, and would need adaptation from marketplace-supply causal inference to time-series/cross-sectional trading contexts before it's testable.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

Good methodological background on hierarchical/shrinkage causal estimation, but no direct path to a trading test — the application domain doesn't transfer without substantial adaptation, and Commodities XS Phase A (data fetch + roll validation) hasn't even started yet per current_focus.md.
