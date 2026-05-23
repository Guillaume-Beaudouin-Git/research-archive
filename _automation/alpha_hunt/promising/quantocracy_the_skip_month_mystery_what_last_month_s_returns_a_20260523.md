# The Skip-Month Mystery: What Last Month's Returns Are Really Telling You [Alpha Architect]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=87sqiXPZ22&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 9dd7248775a47e0efb635f972dcf7e53

## Summary
New research challenges the standard momentum construction rule of skipping the most recent month before the lookback window (the "skip-month" convention). The article examines what short-term return reversal in the most recent month actually signals — whether it reflects market microstructure (bid-ask bounce, liquidity effects) or a genuine behavioral phenomenon — and tests whether removing the skip-month convention changes momentum performance.

## Why it might be useful
Directly applicable to Strategy A (crypto TSMOM v3): the signal uses 28-day cumulative return. Crypto perpetuals don't have the same monthly reconstitution pressure as equities, but they do have weekly funding settlement cycles (8h for Hyperliquid). Testing whether the skip-month convention (e.g., using day -2 to day -29 instead of day -1 to day -28) improves the TSMOM signal on BTC/ETH/SOL is a clean, low-cost test. The existing cached parquet data makes this implementable in under 1 day. If the skip-month effect is microstructure-driven in equities but absent in crypto (which has continuous 24h trading), this is a useful null result that confirms the current 28-day window is appropriate.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

Test skip-month convention on Strategy A signal (compare 28-day with and without 1-day lag). Data in data/raw/ (cached crypto parquet). Half-day effort. Counts as modification #1 if result improves Sharpe — or useful null result that doesn't count as modification.
