# Second-Generation Heterogeneous Panel Data Model with Individual and Common Shocks

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.29063v1
**Captured**: 2026-06-30 02:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 6754755d14a94d97d98e4169ba7478cf

## Summary
This paper proposes two estimators for panels that combine cross-sectional dependence (from unobserved common factors) with unit-specific structural breaks at heterogeneous dates. The F-CCEMG estimator augments the standard CCE regression with deterministic Fourier terms, simultaneously filtering the common factor and absorbing timing-heterogeneous breaks. In a Monte Carlo study across 500 replications, F-CCEMG achieves the lowest RMSE in almost every configuration and near-nominal coverage once the cross-section is not minimal. Standard estimators that do not filter the common factor lose coverage as cross-sectional dependence strengthens. An empirical application to renewable energy and GDP growth in G7 (1965–2019) finds no significant aggregate effect.

## Why it might be useful
The active Commodities XS research (`Commodities/research/active/xs_basis_tsmom/`) plans a cross-sectional IC scan on 24 continuous contracts with monthly rebalancing. Commodity futures are well-known to share common risk factors (energy factor, metals factor) plus structural breaks tied to specific episodes (2008 GFC, COVID-2020, 2022 energy shock). Running a naive pooled regression or mean-group on raw returns will absorb common-factor noise into the slope estimates, inflating apparent IC. F-CCEMG provides a cleaner estimator for IC in this setting: it filters the common factor while allowing each contract's basis-signal relationship to shift at a different date. This is more principled than adding manual dummy variables for known break dates. Implement when the panel is assembled and the baseline IC scan is running; augment `Commodities/research/active/xs_basis_tsmom/` with an F-CCEMG IC comparison as a robustness check.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE
