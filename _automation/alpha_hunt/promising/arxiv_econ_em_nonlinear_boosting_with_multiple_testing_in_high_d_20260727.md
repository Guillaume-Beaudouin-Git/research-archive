# Nonlinear Boosting with Multiple Testing in High-Dimensional Generalised Linear Models with Binary Responses

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2607.22440v1
**Captured**: 2026-07-27 04:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: eb03cc91cd9846925cd0adfa9319041d

## Summary
Proposes BMT (boosting with multiple testing), a variable-selection procedure for high-dimensional generalized linear models with binary responses — at each stage, add only the most-significant remaining covariate conditional on those already selected, explicitly accounting for the multiple-testing nature of repeated significance checks. Proves BMT selects all truly-nonzero-coefficient covariates (and no others) with probability tending to one, and that the post-selection MLE is asymptotically equivalent to an oracle estimator that already knew the true sparse model; demonstrated on a US-inflation-threshold binary classification task with strong out-of-sample performance.

## Why it might be useful
Origin paper for the BMT method also used in aa7ef3b52e7d60ed76c09d8848ffab8d (electricity-price variable selection, filed elsewhere in this batch) — together they show BMT works for both continuous and binary targets. Direct tie to the project's AMTP discipline: BMT builds multiple-testing correction directly into the stepwise variable-selection procedure itself, rather than as a post-hoc penalty applied after the fact (the current approx_multi_test_penalty approach) — a methodologically cleaner alternative for any future binary/regime-classification signal construction (a directional-accuracy classifier for TSMOM, or a regime-flag classifier of the kind L54 killed) where current practice is to build the classifier first and correct for n_tests afterward.

## Extracted content
No code (algorithm described, not reproduced verbatim). No numeric claims specific to a Sharpe/trading metric — the empirical example is a US-inflation-threshold classifier, not a trading signal.

## Action proposed
TEST_LATER — same rationale and underlying method as aa7ef3b52e7d60ed76c09d8848ffab8d; implementing BMT once covers both the continuous-target and binary-target use cases documented across these two papers. Bundle as a single follow-up task rather than two separate ones.
