# A Cross-Asset Lead-Lag Trade in US Refiners (Beyond Passive)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=7yQThELpkX&amp;source=feedburner
**Captured**: 2026-07-11 06:00 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 9f838429c0e3d64b5c1dc9bac2736bfc

## Summary
The author describes a lead-lag relationship between the crack spread (the refining margin, traded tick-by-tick in the futures market) and US refiner equities, which are said to reliably reprice more slowly in response to the same margin information. The implied trade is to use real-time crack-spread futures moves as an early signal for refiner equity returns, exploiting the equity market's slower price discovery relative to the futures market. The excerpt cuts off before showing the actual lag length, entry/exit rule, or any backtest statistic.

## Why it might be useful
This is a concrete, testable cross-asset structural relationship (futures leading equities) rather than a single-instrument technical pattern, which maps onto the methodology axis of beta-orthogonality (L38): the correct test is to HAC-regress refiner equity next-day excess returns on same-day crack-spread futures moves and check whether the coefficient survives after controlling for the refiner's own beta to broad energy/equity indices (t>2.5 threshold per the IC feasibility gate), rather than assuming the correlation is itself the edge. It also connects to `Commodities/research/active/xs_basis_tsmom/` (the currently open commodity-futures basis/TSMOM chantier, phase A incomplete) as a genuinely different signal family (lead-lag rather than basis/TSMOM) that could be tested against the same commodity futures data already staged there.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
TEST_LATER — no immediate fit to A/B/C (equities + commodity futures, not crypto/HL/NQ), but concretely testable via an HAC lead-lag regression against the open Commodities basis/TSMOM research budget; needs refiner-equity data alongside existing crack-spread futures data, roughly a 1-3 day job.
