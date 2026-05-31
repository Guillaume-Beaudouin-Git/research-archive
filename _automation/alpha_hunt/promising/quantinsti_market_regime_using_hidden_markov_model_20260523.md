# Market Regime Detection with Hidden Markov Models and Random Forest Signals — Python Guide

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/regime-adaptive-trading-python/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic, code_quant, methodology], L2_OK
**Hash**: c715ca7058da1ed2ef4311103e3b0c9f

## Summary
A hands-on tutorial combining Hidden Markov Models for unsupervised market regime detection with a Random Forest classifier that generates signals conditioned on the active regime. The HMM is fitted on price and volatility features to identify discrete latent states such as trending versus mean-reverting or low- versus high-volatility periods. Once regimes are labeled, the RF classifier is trained within each state to generate directional signals. The article includes complete Python code and a walk-forward backtesting framework. No specific performance figures are cited in the excerpt; full article access is needed.

## Why it might be useful
This is directly applicable to Strategy D (D3+D5 portfolio combination, `Futures/research/active/strategy_d/hypotheses_preregistered.md`). D3 (opening range mid-fade 09:45-11:00, Sharpe=-1.08) and D5 (afternoon BB squeeze breakout 14:00-15:30, Sharpe=-1.32) both failed individually but maintain useful decorrelation from Strategy C (corr_C=-0.21 and -0.05 respectively). The active working hypothesis is that a regime filter can rehabilitate the combined D3+D5 portfolio. An HMM with 2-3 states fitted on NQ daily realized volatility and intraday range features represents a concrete, pre-registerable candidate for this filter. The NQ 1-min dataset is available locally at `Dataset_NQ_1min_2022_2025.csv`. Implementation would use `hmmlearn` or `pomegranate` for HMM fitting and `sklearn` for the RF layer. Walk-forward validation must span ≥5 folds with HAC lag-6 t-stats, and AMTP is mandatory if multiple regime parameterizations are compared. Note from L15: regime overlays on high-Sharpe (SR>1.0) strategies yield only ~1.7%/yr lift — but D3+D5 starts from negative Sharpe, so the filter acts as a trade-count screener rather than a marginal overlay. Strategy D has 3 modifications available, 0 consumed.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for code extraction.

## Action proposed
TEST_LATER — Directly applicable to Strategy D regime filter (active research, 0/3 mods consumed). NQ 1-min data available locally. Implementation cost ~1-2 days: HMM fitting on daily NQ features + walk-forward ≥5 folds with HAC validation. Read full article first to extract code skeleton.
