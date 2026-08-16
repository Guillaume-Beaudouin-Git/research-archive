# MACD: The Indicator Is a Passenger (The Refutation)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=QCjVDRgMbT&amp;source=feedburner
**Captured**: 2026-07-21 07:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 8bcb78bbcd915816d57fbf0b9fdbbdb2

## Summary
The authors pre-registered four predictions before running any tests, then executed 360 measurements across 320 tuned variants of MACD-based systems and put three complete systems through regime cross-validation. The stated conclusion (per the title) is that MACD itself is not the source of whatever edge shows up — it is "a passenger," implying the real driver is something else in the system (trend filter, regime conditioning, position sizing) and MACD's presence is largely coincidental to performance. This is presented as a rigor case-study as much as a result about MACD specifically. The excerpt stops before showing the actual predictions, the regime-cross-validation results, or the effect sizes.

## Why it might be useful
This is a strong methodological match for lesson L20 (DSR mandatory once n_mod≥2 — 320 tuned variants is exactly the kind of search that inflates a naive Sharpe and demands deflation before any number is cited) and for the walk-forward/regime-cross-validation discipline the repo already enforces (≥5 folds, expanding window, never a single split). It is also a useful negative-result template for the alpha-hunt pipeline itself: named-indicator claims (MACD, RSI, etc.) are a common shape of incoming candidate and this piece is direct evidence that an indicator's apparent edge can be entirely attributable to surrounding system structure rather than the indicator — a pattern worth flagging explicitly in `_automation/feasibility`'s Level C sanity checks when a submitted hypothesis leans on a named technical indicator rather than an economic mechanism.

## Extracted content
The author states 360 measurements were run across 320 tuned variants, with 3 complete systems put through regime cross-validation; no formulas or Sharpe/return figures are present in the excerpt.

## Action proposed
REFERENCE — solid validation of the DSR/AMTP discipline already mandated in this repo's methodology toolkit, but no MACD-based signal exists in any active strategy, so there is no direct test path.
