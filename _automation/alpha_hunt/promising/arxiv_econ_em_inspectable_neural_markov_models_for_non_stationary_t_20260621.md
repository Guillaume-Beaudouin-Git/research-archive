# Inspectable Neural Markov Models for Non-Stationary Time Series

**Source**: arxiv_econ_em
**URL**: http://arxiv.org/abs/2605.30943
**Captured**: 2026-06-20 12:09 UTC
**Filters passed**: L1=[topic_relevance], L2_OK
**Hash**: ad1830736a9d6acc

## Summary
Inspectable Neural Markov Models (INMMs) couple a neural state-transition function with a discrete Markov chain whose regime labels remain human-interpretable. Applied to financial volatility and return series, INMMs identify 3-5 persistent regimes with Markov transition matrices exhibiting meaningful economic content (trending, mean-reverting, high-volatility crash regimes). Walk-forward cross-validation on equity indices (2000-2024) shows 12% improvement in out-of-sample log-likelihood versus standard HMMs.

## Why it might be useful
This is the most directly applicable paper for Strategy D's regime filter component (D3 mid-fade + D5 BB squeeze, both individually failed, portfolio combination + regime filter under study). INMMs can provide interpretable regime labels for NQ intraday that go beyond simple VIX-based regime splits while remaining backtest-valid (walk-forward validated). The 3-5 regime structure aligns with Strategy D's hypothesis that different NQ market conditions (trending, mean-reverting, volatile) warrant different signal application. Concretely: implement INMM on NQ 1-min data (`data/raw/NQ_1min_databento_2010-2026.parquet`) to generate regime labels, then test whether D3+D5 combo performance stratifies cleanly by regime. Implementation: ~2-3 days (requires PyTorch or JAX for neural transition function, Viterbi decoding for regime labels).

## Extracted content
- Claims: 3-5 persistent regimes identified with interpretable economic content; 12% OOS log-likelihood improvement vs HMM (equity indices, 2000-2024)
- Architecture: neural state-transition function + discrete Markov chain with interpretable regime labels

No verbatim code or formulas in the excerpt.

## Action proposed
TEST_LATER
(Directly applicable to Strategy D regime filter; implement after D3+D5 combo baseline is established and budget of 3 mods is confirmed unspent.)
