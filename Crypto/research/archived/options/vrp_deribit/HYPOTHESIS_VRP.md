# HYPOTHESIS_VRP — Deribit BTC Variance Risk Premium Strategy
*Created: 2026-05-23 | Status: PHASE 1 COMPLETE → PHASE 2 IN PROGRESS*
*n_tests_start: 153 | n_tests_budget: +2 (153 → 155)*

---

## 1. Core Hypothesis

**Bitcoin options on Deribit systematically overprice future realized variance.** The spread
`DVOL[t]² − RV30[t]²` (ex-ante VRP signal, both observable at T) predicts the P&L of a
delta-hedged short straddle over the subsequent 16-day holding period.

**Mechanism**: Options buyers persistently pay an insurance premium for vol exposure (variance
risk premium). The seller of this premium, delta-hedged to remove directional exposure, captures
the spread between implied and realized variance as theta decay net of gamma losses.

**Signal** (observable at T, used to trade at T+1):
```
VRP_signal[t] = DVOL[t]^2 − RV30[t]^2     (variance spread, annualized)

Where:
  DVOL[t]  = Deribit BTC Volatility Index, 30d forward-looking (%)
  RV30[t]  = realized vol trailing 30 days = sqrt(365/30 × Σ r²_d)
```

**Outcome** (measured over T+1 to T+1+HOLD_DAYS):
```
PnL%[t] ≈ ½ × N'(0) × (DVOL[t+1]² − RV_realized[t+1:t+HOLD_DAYS]²) × T_hold / DVOL[t+1]

Where:
  N'(0)           = 0.3989  (standard normal PDF at 0, from ATM gamma formula)
  RV_realized[t]  = actual realized vol in the subsequent HOLD_DAYS
  T_hold          = HOLD_DAYS / 365 (in years)
  HOLD_DAYS       = 16  (30 DTE entry → 14 DTE exit, Decision 1)
```

This is the Black-Scholes delta-hedge P&L approximation, normalized by notional.

---

## 2. Design Decisions Integrated (from GO PHASE 1+2 validation)

### Decision 1 — Roll at 14 DTE (HOLD_DAYS = 16)
- **Rationale**: 7 DTE zone has gamma explosion (+46% vs 14 DTE) → delta-hedge cost spikes
- **Impact on theta**: Straddle captures 16 days of decay per cycle; 1.875 cycles/month
- **Impact on cost**: More rolls per month (+0.12%/month in option fees) but avoided gamma
  explosion cost in 7–14 DTE period more than compensates
- **Phase 3 sensitivity**: Grid test {7, 14, 21, 30} DTE roll thresholds. Default = 14 DTE.

### Decision 2 — Delta Hedge: Deribit Perp (Maker Only, No HL)
- **Venue**: Deribit BTC-PERPETUAL (single venue, simpler ops)
- **Fee model**: 70% maker fill rate × (−0.01% rebate) + 30% taker × (+0.03%) = +0.002% net per hedge
- **Net hedge cost**: ≈ zero (blended positive and negative nearly cancel)
- **Fallback**: if maker not filled within 2s → taker market order at +0.03%
- **Phase 3 sensitivity**: fill_rate ∈ {60%, 70%, 80%}

### Decision 3 — COVID Scenario: Synthetic Stress Tests (Phase 4, Not Phase 2 Gate)
Three scenarios to be implemented in Phase 4:
- **COVID-like**: BTC −50%/24h, IV_ATM ×3, IV_skew ×2
- **Flash crash**: BTC −25%/4h, IV_ATM ×2
- **Slow grind (LUNA-like)**: BTC −40%/6 weeks (isolate from 2022 data)
- File: `Crypto/research/active/_meta/synthetic_stress_scenarios.md` (Phase 4)
- **Hard stop**: if max_loss(COVID-like) > 15% portfolio → redesign sizing
- Phase 2 does NOT require stress testing. Stress tests gate Phase 3 → Phase 4 transition.

### Decision 4 — Corr(A) Tail Protection: Regime Filter (Phase 3)
- **Condition**: No new straddle positions when BTC 30-day drawdown > 15%
- **Unwind trigger**: Unwind existing positions if BTC DD exceeds 20% intra-position
- **Measurement**: BTC_DD30 = 1 − BTC_close[t] / max(BTC_close[t-30:t])
- **Trade-off**: measured in Phase 3 as Sharpe WITH vs WITHOUT filter

---

## 3. Cost Model (Revised — 14 DTE Roll, Deribit Maker)

### Per cycle (16-day hold, 1.875 cycles/month at $100K notional)

| Component | Calculation | Cost/cycle | Cost/month |
|-----------|-------------|------------|------------|
| Option fees (entry + exit) | 2 × 0.03% × $100K × 2 | $120 | $225 |
| Settlement fee (exit) | replaced by early roll → 0.03% × 2 | included above | — |
| Bid-ask spread (entry, 30 DTE) | 0.5% × 18.2% notional | $91 | |
| Bid-ask spread (exit, 14 DTE) | 0.6% × 12.5% notional | $75 | |
| Spread subtotal/cycle | — | $166 | $311 |
| Delta hedge (Deribit maker 70%) | ~12 hedges × 0.002% × 8.8% size | ≈ $2 | ≈ $4 |
| Funding on hedge | symmetric → ≈ 0 | ~$5 | ~$9 |
| **Total per cycle** | — | **$293** | **$549** |

**As % of $100K notional:**
- Per cycle: 0.293%
- Per month: 0.549%
- **Annualized: ~6.6%/yr**

### GATE 1: Net edge > 5%/yr

```
Gross VRP      ≈ 14%/yr  (Almeida et al. 2024, DVOL² − RV²)
Total costs    ≈  6.6%/yr
Net VRP est.   ≈  7.4%/yr   ✓  > 5%/yr GATE 1 PASSES

Expected P&L volatility: σ_PnL ≈ 12-18%/yr (from variance of VRP spread)
Estimated Sharpe: 7.4% / 15%  ≈  0.49  (conservative)
              or: 7.4% / 12%  ≈  0.62  (moderate regime)
```

**GATE 1: PASS.** Net edge 7.4%/yr > 5% threshold. Proceed to Phase 2 IC test.

Note: Sharpe 0.49–0.62 is below PROPFIRM_PASS (1.0) but above RESEARCH_PASS floor (0.7? — borderline). The primary value of this strategy is diversification (orthogonal to A+B in normal regimes) and CV research value (Deribit options VRP is novel quantitative research domain).

---

## 4. GATE 2 Definition (Phase 2 Output)

| Gate | Threshold | Metric |
|------|-----------|--------|
| IC magnitude | > 0.10 | Spearman(VRP_signal[t-1], PnL%[t:t+16d]) |
| Statistical significance | t_HAC > 2.5 | HAC(maxlags=6) on daily OLS |
| Event count (monthly) | [12, 50]/yr | 1 per 16-day cycle = ~22/yr; floor=12 ✓ |
| IC direction | positive (VRP > 0 → PnL > 0) | sign(IC) must be positive |
| Sub-period stability | IC > 0 in ≥ 2/3 years | Year-by-year IC sign |

If GATE 2 FAILS on any criterion:
- IC < 0 (wrong direction) → ARCHIVE immediately
- IC > 0 but t_HAC < 2.0 → ARCHIVE (underpowered signal)
- IC > 0 and 2.0 < t_HAC < 2.5 → BORDERLINE, flag for user review
- IC > 0 and t_HAC > 2.5 → PASS → proceed to Phase 3 (with user GO)

---

## 5. Data Sources (Phase 2)

| Data | Source | Endpoint | Window |
|------|--------|----------|--------|
| DVOL daily | Deribit public API | `public/get_volatility_index_data` | 2021-04-01 → now |
| BTC daily close | Binance public API | `/api/v3/klines?symbol=BTCUSDT&interval=1d` | 2021-04-01 → now |
| Cache format | Parquet | `data/vrp/cache/{dvol,btc}_daily.parquet` | — |

---

## 6. PHASE 2 RESULTS — IC Feasibility (2026-05-23)

**Data window**: 2021-05-01 → 2026-05-07 (1833 days, 1879 DVOL bars fetched from 2021-04-01)

### Descriptive statistics
| Metric | Value |
|--------|-------|
| DVOL mean | 61.0% (std 18.5%) |
| RV30 mean | 52.9% (std 19.0%) |
| VRP signal | mean=0.091, pct_positive=80% |
| PnL% mean/cycle | +0.0011 (std 0.0036) |
| PnL Sharpe (raw) | **1.45** (pre-costs, all cycles) |

### IC test results
| Test | n | IC (Spearman ρ) | t_HAC |
|------|---|----------------|-------|
| Daily overlapping, HAC(6) | 1832 | **+0.1261** | **2.351** |
| Non-overlapping (1/16d) | 114 | −0.0156 | −0.153 |

### Year-by-year IC (sub-period stability)
| Year | IC | Direction | n |
|------|-----|-----------|---|
| 2021 | +0.1246 | + | 244 |
| 2022 | −0.0120 | − | 365 |
| 2023 | −0.0737 | − | 365 |
| 2024 | **−0.2579** | − | 366 |
| 2025 | +0.0724 | + | 365 |
| 2026 | −0.1800 | − | 127 |

Sub-period stability: **2/6 years positive (33%)** — fails ≥67% threshold.

### Gate 2 evaluation
| Gate | Threshold | Value | Result |
|------|-----------|-------|--------|
| G1 IC magnitude | > 0.10 | 0.1261 | ✓ PASS |
| G2 t_HAC | > 2.50 | 2.351 | ✗ FAIL (borderline) |
| G3 IC direction | > 0 | +0.1261 | ✓ PASS |
| G4 Sub-period stability | ≥67% years+ | 33% | ✗ FAIL |
| G5 Event count | [12, 50]/yr | ~22/yr | ✓ PASS |

**VERDICT: BORDERLINE (3/5 gates)** — per decision tree: "IC > 0 and 2.0 < t_HAC < 2.5 → BORDERLINE, flag for user review."

### Interpretation flags
1. **t_HAC very close to gate** (2.351 vs 2.5): with more data or slightly different parameterization, this could pass or fail. Not a robust pass.
2. **Non-overlapping IC near zero** (−0.016): the cleaner test (no 16-day overlap bias) shows essentially no signal. The overlapping IC of +0.126 may be partially driven by residual autocorrelation that HAC(6) doesn't fully absorb.
3. **2024 strongly negative** (IC = −0.258): in the most recent full year, high VRP *anti-predicted* straddle P&L — the market correctly priced vol and sellers lost when predicted. This is the most recent regime, raising concerns about out-of-sample performance.
4. **Raw Sharpe 1.45**: the strategy has positive expected P&L (VRP premium), but the SIGNAL's ability to time entry (buy high VRP → sell low VRP) is weak and inconsistent.

### N_tests update
n_tests: 153 → 154 (+1 for this IC test)
Remaining budget: +1 (for DVOL-level alternative signal — pending user decision).

**HARD STOP. Do not proceed to Phase 3 (backtest) without explicit user GO.**

---

## 7. Key Risks

1. **COVID tail not in data**: March 2020 (−50%/24h) is before DVOL window. Short straddle
   can lose > premium on such events. Stress-tested in Phase 4 (synthetic scenarios).
2. **Corr(A) in crashes**: Strategy A (TSMOM) and short-vol lose simultaneously in BTC bear
   markets. Regime filter (Decision 4) partially mitigates; measured in Phase 3.
3. **DVOL smoothing**: DVOL is a 30d forward estimate, computed from multiple expirations.
   It may not match the exact ATM IV of the straddle we sell. Phase 3 uses actual mark prices.
4. **BTC perp delta hedge imperfect**: Deribit BTC-PERPETUAL may not perfectly hedge BTC
   options delta (basis between perp and spot). Expected basis error < 0.1%.
5. **Regime collapse**: If BTC enters prolonged low-vol bear (IV = RV, VRP ≈ 0), all cycles
   produce near-zero P&L. Not catastrophic but renders the strategy idle.
