# Should You Trade Thin Stocks? Short-Term Opportunities in Illiquid Single-Name Equities

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=pRYhE7mXRj&source=feedburner
**Captured**: 2026-06-22 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d83d0251edf31ce6897e7608e7558c5d

## Summary

Concretum Group examines whether low-liquidity ("thin") single-name stocks offer exploitable short-term trading edges that are unavailable in liquid large-caps. Their argument, developed across several prior publications, is that institutional avoidance of illiquid names creates mispricings that systematic retail-accessible strategies can capture. The central question is whether the higher expected alpha from reduced competition is sufficient to offset the wider bid-ask spreads and execution friction inherent to thin names. The excerpt is cut before any quantitative results are disclosed — the specific alpha estimates, universe definition, and holding periods require reading the full article.

## Why it might be useful

Two connections to Algo_claude. First, the active `sector_hothand_propfirm` research (`Equities/research/active/sector_hothand_propfirm/`) reports an anomalously high t_HAC = 10.38, flagged as a red flag requiring audit (`_audit/sector_hothand_audit_2026-05-30.md`). A key question in that audit is whether the signal's apparent edge is concentrated in illiquid names — if so, the reported alpha is not executable at any meaningful notional. This article's liquidity threshold analysis could provide a quantitative benchmark for what constitutes "too thin to trade" in an FTMO-targeted equity context. Second, the archived `jt_momentum_cs` (J-T cross-sectional, 70 stocks monthly, sharpe=-0.026) failed partly due to the universe containing both liquid and illiquid stocks without differentiation. A thin-stock-specific momentum sleeve would be a distinct hypothesis — but it would need to clear N≥30 (L6) with a liquidity floor that still leaves tradeable names, and the FTMO-suitable profile (L24: high win-rate, low kurtosis, high frequency) is hard to achieve in monthly-rebalance single-name frameworks. Concretely: read the full article before the sector_hothand audit to extract the liquidity gating methodology; do not extend to a new test until the sector_hothand audit is complete.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

Requires the sector_hothand_propfirm audit to close first. If the audit confirms the t_HAC = 10.38 is real and not concentrated in illiquid names, this article becomes irrelevant for that strategy. If the audit finds the edge is thin-stock-specific, revisit this article to calibrate a liquidity floor. Implementing a net-new thin-stock strategy would require a universe construction step (yfinance + Tiingo, N≥30 liquid-enough names) and a cost gate at equities 0.05-0.10% RT — plausible in 1-2 days but no gap identified in the current book that this fills better than the active D/XS threads.
