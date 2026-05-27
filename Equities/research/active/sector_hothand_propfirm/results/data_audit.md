# Phase 0 — Data Audit Report

**Run date:** 2026-05-28  
**Period fetched:** 2000-01-01 → 2026-05-27  
**Source:** yfinance daily (auto_adjust=True)  
**Tickers:** 10

## Quality table

| Ticker | Rows | First valid | Last valid | Missing % | Gap-tail % | Autocorr(1) | Flag |
|--------|------|-------------|------------|-----------|------------|-------------|------|
| QQQ | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 39.42 | -0.0574 | OK |
| XLK | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 43.12 | -0.0671 | OK |
| XLE | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 46.89 | -0.0454 | OK |
| XLP | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 21.49 | -0.0797 | OK |
| XLU | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 24.97 | -0.0671 | OK |
| XLV | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 27.54 | -0.0389 | OK |
| XLF | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 40.64 | -0.0984 | OK |
| XLI | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 38.26 | -0.0361 | OK |
| XLB | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 38.84 | -0.033 | OK |
| XLY | 6638 | 2000-01-03 | 2026-05-26 | 3.63 | 37.53 | -0.0304 | OK |

## Metric definitions

- **Missing %** : (biz-days in calendar − rows with valid close) / biz-days. Flag if > 5%.
- **Gap-tail %** : fraction of trading days where |open_t − close_{t−1}| / close_{t−1} > 0.5%.
- **Autocorr(1)** : lag-1 autocorrelation of daily log-returns (sanity; near 0 expected).
- **Flag** : OK | MISSING>5% | LATE_START(date) | EMPTY

## Verdict

**STATUS: OK — all tickers pass quality gates.**

→ Proceed to Phase 1 (baseline engine).