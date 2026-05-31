# Dynamic Capital Allocation via Market Breadth and Random Forest Regime Detection (EPAT Project)

**Source**: quantinsti
**URL**: https://blog.quantinsti.com/epat-project-machine-learning-market-regime-detection-random-forest-python/
**Captured**: 2026-05-23 18:12
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: d727feaac7d1b9fcfd633ad79ed6a7f0

## Summary
An EPAT student project that uses market breadth indicators — advance/decline ratios and the fraction of stocks trading above key moving averages — combined with a Random Forest classifier to distinguish bull, bear, and high-volatility regimes. Capital allocation is adjusted dynamically by regime: fully deployed in bull states, reduced or flat during bear and high-volatility regimes. The regime-conditional allocation design aims to cut tail drawdowns without sacrificing participation in trending markets. No specific return or Sharpe figures appear in the excerpt.

## Why it might be useful
Market breadth offers a complementary angle to HMM-based regime detection for Strategy D's active regime filter requirement (`Futures/research/active/strategy_d/hypotheses_preregistered.md`). D3 (Sharpe=-1.08) and D5 (Sharpe=-1.32) each failed individually; the active hypothesis is that a regime gate can rehabilitate the D3+D5 combination. Breadth features have an interpretability advantage over HMM latent states: they carry an explicit economic narrative — "NQ intraday breakouts fire during broad participation" — that can be pre-registered with a clear IC hypothesis before any backtest, satisfying the methodology rule. Concretely, NYSE advance/decline ratio and SPY percentage of stocks above the 50-day MA are available daily via yfinance and could serve as conditioning variables. Any breadth-based regime gate must be validated with ≥5 walk-forward folds and AMTP if multiple threshold combinations are tested. The sector_hothand_propfirm active research (`Equities/research/active/sector_hothand_propfirm/`) also uses a regime conditioning framework; lessons from its audit (`_audit/sector_hothand_audit_2026-05-30.md`) apply here.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — Useful background for Strategy D regime filter design, complementary to the HMM article (`quantinsti_market_regime_using_hidden_markov_model_20260523.md`). Read both before pre-registering a specific breadth-based regime feature for D3+D5.
