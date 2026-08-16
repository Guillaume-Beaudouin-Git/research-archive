# Network Momentum as a Cross-Asset Factor (Aligrithm)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=SoiqxiL97A&amp;source=feedburner
**Captured**: 2026-07-13 06:30 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 864cf59c993228ff86e905862fb7933f

## Summary
The piece opens with the standard case for momentum (winners keep winning across equities, bonds, commodities and currencies over a century of data) and then pivots toward a network-based reframing — modeling momentum propagation across assets via their graph/network relationships rather than treating each asset's trend in isolation. The excerpt cuts off exactly at the pivot, so the specific network construction (correlation graph, lead-lag graph, supply-chain graph, etc.) and how momentum is scored on it are not shown, nor is any backtest figure.

## Why it might be useful
This bears on two things at once: it is a genuinely cross-asset, multi-instrument momentum construction (satisfying the N≥30 hard rule if built broadly enough), which is the natural escape hatch from lesson L11's finding that long-only crypto cross-sectional momentum (Strategy A's own family) is beta-dominated — a network-momentum construction applied across a broader, multi-asset-class universe (not crypto-only) would sidestep that closure rather than collide with it. Concretely, it fits the open budget in `Futures/research/active/strategy_d/` (D3+D5 portfolio work, 0/3 modifications consumed) as a genuinely new angle for cross-sectional futures momentum construction, rather than a re-test of the same signal family.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no immediate fit to any currently-live strategy (A/B/C), but concretely applicable to Strategy D's open research budget; building a cross-asset network/graph momentum prototype is a 1-3 day job, not same-day.
