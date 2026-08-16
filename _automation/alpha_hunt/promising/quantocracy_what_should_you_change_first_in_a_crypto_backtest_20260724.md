# What Should You Change First in a Crypto Backtest? 99.75 Million Tests (Rulyfi)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=zllo4aHObq&source=feedburner
**Captured**: 2026-07-24 07:30 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: b0a7b17f47f615768a4b0d5642842027

## Summary
The author ran a very large-scale sensitivity sweep — 99.75 million backtest variations across ten different market-direction regimes — to determine whether entry rules or exit rules drive more of a crypto strategy's results. The reported takeaway is that neither component dominates uniformly: win rate is consistently more sensitive to exit design across all ten regimes tested, while maximum drawdown is more sensitive to a different lever (the excerpt is cut off before naming which one, plausibly entries). The framing implies a general prioritization heuristic for where to spend backtest-refinement effort depending on which output metric matters most.

## Why it might be useful
This corroborates L59 (delay+1 only certifies entry, not exit — the gap_pattern_rehab case saw its edge flip from +0.041 to -0.020 gross once exit geometry was held constant) at a far larger scale (99.75M tests vs the repo's single case study), reinforcing that exit-side re-pricing is not optional methodology. It is also directly relevant to Strategy C's ORB design (entry 09:46 ET, TP 1.5R, stop 12:30 ET, re-baselined Sharpe 0.41): if win rate is generically more exit-sensitive than entry-sensitive across regimes, that argues for auditing Strategy C's TP/stop parameters before touching the entry filter (VWAP + gap<1.2% + OR≥30pts), within the project's "max 3 modifications per strategy hypothesis" budget.

## Extracted content
The author claims "99.75 Million Tests" across "ten market-direction jobs," reporting win rate as consistently more exit-sensitive and max drawdown as more sensitive to a factor cut off in the excerpt.

## Action proposed
TEST_LATER — the ablation methodology (entry-vs-exit sensitivity sweep) is directly portable to Strategy C's existing backtest, but building a comparable multi-regime sweep harness is a multi-day undertaking, not a same-day fit.
