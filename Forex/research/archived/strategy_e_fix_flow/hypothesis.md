# Hypothesis — Strategy E: WMR Fix + End-of-Month USD Flow

**Pre-registration date:** 2026-05-23  
**n_tests at registration:** 174 (from Strategy D closure) + 1 = 175 (this strategy)  
**Note:** User session count = 136; canonical project count = 175. Bonferroni uses 175.  
**Scope:** IC feasibility (stylized facts verification) only. No full backtest unless H1+H2 both PASS.

---

## Market mechanism

### H1 — WMR Fix W-shape (microstructure)
Asset managers submit large fix orders to banks before 3:55 PM London. Banks accumulate directional inventory and push prices during the 5-minute fix window (15:57:30–16:02:30 London). Post-fix, their inventory unwinds → mean reversion. This creates a detectable W-shape in cumulative returns: drift before fix, overshoot during, reversion after.

**Post-2015 context (window widening 2015-02-15):** Price impact reduced ~40% per Krohn & Sushko (2022). Signal magnitude lower but mechanism persists.

### H2 — End-of-Month USD Flow (macro)
When US equities outperform global equities month-to-date, global fund managers are overweight USD (US equity exposure = USD long). On the last business day, they rebalance → sell USD at the fix. When outperformance is large (>2% SPX vs MSCI World ex-US), flow is systematic and large enough to detect at the fix level.

---

## Pre-registered hypotheses

### H1: W-shape pattern around 4PM London Fix
- **Signal**: directional bias in the 30-minute pre-fix window (15:27:30–15:57:30 London)
- **Entry**: at 15:57:30 London, fade the pre-fix direction (contrarian)
- **Exit**: at 16:02:30 London (end of fix window)
- **Return**: close-to-close of the 5-minute fix window return, direction = −sign(pre-fix 30-min drift)
- **Test**: mean fix-window return across all trading days 2016-2026 (all 6 pairs), t-stat HAC lag-6

**Gate — PASS:** t_HAC > 2.0 AND mean return consistent sign across ≥ 4/6 pairs  
**Gate — FAIL:** t_stat < 1.0 OR mean return ≤ 0 → STOP, archive  
**Gate — INCONCLUSIVE:** 1.0 ≤ t_stat < 2.0 → check H2 before deciding

### H2: End-of-month USD selling pressure at fix
- **Condition**: last business day of month (LSE calendar); SPX MTD return − MSCI World ex-US MTD return > +2%
- **Signal**: short USD (buy EURUSD + GBPUSD, sell USDJPY + USDCAD + USDCHF, AUDUSD neutral)
- **Entry**: 14:00 UTC (pre-positioning window)
- **Exit**: 16:30 UTC (after fix, reversion complete)
- **Return**: entry-to-exit log return, USD-short direction
- **Test**: mean event return across all qualifying EOM events 2016-2026, t-stat HAC lag-3 (monthly)
- **Minimum events**: ≥ 80 total events (across 6 pairs) to establish statistical power

**Gate — PASS:** mean return > 0 AND t_HAC > 1.5 AND n_events ≥ 80  
**Gate — FAIL:** mean return ≤ 0 OR t_stat < 1.0 → STOP, archive  
**Gate — INCONCLUSIVE:** t_stat ≥ 1.0 but < 1.5 → flag for combined H1+H2 test

### H3: Independence of H1 and H2
- **Test**: correlation between H1 daily returns and H2 monthly returns  
- **PASS:** |correlation| < 0.3 (strategies are decorrelated, combinable)  
- **FAIL:** |correlation| ≥ 0.5 → strategies share the same underlying mechanism, count as single test

---

## Universe

| Pair | Direction | Notes |
|------|-----------|-------|
| EURUSD | Base EUR | Largest fix volume |
| GBPUSD | Base GBP | High fix flow (UK pension funds) |
| USDJPY | USD base | Invert for USD short = sell USDJPY |
| AUDUSD | Base AUD | Commodity proxy |
| USDCAD | USD base | Invert for USD short = sell USDCAD |
| USDCHF | USD base | Invert for USD short = sell USDCHF |

**Period:** 2016-01-01 → 2026-05-01 (post WMR window widening 2015-02-15)  
**Frequency:** M5 (5-minute OHLCV from Dukascopy)  
**Convention:** XXXUSD returns; USD/XXX pairs are inverted

---

## Fix window definition

```
Fix window:    15:57:30 – 16:02:30 London time
Pre-fix drift: 15:27:30 – 15:57:30 London time (30-min window)
Post-fix:      16:02:30 – 16:32:30 London time (30-min reversion check)

London DST:
  BST (UTC+1): last Sunday March → last Sunday October
  GMT (UTC+0): otherwise

Fix window in UTC:
  BST season: 14:57:30 – 15:02:30 UTC
  GMT season: 15:57:30 – 16:02:30 UTC
```

---

## Diagnostics (pre-registered, no optimization)

1. **W-shape plot**: mean cumulative return by minute from −180 to +60 relative to fix (16:00 London), with 95% block bootstrap CI (block size = 5 days)
2. **By-year decomposition**: H1 mean return per calendar year 2016-2025 (detect further signal decay)
3. **By-pair decomposition**: H1 t-stat per pair (identify pair-specific effects)
4. **EOM vs non-EOM**: H1 return on last business day vs all other days
5. **Fix window sensitivity**: H1 return using ±30s shift on fix window (15:57:00 and 15:58:00 start)

**CONSTRAINT**: No parameter optimization. Window boundaries and thresholds pre-registered here. Any modification after seeing data = new hypothesis + new n_test.

---

## AMTP analysis (n = 175)

| Threshold | t value |
|-----------|---------|
| Naive (α=0.05) | 1.645 |
| BH FDR rank=1 | ~4.65 |
| Bonferroni | ~4.65 |

Note: at n=175, Bonferroni ≈ BH rank=1. Stylized facts IC gate (t > 2.0) is below AMTP. If H1+H2 pass IC gate, full backtest must clear AMTP for Sharpe significance.

---

## Modification budget (max 3 per CLAUDE.md rule)

| # | Modification | Status |
|---|-------------|--------|
| 0 | Base hypothesis (H1+H2 as specified) | PRE-REGISTERED |
| 1 | Reserved | — |
| 2 | Reserved | — |
| 3 | Reserved | — |

---

## Data dependencies

- M5 OHLCV: Dukascopy (via dukascopy-python or duka CLI), cached parquet in `Forex/data/cache/dukascopy_m5/`
- EOM equity returns: yfinance (^GSPC for SPX, URTH for MSCI World ex-US ETF proxy)
- LSE holiday calendar: `pandas_market_calendars.get_calendar('LSE')`

---

## Decision tree

```
H1 t_stat < 1.0              → ARCHIVE (W-shape dead post-2015)
H1 t_stat ≥ 2.0 + 4/6 pairs → H2 test
H1 INCONCLUSIVE (1.0–2.0)   → H2 test (combined decision)

H2 mean return ≤ 0           → ARCHIVE (EOM flow reversed or absent)
H2 t_stat ≥ 1.5 + n ≥ 80   → FULL BACKTEST (Phase 2)
H2 INCONCLUSIVE (1.0–1.5)   → Combined H1+H2 portfolio IC test before Phase 2 decision
```
