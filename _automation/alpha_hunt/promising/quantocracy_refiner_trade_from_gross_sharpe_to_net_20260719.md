# Refiner Trade: From Gross Sharpe to Net (Beyond Passive)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=JIYYWiAeYg&source=feedburner
**Captured**: 2026-07-19 07:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 0017d4035d88c21d8899424610c76bce

## Summary
This piece (part of the same "Refiner Trade" series as another item in this batch) walks through converting a strategy's headline gross Sharpe of roughly 1.5 into a realistic net figure by subtracting broker fees and other real-world frictions. It explicitly argues that gross Sharpe is the easiest number to produce and the least meaningful one to quote, because it assumes fills and prices that may not actually be achievable in live trading.

## Why it might be useful
This mirrors the project's own 2026-07-29 recalculation of Strategy A: the widely-cited "1.33 OOS" headline turned out to be gross-of-RF on a 14-coin universe, while the true live-config (BTC/ETH/SOL) excess Sharpe is only 0.566 with an IC95 that contains zero — exactly the gross-vs-net distinction this article is making, which gives it direct resonance with the project's own hard-won lesson. It also reinforces the "5 mandatory script fixes" (excess returns via FRED DTB3, HAC lag-6, daily vol targeting) and L33 (it is the real instrument's cost structure, not a generic cost assumption, that decides net performance) — useful as external validation for why CLAUDE.md never cites gross Sharpe for any live strategy.

## Extracted content
The author reports carrying forward "a gross Sharpe of about one and a half" from the prior part of the series, framing it as the "easy" figure that will be reduced once real costs are applied. No code or formulas are present in the excerpt.

## Action proposed
REFERENCE — restates a principle the repo already enforces internally (gross vs. net/excess Sharpe); no new test or data path, useful as methodological corroboration.
