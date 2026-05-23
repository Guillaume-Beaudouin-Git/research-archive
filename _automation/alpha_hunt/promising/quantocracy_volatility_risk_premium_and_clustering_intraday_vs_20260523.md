# Volatility Risk Premium and Clustering: Intraday vs Overnight Dynamics [Relative Value Arbitrage]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=CkL3XQe7dt&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 39fc3e9cafe84808d04165b7f5e6be65

## Summary
Research decomposing the volatility risk premium (the gap between implied and realized vol) into its intraday and overnight components, examining how vol clustering behaves differently in each session. The argument is that VRP collection strategies and hedging approaches should separate the two components rather than treating daily vol as monolithic — intraday VRP dynamics differ from overnight dynamics due to different market microstructure and participant composition.

## Why it might be useful
CLAUDE.md archives "VIX term structure carry (3 tests): edge died post-2020." This article is not about VIX term structure specifically but about VRP decomposition — a different mechanism. The intraday vs overnight split is however directly relevant to Strategy C (NQ opening momentum): the ORB signal (09:30-09:45) is entirely an intraday event, and vol clustering within that window determines whether the 30pt opening range minimum filter captures genuine vol expansion or noise. If intraday VRP is negatively autocorrelated (overnight VRP is positively autocorrelated), the morning session entry window may benefit from a VRP-based entry quality filter.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

If intraday VRP dynamics are quantified in full article, test whether overnight VRP (e.g., realized vol of yesterday close vs today open) predicts Strategy C ORB signal quality. Would count as a filter modification toward Strategy C's 3-mod cap. 1-day effort with NQ 1-min data.
