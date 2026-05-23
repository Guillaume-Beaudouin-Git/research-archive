# Dual Momentum Allocation Between Physical Gold and Bitcoin [Quantpedia]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=nE7Dy5q49i&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 0ab0632748cead0e979e0b72d208dd3b

## Summary
Quantpedia examines dual momentum — combining absolute and relative momentum signals — to dynamically allocate between physical gold and Bitcoin as competing alternative stores of value. The framework switches between the two assets (or holds cash) based on which exhibits stronger momentum and whether either clears an absolute momentum hurdle.

## Why it might be useful
Strategy A (crypto TSMOM v3, PAUSED) currently runs on BTC, ETH, SOL with tanh momentum. Extending to gold as a 4th asset with relative momentum between gold and BTC is a candidate modification for Strategy A v4. However, CLAUDE.md explicitly archives "TSMOM on commodity ETFs: ETF roll drag contaminates momentum signal" — gold would likely enter via GLD (ETF), not futures. Before testing, verify GLD roll drag is negligible (it's a physically-backed ETF, so roll drag is minimal, unlike commodity futures ETFs). If GLD passes the roll-drag check, this would be modification #1 for Strategy A v4 and requires ≥5 walk-forward folds with HAC lag-6.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Low priority. First verify GLD doesn't have ETF-like roll drag (physically backed — likely OK). Then run dual momentum BTC+GLD as Strategy A v4 modification. Data available via yfinance or cached parquet.
