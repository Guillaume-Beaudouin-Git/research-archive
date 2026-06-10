# What Trend Following Actually Adds to a Risk-Premia Core

**Source**: quantocracy (via Beyond Passive)
**URL**: https://quantocracy.com/redirect.php?key=ep3cEZqWhO&source=feedburner
**Captured**: 2026-06-10 06:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: c4de23ec69921ec63a6bb930b2c61a6f

## Summary
The author documents a Sharpe ratio improvement from 1.1 to nearly 1.5 when a trend-following program is overlaid on a three-asset risk-premia core portfolio. Crucially, the article argues against interpreting this as free diversification: the protective benefit of trend following during drawdowns is conditional on the trend signal being correctly positioned at the moment of stress, and the correlation between trend and risk-premia is non-stationary. The implied message is that trend following earns its place in the portfolio through crisis-alpha in specific regimes, not through constant decorrelation.

## Why it might be useful
The SR 1.1→1.5 improvement claim is directly comparable to the Algo_claude A+B portfolio book (SR=2.31, gate for D at SR>2.54). Strategy A is a trend-following component (TSMOM v3, SR=1.33 OOS) and Strategy B is a carry/delta-neutral component analogous to a risk-premia position. The article's non-stationary correlation caveat maps precisely to the CLAUDE.md note that ρ_AB=0.039 is full-sample — if this correlation spikes during crypto risk-off (both A and B long crypto in different forms), the portfolio SR of 2.31 is overstated in exactly the stress scenarios where it matters most. Concrete action: after reading the full article, extract the regime-conditional correlation methodology and apply it to A and B's return series to stress-test the ERC SR=2.31 estimate. Specifically, check whether A and B become positively correlated during the 2022 crypto bear market period that both series cover.

## Extracted content
The author claims Sharpe ratio improves from 1.1 to nearly 1.5 when overlaying a trend-following program on a three-asset risk-premia portfolio.

## Action proposed
TEST_LATER — the regime-conditional correlation methodology has direct application to stress-testing the A+B book SR=2.31 before Strategy D is selected. Requires reading the full article to extract the correlation decomposition method; implementation would be a ~0.5-day analysis in Portfolio/risk/ using existing A and B return series.
