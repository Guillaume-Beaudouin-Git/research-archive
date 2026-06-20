# Resolution-Aware Perpetual Futures on Binary Prediction Markets: An Empirical Framework

**Source**: arxiv_econ_em
**URL**: https://arxiv.org/abs/2605.10400
**Captured**: 2026-06-20 12:03 UTC
**Filters passed**: L1=[metrics], L2_OK
**Hash**: 6d819cfb7de1456261d4cbba3cb1fab7

## Summary
This paper develops a resolution-aware risk-design framework (PIRAP) for perpetual futures tracking binary prediction market probabilities. The framework specifies six components: an index estimator combining mid-price, depth-weighted mid, and time-decayed VWAP; jump-aware tiered margin sized against bounded-event terminal-collapse magnitude; a leverage compression schedule contracting toward resolution; a resolution-aware funding rule; and circuit breakers for extreme mispricings. The framework is counterfactually evaluated using Polymarket data, comparing PIRAP against naive perpetual designs. The key finding: proper terminal-collapse margin sizing eliminates the most common failure mode of event-linked perpetuals (liquidity crisis near resolution).

## Why it might be useful
This paper is relevant to Strategy B's future development. Strategy B is delta-neutral carry on Hyperliquid perpetuals — a related but different instrument class. The funding rate dynamics (Strategy B's CARRY_FLOOR_8H = 0.0034/(30×3)) and the HL perpetual's funding mechanism share structural similarities with the prediction market perpetuals studied here. More directly: HMSTR (the current active pair in Strategy B) has highly uncertain terminal events that affect its funding rate. The PIRAP's jump-aware margin sizing and circuit breaker logic are directly applicable to assessing liquidation risk in volatile HL pairs. Read before expanding Strategy B's VIABLE_ASSETS set to tokens with pending unlock/resolution events.

## Extracted content
PIRAP framework six components: (1) index estimator = mid + depth-weighted mid + time-decayed VWAP; (2) jump-aware tiered margin; (3) leverage compression toward resolution; (4) resolution-aware funding rule; (5) circuit breakers. Evaluated on Polymarket data. Finding: "proper terminal-collapse margin sizing eliminates the most common failure mode."

## Action proposed
TEST_LATER

Read Section 3 (PIRAP specification) before expanding Strategy B's VIABLE_ASSETS to include tokens with unresolved events (lockups, governance votes). The jump-aware margin and circuit breaker logic could be adapted as pre-trade checks in `strategies/delta_neutral/`. Pair with paper ff0a6c90 (Polymarket-v1 Database) for empirical basis.
