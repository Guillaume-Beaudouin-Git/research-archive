# PyBroker: Open-Source Python Backtesting with Walk-Forward Analysis and Bootstrapped Metrics

**Source**: hn_algotrading
**URL**: https://github.com/edtechre/pybroker
**Captured**: 2026-06-25 04:00 UTC
**Filters passed**: L1=[metrics, code_quant, methodology], L2_OK
**Hash**: 1d456d1ccfa544ff91ca85f1434ae414

## Summary
PyBroker is an open-source Python backtesting framework built on NumPy and accelerated with Numba. Its key differentiator is native walk-forward analysis that simulates live retraining across multiple time windows, directly mirroring the methodology required by CLAUDE.md (≥5 folds, no single split). It also computes Sharpe, Profit Factor, and MaxDD via randomized bootstrapping — randomly sampling returns to generate thousands of alternate scenarios — rather than relying on point estimates, providing statistical significance testing out of the box. Additional features include multi-instrument support with ranking-based position sizing, historical data via Alpaca and Yahoo Finance, and automatic caching of data/indicators/models.

## Why it might be useful
Two concrete uses: (1) The bootstrapped Sharpe calculation maps exactly onto the block bootstrap requirement in CLAUDE.md methodology (Politis-Romano for clustered returns). Comparing PyBroker's bootstrap output against the current manual implementation in research scripts would validate or surface discrepancies — run on NQ ORB iter_10 data (`data/raw/NQ_1min_databento_2010-2026.parquet`) as a sanity check. (2) For Strategy D (D3+D5 portfolio combination under active research), PyBroker's walk-forward infrastructure could replace the bespoke expanding-window code in `Futures/research/active/strategy_d/` — reducing implementation surface and making the 5-fold gate auditable by a third party. The limitation is that PyBroker uses Alpaca/Yahoo Finance data sources, not the local Databento parquet, so data integration would require a custom feed. Worthwhile to evaluate before writing new walk-forward infra for D.

## Extracted content
From the HN post (author description):

> "PyBroker calculates metrics such as Sharpe, Profit Factor, and max drawdown using bootstrapping, which randomly samples your strategy's returns to simulate thousands of alternate scenarios that could have happened. This allows you to test for statistical significance and have more confidence in the effectiveness of your strategy."

> "Walkforward Analysis [...] splits your historical data into multiple time windows and then walks forward in time in the same way that the strategy would be executed and retrained on new data in the real world."

The author claims: 70 points on HN, released 2023-03-09. No specific Sharpe/MaxDD benchmark claims for the framework itself.

## Action proposed
TEST_LATER — Worth evaluating the walk-forward and bootstrap modules against current bespoke implementations before building new infra for Strategy D. Data integration is the main friction (Databento parquet vs Alpaca/Yahoo). Estimated 0.5 days to evaluate.
