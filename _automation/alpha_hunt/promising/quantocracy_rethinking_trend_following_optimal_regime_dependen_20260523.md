# Rethinking Trend Following: Optimal Regime-Dependent Allocation [Alpha Architect]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=aE4mv1x4WA&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 80c0dbd38c8aecd4531306f3b76be17d

## Summary
Rather than asking "how do we detect trends better," the paper examined here asks "how should allocation to a trend-following strategy vary across market regimes?" The central finding is that optimal trend allocation is regime-dependent: the strategy should be sized up or down not based on the trend signal strength alone, but based on the identified macro or vol regime in which the trend is occurring.

## Why it might be useful
Directly applicable to Strategy A (crypto TSMOM v3, PAUSED): the tanh signal already vol-normalizes position size, but this framework adds a layer — regime-conditional scaling on top of vol targeting. Concretely, a two-regime model (high-vol expansion vs. low-vol consolidation) applied to crypto would increase position size in confirmed uptrend + low vol regimes and reduce in high vol or regime-ambiguous conditions. This is modification #1 or #2 candidate for Strategy A v4. Also relevant to Strategy C (NQ momentum): the ORB signal could be scaled by market regime (trending vs range-bound open) to improve the risk-adjusted Sharpe above 1.52. Full article needed for the specific regime classification methodology used.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_NOW

Strategy A v4 (awaiting new propfirm deployment) needs regime-dependent sizing to hit PROPFIRM_PASS gate (MaxDD<-10%). Read full article, implement regime classifier on crypto data in data/raw/, add regime-scaled sizing to TSMOM signal. Walk-forward ≥5 folds with HAC lag-6. Counts as modification #1 toward 3-mod cap.
