# A Comparison of High-Dimensional Variable Selection Procedures for Electricity Spot Price Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2608.09213v1
**Captured**: 2026-08-11 02:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: aa7ef3b52e7d60ed76c09d8848ffab8d

## Summary
Compares six high-dimensional variable-selection methods for forecasting electricity spot prices across six regional markets, including a "Boosting Multiple Testing" (BMT) procedure. Finds LASSO and Elastic Net achieve the best raw accuracy but are heavily over-parameterized; BMT matches their forecasting accuracy while selecting under one-tenth as many variables, making it a substantially more interpretable and computationally cheap alternative without any accuracy cost.

## Why it might be useful
Directly upgrades the project's own AMTP/multiple-testing discipline — BMT is explicitly a multiple-testing-aware stepwise selection procedure (add only the most-significant covariate at each stage, correcting for repeated significance checks), a more principled and far more parsimonious alternative to the current approx_multi_test_penalty (AMTP) post-hoc correction used whenever n_tests > 1. Second link: this is the same BMT method as eb03cc91cd... ("Nonlinear Boosting with Multiple Testing in High-Dimensional GLMs," filed separately in this batch) — read together they show BMT works for both continuous (electricity price) and binary (GLM) targets, covering most of this project's signal-construction use cases.

## Extracted content
No code in excerpt (BMT is cited as an existing, "recently proposed" method, not derived here). Numeric claim (author's): BMT "matches [LASSO/Elastic Net] forecasting performance while using less than one-tenth as many variables."

## Action proposed
TEST_LATER — BMT is a promising drop-in replacement for ad hoc feature selection in future multi-signal research (e.g., Commodities XS Basis+TSMOM), but needs the underlying algorithm sourced/implemented first (not evidently in a standard Python package) — more than a few hours of work, and no active thread is currently blocked on variable selection. Bundle with eb03cc91cd... as one follow-up task.
