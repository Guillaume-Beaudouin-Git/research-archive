# Multivariate Financial Forecasting with Chronos-2: Marginal Benefit of Multivariate Inputs

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.21504
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 3f8dd6c17ccc6244a54a4870b8b0e8e9

## Summary
Using Chronos-2 (open-source time-series foundation model) across rolling monthly evaluations on Magnificent-7 equities and US Treasury rates from 2000-2025, this study finds that multivariate inputs do not consistently outperform univariate baselines across all settings. For shorter horizons (1-5 days) on equities, multivariate provides ~5% MAPE reduction; beyond 10 days, the improvement disappears. For Treasuries, multivariate consistently outperforms. Chronos-2 outperforms ARIMA and LSTM on 8 of 12 benchmark configurations. The study varies input window lengths and forecast horizons systematically.

## Why it might be useful
The finding that multivariate Chronos-2 beats univariate only at 1-5 day horizons for equities is directly relevant to the FX intraday deepdive at `Forex/research/active/fx_intraday_deepdive/`: if a foundation model is considered for signal enhancement, the 1-5 day horizon finding aligns with the 1-bar execution-delay discipline in L26 (signal at T-1, trade at T). For the ZN Baltussen bond futures momentum at `Futures/research/active/zn_baltussen/`, the consistent multivariate advantage for Treasuries suggests that incorporating correlated rates series (5Y, 10Y, 30Y jointly) would improve forecast quality—relevant to the regime filter design. The 5% MAPE reduction at short horizons is modest; at 0.17% RT crypto costs, even a 5% improvement in direction accuracy matters only if the signal's gross IC is already above the cost gate.

## Extracted content
Specific numeric claims: ~5% MAPE reduction from multivariate inputs at 1-5 day equity horizons, no improvement >10 days. Chronos-2 outperforms ARIMA/LSTM on 8 of 12 configurations. Study period 2000-2025, rolling monthly evaluation.

## Action proposed
REFERENCE

Foundation model benchmark; useful context for signal design but no direct test path without implementing Chronos-2 inference pipeline. Multivariate Treasury finding is noted for ZN Baltussen.
