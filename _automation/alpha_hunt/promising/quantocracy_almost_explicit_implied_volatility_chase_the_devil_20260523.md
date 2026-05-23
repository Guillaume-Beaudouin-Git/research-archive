# Almost Explicit Implied Volatility [Chase the Devil]

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=rJJdZgihPi&source=feedburner
**Captured**: 2026-05-23 19:32 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: 6b9df83ac2a2bdef23290e653f91c515

## Summary
Chase the Devil compares algorithms for inverting the Black-Scholes formula to extract implied volatility, building on prior work by the author and improvements proposed by Jherek Healy. The focus is computational accuracy and speed of different IV approximation approaches versus the Newton-Raphson root-finding baseline.

## Why it might be useful
None of the current Algo_claude strategies trade options or require Black-Scholes IV computation. Strategy C (NQ) uses NQ futures directly; Strategy A (crypto TSMOM) and Strategy B (delta-neutral carry) deal in spot/perpetuals. This is a pure options-infrastructure item with no fit to the current active strategy set. Possibly relevant if a future Strategy D involves options on NQ or crypto, but that is not on the current research agenda.

## Extracted content
No code, formulas, or specific numeric claims in the excerpt. Full article needed for further extraction.

## Action proposed
REFERENCE

Options IV computation techniques. Not applicable to current strategies (no options trading). File for future options research.
