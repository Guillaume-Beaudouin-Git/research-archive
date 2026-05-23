# FGVD H1 — Pre-Registered Hypothesis
*Date: 2026-05-23 | Status: LOCKED (pre-registration before data analysis)*
*n_tests: 157 → 158 (Phase 2 IC test block: Tests A+B+C = 1 combined test)*

---

## 1. Signal Specification (Exact, Immutable)

```
fg_velocity(t)    = z_90d(F&G_t − F&G_{t−7})
price_velocity(t) = z_90d(log(BTC_t / BTC_{t−7}))
fgvd_signal(t)    = fg_velocity(t) − price_velocity(t)

entry_long:  fgvd_signal(t−1) < −1.5  [signal at T-1 close]
exit_long:   T+7 calendar days         [close at T+7 open]
```

z_90d: rolling 90-day window, unbiased std (ddof=1), min_periods=30.
All signals are computed using data available at T−1. No look-ahead.

---

## 2. Phase 2 IC Test Block (Pre-Registered, 1 combined n_test)

Three parallel IC tests on same window 2018-02-01 → 2026-05-23, BTC daily:

| Test | Signal | Label |
|------|--------|-------|
| A | `−price_velocity(t)` | Naive price mean-reversion |
| B | `fg_velocity(t)` | F&G velocity standalone |
| C | `fgvd_signal(t)` | FGVD combined (hypothesis) |

**Metric**: Spearman IC between `signal(t)` and `log_return_{t+1..t+8}` (7-day forward return). HAC Newey-West t-stat, lag=6.

**Event count**: Frequency of `signal(t) < −1.5σ` per year.

**Orthogonality**: `corr(fgvd_signal, tsmom_z)` Pearson, full sample.

---

## 3. Gate Criteria (Pre-Registered, No Tuning)

### 3a. Decomposition Decision Rules

These fire BEFORE the IC magnitude gate:

**Rule D1 (Price MR dominance)**: If `|IC_A| ≥ 0.5 × |IC_C|` → FGVD does not contain significant incremental sentiment information. STOP, archive with note: "FGVD = relabeled price mean-reversion."

**Rule D2 (Combined signal value)**: If `|IC_B| ≥ 0.3 × |IC_C|` AND `|IC_C| > max(|IC_A|, |IC_B|)` → sentiment velocity adds independent information on top of price MR. PROCEED to IC magnitude gate.

**Rule D3 (F&G void)**: If `|IC_B| < 0.01` AND `|IC_C − IC_A| < 0.01` → F&G contributes nothing. STOP, archive with note: "F&G velocity is noise; FGVD ≈ price MR."

Ambiguous case (D1/D2/D3 not conclusive): STOP, report all three IC values to user before deciding Phase 3.

### 3b. IC Magnitude Gates (apply only if decomposition rules allow PROCEED)

| Gate | Criterion | PASS |
|------|-----------|------|
| IC direction | `IC_C < 0` (contrarian: low signal → positive return) | Required |
| IC magnitude | `IC_C < −0.05` | Required |
| HAC t-stat | `t_HAC_C < −2.0` (lag=6) | Required |
| Event frequency | ≥ 20 events/year at signal < −1.5 | Required |
| Orthogonality | `|corr(fgvd, tsmom_z)| < 0.5` | Required |

**All 5 must pass**. Any single FAIL → archive.

### 3c. Strict Marginal Case Rule

Per mission specification: if HAC t-stat is in [−2.0, −2.5], treat as FAIL (not borderline pass). Signal at the limit is not robust. Threshold is −2.0 hard minimum, not a soft boundary.

---

## 4. Pre-Registered Failure Conditions → Archive

| Condition | Archive label |
|-----------|---------------|
| IC_C > 0 (wrong direction) | "FGVD wrong direction: F&G divergence → continuation not reversion" |
| |IC_C| < 0.05 | "FGVD IC too small: insufficient economic magnitude" |
| t_HAC_C > −2.0 | "FGVD IC statistically insignificant after HAC" |
| Decomposition D1 | "FGVD = price MR, no sentiment increment" |
| Decomposition D3 | "FGVD: F&G velocity is noise" |
| corr(fgvd, tsmom_z) > 0.5 | "FGVD: beta-contamination, not orthogonal to A" |
| Events/year < 20 | "FGVD: event sparsity, L12 floor violation" |

---

## 5. Pre-Registered Alerts (From Bootstrap)

**Alert A** (Guégan & Renault 2021): Social media sentiment signals have sub-cost economic magnitude at daily frequency. IC statistical significance does not imply economic profitability. Phase 3 must clear the NET Sharpe gate after 0.19% RT costs.

**Alert B** (Da et al. 2011 equity basis): The reversal mechanism is from an equity study. Crypto "faster metabolism" suggests 5–7 day holding may be appropriate but this is an extrapolation. Phase 3 WF will empirically validate or refute.

**Alert C** (Post-ETF regime): Phase 3 must report separately for pre-2022 and post-2022 sub-periods. If post-2022 Sharpe < 0, flag as structural break regardless of overall result.

---

## 6. Phase 3 Design (Conditional on Phase 2 Pass)

**Walk-forward** (annual folds, expanded due to sparse events):

| Fold | Train | Test | Expected events |
|------|-------|------|----------------|
| 1 | 2018-02 → 2019-12 | 2020 | ≈8 |
| 2 | 2018-02 → 2020-12 | 2021 | ≈8 |
| 3 | 2018-02 → 2021-12 | 2022 | ≈8 |
| 4 | 2018-02 → 2022-12 | 2023 | ≈8 |
| 5 | 2018-02 → 2024-12 | 2025 + 2026-partial | ≈12 |

RESEARCH_PASS: Sharpe HAC NET > 0.7, MaxDD > −25%, WF pass rate > 50% (3+/5 folds profitable).

DSR with n_tests=158.

Signal is fixed (threshold −1.5, 7-day hold). No iteration. No alternative parameters in Phase 3.
