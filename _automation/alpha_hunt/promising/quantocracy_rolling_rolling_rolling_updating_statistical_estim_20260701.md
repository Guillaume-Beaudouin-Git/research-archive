# Rolling, Rolling, Rolling…. Updating Statistical Estimates Yes or No [Investment Idiocy]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=1V6338JpKb&amp;source=feedburner
**Captured**: 2026-07-01 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 1e0ca71788720d16ef170e98c34df22a

## Summary

This is the latest post in Robert Carver's ongoing portfolio-optimisation series (Investment Idiocy), asking whether parameter estimates used for sizing/allocation (vol, correlation, forecast weights) should be continuously re-estimated as new data arrives or held fixed after an initial calibration. The excerpt frames this as a follow-on to earlier posts on formal structural-break testing within the same series. No specific numbers or conclusion are visible in the captured snippet — it reads as an intro paragraph teeing up the argument rather than the argument itself.

## Why it might be useful

Directly touches the re-estimation-frequency question that CLAUDE.md's methodology toolkit already takes a stance on (63-day rolling vol window, sampled at month-ends) and that Strategy A hardcodes as a fixed 28-bar window for both signal and vol scaling. The open question Carver raises — rolling re-estimation vs. periodic fixed recalibration, and whether a formal break test should gate when to update — is exactly the kind of check that hasn't been run on Strategy A's 28d window choice (chosen once, frozen since). It also bears on the pending sector_hothand_propfirm audit (t_HAC=10.38 red flag): if that strategy's factor loadings were estimated on a full-sample static window rather than rolling, that's a candidate contributor to an inflated in-sample stat worth checking alongside the DSR/AMTP audit already required.

## Extracted content

No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed

REFERENCE

The captured excerpt is a teaser paragraph only (~40 words of actual content) — there isn't enough here to design a concrete test. Worth reading the full post once the sector_hothand_propfirm audit is underway, since re-estimation methodology is one of the open questions in that audit.
