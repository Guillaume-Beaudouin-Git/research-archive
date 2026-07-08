# Factor-Augmented Machine Learning Panel Regressions

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.06368v1
**Captured**: 2026-07-08 01:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 9220feb86c50027df7e523891bfb3af6

## Summary
The paper derives asymptotic theory for high-dimensional panel regressions where errors are cross-sectionally dependent through common factors — the standard situation for any cross-sectional trading universe (all assets share market/sector shocks). Their estimator is a sparse-group LASSO augmented with latent factors, combined with MIDAS aggregation to handle predictors sampled at a different frequency than the target. The claim is that factor-augmentation lets the LASSO separate genuine sparse signal from factor-driven co-movement, improving both prediction and estimation accuracy relative to plain LASSO when cross-sectional dependence is present.

## Why it might be useful
This bears on two things in Algo_claude. First, the Commodities XS Basis+TSMOM research (`Commodities/research/active/xs_basis_tsmom/`) is a monthly cross-sectional IC scan over 24 continuous contracts — exactly the cross-sectionally-dependent-errors setting this paper targets, and exactly the setting where a naive HAC/OLS IC test (the repo's default per the methodology toolkit) can be biased by shared commodity-complex factors (energy, ag, metals) rather than idiosyncratic basis/momentum signal. Second, it speaks directly to the `ml_portfolio_hac_robustness` theme tracked in `_automation/synthesis/_state.json` ("ML/RL fails HAC-robust inference across Nasdaq-100/Nikkei/Euro Stoxx... best forecast MSE ≠ best Sharpe") — this paper is a candidate theoretical fix for that exact failure mode, since it builds HAC-valid asymptotics for the ML estimator itself rather than bolting HAC SEs onto ML residuals post hoc. No code in the excerpt, and Commodities XS Phase A (data fetch + roll validation) isn't complete yet, so there's nothing to implement today.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — blocked on Commodities XS Phase A (data fetch + roll validation) completing first; implementing a factor-augmented sparse-group LASSO from theory alone (no reference code in the excerpt) is a multi-day cost not justified before the base CS scan exists.
