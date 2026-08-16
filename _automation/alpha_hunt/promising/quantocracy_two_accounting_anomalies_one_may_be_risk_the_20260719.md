# Two Accounting Anomalies: One May Be Risk, the Other Is Mispricing

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=Jh6BEiRDTW&amp;source=feedburner
**Captured**: 2026-07-19 07:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: ff8f309edca745dfe822b23691d4a81e

## Summary
The post (via Alpha Architect) revisits two long-standing equity anomalies — the accrual anomaly and post-earnings-announcement drift (PEAD) — and argues they have different economic origins despite both being persistent return predictors: one is framed as compensation for a genuine risk factor, the other as a mispricing that the market fails to correct quickly. The captured excerpt states the framing but does not yet give the specific test used to separate the two explanations.

## Why it might be useful
PEAD is the equities-literature instance of exactly the post-event momentum-continuation mechanism codified in lesson L42 (pre-FOMC drift continues after the event rather than reversing) — this is useful corroborating background for L42's mechanism, not a new test, since the asset classes and cost structures differ entirely (no equities-anomaly infra in this repo). More directly useful is the risk-vs-mispricing framing itself: it's the same question lesson L38's beta-orthogonality test asks of any "structural premium" (regress it on a vol-targeted buy-and-hold of the primary asset; R²>30% means it's beta-timing, not orthogonal alpha) — if the full article specifies how it separates a risk-based anomaly from a mispricing-based one, that separation test is a candidate to formalize alongside L38 for future propfirm-adjacent CFD candidates that need to distinguish real edge from disguised beta.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction (the risk-vs-mispricing separation methodology is not yet visible in the captured text).

## Action proposed
REFERENCE — equities anomaly with no local data pipeline or active-strategy fit; useful only as conceptual corroboration of already-established L38/L42 methodology, no concrete implementation step from the excerpt alone.
