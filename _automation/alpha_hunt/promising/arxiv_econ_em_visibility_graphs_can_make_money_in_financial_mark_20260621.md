# Visibility Graphs RSI: A Graph-Based Technical Indicator

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.01300
**Captured**: 2026-06-21 10:06 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 0b643f5dd0caf13cca7c6ff9faab2358

## Summary
The paper proposes the Visibility Graph Relative Strength Index (VGRSI), which encodes price series as a directed graph where nodes are price observations and edges connect points with unobstructed line-of-sight in the time-price plane, then computes a backward visibility degree distribution rescaled to 0-100 like a standard RSI. Evaluated on DJI30, EUR/USD, and XAU/USD over 503 days (2024-2025) using a walk-forward approach with 30-day optimization and 7-day test windows. The backtested P&L was $146k (DJI30), $69k (EUR/USD), and $125k (XAU/USD) from a $1k-per-trade sizing. The authors report Sharpe ratios of 2.55 (DJI30), 3.1 (EUR/USD), and 3.6 (XAU/USD), with moderate drawdowns of 10-18% on a $10k portfolio.

## Why it might be useful
The EUR/USD and XAU/USD assets overlap with our FX deepdive data (`data/deep_history_utc/`). However, the sample is extremely short — 503 days (about 1.4 years, 2024-2025), which falls under L14 (N<250 is inadmissible for Sharpe estimation on any non-daily-reset strategy). Sharpe of 2.55-3.6 on 503 days with a 30-day optimization window means only ~17 independent walk-forward periods: extremely high estimation noise. This has the same signature as our archived FX strategies where OOS performance was inflated by the short testing window. The mechanism itself (visibility graph as a nonlinear RSI) is novel and could be tested on longer data, but only after applying DSR correction (L20). Connection to archived `Forex/research/archived/` strategy families (L43: retail FX intraday-flat is cost-dead): any FX signal at this frequency (3.3-4.8 trades/day implies intraday) must clear the L43 gross_per_trade/cost_p95 ≥ 1.5 gate first.

## Extracted content
"The performance of the indicator was evaluated using an automated trading strategy based on a 30-day optimisation window and a 7-day test window for three instruments representing different asset classes: DJI30, EUR/USD and XAU/USD over the 2024-2025 period (503 trading days)."

The author claims Sharpe ratios of 2.55 (DJI30), ~3.1 (EUR/USD), and 3.6 (XAU/USD) with drawdowns of 10-18% relative to a $10,000 portfolio.

"A relatively low trading intensity (3.3-4.8 trades per day)"

No code available in abstract. Implementation requires constructing visibility graph from price series.

## Action proposed
TEST_LATER

Before any implementation: (1) Apply L14 and L43 gates. At 3-4 trades/day on FX, need gross_per_trade > 3× cost/trade. With 0.15% RT FX cost, need ≥0.45% per trade — plausible given the reported numbers but only on 503 days. (2) If gate passes: test VGRSI on `data/deep_history_utc/EURUSD_M1.csv` 2007-2026 under walk-forward ≥5 folds, HAC SE. Cost: 1.5 days (implement visibility graph + WF harness). LATER because L43 gate failure is likely on longer history — intraday FX flat strategies have been systematically dead in 2007-2026 sample.
