# Building Meta-Strategies with Quantpedia API

**Source**: quantpedia
**URL**: https://quantpedia.com/building-meta-strategies-with-quantpedia-api/
**Captured**: 2026-06-02 16:06 UTC
**Filters passed**: L1=[academic_curated], L2_OK
**Hash**: 737199c2a911d2411c6d44037cb955b5

## Summary
Meta-strategies operate at the strategy layer rather than the asset layer: instead of allocating capital to individual strategy equity curves using rules such as trend-following, risk parity, or mean-variance optimization, rather than allocating directly to securities. Once historical return streams for multiple strategies are available, the research question shifts from "which individual strategy is best" to "how should capital be dynamically allocated across them." Standard portfolio allocation rules — momentum, volatility targeting, risk parity, mean-variance — can be applied verbatim to strategy-level returns. The Quantpedia API delivers this for their proprietary strategy library, making systematic strategy-of-strategies construction programmatic.

## Why it might be useful
The Algo_claude portfolio currently uses a static ERC allocation across A/B/C (A=10%, B=68%, C=22% at SR_B=2.0), and the gate for any new Strategy D requires lifting portfolio Sharpe from 2.24 to >2.46. Applying strategy-level momentum (e.g., 60-day trailing Sharpe weighting) or volatility-targeting to the A/B/C equity curves could improve the baseline before committing to D — directly relevant to `Portfolio/state/portfolio_state.py` and the ERC logic currently hardcoded there. The Quantpedia API itself is irrelevant (we hold our own equity curves), but the framework transfers verbatim: compute trailing return streams for A/B/C → apply momentum or vol-parity allocation → rerun the A+B+C simulation in `Portfolio/risk/propfirm_canonical.py`. This is also the strategy-level analogue of Strategy A's TSMOM signal, applying the same momentum intuition one layer up. Concrete next step: add a 60-day rolling-Sharpe weighting function to `portfolio_state.py` and benchmark dynamic vs. static ERC on the historical A+B+C equity curves to quantify whether dynamic allocation is worth the added complexity.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — Concept directly applicable to the A/B/C static ERC allocation in `portfolio_state.py`, but requires assembling a unified historical equity curve frame (A OOS period, B testnet logs, C backtest) and benchmarking dynamic vs. static allocation. Roughly 1-2 days of work. No external API dependency needed; the Quantpedia API is irrelevant for this use case.
