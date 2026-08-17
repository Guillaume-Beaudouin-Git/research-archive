# Price-Path Convexity: A New Cross-Sectional Anomaly [Aligrithm]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=o3eJPu0fJH&source=feedburner
**Captured**: 2026-08-17 06:30 UTC
**Filters passed**: L1=[methodology], L2_OK
**Hash**: 2548dda58addcad65a66b2912dfaf74b

## Summary
The article proposes a new cross-sectional equity anomaly based on the SHAPE of the price path over a month rather than just its endpoint return. The illustrative example: two stocks that both end the month exactly flat, but one dipped low and recovered (concave path) while the other rallied then gave it all back (convex path) — same start, same end, different path. The claim is that this convexity/concavity of the intra-period path carries cross-sectional predictive information that a simple total-return factor misses entirely, since a flat-return stock would otherwise be invisible to standard momentum or reversal factors.

## Why it might be useful
There is no active equities cross-sectional strategy on the book right now — the closest live research is `Equities/research/active/sector_hothand_propfirm/`, which CLAUDE.md already flags as BREACH-in-the-state (t_HAC 10.38 red flag, MDD -13.3% over FTMO's 10% limit, audit obligatoire) — so this is not a candidate for immediate testing, but it is a genuinely different signal construction (path shape, not endpoint return) worth filing against that audit. Methodologically, a path-shape signal is highly autocorrelated within the formation window, which makes it a good stress-test case for the "block bootstrap, iid forbidden when trade clusters exist" rule in the Methodology toolkit, and any future test would need N≥30 instruments (L6, small universe + AMTP = everything fails) to even be eligible for a feasibility gate run through `_automation/feasibility/`.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no active equities cross-sectional strategy to attach this to today (sector_hothand_propfirm is itself under audit, not a healthy base to extend), and the excerpt gives no numeric claim or construction detail to evaluate; worth re-surfacing once that audit closes or a new equities cross-sectional research line opens.
