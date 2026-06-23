# Neural Networks with Explicit ARMA Error Structure for Nonlinear Time-Series Regression

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.22483v1
**Captured**: 2026-06-23 03:00 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: b6ff4a9b249bdfdffeaa44ffe7c1999e

## Summary

This paper proposes embedding autoregressive moving average (ARMA) error dynamics directly inside feedforward neural networks, as an alternative to the common practice of adding lagged features to capture temporal dependence. Simulations show the approach recovers nonlinear regression functions of varying complexity under a range of sample sizes and signal-to-noise ratios. Out-of-sample performance is robust to misspecification of both the lag structure and the ARMA order. The empirical application is climate (cloud cover over the Mediterranean), where the model outperforms LSTM networks, with the largest gains in mountainous terrain where nonlinear effects dominate.

## Why it might be useful

The key methodological idea — separating the signal's nonlinear structure from the error's autocorrelation structure, rather than conflating both into lagged features — is directly applicable to any momentum or carry signal estimated on a short time series. For Strategy A (TSMOM, 28-bar lookback on BTC/ETH/SOL), the error residuals of the vol-scaled cumulative return are serially correlated; this architecture would let the model distinguish true nonlinear signal shape from autocorrelation noise. The approach also matters for the ZN Baltussen active research arc (`Futures/research/active/zn_baltussen/`) where bond momentum residuals carry strong autocorrelation. More broadly, this connects to HAC lag-6 correction in CLAUDE.md's mandatory methodology: if the signal model itself absorbs ARMA structure, HAC inflation is reduced — potentially lifting the effective t-stat on marginal strategies. Concrete test: implement this as a signal estimator variant for TSMOM (replace tanh(cumret/vol) with a shallow NN with ARMA(1,1) errors, walk-forward on BTC 2020-2026) to see whether it improves OOS Sharpe beyond 1.33 without violating the 3-modification budget on Strategy A (currently frozen).

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

Interesting architecture for signal refinement on Strategy A or ZN arc. Blocked by: (1) Strategy A is FROZEN at Propr — modification would re-open the budget; (2) implementation cost ~2 days for proper walk-forward validation. Revisit when A is unfrozen or for Strategy D signal generation.
