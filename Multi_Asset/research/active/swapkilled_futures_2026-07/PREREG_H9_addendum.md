# PRE-REG ADDENDUM — H9 Mean-reverting underlying for the grid (economically-anchored spreads)

**Date frozen:** 2026-07-15, before any H9 result. Feeds H8 (grid needs a stationary underlying).

## H9 — Can an economically-anchored spread pass OOS stationarity + give the grid EV>0 at ruin<30%?

- **Prior / why anchored spreads:** the repo's data-mined equity/index pairs fail OOS cointegration
  (decorrelated_sleeves 0/12; statarb closed). Escape route (L44 mechanism-first): test spreads with a
  **physical/structural economic link** — those mean-revert more reliably than statistical pairs. The link
  is pre-registered per pair (no fishing).
- **Universe (frozen, each with its mechanism):**
  - WTI–Brent (same crude, transport/quality arb)
  - Gold–Platinum, Gold–Silver, Platinum–Palladium (precious-metal substitution)
  - Corn–Wheat (feed/acreage substitution)
  - Soybean–SoyMeal, Soybean–SoyOil (crush complex, processing identity)
  - Gasoline–Crude, HeatingOil–Crude (crack / refining margin)
- **Method (frozen):**
  1. TRAIN 2005-2015: hedge ratio β from OLS(logA ~ logB); spread = logA − β·logB.
  2. OOS 2016-2026: **ADF test on the OOS spread** (stationarity), **half-life** (OU fit), and
     stability of the mean.
  3. Survivors (OOS-stationary) → **grid MC on the real OOS spread** (H8 engine): ruin over 6/12mo, E[g].
- **Gate (frozen — PROMOTE only if ALL):**
  - (K1) OOS ADF p < 0.05 (stationary out-of-sample — the repo's killer).
  - (K2) half-life ∈ [3, 60] days (harvestable within horizon).
  - (K3) grid on the real OOS spread: **P(ruin ≤1yr) < 30% AND E[final] > acct0** net cost.
  - (K4) two-sided: spread reverts from BOTH extremes (not a one-way drift) — regress reversion sign.
  - (K5) DSR on the grid P&L; report roll/cost caveat (front-month futures, L5).
- **Default expectation:** most fail K1 (OOS non-stationarity is the norm). A single survivor that clears
  all = the grid's underlying; then it deploys under H8's rules (hard cap + trend kill-switch).
- **N:** 1 family test (spread-stationarity scan).
