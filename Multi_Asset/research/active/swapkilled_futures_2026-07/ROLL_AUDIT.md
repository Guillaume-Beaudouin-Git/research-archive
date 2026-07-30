# ROLL AUDIT (L5) — confirming H4 & H9 on independent roll-clean data

**Date:** 2026-07-15. Cross-check of the two PROVISIONAL sleeves against `data/deep_history_utc`
(MT5 broker-continuous, roll-adjusted internally — an INDEPENDENT source from yfinance =F front-month,
author≠auditor). Purpose: lift or discount the L5 roll-contamination flag before deployment.

## Result

| Sleeve | yfinance =F (front-month) | deep_history (roll-clean) | Verdict |
|---|---|---|---|
| **H4 commodity seasonality** | Sharpe **1.13**, placebo p=0.000 | Sharpe **0.47**, **placebo p=0.086 (fails)** | ❌ **ROLL ARTEFACT — flag NOT lifted** |
| **H9 WTI-Brent stationarity** | ADF p=0.001, hl 19d | ADF **p=0.000, hl 24d** | ✅ **CONFIRMED — flag lifted** |

## Interpretation

- **H4 was largely a seasonal roll-yield artefact.** On roll-clean broker-continuous data the seasonal
  book collapses to Sharpe 0.47 and no longer beats its placebo (p=0.086). The L5 concern was correct:
  much of the yfinance "seasonality" was the seasonal contango/backwardation roll, not price seasonality.
  → **H4 DROPPED from the deployable book.** (Could be revisited only with true excess-return /
  individual-contract data; not on front-month continuous.)
- **H9 mean-reversion is real, not roll.** WTI-Brent stays OOS-stationary on independent data (ADF p=0.000,
  half-life 24d). Expected: a spread of two similarly-rolled legs is roll-robust (roll effects cancel).
  → **H9 confirmed** (grid magnitude still bears the usual cost caveats, but the edge is genuine).

## Corrected combined book (H4 removed)

| | Sharpe | ann | MaxDD |
|---|---|---|---|
| H3 month-end Treasury (70%) | 1.02 | 4.3% | −4.8% |
| H9 crack/WTI-Brent grid (30%) | 0.54 | 5.3% | −16.8% |
| corr H3–H9 | 0.17 | | |
| **COMBINED (1×)** | **1.02** | 4.6% | −5.3% |

Prudent leverage (crisis-DD proxy −10%, cap 3×): **~10-14%/yr, crisis-DD 20-30%**, doubles ~5-7yr.

## Honest bottom line (post roll-audit)

The deployable book is essentially **H3 month-end Treasury (SR ~1.0, the anchor) + H9 spread grid as a
small decorrelating satellite**. Combined Sharpe **1.02**, not the 1.51 reported pre-audit — one of the
three "PASS" sleeves (H4) was a data artefact caught by the roll cross-check. This is the process working:
**a rigorous roll-audit before capital is exactly what prevents deploying an artefact at leverage.**
H3 is the one clean, granular, deploy-today sleeve (TLT fractional). H9 waits for ~€50k + a trend
kill-switch.
