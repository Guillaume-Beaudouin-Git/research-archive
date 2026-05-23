# The NAAIM Exposure Index: Incorporating Active Investment Manager Sentiment into Asset Allocation [Portfolio Optimizer]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=wd3U1zbsGF&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e4c638506c62756be881e8a93116101e

## Summary
Portfolio Optimizer examines the NAAIM Exposure Index — a weekly survey of US equity exposure reported by active managers in the National Association of Active Investment Managers — as a sentiment signal for asset allocation. The piece tests whether incorporating manager-positioning data improves return and risk metrics versus a passive equity allocation, treating NAAIM as a contrarian or trend-following indicator depending on regime. The framing is allocation-tilt, not market timing in the absolute sense.

## Why it might be useful
Marginally relevant for Algo_claude as a sentiment overlay candidate. The NAAIM signal is weekly-frequency US equity sentiment — it does not fit Strategy A (crypto TSMOM), B (delta-neutral HL), or C (intraday NQ momentum) directly, since none of those touch US equity allocation. The methodology angle is more interesting than the signal itself: it's an example of how a position-disclosure dataset gets transformed into an allocation tilt with walk-forward validation. Could become relevant if I ever build an equity book outside the propfirm constraint. Cross-reference with archived "equity momentum 73 large caps" (FAIL, β-dominance) — NAAIM sentiment overlay was not part of that experiment and could be a Phase-2 angle if equity ever returns to active research. Data accessibility: NAAIM publishes the index weekly for free, so no paywall risk.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

No fit to current active strategies. Equity sentiment overlay is interesting methodologically but would require building an equity allocation framework first, which is not on the roadmap given propfirm focus + crypto/futures personal book split.
