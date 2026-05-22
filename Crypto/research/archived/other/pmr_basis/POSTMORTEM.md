# PMR Basis Mean-Reversion — Post-Mortem

*Date: 2026-05-23 | Verdict: RESEARCH_FAIL → Path B*

---

## Summary

Signal is statistically real. Strategy is not exploitable with free data and taker costs.

---

## Timeline

| Phase | Date | Result |
|-------|------|--------|
| Pre-flight IC test | 2026-05-23 | IC = −0.064, t = 2.86 at 3d (PASS) |
| Event-count gate | 2026-05-23 | 912 events in 2024 >> 18 (PASS) |
| Full backtest | 2026-05-23 | Sharpe = −0.55, MaxDD = −65% (FAIL) |
| Walk-forward | 2026-05-23 | WF% = 0% (FAIL) |

---

## Signal Description

**Basis z-score**: basis = (perp_close / spot_close − 1), z-scored over rolling 90-day window.

**Entry**: |basis_z| ≥ 1.5σ → open position opposite to direction (fade the extreme).
- basis_z ≥ +1.5: short perp (expect basis to fall back to mean)
- basis_z ≤ −1.5: long perp (expect basis to rise back to mean)

**Exit**: basis_z returns to 0 OR 7-day hard stop.

**Parameters**: ALL fixed ex-ante. No grid search.

---

## Why The Signal Is Real

Cross-sectional IC measured in pre-flight (N=29 coins, June 2023–May 2026):
- IC(basis_z_lag1 → fwd_3d_perp_return) = −0.0643, t = −2.86 ✓
- IC(basis_z_lag1 → fwd_7d_perp_return) = −0.0385, t = −1.74 (weak)
- IC(basis_z_lag1 → fwd_14d_perp_return) = −0.016, t = −0.76 (noise)

The direction is correct: perp-spot basis above historical norm tends to revert toward the mean within 3 days. This is a real phenomenon, consistent with arbitrage capital compressing the premium.

---

## Why The Strategy Is Not Exploitable

**Root cause: signal fires on 12.6% of coin-days (gaussian tail ≥1.5σ)**

- 912 events in 2024 across 29 coins × ~250 days = 7,250 coin-day observations
- Expected from |z| ≥ 1.5 normal distribution: 13.4% → actual 12.6% ✓ (stationary distribution)
- With MAX_CONCURRENT = 12 positions and 3.6 new events/day, book always fully deployed
- Mean hold = 2.9 days → position turnover = 12 / 2.9 ≈ 4.1 positions closed/day
- Daily cost drag: 4.1 × 0.17% = 0.70%/day = **178%/year**

**Gross P&L**:
- IC contribution: 0.064 × 5%/3d vol × 1.7 avg signal ≈ 0.54% per trade
- With 1392 trades, gross annual ≈ +16-20%
- Cost annual ≈ 97-178%/year (two calculation methods converge to high drag)
- Net: catastrophically negative

**IC horizon mismatch**: Pre-flight IC measured at weekly cross-section (3d forward returns).
Backtest trades at 2.26 turns/day — much higher frequency than IC measurement horizon.
The daily IC (not measured) is likely ≈ 0.01-0.02, far below the weekly 0.064.

**Break-even analysis**: Net positive requires cost drag ≤ gross edge.
- Gross Sharpe (pre-cost estimate): ≈ 0.50 at 10% vol target
- Break-even annual cost: ≤ ~5%/year at target vol
- Required turnover for 5%/year: ≤ ~30 RT per year per position
- Required N_events: ≤ ~18/year → exactly the gate threshold
- The gate was designed for minimum events; the problem is maximum events

The gate checked the floor (≥18 events). The ceiling problem (too many events → cost overflow) was not gated, and it should be in future strategies.

---

## Orthogonality (Verified)

| Pair | |ρ| | Status |
|------|-----|--------|
| PMR vs A (TSMOM proxy) | 0.18 | ✓ (< 0.30) |
| PMR vs B (real returns) | 0.057 | ✓ (< 0.30) |

Delta-neutral execution successfully eliminates BTC beta. The orthogonality problem
(Lesson 11) is solved. The cost problem is separate.

---

## What Would Make PMR Viable

1. **Sub-bps maker rebates** (−0.02% cost instead of +0.17%): break-even from infeasible
   to feasible. Available to market makers, not systematic traders at retail scale.

2. **Wider threshold (3.0σ instead of 1.5σ)**: reduces event frequency by ~95% (from 12.6%
   to <0.3% of coin-days). Would require ~12 events/year → below the minimum gate.
   Cannot test without violating the no-grid-search constraint.

3. **Paid data with deeper signal persistence**: if basis_z signal persisted 21+ days
   (declining slowly rather than reverting in 3 days), the cost/IC ratio would flip.
   Requires proprietary or institutional data not available at this stage.

4. **Execution improvement**: pair-trading (long perp + short spot) earns funding on the
   short perp leg while waiting for basis reversion. At 0.5%/week funding, a 7-day hold
   earns ~0.5% additional vs 0.17% cost → net positive. Full delta-neutral implementation
   changes the economics significantly. But this requires spot position infrastructure.

---

## Lessons For Future Research

1. **Event-count ceiling gate**: future strategies with event-driven entry should measure
   BOTH minimum (< 18/year = too sparse) AND maximum (> 200/year = turnover overflow)
   event frequency in pre-flight. Add to methodology.

2. **IC horizon → execution frequency alignment**: IC measured at horizon H should target
   rebalance frequency ≈ H (not H/7). If IC is at 3d, position changes should target
   3-day holding, not daily recalculation.

3. **PMR as an overlay**: basis_z extreme (≥ 2.0σ) could be used as an EXIT signal for
   existing directional positions (Strategy A, C) rather than a standalone strategy.
   Signal is real; exploitation mode differs from full standalone strategy.

---

## N_tests Accounting

| Session | Tests added | Cumulative |
|---------|-------------|-----------|
| Prior sessions | — | 142 |
| Pre-flight IC tests (CS-FS, PMR×3, FRA) | +5 | 147 |
| PMR backtest v1 | +1 | 148 |

E[max_SR] at N=148: ≈ 4.33 (AMTP threshold; any future strategy Sharpe must be deflated
by this before comparing to the gate).

---

## Conclusion

**Free-data crypto edge orthogonal to both Strategy A (TSMOM) and Strategy B (delta-neutral
carry) is structurally exhausted in the current universe (29 Binance perps, public APIs).**

This is a scientifically valid conclusion, not a failure. The exhaustion is documented with:
- 8 signals tested (MAX, ILLIQ, OI-MOM, liquidation, CS-FS, FRA, skewness, PMR)
- 2 structural constraints identified (β-dominance for long-only, cost overflow for event-driven)
- 1 real signal found (PMR basis reversion) that cannot be exploited at current cost structure

Recommendation: next research session requires either (1) paid data source, (2) institutional
execution infrastructure (maker rebates), or (3) different asset class (NQ-style, non-crypto).
