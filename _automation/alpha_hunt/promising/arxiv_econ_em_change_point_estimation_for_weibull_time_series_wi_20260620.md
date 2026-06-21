# Change-Point Estimation for Weibull Time Series with Copula-Markov Models

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.29541
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: e00686fedc3c379372adf5d2511ace9e

## Summary
A copula-based Markov model with Weibull marginals is proposed for change-point detection in non-negative time series like realized volatility. Clayton and Joe copulas capture lower-tail and upper-tail asymmetric dependence. Maximum likelihood jointly estimates the change point and model parameters, validated on Monte Carlo and vol series.

## Why it might be useful
Strategy D (Futures/research/active/strategy_d/) needs a regime detection mechanism for its D3+D5 portfolio filter. NQ realized volatility from NQ_1min_databento_2010-2026.parquet is exactly the type of non-negative, fat-tailed series this model targets. Concrete test: apply Weibull copula-Markov change-point to NQ realized vol, compare detected regimes against D3/D5 IC conditional on regime, and check if high-vol regimes predict higher or lower hit rate for each strategy component. 1-2 days with scipy/statsmodels. TEST_LATER pending Strategy D pre-registration completion.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Apply Weibull copula-Markov change-point to NQ realized vol for Strategy D regime filter; 1-2 days using NQ_1min_databento_2010-2026.parquet.
