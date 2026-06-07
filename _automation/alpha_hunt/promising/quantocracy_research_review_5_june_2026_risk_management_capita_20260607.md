# Research Review: Model-Free Bubble Detection via Put-Call Disparity (Capital Spectator, June 2026)

**Source**: quantocracy
**URL**: https://quantocracy.com/redirect.php?key=yVWGGRJfBe&source=feedburner
**Captured**: 2026-06-07 06:04 UTC
**Filters passed**: L1=[trading_topic], L2_OK
**Hash**: dd2673ad8b9051c01b99b9f98318929f

## Summary
Capital Spectator's weekly digest of recent academic risk management work highlights a May 2026 paper by Jarrow (Cornell) and Kwok (Sydney) proposing a model-free lower bound on asset bubble magnitude derived from the disparity between put and call option prices. Unlike structural bubble models that require calibrating a specific process, the Jarrow-Kwok approach extracts a bubble signal directly from the put-call spread across moneyness levels, without assuming a specific dynamics model. The digest likely covers additional papers in the risk management space beyond this lead item, given the "Research Review" format.

## Why it might be useful
The archived crypto VRP angle (L13, BTC options via Deribit) was killed by cost dominance — gross 4.4%/yr vs 8.9%/yr costs. The Jarrow-Kwok approach does not require short options positions; it uses the options market as a signal about the underlying, not as a position vehicle. This means it sidesteps L13's cost kill and could be used as a **regime filter** rather than a direct strategy. Specifically: if put-call disparity flags a bubble regime, a long-only BTC/ETH/SOL momentum strategy (Strategy A TSMOM v3) could reduce its signal weight or go flat — this is the exact type of regime overlay CLAUDE.md L15 describes, though L15 notes the lift is sub-threshold (~1.7%/yr) for strategies with SR>1.0. Strategy A is currently frozen (Propr breach), so this is lower urgency. More relevant connection: if a futures-based version exists for NQ (CME options on NQ futures), the Jarrow-Kwok statistic could serve as a real-time risk filter for Strategy C entries — cut new positions when the NQ put-call disparity signals elevated bubble risk. That said, CME options data access is not in the current data stack, which is the key blocker.

## Extracted content
The author's description of the lead paper:
> "Measuring Bubbles via Put-Call Disparity: A Model-Free Approach" — Robert A. Jarrow (Cornell U.) and Simon Kwok (U. of Sydney), May 2026. This paper introduces simple, model-free lowe[r bounds]...

No formulas or code in the excerpt. Full digest article needed for the remaining papers and the complete Jarrow-Kwok setup.

## Action proposed
REFERENCE

No immediate test path: CME options data not available in current stack, and Strategy A is frozen. File as reference for when Strategy A is reactivated or when evaluating an options-based regime filter. If the Apex pivot for Strategy A (CME futures) ever includes options-on-futures access, revisit this as a drawdown guard signal.
