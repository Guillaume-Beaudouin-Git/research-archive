# Does Your Backtest Survive the Adverse Same-Bar Fill? A 48.8-Million-Pair Stress Test

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=i3Vl2GB748&source=feedburner
**Captured**: 2026-07-30 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: cf0be267630807950ee61134c873cd36

## Summary
Rulyfi runs a large-scale stress test (48.8 million bar-pairs) on the well-known OHLC ambiguity problem: when a single bar shows both the take-profit and stop-loss levels touched, the bar's OHLC data alone cannot tell you which was hit first, so a backtest has to assume an order and that assumption can silently bias reported performance. The piece proposes searching under the "adverse" assumption (always resolve the ambiguity against the trade) as a stress test to see whether a strategy's edge survives the worst-case fill ordering. The excerpt doesn't give the magnitude of performance degradation found across the 48.8M pairs, only the setup.

## Why it might be useful
This is a direct, independent confirmation of L59 (the project's own finding that "delay+1 only certifies the entry — the exit needs separate re-pricing," which dropped a stop-entry/bracket-exit strategy's Sharpe from 0.99 to 0.49 when stops were repriced realistically, since 25% of stop bars open beyond the exact stop level). It's also relevant to Strategy C (NQ opening-range momentum, TP 1.5R / stop, re-baselined Sharpe 0.41), whose L19-documented slippage stress (up to 3x on adverse fills) has never explicitly been decomposed into a same-bar TP/SL ambiguity test — running Rulyfi's "adverse-order" assumption against Strategy C's existing 1-min Databento bars would extend L59's audit methodology to a second strategy. It also generalizes the "stop-entry family of 109 setups validated incompletely" caveat noted under L59 beyond the original dataset.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — applying the adverse-order stress test to Strategy C's ORB exits on the Databento 1-min data is a concrete, few-day audit (build the pair-resolution logic, rerun the 2014-2026 backtest under worst-case ordering), not a same-day fix.
