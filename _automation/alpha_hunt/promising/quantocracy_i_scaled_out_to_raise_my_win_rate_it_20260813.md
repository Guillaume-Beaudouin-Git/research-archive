# I Scaled Out to Raise My Win Rate — It Didn't Move, and It Cost Me $115,000 (Jan Heger)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=cK9vMSsr0A&source=feedburner
**Captured**: 2026-08-13 08:00 UTC
**Filters passed**: L1=[trading_topic, metrics], L2_OK
**Hash**: 0312abe70dd504a1e61294864107610f

## Summary
The author backtested a common exit-management habit — scaling out of winning positions early to "lock in gains" — against 3,966 of their own historical trades, specifically to test the folk claim that doing so raises win rate. The measured effect on win rate was essentially flat, while the practice reduced realized P&L by $115,000 over the sample. The piece frames this as evidence that a widely repeated trading heuristic does not deliver its claimed benefit and instead carries a real, measurable cost. The excerpt cuts off before describing the second of "two" additional findings the author promises.

## Why it might be useful
This connects to Strategy C's exit design (TP 1.5R, stop 12:30 ET) and to L59 (delay+1 certifies entry only — exit must be re-priced separately; the gap_pattern_rehab case study saw its edge flip from +0.041 to -0.020 gross once exit geometry was held constant). This item is a real-world instance of exit-rule intuition being wrong, which argues for re-auditing Strategy C's TP/stop choice with the same rigor rather than assuming the current geometry is optimal. Methodologically it is also a useful negative example: this is a single-account anecdote (N=3,966 trades, no HAC, no walk-forward, no block bootstrap) — exactly the kind of claim the project's hard rules (HAC lag-6, WF ≥5 folds) and "5 mandatory script fixes" exist to filter before a number like "$115,000 cost" gets cited as evidence of anything general.

## Extracted content
The author claims a sample of "3,966 of my own trades" and reports the scale-out practice "cost me $115,000" with no measurable change in win rate. No code or formulas are present in the excerpt.

## Action proposed
REFERENCE — anecdotal single-trader analysis without a transferable ruleset or data; useful as a cautionary methodological reference on exit-rule assumptions, not a directly testable hypothesis as-is.
