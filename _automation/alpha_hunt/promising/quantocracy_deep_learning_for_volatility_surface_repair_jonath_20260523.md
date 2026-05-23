# Deep Learning for Volatility Surface Repair [Jonathan Kinlay]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=2YP30ouZhn&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: df10119338995fead1047258a02c0740

## Summary
Kinlay benchmarks a small mask-conditional CNN against calendar-projected linear interpolation and a per-slice SVI fit for repairing missing or arbitrage-violating entries in an options volatility surface. The CNN approach is tested on a synthetic benchmark with known ground truth, making it a relatively clean comparison. The focus is on surface repair (filling in arbitrage-free values) rather than surface prediction.

## Why it might be useful
None of the current Algo_claude strategies trade options. Strategy A (crypto TSMOM), Strategy B (delta-neutral carry on perpetuals), and Strategy C (NQ futures ORB) are all futures/perpetuals-based with no vol surface dependency. If a future strategy involves equity options on NQ or crypto options, this methodology would become relevant. The VIX term structure carry strategy is archived ("edge died post-2020"), and vol surface repair is a prerequisite for any options-based strategy. Not actionable now.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Volatility surface repair methodology. Not applicable to current strategies (no options). File for potential future options research.
