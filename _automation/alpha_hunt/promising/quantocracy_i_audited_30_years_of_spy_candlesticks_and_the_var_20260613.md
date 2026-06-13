# I Audited 30 Years of SPY Candlesticks and the Variance Risk Premium — Peter Olayemi

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=NyzNx2ba50&source=feedburner
**Captured**: 2026-06-13 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e9d28f50e566fdf434d809ab9838cc17

## Summary
Peter Olayemi ran a systematic empirical audit of three decades of SPY daily candlestick patterns to test whether they carry predictive content for next-bar price direction. The study pairs this with an analysis of the Variance Risk Premium (VRP — the spread between implied and realised volatility) on the same instrument. The framing is explicitly falsificationist: the author built measurement tools rather than relying on anecdotal conviction. The excerpt cuts off before any result is revealed ("I built a..."), so no performance figures or IC estimates are available from this capture.

## Why it might be useful
Two concrete CLAUDE.md connections: **(1) SPX VRP Angle C is archived** with IC = −0.144 in the wrong direction (t-stat negative). Olayemi's 30-year SPY audit may reveal whether the VRP edge is regime-conditional — i.e., positive IC only during specific VIX levels or realised/implied spread regimes. Our archived Angle C used VIX_z as the sole conditioning variable on a much shorter sample; a 30-year empirical decomposition might identify a superior conditioning variable worth re-testing. Concrete action: read full article, extract the regime-breakdown table if present, compare to our archived `options/spx_vrp_angle_c/` setup. **(2) Candlestick patterns as potential decorrelated overlay for Strategy D** — D3 (NQ mid-fade, Sharpe −1.08, n_test=156) and D5 (NQ BB squeeze, Sharpe −1.32, n_test=158) both failed individually; if any candlestick formation survives a rigorous 30-year SPY test with two-sided IC (L25 gate), it could serve as a cheap entry-filter overlay on top of D3/D5. SPY is not NQ, but the methodology for measuring candlestick IC is directly transferable given that `data/raw/NQ_1min_databento_2010-2026.parquet` is already available.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

If the full article includes VRP IC decomposed by volatility regime (realised/implied spread quantile, VIX level), this reopens a targeted re-test of SPX VRP Angle C with a more discriminating conditioning filter. Data already in repo: SPY daily via yfinance, VIX daily from FRED. No new infrastructure required. Cost: ~15 min to read + ~1 day to re-run the Angle C test with any new regime variable the article surfaces. Block until full article is read; this is not a TEST_NOW because the excerpt gives no result to act on.
