# The Sharpe Stability Ratio of Trading Strategies — Macrosynergy

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=8D5DJ4NckT&source=feedburner
**Captured**: 2026-05-31 08:06 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 18973917d2174345c860fd27880904c8

## Summary
Macrosynergy introduces a diagnostic called the "Sharpe stability ratio" (SSR), defined as the mean Sharpe ratio computed over sequential overlapping lookback periods, divided by its standard deviation across those periods. The ratio captures whether a strategy's risk-adjusted returns are consistent over time or are concentrated in a handful of favorable windows — a stability check orthogonal to the single OOS Sharpe. Higher SSR indicates that performance is not luck-of-timing. The excerpt is truncated; numeric thresholds and the full methodological detail are in the full article.

## Why it might be useful
This is a concrete methodological complement to the walk-forward validation already mandatory in Algo_claude (≥5 folds, expanding window). The SSR is essentially a signal-to-noise ratio of the per-fold Sharpes — it penalizes strategies where one outstanding fold drives the aggregate, which is exactly the concern with Strategy D (D3+D5 portfolio: two individually failed strategies whose combination is being tested). Computing SSR on Strategy C's 9 walk-forward folds (7/9 positive, Sharpe 1.52) would validate whether the win folds are spread out or clustered. It also directly complements DSR (Bailey-LdP, mandatory for n_mod≥5 per L20): SSR checks temporal consistency while DSR checks correction for multiple testing — they are orthogonal audits. Implement SSR as a fifth mandatory diagnostic alongside HAC, AMTP, WF, and daily vol targeting.

## Extracted content
The author defines the ratio as: SSR = mean(Sharpe_over_lookback_windows) / std(Sharpe_over_lookback_windows). No numeric thresholds, Python code, or full formulas in the excerpt. Full article needed.

## Action proposed
TEST_LATER — Implement SSR as a diagnostic function in `Portfolio/risk/` or as a standalone utility, then apply retroactively to Strategy C (9 folds) and prospectively to Strategy D. Blocked on reading the full article for threshold definitions and lookback-window methodology.
