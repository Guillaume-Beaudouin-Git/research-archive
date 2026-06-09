# AI Predictions as Prognostic Covariates for Variance Reduction in Experiments

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.08853v1
**Captured**: 2026-06-09 06:04 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 79391ff60a15ea1d604fbd11f8fac5e0

## Summary
LLM-generated predictions of outcomes can be included as control covariates in standard OLS regression-adjusted estimation, reducing variance in treatment effect estimates without introducing bias. The key insight is that this requires no new estimator — it is mechanically equivalent to adding a prognostic score as a covariate in a regression. A critical "do no harm" property holds: if the AI predictions have zero explanatory power, the estimator degenerates to the unadjusted difference-in-means, so there is no risk of inflating type-I error by adding useless covariates. Competing approaches like prediction-powered inference do not guarantee this. Empirical applications in survey experiments, email A/B tests, and a large-scale platform experiment confirm modest but real efficiency gains, especially when inputs include substantial unstructured text data.

## Why it might be useful
The "do no harm" property is directly applicable to the mandatory IC testing framework (HAC lag-6, AMTP). When testing a strategy's signal IC with additional covariates (e.g., adding a VIX regime indicator, a FOMC calendar dummy, or an LLM-generated macro sentiment score as controls in the IC regression), naive inclusion can overfit and inflate t-stats. The paper's result says that including such covariates in an OLS regression adjustment is safe as long as you use the standard form — the estimator will self-regularize when covariates add no information. This is relevant to the sector_hothand_propfirm audit (`_audit/sector_hothand_audit_2026-05-30.md`), where t_HAC=10.38 is flagged as a red flag: if that regression includes extra covariates without the "do no harm" guarantee, inflated t-stats could result. The approach also applies to Strategy B mainnet validation: when we eventually run a live IC test on carry spreads (expected ~2026-07 per L14), adding this variance-reduction adjustment with FOMC/expiry calendars as covariates could improve power in the small-sample regime without inflating false positives.

## Extracted content
No code or numeric trading performance claims in the excerpt. The authors state efficiency gains are "real if modest, with greater benefits in studies that contain substantial text and other unstructured data."

## Action proposed
REFERENCE
