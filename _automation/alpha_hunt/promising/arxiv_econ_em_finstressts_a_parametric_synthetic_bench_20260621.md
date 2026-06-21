# FinStressTS: A Synthetic Benchmark for Diagnosing Financial Forecaster Failure Modes

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2606.03184
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: 1e24cf49d02ed1323bf827e2e7683e0d

## Summary
Financial time-series forecasting suffers from entangled failure modes—heavy tails, regime shifts, jumps, low signal-to-noise—that are impossible to isolate in real data because only one historical path is observed. FinStressTS addresses this by wrapping any forecaster in a standardized evaluation harness that sweeps controllable data-generating parameters (Heston stochastic vol, HMM regime-switching, alpha-stable heavy tails, Merton drift-jumps) and produces diagnostic profiles linking parameter settings to specific model failures. The benchmark compares ARIMA/GARCH, XGBoost/LSTM/N-BEATS, and Chronos across these regimes, revealing systematic failure modes per model family. The key contribution is the ability to attribute underperformance to a specific mechanism rather than observing undifferentiated degradation.

## Why it might be useful
The FinStressTS framework is directly applicable to validating vol estimation in Strategy A (TSMOM v3), where the 28-bar log-return vol window must remain accurate through regime transitions—the Propr breach in May 2026 plausibly coincided with a vol regime shift. Running the Heston and HMM generators against the vol estimator in `strategies/tsmom_v2_propfirm/signal.py` would reveal whether the tanh signal degrades gracefully or catastrophically under jump-and-regime conditions. For Strategy D (`Futures/research/active/strategy_d/`), the diagnostic profile approach could help distinguish whether D3's Sharpe=-1.08 and D5's Sharpe=-1.32 stem from regime misidentification (HMM generator relevant) or from fat-tail fill slippage (alpha-stable generator relevant)—a cleaner attribution than the current portfolio-combination-plus-regime-filter approach. The benchmark is also useful as a stress-testing scaffold for any new strategy D candidate before the 3-mod budget is consumed.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Methodology tool for stress-testing vol estimators and regime filters; no direct backtest path without implementing the full synthetic generator suite.
