# Daily Long/Short Trend Following: Parameters, Asset Classes, and Universe Depth (Delphic Alpha)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=ygkLLr1xQs&source=feedburner
**Captured**: 2026-07-22 06:30 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: a83e5c5e3e567a5507fe3b3d9b2e7cb0

## Summary
The author runs one daily long/short trend-following signal, held constant, across four asset classes to compare relative net performance: futures produced a net Sharpe of 0.73 and crypto 0.56 (equities and FX figures are cut off in the excerpt). The title suggests the piece also studies how universe depth (instrument count) affects the strategy's stability, bearing on how many instruments a trend or cross-sectional system needs to behave reliably.

## Why it might be useful
Strategy A's live excess Sharpe was recalculated to 0.566 on the BTC/ETH/SOL long-only config (IC95 [-0.50, 1.63], containing zero) — this external benchmark's crypto net Sharpe of 0.56 for a LONG/SHORT trend variant lands in the same neighborhood, which is notable given L11 (long-only CS crypto is beta-dominated regardless of IC; only delta-neutral escapes it): a long/short trend variant reaching comparable Sharpe to A's long-only excess Sharpe is a concrete external data point on whether adding a short leg would help Strategy A or just add complexity. Both reported numbers (futures 0.73, crypto 0.56) also fall inside L21's Sharpe-by-category range for CS academic daily strategies (0.3-1.2), unlike another item in this batch (a claimed 3.275 FX Sharpe), making this a comparatively credible external reference point.

## Extracted content
The author reports "a net Sharpe of 0.73" for futures and "0.56" for crypto, from the same daily long/short trend signal run across asset classes.

## Action proposed
TEST_LATER — a genuine long/short variant of Strategy A's trend signal is a concrete, scoped test but requires new short-leg infrastructure and a delta-neutral/L-S backtest harness (medium implementation cost), and the full article's parameter/universe details are not in the excerpt.
