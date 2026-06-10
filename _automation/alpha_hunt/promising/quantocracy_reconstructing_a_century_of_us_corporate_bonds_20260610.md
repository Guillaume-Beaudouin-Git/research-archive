# Reconstructing a Century of U.S. Corporate Bonds

**Source**: quantocracy (via Quantpedia)
**URL**: https://quantocracy.com/redirect.php?key=GHOYmBfpr6&source=feedburner
**Captured**: 2026-06-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 05922aa034e40b796739e88e0895f95e

## Summary
Most empirical work on corporate bond pricing relies on post-1973 data from TRACE and Mergent databases, leaving a blind spot over the full 20th century. This Quantpedia-featured paper reconstructs US corporate bond return series going back approximately 100 years by combining fragmentary historical price records with yield-curve inference. The reconstruction spans multiple complete business and credit cycles — Great Depression, WWII expansion, stagflation — enabling proper out-of-sample testing of credit factor models that would otherwise only have ~50 years of history. The methodology appears to focus on maintaining consistency across data sources rather than raw yield interpolation.

## Why it might be useful
The most direct connection is to the active ZN Baltussen research (`Futures/research/active/zn_baltussen/`) studying bond futures momentum: if corporate bond premia are persistent over 100 years, that strengthens the prior for duration-momentum on CME ZN futures, and the century-long dataset provides the kind of multi-regime validation that walk-forward on 20 years cannot. The second connection is to the archived multi-asset TSMOM (Sharpe 0.21, alpha t=1.31 — archived), where adding investment-grade credit as an asset class was not tested; a 100-year series would enable a cleaner test of whether IG credit improves cross-sectional breadth without the ETF roll drag problem (L5 in methodology). Concrete action: check if the paper provides downloadable series or if Quantpedia packages it as a dataset — if accessible, re-run the multi-asset TSMOM with IG credit added, with costs set to 0.01% RT (futures) rather than 0.10% (ETF).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — data reconstruction paper with potential relevance to ZN Baltussen and multi-asset TSMOM, but the primary blocker is data accessibility (no download link in excerpt). Revisit if Quantpedia provides the series as a premium dataset.
