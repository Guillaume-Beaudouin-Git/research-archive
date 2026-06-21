# Quantifying the Risk-Return Tradeoff in Forecasting

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.09712
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 8cb1c9c1f28bbd01a45b52804582765e

## Summary
This paper reframes forecast evaluation by treating loss differentials (relative to a benchmark) as a return series and then computing risk-adjusted metrics on those differentials — Sharpe ratio, Sortino, Omega, drawdown statistics. The central insight is that average accuracy understates the quality of "reliable" forecasters: professional macroeconomic forecasters dominate machine learning methods on risk-adjusted metrics even when ML beats them on RMSE, because professionals rarely experience catastrophic failure episodes. A new "Edge Ratio" is introduced to measure a model's propensity to produce uniquely informative predictions not captured by the frontier ensemble of all models. The framework extends naturally to density forecasts and to meta-analyses across targets, horizons, and sample windows.

## Why it might be useful
The Edge Ratio is directly applicable to Strategy C/D signal evaluation: instead of reporting IC t-stat alone, compute the Edge Ratio of iter_10's ORB signal versus a naive direction benchmark. This would quantify whether the signal adds non-redundant information beyond what any simple rule already captures — which is exactly the question after the Databento re-baseline showed Sharpe 0.41. For Strategy D (D3+D5 currently failing individually), the risk-adjusted drawdown metrics on loss differentials would reveal whether D3's failures concentrate in regime-specific windows (the basis for the regime filter hypothesis). Methodologically, Sortino ratio on forecast differentials complements our HAC t-stat: it captures downside asymmetry in prediction error, which matters for FTMO daily-DD-breaching events. Implement as a wrapper around existing signal_engine evaluation: no new data needed, just apply the framework to existing NQ backtest trade P&L as a "loss differential series."

## Extracted content
The author claims: "While it is often feasible to beat professional forecasters in terms of average accuracy, it is much harder to beat them on a risk-adjusted basis. They rarely exhibit catastrophic failures and often achieve high Edge Ratios."

Edge Ratio: "capturing a model's propensity to deliver uniquely informative predictions relative to the forecasting frontier."

No code provided in abstract. Full paper needed for Edge Ratio formula.

## Action proposed
TEST_LATER

Implement Edge Ratio on existing Strategy C/D NQ backtest P&L series. Cost: 0.5 day (wrapper around existing backtest output). Blocked on having a sensible benchmark: use naive 50/50 long-flat as frontier or compare iter_10 vs D3 vs D5 signals. Also useful for ZN Baltussen evaluation. Mark as LATER because iter_10 is currently deactivated (Tradeify annulé) — priority rises when D3/D5 decision is needed.
