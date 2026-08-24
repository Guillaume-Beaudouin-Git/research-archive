# VWAP MR Fade NQ — POSTMORTEM

**Status**: ARCHIVED 2026-05-26  
**n_tests consumed**: 2 (VARIANT_A + VARIANT_B)  
**Global n_tests after archival**: 324  

---

## Hypothesis

VWAP deviation Z-score > 2.0 predicts mean-reversion in NQ over the next 30 minutes.
Based on Adams et al. (2025) SSRN 5641974 (GEX dealer-hedging on ES/MES).

## Result

**H1 FAIL** — signal is strongly ANTI-predictive.

| Year | Sharpe HAC | Win rate | SL rate |
|------|-----------|----------|---------|
| 2023 | -3.390 | 36.5% | 71.0% |
| 2024 | -2.987 | 36.7% | 71.9% |
| 2025 | -2.900 | 36.9% | 71.7% |

HAC t-stat = -4.2 → **strongly statistically significant FAILURE** (wrong direction).

## Root cause

NQ exhibits **intraday MOMENTUM** around VWAP, not mean-reversion.
When price deviates 2σ, it continues extending (SL fires 71%) rather than reverting.

The Adams et al. GEX-pinning mechanism is ES/SPX-specific:
- SPX 0DTE volume >> NDX 0DTE (5× difference)
- NQ is inherently more momentum-driven (concentrated high-beta tech names)

## What might work (not tested — new n_test)

A VWAP **momentum** / **breakout** signal (follow Z > 2, not fade) might have edge.
Win rate at SL level suggests ~28–30% reversal vs 70% extension — consistent with
a momentum signal at ~0.6 direction accuracy. Not tested here.

## Lessons

No new lesson added — this is consistent with the existing momentum literature on NQ.
The strategy was a legitimate test of a published academic mechanism on a related instrument.

## Files

- `prespec.md` — pre-registered spec (Adams et al. adaptation)
- `feasibility.py` — backtest engine (reusable for VWAP momentum hypothesis)
- `data_setup.py` — NQ 1-min RTH loader (reusable)
- `tests/` — 13 TDD tests all passing
- `analysis/canary_report.md` — STOP-POINT 1 & 2 results
- `analysis/canary_results.json` — raw numbers
