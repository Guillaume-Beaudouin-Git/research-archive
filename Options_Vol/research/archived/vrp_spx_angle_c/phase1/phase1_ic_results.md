# Phase 1 IC Results — SPX VRP (Angle C: VIX z-score Conditional)

**Date**: 2026-05-23  
**Verdict**: **FAIL — archive Options_Vol research (pending manual git mv)**  
**n_tests increment**: +1 (global n_tests: ~321)

---

## 1. Methodology

**Outcome** (variance swap P&L proxy):
```
Outcome[t] = VIX[t]² − RV_fwd[t]²   (variance points; + = seller profitable)
RV_fwd[t]  = sqrt(252 × mean(log_ret²[t+1 .. t+30])) × 100
```

**Signal** (strict T-1 lag):
```
VIX_z[t-1] = (VIX[t-1] − EMA90[VIX][t-1]) / EWMSD90[VIX][t-1]
```

**IC test**: Spearman rank correlation via rank-OLS.  
**HAC**: Newey-West lag-30 (30-day outcome overlap → structural autocorrelation).  
**IC gate**: t_HAC > 3.5 (global n_tests ~320, BHY-FDR compromise vs Bonferroni t ≈ 3.9).  
**Threshold**: z > 1.0 (pre-committed; no scan of z > 0.5 or z > 1.5).

**Data**: VIX and SPX daily close via Yahoo Finance v8 chart API (`query1.finance.yahoo.com`).  
Range: 1990-01-02 → 2026-05-22 (9,165 raw days).  
Analysis sample (post-2000 EWM warmup): 6,607 clean observations.  
Cached: `phase1/data/vix_daily.csv`, `phase1/data/spx_daily.csv`.

**HAC note**: Daily overlapping used as primary (HAC-30). Monthly non-overlapping (every 30 rows → "monthly", HAC-1) used as robustness check. Primary result: HAC-30 on daily overlapping conditional sample.

---

## 2. Pre-flight Gate — VRP Magnitude

| Period | Mean VRP (vol pts) | % Positive days | N |
|---|---|---|---|
| 2010–2015 | **+3.66** | 84.4% | 1,510 |
| 2015–2020 | **+2.97** | 80.5% | 1,258 |
| 2020–2025 | **+3.42** | 84.4% | 1,508 |

**Gate**: VRP 2020-2025 ≥ 2.0 vol points → **PASS (3.42)**.

The VRP is persistently positive across all three sub-periods (2.97–3.66 vol points, 80–84% of days). The static premium is real and stable. This pre-flight gate clears.

---

## 3. IC Results

### 3a. Unconditional IC (all dates, 2000-present)

| Metric | Value |
|---|---|
| Spearman IC | **+0.1520** |
| HAC(30) t-stat | **+3.671** |
| p-value | 0.0002 |
| N | 6,607 |

The unconditional IC (0.1520, t=3.671) **would pass** the t > 3.5 gate. Across all market states, higher VIX_z on day T-1 predicts a more positive variance swap P&L on day T. This is a noteworthy finding — but it is NOT the hypothesis tested (Angle C was specifically conditional on z > 1.0, not unconditional).

### 3b. Conditional IC (Signal > 1.0) — the committed hypothesis

| Metric | Value |
|---|---|
| Spearman IC | **−0.0092** |
| HAC(30) t-stat | **−0.144** |
| p-value | 0.8853 |
| N | 879 |
| Mean Outcome | +29.14 variance pts |
| Monthly IC (HAC-1, robustness) | +0.0407 (t=0.446, N=149) |

**Gate**: IC t_HAC > 3.5 → **FAIL (t=−0.144)**.  
**Gate**: IC direction > 0 → **FAIL (IC=−0.0092)**.

The conditional IC is effectively zero (both t-stat and IC are near zero) and slightly negative in direction. Within the z > 1.0 regime, the LEVEL of VIX_z does not predict whether this particular elevated-VIX day will generate a more or less profitable variance swap. The mean outcome is positive (+29.14 variance pts), confirming the VRP EXISTS in elevated-VIX states, but is completely unpredictable within that regime.

---

## 4. Sub-period Stability

| Period | N | Spearman IC | t_HAC | Mean Outcome (var pts) |
|---|---|---|---|---|
| 2010–2015 | 193 | **+0.0804** | +0.888 | +250.47 |
| 2015–2020 | 152 | **+0.2085** | +3.271 | +193.80 |
| 2020–2025 | 200 | **−0.0018** | −0.015 | **−70.78** |

**Gate**: No sub-period sign reversal → **FAIL** (2020-2025 IC = −0.0018, mean_outcome = −70.78).

Critical finding: **The 2020-2025 sub-period has NEGATIVE mean outcome** (−70.78 variance points) in the conditional sample. When VIX_z > 1.0 during 2020-2025, the variance swap seller LOST money on average. This is a structural regime failure, not a statistical fluke.

**2015-2020 is the only sub-period with marginally significant IC** (t=3.271), suggesting the conditional strategy works in some vol regimes but not others.

---

## 5. Event Count

| Metric | Value |
|---|---|
| Mean events/year (z > 1.0) | 33.8 |
| Min per year | 2 (2003) |
| Max per year | 67 (2008) |

**Gate**: Events/yr ≥ 30 → **PASS (33.8)**.

Event count is adequate on average but highly variable (2 in 2003, 67 in 2008). Low-vol years (2003-2005, 2017, 2019) have very few conditional trading opportunities.

---

## 6. Gate Summary

| Gate | Threshold | Value | Result |
|---|---|---|---|
| VRP magnitude (2020-2025) | ≥ 2.0 vol pts | 3.42 | **PASS** |
| IC direction | > 0 | −0.0092 | **FAIL** |
| HAC(30) t-stat | > 3.5 | −0.144 | **FAIL** |
| Events/yr | ≥ 30 | 33.8 | **PASS** |
| Sub-period sign stability | all positive | IC_2020-2025 = −0.0018 | **FAIL** |

**Overall: FAIL (3 gates failed)**

---

## 7. Root Cause Analysis

### Primary failure: conditional IC ≈ 0

Within the z > 1.0 regime, the LEVEL of VIX_z has no additional predictive power over the variance swap P&L. Two mechanisms explain this:

1. **Rank order breaks down within high-vol regimes**: When VIX_z = 1.2 vs. VIX_z = 2.5, the difference in subsequent realized vol (which determines Outcome) is driven by tail events (COVID-scale shocks), not by how high VIX was relative to its EMA. The variance of Outcome within the conditional sample is dominated by whether a vol-explosion follows (rare, random conditioning on VIX level).

2. **Selection paradox**: The z > 1.0 filter selects exactly the periods when vol explosions are most likely. During these periods, realized vol can DRAMATICALLY exceed the VIX level (COVID: VIX ~60, realized vol ~120%+ annualized), making Outcome deeply negative. The mean outcome (+29.14) is positive but variance is enormous and unpredictable.

### Secondary failure: 2020-2025 regime break

Mean Outcome in 2020-2025 conditional sample = **−70.78 variance points** vs. +250.47 in 2010-2015 and +193.80 in 2015-2020.

The 2020-2025 period contained:
- **Mar 2020 COVID**: VIX spiked to 85.47 (all-time high). Over subsequent 30 days, realized SPX vol exceeded 100% annualized — the seller lost massively on every position entered during VIX_z > 1.0.
- **2022 inflation volatility**: Sustained high vol (VIX 25-35 for months). Sellers of variance in high-VIX-z states in early 2022 experienced realized vol EXCEEDING implied, negative P&L.
- **2024 Japan carry unwind (Aug 2024)**: Brief VIX spike to 65, immediately reversed. Mixed P&L depending on exact entry.

This is the canonical failure mode for short-vol strategies: the z > 1.0 threshold selects periods of elevated risk, and in the 2020-2025 regime, elevated risk periods were FOLLOWED by even higher realized vol, not reversion.

### Surprising side finding: unconditional IC

The unconditional IC (0.1520, t=3.671) passes the gate. Across ALL market states (including low-VIX periods), VIX_z is positively correlated with subsequent variance swap P&L. This is consistent with the broader VRP literature: VRP tends to be larger (more profitable to sell) when VIX is elevated, not because the conditional timing works, but because the static premium itself scales with VIX.

This suggests a fundamentally different hypothesis: instead of a binary threshold (sell when z > 1.0, flat otherwise), use VIX_z as a **continuous position scaler** (position size ∝ VIX_z, long the full period). This would be Angle A (delta-hedged straddle with VIX_z sizing) — a NEW untested hypothesis.

**Per methodology rules: this new hypothesis is NOT tested here.** It requires a new n_tests budget and explicit chat validation.

---

## 8. Lessons Learned

| Lesson | Content |
|---|---|
| Conditional on high VIX ≠ good timing | Selecting z > 1.0 picks tail-risk periods where realized vol can EXCEED implied vol. The conditional regime is the SHORT-vol danger zone, not the profit zone. |
| Static VRP vs. timing | Static VRP (unconditional IC 0.1520) exists; timing it by conditioning on z > 1.0 does NOT work. This confirms the archived VIX term carry lesson: "the premium is a static factor, not a timeable signal." |
| 2020-2025 regime is a structural break | Mean outcome = −70.78 var pts in the most recent sub-period. Any short-vol timing strategy must explicitly model regime persistence. |
| Unconditional IC deserves separate test | The 0.1520 unconditional IC (t=3.671) is a legitimate signal if the hypothesis is reformulated as continuous sizing, not binary threshold. Document for future session. |

---

## 9. Verdict and Next Steps

**VERDICT: FAIL — Options_Vol Phase 1 IC (Angle C, z > 1.0)**

Per methodology rules:
- No fallback to Angle A or alternative threshold scan (pre-committed: one test, z > 1.0)
- Archive Options_Vol research
- n_tests global += 1 (from ~320 to ~321)

**Archiving action** (pending manual execution by user):
```bash
# Run from repo root after reviewing this report:
mkdir -p Options_Vol/research/archived/vrp_spx_angle_c
git mv Options_Vol/research/active/ Options_Vol/research/archived/vrp_spx_angle_c/
```

**Future directions** (NOT approved — require new chat validation):
1. **Unconditional VIX_z sizing (Angle A reformulation)**: Position size ∝ VIX_z (all states), delta-hedged straddle. The unconditional IC (0.1520, t=3.671) provides a Phase 1 GO signal IF the hypothesis is reformulated. New n_tests budget = +1.
2. **Deribit BTC options VRP** (Phase 0 backup): DVOL-based IC test, free data, different asset class. Would require a fresh Phase 0 for crypto options.
3. **Dispersion trading**: Not pursued (data cost too high, crowded).

**WAITING for explicit chat validation before any further testing.**

---

*Generated: 2026-05-23 | n_options_total = 1 | Global n_tests: ~321*
