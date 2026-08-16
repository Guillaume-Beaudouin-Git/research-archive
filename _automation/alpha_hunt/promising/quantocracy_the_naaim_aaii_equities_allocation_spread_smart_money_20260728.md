# The NAAIM-AAII Equities Allocation Spread: Smart Money Relative Sentiment Indicator

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=OwFDTYjrzV&source=feedburner
**Captured**: 2026-07-28 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 5e7b446042d437c861b9d4525e9ec3ae

## Summary
Portfolio Optimizer follows up on an earlier post about the NAAIM Exposure Index (active manager equity exposure survey) by constructing a spread between NAAIM (professional/"smart money") and AAII (retail sentiment) allocation surveys, framed as a relative sentiment signal that isolates the professional-vs-retail positioning gap rather than either survey in isolation. The excerpt establishes only the motivation and data sources (two long-running US equity sentiment surveys); it does not yet state the trading rule, sample period, or performance metrics for the resulting spread signal.

## Why it might be useful
This falls into the same family the project has already closed twice: L17/L18 explicitly closed the sentiment-proxy branch for crypto (Fear & Greed velocity, Wikipedia attention — both found to be momentum proxies with null IC), and per the reopening-policy table that was a MECHANICAL kill (signal ≈ momentum proxy, IC null), which stays closed regardless of new instrumentation. A NAAIM-AAII spread on US equities is a different asset class and a genuinely different construction (survey-based positioning gap, not attention/velocity), so it isn't automatically disqualified by L17/L18, but it would need the same falsification discipline: an IC test with HAC lag-6 and a check (per L37/L38) that its sign doesn't just track realized equity momentum. No active equities strategy currently exists to attach it to.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no active equities research family currently exists to receive this signal, and building the historical NAAIM/AAII spread plus an IC test from scratch is a multi-day undertaking with no immediate strategy fit.
