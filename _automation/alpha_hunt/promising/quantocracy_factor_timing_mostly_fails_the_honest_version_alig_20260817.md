# Factor Timing Mostly Fails — the Honest Version [Aligrithm]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=JrHkcaHwHV&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: d50b9f3fce307f5e9287bc23660429bf

## Summary
The article takes on the "seductive idea" that an investor can beat a static basket of factors by timing them — leaning into value when it looks cheap, loading momentum when momentum is running, cutting a factor that looks stretched — and delivers what it bills as an honest (i.e., not cherry-picked or overfit-friendly) empirical verdict that this mostly fails to add value once evaluated rigorously. The framing suggests the piece walks through the standard timing signals that look promising in isolation but don't survive an honest out-of-sample or cost-adjusted test.

## Why it might be useful
This is a direct external validation of registre L54, gravé on this exact question: "the binding condition of a regime overlay is NOT the MaxDD, it's that the regime predicting variance must also predict the mean in the same direction." The MONO book's own regime-overlay research (`regime_overlay_ftmo`, dated 07-30) found the same result the hard way — no overlay variant beat a plain vol-matched de-lever, and duration got worse, not better, because the overlay was cutting the very days that paid the overnight risk premium. An external, independently-arrived-at "factor timing mostly fails" result is useful corroboration that this isn't an idiosyncratic finding of the book's own data, and it reinforces the default posture (skeptical of any new timing/overlay proposal from `_automation/alpha_hunt` unless it can show the L54 mean-direction condition, not just a variance-prediction plot).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE — corroborates an already-graven lesson (L54) with independent evidence; no new test implied, useful as a citation the next time a timing/regime-overlay idea is evaluated.
