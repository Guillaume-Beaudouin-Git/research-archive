# VIX and Trend Following Revisited: Nearly a Decade of Out-of-Sample Evidence [Alpha Architect]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=GQlFepQ5dy&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 063f80a394ff78dd7d29f8df5061156e

## Summary
The piece revisits a 2017 Alpha Architect study on combining VIX-level information with trend-following signals, this time checking whether the original conclusion survives nearly a decade of genuine out-of-sample data. The original claim was that conditioning trend exposure on the VIX level (or its regime) improves risk-adjusted performance versus unconditional trend-following. The update reportedly re-runs the same test through the post-2017 sample, which spans the 2018 vol spike, 2020 COVID crash, and the 2022 rate-hiking regime — a much harder OOS stress test than the original in-sample period. The framing is explicitly about honesty in OOS validation rather than presenting a new signal.

## Why it might be useful
This is directly on-point for the `trend_following_structural_mechanism` theme currently tracked as "declining" in `_automation/synthesis/_state.json` — a genuine multi-year OOS re-test of a vol-conditioned trend overlay is exactly the kind of paper that could revive it. More importantly, it bears on registre L54: the corrected condition for when a regime overlay helps a trend book is that the regime variable must predict the MEAN in the same direction it predicts the VARIANCE, not just flag high-vol periods (the naive MaxDD-only condition from L15 already failed on Strategy A's book). Strategy A (crypto TSMOM v3) is currently long-only and un-overlaid; before attempting any VIX-analogue vol-regime filter on it, this article's decade-long OOS design (vs. the original single in-sample window) is a useful methodological template to replicate — it directly matches the walk-forward ≥5-folds / no-single-split hard rule.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no code, data, or explicit performance numbers in the excerpt to act on directly; need the full article to see whether the VIX-conditioning mechanism is disclosed in a form transferable to a crypto-vol analogue for Strategy A, and any such overlay must first be checked against the L54 condition (mean-in-same-direction-as-variance) before it's worth prototyping.
