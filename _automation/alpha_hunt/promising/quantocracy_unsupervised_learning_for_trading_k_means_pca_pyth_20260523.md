# Unsupervised Learning for Trading: K-Means, PCA & Python Examples [Quant Insti]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=G9QxwOvAuV&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d73e969700d12ea3b6cf31cf2fa4242a

## Summary
Quant Insti's introduction to K-Means clustering and PCA applied to trading, including Python code examples. The article covers how to use K-Means to identify market regimes from price/vol feature sets and how PCA can reduce the dimensionality of multi-asset factor spaces before applying clustering. Typical use case: cluster market sessions by feature set to label regimes and use those labels as a trading signal filter.

## Why it might be useful
The K-Means regime clustering methodology is directly applicable to Strategy C (NQ opening momentum): clustering NQ pre-market (09:00-09:29) feature sets (overnight gap, pre-market vol, futures vs cash spread) could produce regime labels that improve the 78% walk-forward win rate or reduce the false-positive rate of the ORB signal. This is a cleaner approach than the current hard-coded VWAP + gap filters, and the Python code makes it immediately implementable with Dataset_NQ_1min_2022_2025.csv. Also connects to the LLM regime labeling item (item 06): K-Means provides the deterministic baseline referenced there. PCA on crypto return features could also improve Strategy A's vol estimate input.

## Extracted content
No code in excerpt. Full article contains Python implementation — retrieve for code extraction.

## Action proposed
TEST_LATER

Extract Python K-Means clustering code from full article. Apply to NQ pre-market feature set to build regime labels for Strategy C filter. 1-2 day effort. Lower priority than completing VWAP 1-min vs 5-min reconciliation first.
