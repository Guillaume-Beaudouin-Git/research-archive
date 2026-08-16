# Momentum Is a Ranking Problem: Learning-to-Rank vs Regress-then-Rank (Aligrithm)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=oYjTu7PKfj&source=feedburner
**Captured**: 2026-07-26 06:00 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: ed1ae6eb9599fc1b20370895ef24ed0c

## Summary
The piece reframes cross-sectional momentum as fundamentally a ranking task rather than a return-prediction task: at each rebalance the strategy only needs the relative ordering of assets from worst to best (buy the top, sell the bottom), not calibrated return forecasts. It contrasts the conventional "regress-then-rank" workflow — fit a regression to predict returns, then sort by the prediction — against directly optimizing a learning-to-rank objective that targets the ordering itself, arguing the latter better matches what the strategy actually needs. The excerpt stops before presenting any backtest comparison between the two approaches.

## Why it might be useful
This connects to L44 (cross-sectional contrast is the cheapest, most reliable IC falsifier — e.g. Europe t=2.11 vs Asia-native t=-0.57) and to the N≥30 instruments hard rule for cross-sectional strategies: a ranking-loss reformulation would need validation on a large enough cross-sectional universe with proper walk-forward (≥5 folds) and AMTP before any Sharpe claim from it is trusted, the same discipline the repo already applies to its own CS work. It could also plausibly inform the active Commodities XS Basis+TSMOM research (`Commodities/research/active/xs_basis_tsmom/`), which already has a basis/momentum ranking step — swapping regress-then-rank for a learning-to-rank objective would be a concrete, scoped modification (counting toward that hypothesis's "max 3 modifications" budget) worth logging if pursued.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no numeric evidence in the excerpt to act on immediately, and implementing/comparing a learning-to-rank objective against the existing regress-then-rank pipeline is a multi-day methodology change, not a same-day test.
