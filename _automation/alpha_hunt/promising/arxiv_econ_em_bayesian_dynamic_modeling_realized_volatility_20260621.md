# Bayesian Dynamic Models for Joint Price and Realized Volatility Forecasting

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.12099
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: edb172fa2ef011c03dff179e27a26d7e

## Summary
This paper introduces a class of Bayesian dynamic models that jointly model asset prices and realized volatility as a bivariate system. A novel dynamic gamma process for realized vol is integrated with Bayesian dynamic linear models for prices, capturing volatility leverage and feedback effects through realized volatility proxies. The approach synthesizes higher-frequency data to improve daily forecast accuracy and produces proper predictive intervals for both price and volatility 1-10 days ahead. Empirically on equity indices, the joint price-vol model outperforms univariate DLMs and GARCH benchmarks in directional accuracy and calibration.

## Why it might be useful
Strategy A's 28-bar log-return vol window is a simple backward-looking estimator that feeds directly into the tanh signal and the VOL_TARGET_LIVE=0.18 sizing; a Bayesian dynamic vol model with proper predictive intervals would improve both the signal (better vol estimate at T-1) and the risk management (uncertainty bounds on vol targeting). The outperformance over GARCH on equity indices is relevant because realized vol from higher-frequency BTC/ETH/SOL intraday data (available via Binance klines) could replace the simple daily vol estimator in `strategies/tsmom_v2_propfirm/signal.py`. This would be a Modification 1 candidate for Strategy A when it comes off freeze—but critically, must be validated as producing the same or better OOS Sharpe relative to the current 1.33 before being adopted, within the 3-mod budget.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Bayesian realized vol model as a replacement for the 28-bar window in Strategy A is a concrete test, but Strategy A is currently frozen (breach 2026-05-11) and must be unfrozen before any modification is made. Queue as Modification 1 candidate.
