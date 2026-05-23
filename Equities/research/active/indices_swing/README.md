# Indices Swing — IC Feasibility Scan

**Asset class**: US equity indices (SPY, QQQ) + Europe proxy (EWQ)  
**Sprint**: Sprint 1 — IC scan 6 signals × 4 horizons × 3 assets  
**Branch**: feat/indices_swing_screening  
**n_tests added this sprint**: ~72 (6 signals × 4 horizons × 3 assets; AMTP deferred to Sprint 2)

---

## Research motivation

Propfirm book currently has one live strategy (C = NQ opening momentum). A decorrelated
second strategy D would push portfolio Sharpe from 1.52 → ~2.0 with ERC sizing.
Constraint: must target Sharpe > 1.0 propfirm-grade with MaxDD < -10%.

Swing signals (1-10d hold) on liquid equity index ETFs are:
- Executable via futures (MNQ/ES/M2K) or ETFs
- Weekly frequency avoids the high-cost intraday regime
- Mechanistically distinct from NQ opening momentum (different time-of-day, different driver)

---

## Sprint 1 — Indices Swing IC Screening

**Goal**: IC feasibility filter before any full backtest. Criterion for GO:
- |IC mean| > 0.02 (Spearman rank, vol-scaled excess returns)
- IC t-stat (HAC Newey-West, lag = 1.5 × horizon) > 2.0
- Stability: rolling-2y IC same sign as full-sample IC in ≥ 70% of windows
- Post-2020 IC same sign as full-sample IC

**Signals tested**:

| ID | Signal | Native horizon | Mechanism |
|----|--------|---------------|-----------|
| S1 | VRP (VIX² − RV21) | 5d | Risk-premium mean reversion |
| S2 | VIX term structure (VX1/VX2) | 3d | Contango/backwardation regime |
| S3 | Turn of Month (TOM) | 1d | Institutional rebalancing flows |
| S4 | Sentiment composite (AAII + NAAIM + PCR10) | 5d | Crowd positioning reversal |
| S5 | XS momentum (6-ETF ranking, 6m lookback) | 10d | Jegadeesh-Titman cross-asset |
| S6 | HY OAS regime (Δ5d > threshold) | 5d | Credit→equity lead-lag |

**Methodology**:
- Signal at T-1, IC on [T, T+h] vol-scaled excess returns
- Excess return = log(close[T+h]/close[T]) − DGS3MO[T] × h/252
- Vol-scaling: trailing 63-day annualised σ (no look-ahead)
- HAC NW lag = max(2, round(1.5 × h))
- n_tests budget: tracked but AMTP not applied at IC scan stage

**Data sources**:

| Series | Source | Coverage | Notes |
|--------|--------|----------|-------|
| SPY/QQQ/EWQ prices | yfinance (auto-adjusted) | 2003-present | EWQ = CAC tradable proxy |
| VIX (VIXCLS) | FRED Graph CSV | 2003-present | Public, no API key |
| VX1/VX2 futures | CBOE manual CSV | Sprint 2 only | See data/vx_futures_manual.csv |
| DGS3MO, T10Y2Y, T10Y3M | FRED Graph CSV | 2003-present | Full history |
| DTWEXBGS (DXY) | FRED Graph CSV | 2006-present | |
| HY OAS (BAMLH0A0HYM2) | FRED Graph CSV | 2023-present (restricted) | HYG proxy used pre-2023 |
| CBOE PCR (equity + total) | CBOE CDN | 2006-2019 | Post-2019 requires manual download |
| AAII bull-bear spread | Manual XLS | Sprint 2 pending | AAII blocks automated download |
| NAAIM Exposure Index | Manual CSV | Sprint 2 pending | NAAIM blocks automated download |

**Manual data needed for full S4 signal**:
1. AAII: Download XLS from https://www.aaii.com/sentimentsurvey/sent_results → save as `data/aaii_sentiment_manual.xls`
2. NAAIM: Download CSV from https://www.naaim.org/programs/naaim-exposure-index/ → save as `data/naaim_exposure_manual.csv`
3. VX futures (for S2): Download from https://www.cboe.com/us/futures/market_statistics/historical_data/ → save as `data/vx_futures_manual.csv`

---

## Temporal Alignment Contract

```
Signal date T (signal observed at T close)
    └── IC computed against fwd_ret[T] = vol_scaled_excess_return(T → T+h)
        where:
          raw     = log(close[T+h]) - log(close[T])          ← pandas: log_c.shift(-h) - log_c
          excess  = raw - DGS3MO[T] * h / 252
          scaled  = excess / rolling_63d_vol_ann[T]           ← no look-ahead

Sentiment ready_date (pre-applied in fetch_sentiment.py):
  AAII  → observed Thursday, ready Friday (= obs_date + 1BD)
  NAAIM → observed Wednesday, ready Thursday (= obs_date + 1BD)
  PCR   → observed same day at close (no lag)

Signal code must NOT apply additional shifts to sentiment data.
```

---

---

## Sprint 1 — Phase A blockers resolution

### Blocker 1: rf math [FIXED]

**Diagnostic**: `rf = macro["dgs3mo"] / 100 / 252` (daily decimal) was used inside
`_compute_fwd_ret` as `rf_h = rf * h / 252` → double division by 252.
Result: rf_h (h=10) = 4.6e-6 instead of 1.16e-3 (off by factor 252).
The excess return ≈ raw return (rf drag essentially zero), violating methodology.

**Fix**: `rf = macro["dgs3mo"] / 100` (annual decimal) in `load_universe`.
`_compute_fwd_ret` already had `rf_h = rf * h / 252` which is now correct.

**Impact (SPY h=10, 2022)**:
```
BEFORE: mean=-0.6357, std=3.2346  (essentially raw/vol)
AFTER:  mean=-0.6897, std=3.2286  (true excess, ~0.054 vol-scaled units lower)
```

**Test**: `tests/test_rf_magnitude.py` → run with `/usr/bin/python3 tests/test_rf_magnitude.py`

---

### Blocker 2: PCR coverage [SCENARIO (b) — ACCEPT LIMITATION]

**Diagnostic**: All 3 CBOE CDN endpoints (totalpc, equitypc, indexpc) return HTTP 200
but `Last-Modified: Fri, 30 Oct 2020 12:31:08 GMT`. Data ends 2019-10-04.
Not a parsing bug — CBOE froze these files in Oct 2020 when redesigning their site.

**Decision**: Accept limitation. PCR data covers 2006-11-01 to 2019-10-04 (3,253 days).
S4 signal will be tested on this window. Post-2019 PCR requires CBOE subscription or
manual download. `verdict.md` will flag this reduced sample for S4.

**Test**: `tests/test_pcr_endpoints.py`

---

### Blocker 3: AAII + NAAIM automated acquisition [PARTIAL]

**AAII**: `sentiment.xls` URL returns `Content-Type: text/html` (4,540 bytes —
"Pardon Our Interruption" Akamai challenge). User-Agent spoofing does not bypass it.
Status: NOT automatable without Selenium. **DEFERRED to Sprint 2.**
Manual download: https://www.aaii.com/sentimentsurvey/sent_results → `data/aaii_sentiment_manual.xls`

**NAAIM**: **AUTOMATED ✓**. Strategy: scrape `naaim.org/programs/naaim-exposure-index/`
to find current weekly xlsx URL (pattern: `USE_Data-since-Inception_YYYY-MM-DD.xlsx`),
download and cache. Full history: 1,039 rows, 2006-07-05 → 2026-05-20.
Publication day: Wednesday (96%), ready_date = Thursday.

**S4 Sprint 1**: NAAIM + PCR10 composite (AAII deferred → partial composite).

**Test**: `tests/test_sentiment_acquisition.py`

---

## Sprint 1 — Real IC preview (S1 VRP + S3 TOM, pre-Phase B)

Computed on `universe(start="2007-01-01")`, HAC lag = max(2, 1.5×h).

```
signal  asset  h   n_obs    ic   t_HAC  ic_2020+  ic_pre20  stability  verdict
s1_vrp  SPY    5   5022  +0.042  1.69   +0.042    +0.041     0.79     NO-GO  ← t_HAC < 2.0
s1_vrp  QQQ    5   5022  +0.067  2.62   +0.076    +0.061     0.84     GO     ← QQQ VRP passes all gates
s1_vrp  QQQ    10  5017  +0.066  2.03   +0.077    +0.059     0.82     GO     ← borderline t=2.03
s1_vrp  EWQ    5   5022  -0.018  -0.72  -0.025    -0.010     0.37     NO-GO  ← wrong direction
s3_tom  SPY    1   5026  +0.033  1.14   +0.063    +0.017     0.68     NO-GO  ← t < 2.0 full-sample
s3_tom  QQQ    1   5026  +0.030  1.05   +0.053    +0.018     0.72     NO-GO  ← consistent direction
s3_tom  EWQ    1   5026  +0.037  1.28   +0.106    +0.001     0.49     NO-GO  ← EWQ post-2020 notable
```

**Preliminary read**:
- **S1 VRP**: QQQ passes (t=2.62, stable), SPY marginal (t=1.69). EWQ inverse sign → skip EWQ.
- **S3 TOM**: Consistent direction across all assets but t < 2.0 on full sample.
  Post-2020 IC is notably stronger (SPY +0.063, EWQ +0.106 vs pre-2020 near-zero).
  Could be a post-2020 regime shift. Sprint 2 warranted for TOM with post-2020 subsample focus.

---

## Results

→ See `results/ic_summary.csv` and `results/verdict.md` (generated by `ic_scan/run_all_signals.py`).

---

## File structure

```
indices_swing/
├── data/
│   ├── fetch_prices.py        yfinance SPY/QQQ/EWQ
│   ├── fetch_vix.py           FRED VIXCLS + optional VX CSV
│   ├── fetch_macro.py         FRED: DGS3MO, T10Y2Y, T10Y3M, DXY, HY OAS + HYG proxy
│   ├── fetch_sentiment.py     AAII (manual) + NAAIM (manual) + CBOE PCR
│   └── universe.py            Consolidated universe dict + fwd_ret
├── signals/
│   ├── s1_vrp.py              VRP = VIX²×(21/252) − RV21
│   ├── s2_vix_term.py         VX1/VX2 ratio
│   ├── s3_turn_of_month.py    [-1,+3] business day dummy
│   ├── s4_sentiment_composite.py  z-score AAII + NAAIM + PCR10
│   ├── s5_xs_momentum.py      6-ETF cross-sectional ranking
│   └── s6_hy_oas_regime.py    HY OAS 5d change regime
├── ic_scan/
│   ├── ic_engine.py           Spearman IC + HAC NW + rolling stability
│   ├── run_all_signals.py     Entry point: outputs ic_summary.csv
│   └── plots.py               IC time series + rolling 2y (savefig only)
├── results/
│   ├── ic_summary.csv
│   ├── ic_per_signal/*.png
│   └── verdict.md
└── tests/
    └── test_signals.py        Look-ahead assertion tests
```
