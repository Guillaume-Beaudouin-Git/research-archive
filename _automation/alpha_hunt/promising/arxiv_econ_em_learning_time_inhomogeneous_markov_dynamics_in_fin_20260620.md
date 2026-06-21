# Learning Time-Inhomogeneous Markov Dynamics in Financial Time Series

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.04690
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: a81ba908fa70c17d07a3e3eb240dbfa2

## Summary
Neural operators are introduced to estimate time-inhomogeneous Markov transition kernels in financial time series, addressing both data sparsity and non-stationarity. The approach is validated on equity price series as a canonical non-stationary environment, demonstrating improved transition structure estimation over fixed-window approaches. The framework handles high-resolution data where empirical Markov matrices collapse due to sparse observations.

## Why it might be useful
Strategy D (D3+D5 portfolio, Futures/research/active/strategy_d/) explicitly needs regime detection as a portfolio filter. The neural Markov operator could identify non-stationary regime transitions in NQ 1-min data more robustly than rolling-window signals. Concrete test: train on 2010-2022 NQ 1-min data (NQ_1min_databento_2010-2026.parquet), check whether neural Markov regime labels improve D3 or D5 hit rates versus the current signal. 1-2 days with PyTorch, after Strategy D pre-registration is complete.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Test neural Markov regime labels as input to Strategy D regime filter using NQ_1min_databento_2010-2026.parquet; 1-2 days post pre-registration.
