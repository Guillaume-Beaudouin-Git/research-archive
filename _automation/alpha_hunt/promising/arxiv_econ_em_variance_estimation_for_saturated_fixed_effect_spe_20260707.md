# Variance Estimation for Saturated Fixed-Effect Specifications

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.05215v1
**Captured**: 2026-07-07 03:30 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 4df4f23585f39863765b7ebbeb054fa4

## Summary

The paper works out what happens to standard variance estimators in linear regressions with a lot of fixed effects relative to sample size (a "saturated" design). It shows the popular Eicker-White HC0 estimator is biased downward — and therefore over-rejects — by a factor tied to how saturated the fixed-effect structure is, while the HC3 correction over-shoots in the opposite direction. The leave-one-out HC2 estimator comes out as the one that stays correctly calibrated under homoskedasticity or balanced heteroskedasticity, though it still carries a residual bias under general (unbalanced) heteroskedasticity that the authors characterize explicitly. They validate the hierarchy empirically on Piotroski F-Score return regressions in Central/Eastern European equity markets.

## Why it might be useful

This is a direct methodology hit on the "5 mandatory script fixes" section of CLAUDE.md (item 2: correct SE — HAC for time series, but the same underlying concern — using the wrong covariance estimator inflates or deflates t-stats — applies to the cross-sectional fixed-effect panel regressions planned for the Commodities XS project). `Commodities/research/active/xs_basis_tsmom/` runs a monthly cross-sectional IC scan across 24 continuous contracts; once that regression is specified (with contract or sector fixed effects), this paper is the direct guide for which HC estimator to use — HC2, not the statsmodels default HC1 or naive HC0/HC3 — to avoid the same kind of red-flag t-inflation that `_audit/sector_hothand_audit_2026-05-30.md` already flagged for `sector_hothand_propfirm` (t_HAC=10.38). It's a concrete, low-cost fix to apply the moment that CS panel regression code gets written.

## Extracted content

The excerpt contains the core numeric claim as a qualitative bias direction (verbatim from the abstract): "the Eicker–White HC0 estimator is biased downward by a fixed factor $(1-ρ)$... HC3 over-corrects in the opposite direction by a factor $1/(1-ρ)$... The leave-one-out estimator (HC2) removes the first-order leverage distortion." No code in the excerpt; the $ρ$ parameter is the fixed-effect dimension ratio $d_{K_n}/n$. Full paper needed for the exact correction formulas.

## Action proposed

TEST_LATER

Directly actionable (swap HC1→HC2 in the eventual `xs_basis_tsmom` panel regression) but the Commodities XS project is still in Phase A (data fetch + roll validation) — no regression code exists yet to apply this to. Revisit when Phase A completes and the CS IC scan is actually specified.
