# VWAP MR Fade NQ — Canary Report & Final Verdict

**Date**: 2026-05-26  
**Status**: ARCHIVED — H1 FAIL  
**n_tests consumed**: 2 (VARIANT_A + VARIANT_B, pre-registered)

---

## STOP-POINT 1 — Data ✓

| Item | Value |
|------|-------|
| Source | NQ_1min_2022-12-26_2025-12-11.parquet |
| RTH bars (09:31–16:00) | 292,878 |
| Sessions | 764 |
| Median bars/session | 390 |
| vwap_rth = 0 after filter | 0 |
| Valid Z-score bars | 270,722 / 292,878 (92.4%) |

Data quality: clean. vwap_rth confirmed anchored from 09:31.

---

## STOP-POINT 2 — TDD + Canary 2024

### TDD: 13/13 PASS ✓

### Canary results (2024 only)

| Metric | VARIANT_A | VARIANT_B |
|--------|-----------|-----------|
| N trades | 4,905 | 5,862 |
| Win rate | **36.7%** | **37.3%** |
| Avg win | +19.3 pts | +20.0 pts |
| Avg loss | -13.4 pts | -14.0 pts |
| Sharpe naive | **-2.987** | **-2.904** |
| Sharpe HAC | **-3.512** | **-3.857** |
| HAC t-stat | -4.226 | -4.642 |
| MaxDD | -6,896 pts | -7,734 pts |
| Exit: SL | 72% | 71% |
| Exit: TP | 13% | 14% |
| Exit: TIME | 15% | 15% |

**Gate: H1 PRE-REGISTERED (Sharpe ≥ 1.0, WR ≥ 60%) → FAIL**

---

## Year-by-year consistency (VARIANT_A)

| Year | N trades | Sharpe | Win rate | SL rate |
|------|----------|--------|----------|---------|
| 2023 | 4,790 | -3.390 | 36.5% | 71.0% |
| 2024 | 4,905 | -2.987 | 36.7% | 71.9% |
| 2025 | 4,611 | -2.900 | 36.9% | 71.7% |

**Failure is consistent across all three years — not regime-specific.**

---

## Root cause diagnosis

### 1. NQ exhibits intraday MOMENTUM, not mean-reversion around VWAP

When `|Z| > 2.0` (price has deviated 2σ from VWAP), NQ prices continue extending
(SL fires 71–72% of trades) rather than reverting (TP fires only 13%).

Win rate 36.7% vs expected ≥ 60%: the signal direction is systematically wrong.
HAC t = -4.2: **strongly anti-predictive** (not just noise).

### 2. Adams et al. (2025) mechanism does not transfer to NQ

The Adams et al. SSRN 5641974 paper documents GEX-driven mean-reversion on ES/MES,
driven by 0DTE dealer hedging flows pinning price toward VWAP. Two structural differences:

- **SPX options >> NDX options**: SPX 0DTE volume is ~5× NDX 0DTE. The dealer hedging
  that pins ES price is much weaker on NQ. Mechanism transfer unvalidated.
- **NQ is inherently more momentum-driven**: Nasdaq-100 concentrates high-beta tech names.
  NQ price moves are amplified and trend-persistent vs ES.

### 3. 2σ threshold is in the momentum zone for NQ

At |Z| = 2.0, price has already moved ~20 pts from VWAP (sigma_30 ≈ 10 pts, median).
At this level, NQ momentum is still active (SL = 71% consistently).
A reversion strategy would need a higher threshold (|Z| >> 3?) — but that's a modification.

---

## Verdict

**H1 FAIL → ARCHIVE**

Per prespec gate: "H1 FAIL → Archiver — pas d'edge"

No modifications attempted. Budget intact (0/3 consumed) but irrelevant — the
directional failure (win rate 36.7%, HAC t = -4.2) is too large to correct with
Z-threshold or window adjustments.

**FOLLOW signal** (go long when Z > 2, short when Z < -2) would be a new hypothesis
entirely — not a modification of this pre-registered spec.

---

## n_tests register

- Prior: 322
- This series: +2 (VARIANT_A + VARIANT_B)
- **Post-archive global: 324**

---

*Generated: 2026-05-26 | Archived immediately after STOP-POINT 2*
