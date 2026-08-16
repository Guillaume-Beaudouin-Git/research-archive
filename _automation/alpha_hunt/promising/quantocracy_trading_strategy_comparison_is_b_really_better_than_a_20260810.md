# Trading Strategy Comparison: Is B Really Better Than A?

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=DNgPPcr2CY&source=feedburner
**Captured**: 2026-08-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: e822f8063a9b6fc50990f6ef31a97121

## Summary
The article warns that ranking two trading strategies by a single scalar performance metric (implicitly Sharpe-like) can produce a misleading verdict, and proposes deeper diagnostics for comparing strategies beyond that one number. It doesn't specify the exact diagnostics in the excerpt, but frames the problem as strategy A vs strategy B comparison distortion — i.e. a point-estimate ranking can flip once the fuller distributional picture is examined.

## Why it might be useful
This is exactly the failure mode the project already diagnosed and fixed in its own admission criterion: the CLAUDE.md portfolio section explicitly abandoned "1.10 × SR_book = 2.54" as a gate because judging a candidate sleeve by a single ΔSR number rejected accretive low-correlation sleeves and passed nothing at ρ=0 — the corrected criterion (`Portfolio/admission/marginal.py`) now uses Δp(pass) and Δduration under block-bootstrap, not a scalar Sharpe delta. The article's core warning is directly relevant to any future comparison between Strategy A (live excess Sharpe 0.566, IC95 [-0.50, 1.63]) and a resurrected Strategy B once it clears WF≥5 folds — any such comparison must avoid collapsing to "which Sharpe number is bigger" per L46 (honest ledger) and the project's own block-bootstrap requirement (iid forbidden when trade clusters exist).

## Extracted content
"How a single-value performance metric can distort the ranking of trading strategies and how to avoid falling for it and gain deeper insight into strategy comparison." No numeric claims, code, or formulas in the excerpt.

## Action proposed
TEST_LATER

No active portfolio decision is pending until Strategy B produces a WF≥5-fold result, so reading the full article for a concrete diagnostic to bolt onto `Portfolio/admission/marginal.py` can wait until that comparison is actually needed.
