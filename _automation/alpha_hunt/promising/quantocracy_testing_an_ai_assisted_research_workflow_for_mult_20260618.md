# Testing an AI-Assisted Research Workflow for Multi-Asset Pullback Strategy Discovery

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=9TZToe8G6R&source=feedburner
**Captured**: 2026-06-18 05:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: cbf7674d67edfc7252f8b14f8ab9bada

## Summary
A Quantpedia study exploring short-term price reversals — systematic retracements following adverse daily returns — across multiple asset classes, using an AI-assisted workflow to accelerate hypothesis generation and backtest iteration. The framework attempts to turn the well-documented post-adverse-return bounce into a systematic trading strategy by defining entry rules around adverse-day thresholds, holding periods, and asset filters. The excerpt is truncated but the approach is framed as multi-asset and systematic, implying cross-sectional or at least multi-market testing.

## Why it might be useful
Short-term reversal is directly relevant to Strategy D's active research and the FTMO propfirm target. L24 identifies that the FTMO-suitable profile requires high daily Sharpe, WR > 55%, win/loss ≈ 1, low kurtosis, and high trade frequency — which are precisely the properties that a well-calibrated mean-reversion / pullback strategy should exhibit (vs. lumpy momentum which hits the 44% structural ceiling). The archived D4 (Lunch RSI reversal, Sharpe -0.70, IC_t 1.61) and D2 (VWAP touch fade, signal inverted) both failed individual NQ tests, but they tested a narrow intraday window on a single instrument. A multi-asset pullback approach could raise N above the L12 floor and spread cost drag across instruments. Key caveat: L12/L12b (event-count ceiling gate) and L33b (spread as intraday-flat executioner) apply — the full article must specify the holding period (intraday vs overnight) and the cost model to know if the edge survives retail tier. Read before building anything.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Description truncated at strategy introduction. Full article needed for further extraction.

## Action proposed
TEST_LATER — If the full article includes futures or CFD instruments with realistic cost assumptions, run the multi-asset pullback scan on the `data/deep_history_utc/` M1 series (equity indices: US500, US100, GER40) for overnight holding periods, verifying cost gate E[gross/trade] > 3 × cost/trade (L11b) and N_effective above the L12 floor. Do NOT proceed if the strategy is equities-only at daily close (L11 beta dominance). Priority: lower than Tempered Skew-t (more data work required, no confirmed numbers yet).
