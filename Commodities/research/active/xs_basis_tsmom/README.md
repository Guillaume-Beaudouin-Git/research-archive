# XS Commodity Futures — Basis + TSMOM IC Scan

**Asset class**: Commodity futures (24 continuous contracts)  
**Sprint**: 3 — IC feasibility scan, 2 signals, monthly cross-section  
**n_tests this sprint**: ≤ 5 (pre-registered; AMTP applied if > 1 signal passes)  
**Budget constraint**: n_tests_global = 274 → ≤ 279 after Sprint 3

---

## MISSION STATUS (updated 2026-07-10) — EXHAUSTED on free data

| Leg | Verdict | Ref |
|---|---|---|
| **S_TSMOM** (dual vs single momentum) | **FALSIFIED** — all 16 configs net-negative; commodity XS momentum is reversal over 2005-2026 (IC t −3.4) | `results/PHASE_B_RESULTS_dual_momentum.md` (PR #390) |
| **XS reversal** (by-product) | **ARCHIVED** — one-sided losers-rebound (long-leg only, short-winners loses), DSR 0.588 fail after AMTP; not an FTMO sleeve. Revisit only for a future FUTURES book | `results/REVERSAL_RESULTS.md` (PR #391) |
| **S_BASIS** (Erb-Harvey carry) | **DATA-BLOCKED (free)** — roll-gap proxy breadth 3/month & 96% stale; yfinance drops expired contracts. Needs paid term-structure data | `results/S_BASIS_DATABLOCKED.md` |

**Conclusion:** the economically-live axis is basis/roll-yield, but it is **paywalled**.
Park as **BACKLOG(paid-data)**; reopen only if a term-structure source is acquired. Routing
if ever unblocked: invest-long / personal / future FUTURES prop book — **not** the FTMO-CFD
book (L24 lumpy; L32 CFD carry).

---

## Research Motivation

Portfolio currently has propfirm book (Strategy C = NQ momentum). Strategy D candidate
needs Sharpe > 1.0 and decorrelation from C. Equity swing signals (Sprint 1–2) failed
full backtest despite passing IC scan — closed. Commodity futures cross-section is the
next candidate:

- Monthly rebalancing → cost gate essentially absent (L11: breadth ~25×12 = 300/yr,
  futures cost ~0.015% RT → expected drag ≈ 0.45%/yr, negligible)
- Economic mechanism documented in academic literature (not data-mined)
- Two signals tested: momentum (Moskowitz 2012) + basis (Erb-Harvey 2006)
- Historical Sharpe of commodity futures XS: 0.7–1.2 (pre-2015); regime shift post-QE

---

## Universe (~24 contracts)

| Sector | Code | Contract | Exchange | ADV filter? |
|--------|------|----------|----------|-------------|
| Energy | CL | WTI Crude Oil | NYMEX | ≥5k |
| Energy | BZ | Brent Crude | ICE | ≥5k |
| Energy | NG | Natural Gas | NYMEX | ≥5k |
| Energy | HO | Heating Oil #2 | NYMEX | ≥5k |
| Energy | RB | RBOB Gasoline | NYMEX | ≥5k |
| Precious | GC | Gold | COMEX | ≥5k |
| Precious | SI | Silver | COMEX | ≥5k |
| Precious | PL | Platinum | NYMEX | ≥5k |
| Precious | PA | Palladium | NYMEX | ≥5k |
| Industrial | HG | Copper | COMEX | ≥5k |
| Grains | ZC | Corn | CBOT | ≥5k |
| Grains | ZS | Soybeans | CBOT | ≥5k |
| Grains | ZW | Wheat (CBOT) | CBOT | ≥5k |
| Grains | ZM | Soybean Meal | CBOT | ≥5k |
| Grains | ZL | Soybean Oil | CBOT | ≥5k |
| Grains | ZO | Oats | CBOT | ≥5k |
| Softs | KC | Coffee C | ICE | ≥5k |
| Softs | SB | Sugar #11 | ICE | ≥5k |
| Softs | CC | Cocoa | ICE | ≥5k |
| Softs | CT | Cotton #2 | ICE | ≥5k |
| Softs | OJ | Orange Juice | ICE | ≥5k |
| Livestock | LE | Live Cattle | CME | ≥5k |
| Livestock | HE | Lean Hogs | CME | ≥5k |
| Livestock | GF | Feeder Cattle | CME | ≥5k |

**Data source decision**: Spec calls for Stooq continuous contracts, but Stooq now
requires an API key for CSV download (HTTP returns empty body). Falling back to
**yfinance `=F` tickers** (CL=F, GC=F, …), which provide continuous front-month
unadjusted prices — the same data type as Stooq continuous.

---

## Signals (pre-registered, Sprint 3)

### S_TSMOM — Time-Series Momentum
- **Mechanism**: Moskowitz, Ooi & Pedersen (2012) "Time Series Momentum," JFE.
  Trend-following on individual asset's own past return. Positive cumulative return
  over the trailing year predicts positive next-month return (and vice-versa).
- **Formula**: `signal[t, i] = sign(log_ret_12m[t-1, i]) × (1 / vol_12m[t-1, i])`
  - `log_ret_12m[t-1, i]` = sum of daily log-returns from T-252 to T-22 (12m, skip 1m)
  - `vol_12m[t-1, i]` = annualized daily return std over same window
  - Signal is sign × inverse-vol (momentum amplitude scaled by risk)
- **Temporal alignment**: signal at month-end T-1, IC vs fwd_ret[T→T+1m]
- **Lookback**: 12 months, exact per Moskowitz et al. (no variation)

### S_BASIS — Term Structure / Basis
- **Mechanism**: Erb & Harvey (2006) "The Strategic and Tactical Value of Commodity
  Futures," FAJ. Gorton & Rouwenhorst (2006) "Facts and Fantasies About Commodity
  Futures." Backwardation (near > far) predicts positive returns via convenience yield.
- **Formula**: `signal[t, i] = -basis_proxy[t-1, i]`
  where basis_proxy = (P_second - P_front) / P_front × 12 (annualized)
  Positive signal = backwardation = bullish
- **Implementation note**: second-month individual contracts unavailable on free platforms
  (Stooq requires API key; yfinance individual month contracts need per-delivery ticker).
  **Using Roll-Gap Proxy (Approach C)**:
  At each roll date, continuous price jumps from P_near → P_far:
  `roll_return = log(P_after_roll) - log(P_before_roll) = log(F_far/F_near)`
  `basis_proxy = -roll_return × 12` (annualized, positive in backwardation)
  Between rolls, basis is held constant at last observed value (monthly sampling).
- **Temporal alignment**: basis_proxy at month-end T-1, IC vs fwd_ret[T→T+1m]

---

## Methodology

- **Cross-sectional IC**: Spearman rank correlation of signal[t-1] vs fwd_ret[t] across
  ~20–24 assets at each month t (asset-filtered by ADV that month)
- **Time series of monthly IC**: ~240 obs for 2005-2025 (S_TSMOM); ~210 for BZ from 2007
- **HAC t-stat**: Newey-West, lag = 2 months on mean(IC_t), threshold t > 2.5
- **Subsamples**: pre-2015 / post-2015 (QE → normalization regime shift)
- **Stability**: rolling 5-year IC fraction same sign as full-sample
- **L11 cost gate (Israel-Jiang-Ross)**:
  - breadth = N × 12 ≈ 24 × 12 = 288 effective bets/year
  - expected_gross_alpha = 0.40 × IC × √288 × σ_target(10%) ≈ 0.068 × IC
  - expected_cost_drag = turnover × 0.015% (CME Tier 1 futures)
  - Gate: gross_alpha > 3 × cost_drag → very permissive at monthly frequency

---

## Phase A checklist (blocking before IC scan)

- [ ] Fetch 24 continuous contracts from yfinance
- [ ] Roll validation: detect 5σ jumps, classify roll vs market event
- [ ] ADV filter: rolling 60d mean volume ≥ 5000 contracts/day
- [ ] Basis proxy: roll-gap detection validated
- [ ] universe.py: month-end prices, forward returns, rf
- [ ] universe_stats.csv: per-ticker n_obs, adv_median, n_roll_artifacts, basis_coverage

## Phase B checklist (after Phase A validation)

- [ ] S_TSMOM signal + XS IC
- [ ] S_BASIS signal + XS IC
- [ ] Cost gate (L11)
- [ ] Verdict + n_tests update
