# Resourcing a Triangulated Stat Arb Operation as a Solo Trader

**Source**: quantocracy (via Robot Wealth)
**URL**: https://quantocracy.com/redirect.php?key=xbK1ClDgjC&source=feedburner
**Captured**: 2026-06-10 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 1e4381c1a892f4f6f8d1f4063a60203a

## Summary
Robot Wealth examines the practical infrastructure requirements for running a triangulated statistical arbitrage approach as a solo trader without institutional backing. The piece explicitly references the core mechanics of stat arb (the "Tale of Two Prices" pricing-divergence thesis), a non-consensus pair-selection methodology ("Moneyball" — finding undervalued pairs by unconventional metrics), and a candid post-mortem on the structural problems that make classical pairs trading fail ("Winter of our Pairs Trading Discontent"). The framing around "triangulated" suggests using a third instrument or signal dimension beyond simple two-asset cointegration to improve the signal-to-noise ratio.

## Why it might be useful
The archived pairs research in Algo_claude failed hard: Pairs cointegration (0/19 qualify) and Gatev distance (Sharpe -0.44, t=-2.5) — both in the ✗ Archived section. Robot Wealth is one of the credible practitioner voices that does not oversell backtests, so a "triangulation" framing that explicitly addresses the failures of classical pairs is worth reading. More concretely, Strategy B (delta-neutral carry on HL testnet) already trades delta-neutral; if "triangulation" means using a third reference asset to dynamically hedge the correlation, that is architecturally close to what B does with spot/perp basis. Concrete action: read the full article to determine (a) whether "triangulated" means a triple cointegration structure (like Johansen rank-2), and (b) whether it changes the L12 event-ceiling math — if the mechanism generates fewer, higher-quality pairs vs. Gatev's exhaustive scan, the event count drops but IC per event could pass the binary TP/SL gate (L11b).

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — the triangulation framing potentially addresses the exact failure mode of the archived pairs strategies (too many low-IC events). Requires reading the full article to assess whether the new mechanism is substantively different from Gatev distance and whether it fits the delta-neutral HL testnet infrastructure already running for Strategy B.
