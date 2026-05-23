# Modeling Asymmetric Volatility with EGARCH [Krzysztof Ozimek]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=y9Mta8kHQ2&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 9888745c05ef79d9774fb219f7415ca9

## Summary
An accessible introduction to the Exponential GARCH (EGARCH) model, which captures the leverage effect — negative return shocks increase future volatility more than positive shocks of equal magnitude. EGARCH models log-variance rather than variance, naturally satisfying non-negativity without constraints, and is better suited to the asymmetric shock structure observed in both equity and crypto markets.

## Why it might be useful
Strategy A (crypto TSMOM v3) uses a 28-bar rolling log-return standard deviation for vol targeting (CLAUDE.md: "vol: log returns, 28-bar window, sqrt(365) annualization, MUST match backtest"). BTC, ETH, and SOL exhibit strong leverage effects — crash events amplify vol asymmetrically. Replacing the 28-bar rolling vol estimator with EGARCH(1,1) could tighten position sizing during crypto drawdown regimes without changing the signal itself. This is modification #1 candidate for Strategy A v4 (current v3 PAUSED, awaiting new propfirm). Requires walk-forward ≥5 folds with HAC lag-6 on the resulting Sharpe before committing. EGARCH is explicitly in the CLAUDE.md methodology toolkit.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Swap Strategy A's 28-bar rolling vol for EGARCH(1,1) as modification #1 for v4. Data available in data/raw/ (cached parquet). Implement with statsmodels arch package in VPS venv. 2-day effort including walk-forward re-validation.
