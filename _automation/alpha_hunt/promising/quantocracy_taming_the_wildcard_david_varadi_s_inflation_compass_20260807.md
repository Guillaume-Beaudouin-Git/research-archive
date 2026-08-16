# Taming the Wildcard: David Varadi's "Inflation Compass"

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=mGWemHWL2y&source=feedburner
**Captured**: 2026-08-07 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 894f2815e12d63d96fb674267a09a626

## Summary
This is an independent third-party replication/test of a tactical asset allocation strategy by David Varadi called "Inflation Compass," described as an extension of his earlier "Growth and Inflation" regime-based rotation model with an added macro/inflation regime overlay (the "wildcard"). The excerpt frames it as an out-of-sample-style sanity check on someone else's published strategy rather than the author's own original research, but doesn't give the specific rules or backtest numbers.

## Why it might be useful
Any macro-regime overlay strategy is directly testable against L54 (the corrected regime-overlay condition): an overlay only helps if the variable predicting variance also predicts the mean in the same direction — the project's own MONO book counterexample had MaxDD -81% and passed the old MaxDD-based condition (L15) yet still failed because the flagged high-vol days were also the highest-return days. Before adopting anything like an "Inflation Compass" overlay for the Commodities XS Basis+TSMOM active research (`Commodities/research/active/xs_basis_tsmom/`), it would need the same regime/mean-direction check, plus L46's honesty checklist (canonical ledger, real measured cost, frozen spec, full-sample regime) before citing any of Varadi's or this replicator's numbers.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER

No active strategy currently uses a multi-asset growth/inflation regime rotation structure, and replicating the full Inflation Compass model plus the L54 mean-direction check would be a multi-day project — worth revisiting only if the Commodities XS Basis+TSMOM research needs a regime-overlay component.
