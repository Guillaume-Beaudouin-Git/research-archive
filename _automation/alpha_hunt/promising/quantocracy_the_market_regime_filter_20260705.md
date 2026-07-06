# The Market Regime Filter

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=jAULCipr1w&amp;source=feedburner
**Captured**: 2026-07-05 06:30 UTC
**Filters passed**: L1=[trading_topic, methodology], L2_OK
**Hash**: 089dff9d007cde9ffb7ef22a952e99eb

## Summary

The article (Financial Hacker) opens from the observation that markets alternate between trending, oscillating, and sideways phases, and that a trading system built for one regime degrades — or actively loses money — when the regime it was tuned on disappears. The excerpt is cut off before the actual regime-detection mechanism is described, so the specific filter construction (indicator, thresholds, lookback) is not available here; the piece appears to set up a regime-classification layer meant to be laid on top of an existing trend-following or mean-reversion system rather than to propose a standalone alpha source. No performance numbers are present in the captured text.

## Why it might be useful

Directly overlaps with the in-progress **Strategy D** pre-registration (`Futures/research/active/strategy_d/hypotheses_preregistered.md`), where D3 (ORB mid-fade) and D5 (afternoon BB squeeze) both failed individually (Sharpe -1.08/-1.32) and a "regime filter" is explicitly listed as the untested combination lever. Before adopting any regime-classification scheme from this article, it must clear **L37 (filter sanity check)**: compute the fraction of days the regime state disagrees with the raw D3/D5 signal — if under 5%, the filter is cosmetic and the sleeve should be named for what it actually is, not relabeled as regime-aware. It should also be read against **L15** (regime overlays on already-high-Sharpe strategies give only sub-threshold lift, ~1.7%/yr) — D3/D5 are currently negative-Sharpe, not high-Sharpe, so the overlay's job here is closer to "make the strategy exist at all" than "trim tail risk," which is a different bar than L15 covers. Action: once the full article is read for the actual regime-detection formula, run the L37 percentage-disagreement check on D3/D5 signals before writing it into the pre-registration.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

TEST_LATER

Strategy D's regime-filter combination step is still in pre-registration (0/3 modification budget consumed) and the excerpt doesn't contain the actual regime-detection method — reading the full article is needed before any concrete filter can be coded and run through the L37 check.
