# I Paper-Traded 22 Popular Crypto Strategies on Real Fees for 10 Days [Strat Proof]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=dtjwhdpNYk&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 0296c2a5713c9412fbbd3cca94769bde

## Summary
A practitioner forward-tested 22 common crypto trading strategies simultaneously via a paper trading bot with realistic fee modeling over a 10-day window. The article reports strategy-level P&L rankings, fee drag per strategy, and which approaches survived versus failed under live market conditions. The motivation (Claude + TradingView integration for bot construction) and methodology (parallel paper trading with actual exchange fee schedules) are documented.

## Why it might be useful
Strategy B (delta-neutral carry on Hyperliquid, LIVE on testnet since 2026-05-17) is currently in its own 60-day paper validation window. The author's fee drag findings across 22 strategies could calibrate whether Strategy B's 0.17% round-trip cost assumption (CLAUDE.md) is conservative or aggressive for Hyperliquid maker/taker fee structures. For Strategy A (crypto TSMOM, PAUSED): checking if the 22-strategy set includes any long-only TSMOM variant tells us how we rank versus practitioner-built alternatives. 10 days is too short for AMTP-valid statistics but useful for fee benchmarking.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for fee data extraction.

## Action proposed
TEST_LATER

Read full article for fee drag per strategy type. Cross-reference with Strategy B Hyperliquid rate data in data/funding_carry/. Low implementation cost (read-only).
