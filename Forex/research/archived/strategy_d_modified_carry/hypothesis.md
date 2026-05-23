# Hypothesis — Strategy D Modified FX Carry
**Pre-registration date:** 2026-05-23  
**Author:** Guillaume Beaudouin  
**Strategy slug:** `modified_carry_g10`  
**n_tests at registration:** 172 (ground truth from _ic_feasibility.md, Phase 1.5)  
**Tests consumed by Phase 1 IC feasibility:** n=173 (raw carry), n=174 (REER-modified carry)

> This document is **locked at registration**. Changes after the first backtest run must be logged
> as modifications (max 3 total). Each modification increments n_tests.

---

## 1. Hypothesis statement

At the end of each calendar month, currencies with high interest rate differentials vs USD
(**carry**), that are **not fundamentally overvalued** (REER below 10Y mean) and have
**improving external balances** (positive/rising current account) generate excess returns in
the following month. The edge arises from:

1. **Carry premium**: compensation for crash risk (Lustig et al. 2011, Brunnermeier et al. 2009)
2. **REER filter**: reduces pre-crash exposure by reducing positions in overvalued carry currencies
   — the mechanism documented in Jordà & Taylor (2012)
3. **CA/inflation filter**: further reduces positions in currencies with structurally deteriorating
   fundamentals, which are empirically associated with carry crashes (Corte et al. 2016)

**Why this is different from archived FX-1 (raw carry, Sharpe −0.13):**
- FX-1 failed due to crash tail risk (GFC −33%, COVID −14%), NOT due to zero IC
- Modified carry targets the SAME edge as FX-1 but attenuates crash exposure
- Three fundamental filters are theoretically motivated, orthogonal to each other, and
  confirmed in out-of-sample academic evidence (Jordà & Taylor, Asness et al. 2013)

---

## 2. Universe

**Base G10 (IC feasibility + IS backtest):**  
EUR, GBP, JPY, CHF, AUD, CAD, NZD, NOK, SEK (9 currencies vs USD)

**EM extension (Phase 2+ only):**  
BRL, MXN, ZAR, INR, TRY — via CME futures or spot proxies. Defer to Phase 2.

**Instruments:**  
Monthly spot FX returns via yfinance (XXXUSD=X or inverted USDXXX=X).  
Convention: all prices expressed as XXXUSD (USD per 1 unit of foreign currency).

---

## 3. Signal construction (pre-registered weights)

### 3.1 Inputs

| Factor | Source | Lag | FRED/BIS code |
|---|---|---|---|
| Carry = r_foreign − r_USD | FRED 3M interbank rates | 1 month (signal at T-1) | See universe.yaml |
| REER deviation | BIS broad REER Excel | 2 months (pub lag 1M + data lag 1M) | RBXX codes |
| Current account / GDP | FRED quarterly, fwd-filled | 2 quarters | BOPCRNT (US); OECD for others |
| Inflation differential | FRED CPALTT01XXM659N | 2 months | 12M smoothed y/y |

### 3.2 Cross-sectional z-scoring (at each monthly rebalance)

```
z_carry[ccy, t] = (carry[ccy, t] − mean(carry[:, t])) / std(carry[:, t])
z_reer[ccy, t]  = −(reer_dev[ccy, t])   # negative: overvalued = reduce signal
z_ca[ccy, t]    = cs_zscore(ca_gdp[ccy, t])
z_infl[ccy, t]  = cs_zscore(−infl_diff[ccy, t])  # negative: high infl = reduce
```

Where:
- `reer_dev[ccy, t]` = rolling 10Y z-score of REER level (0 = at 10Y mean)
- `cs_zscore(x)` = (x − mean(x_t)) / std(x_t) cross-sectionally at time t
- `infl_diff` = (foreign CPI y/y) − (US CPI y/y), 12M Gaussian smoothing

### 3.3 Composite signal (pre-registered weights)

```
signal[ccy, t] = 0.50 × z_carry + 0.20 × z_reer + 0.15 × z_ca + 0.15 × z_infl
```

**Initial weights are fixed for Iter 1. Sensitivity analysis (not re-optimisation)
will test ±20% perturbation. Any weight change counts as modification #1.**

### 3.4 IC feasibility (Phase 1 only)

For the IC feasibility test, test two versions:
1. **Raw carry only**: `signal = z_carry` (n_tests = 173)
2. **Modified carry (carry + REER only)**: `signal = 0.5 × z_carry + 0.5 × (−z_reer_dev)` (n_tests = 174)
   - CA and inflation deferred to full backtest (quarterly/complex data)

---

## 4. Portfolio construction

- **Ranking:** Rank all 9 G10 currencies by signal at end-of-month T-1
- **Long:** top 3 currencies (highest signal)
- **Short:** bottom 3 currencies (lowest signal)
- **Middle 3:** zero position (reduces turnover and noise)
- **Dollar-neutral:** long leg and short leg each 100% notional → 200% gross, 0% net
- **Equal-weight within each leg:** 1/3 allocation per currency

---

## 5. Execution

- **Rebalance frequency:** Monthly, last business day of month (signal) → first business day of next month (execution)
- **Signal at T-1, trade at T:** Carry computed on FRED monthly rate available end of month T-1
- **BIS REER lag:** apply shift(2) to raw REER series (1M publication lag + 1M look-ahead buffer)
- **Forward rates:** Use spot FX + interest rate parity as carry proxy (no actual forward contract data)

---

## 6. Position sizing and costs

- **Vol targeting:** daily vol target = 10% annualized, realized with 3M rolling vol
- **Returns:** compute as EXCESS returns (subtract US 3M T-bill / 12 as monthly risk-free rate)
- **Costs (round-trip):**
  - Majors (EUR, GBP, AUD, NZD): 0.5 pip RT ≈ 0.004% per trade
  - JPY, CHF, CAD, NOK, SEK: 1.0 pip RT ≈ 0.008% per trade
  - Note: at monthly rebalance, turnover ~60-80% of portfolio; annual cost ~1.0-1.5%

---

## 7. Acceptance gates

### Research gate (RESEARCH_PASS)
| Metric | Threshold | Period |
|---|---|---|
| Sharpe net (HAC SE) | > 0.7 | IS 2005-2018 |
| MaxDD | > −25% | IS 2005-2018 |
| Walk-forward positive hit rate | ≥ 50% | OOS 5 folds |
| Modified IC > Raw IC | Required | IC feasibility |

### Propfirm gate (not targeted for FX, for reference only)
| Metric | Threshold |
|---|---|
| Sharpe | > 1.0 |
| MaxDD | < −10% |
| WF hit rate | > 60% |

**Note:** FX carry is a PERSONAL BOOK strategy (not propfirm). Propfirm gate is
tracked for portfolio combination analysis only.

---

## 8. AMTP analysis

**n_tests denominator:** 172 (correct count after FX Phase 1.5)  
**Tests consumed here:** n=173 (raw carry IC) and n=174 (modified carry IC)

**Thresholds (annual Sharpe t-stat over 21 years, t = SR × sqrt(21)):**

| Correction method | t-stat threshold | Equivalent min Sharpe |
|---|---|---|
| No correction (naive) | 1.96 | 0.43 |
| Bonferroni (n=172) | 3.45 | 0.75 |
| BH FDR at 5% (n=172) | ~3.0 (if rank=1) | 0.65 |
| Harvey-Liu-Zhu (n=172) | ~3.2 | 0.70 |

**Practical interpretation:**  
Sharpe 0.7 → t = 0.7 × sqrt(21) ≈ 3.21 → passes BH FDR and Harvey-Liu-Zhu thresholds;  
falls short of strict Bonferroni (3.45). RESEARCH_PASS threshold (SR > 0.7) is approximately
calibrated to BH FDR significance at n=172 tests.

**The strategy does NOT claim statistical significance at Bonferroni level.** It claims
significance at BH FDR 5%, which is standard practice in multi-testing asset allocation research
(Harvey, Liu & Zhu 2016 recommend BH, not Bonferroni, for financial applications).

---

## 9. In-sample / Out-of-sample split

| Period | Use | Note |
|---|---|---|
| 2005-01 → 2018-12 | In-sample (IS) | Full first cycle including GFC, EUR crisis |
| 2019-01 → 2026-05 | Out-of-sample (OOS) | COVID, rate hike cycle |
| Walk-forward folds | 5 expanding folds | Each fold uses IS up to split + next 18M OOS |

---

## 10. IC feasibility gate (Phase 1 stop criteria)

**STOP conditions (archive immediately):**
1. IC_raw_carry < 0.02 (no carry edge at all — structural failure)
2. IC_modified < IC_raw (modifications destroy rather than improve signal)
3. IC in high-VIX tercile ≤ 0 (crashes overwhelm carry even in modified version)

**PROCEED conditions (go to full backtest):**
1. IC_modified > 0.02 AND t_HAC_lag6 > 1.65 (soft gate)
2. IC_modified > IC_raw by at least +0.005 (modification adds value)

**STRONG GO (most likely to pass full backtest):**
- IC_modified > 0.04 AND t_HAC_lag6 > 2.5

---

## 11. Diagnostics required (before declaring PASS)

All in `analysis/` directory:
1. Per-currency return decomposition (which currencies drive the edge)
2. VIX-regime performance (terciles: VIX < 15, 15-25, > 25)
3. Decade-by-decade breakdown (2005-2010, 2010-2018, 2018-2026)
4. Correlation with USD index (dollar-neutral verification: ρ < 0.3)
5. Correlation with strategies A/B/C (portfolio impact: ρ < 0.4 with any single strategy)
6. Factor sensitivity: ±20% perturbation on weights (NOT a weight optimisation)

---

## 12. Modification log (max 3)

| # | Date | Description | Reason | n_tests |
|---|---|---|---|---|
| — | — | *No modifications yet* | — | — |
