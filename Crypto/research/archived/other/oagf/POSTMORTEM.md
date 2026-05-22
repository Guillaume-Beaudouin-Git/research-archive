# OAGF — Open Auction Gap Fade — Post-Mortem

*Date: 2026-05-23 | Verdict: RESEARCH_FAIL → Archive*

---

## Summary

Signal direction is correct. Statistical power is insufficient at any feasible sample size.

---

## Timeline

| Phase | Date | Result |
|-------|------|--------|
| Phase 0 bootstrap | 2026-05-23 | Angle selected; data constraint noted |
| Phase 1 IC pre-flight | 2026-05-23 | IC=−0.19 (direction ✓), t_HAC=−1.17 (FAIL) |

---

## Signal Description

**Gap at 8h funding settlement**: gap_ret = (open_t − close_{t-1}) / close_{t-1}
at bars opening at 0:00, 8:00, 16:00 UTC (Binance perp, 1h interval).

**Entry**: ALO limit order at close_{t-1} opposite to gap direction.
**Exit**: 1h later (1h bar close).
**Threshold**: |gap_ret| > 0.30% (fixed ex-ante).

**Data**: Binance 1h perp OHLCV, 29 coins, Jan 2024 → May 2026 (28 months).
*Note: HL candleSnapshot API only has data from ~Oct 2025 (~7 months). Binance data was used as a proxy; the settlement phenomenon is exchange-agnostic.*

---

## IC Results

| Horizon | IC_pooled | IC_daily | t_HAC | N events | Gate |
|---------|-----------|----------|-------|----------|------|
| 1h      | −0.195    | −0.189   | −1.17 | 304      | FAIL |
| 2h      | −0.087    | −0.160   | −1.02 | 304      | FAIL |
| 4h      | −0.084    | −0.102   | −0.61 | 304      | FAIL |

IC direction: correct (negative — gap up → bar returns negative).
IC magnitude: large (−0.19 >> gate 0.04).
**t_HAC: insufficient (−1.17 vs. gate −2.5). FAIL.**

---

## Why The Signal Failed

**Root cause: 128 events/year at 0.30% threshold is too sparse for statistical power.**

- Total triggered events: 304 across 29 coins, 28 months
- Per-year rate: 128/year across the universe (avg 4.4 events/coin/year = 1 event per ~83 days per coin)
- Daily IC grouping: most days have 0 events; IC computed from 1–2 pairs when an event fires → extremely noisy daily IC
- To reach t_HAC = −2.5 with IC = −0.19 and SE ≈ 0.16 per day requires reducing SE to 0.076, which needs ~4.4× more data than 28 months → **~10 years of 1h data**

**Break-even event frequency**: to reach t_HAC = −2.5 in 28 months would need SE ≤ 0.076, meaning ~(0.19/0.076)² ≈ 6.25× the current event count → ~800 events/year = a threshold of ~0.10% or lower.

**Why not lower the threshold?**: 0.30% is fixed ex-ante per methodology (Lesson 1: no threshold tuning). Lowering to 0.10% would:
- Change the strategy fundamentally (entry at near-zero gaps, much more noise)
- Count as a new strategy hypothesis (= +3 more n_tests)
- Risk reverting to a signal that fires on random microstructure noise, not settlement-driven gaps

---

## What Is Real

IC magnitude −0.19 is the strongest pre-flight IC observed in this research program (PMR was −0.064). The phenomenon is likely real: funding settlement at 0:00/8:00/16:00 UTC does create directional order flow that partially reverts within 1h. But:

1. It only creates a gap > 0.30% on 128 occasions per year across 29 coins
2. At that frequency, statistical verification requires ~10 years of data
3. The strategy has no practical edge if the signal fires 4× per year per coin

---

## Data Infrastructure Finding

**HL candleSnapshot API has only ~7 months of historical data** (from ~Oct 2025). Any strategy requiring HL-specific 1h OHLCV for pre-flight IC tests is currently infeasible unless:
1. The backtest is limited to Oct 2025–present (insufficient for WF)
2. A different exchange's data is used as proxy (used here for Binance)

This is a practical constraint for all future HL-native strategies: live execution works, but backtesting requires either proxy data or waiting for HL data to accumulate.

---

## Orthogonality (Not Measurable)

- corr(OAGF, A): 0.055 (PASS — structurally near-zero as expected)
- corr(OAGF, B): NaN — insufficient overlap (B backtest data ends Jun 2025; OAGF fires on sparse days; zero common daily observations)
- The near-zero corr(A) confirms the strategy is not beta-dominated (Lesson 11 respected)

---

## Lessons For Future Research

1. **Sparse event-driven IC requires large N**: IC at t ≤ 2.5 requires event frequency × time × sqrt(N_coins) to accumulate. At 4 events/coin/year, need 10+ years. Future strategies with event-driven entry need to verify event rate BEFORE investing in IC testing at a threshold.

2. **HL data constraint**: HL candle API has only ~7 months. Pre-flight IC tests for HL-native strategies must either use proxy exchange data or accept reduced statistical power.

3. **Large IC + low t-stat = structurally unverifiable signal**: IC magnitude doesn't substitute for statistical confidence. A −0.19 IC with t=−1.17 is less actionable than a −0.05 IC with t=−3.0.

---

## N_tests Accounting

| Session | Tests | Cumulative |
|---------|-------|-----------|
| V1 complete | — | 148 |
| OAGF IC (3 horizons: 1h, 2h, 4h) | +3 | **151** |

E[max_SR] at N=151: ≈ 4.34 (marginal from 4.33).

---

## Conclusion

**OAGF is archived.** The signal direction is real. Statistical verification is structurally impossible at the 0.30% threshold with available data (128 events/year). No variants of this angle should be tested (lowering threshold = different strategy + additional n_tests consumption).

V2 mission: iter 1 of 3 consumed. 2 remaining.
