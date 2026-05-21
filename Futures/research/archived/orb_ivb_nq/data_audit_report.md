# NQ 1-min Data Quality Audit

**Dataset**: `Dataset_NQ_1min_2022_2025.csv`
**Date range**: 2022-12-26 → 2025-12-11
**Bars**: 1,048,575 actual | 1,029,236 expected | coverage 101.9%

## ✅ Critical checkpoint: PASS — no critical data issues

## 1. Total Bars

| Metric | Value |
|--------|-------|
| Actual bars | 1,048,575 |
| Expected bars | 1,029,236 |
| Coverage | 101.88% |
| Date range | 2022-12-26 → 2025-12-11 |
| Years | 2.96 |
| Status | ✅ PASS |

## 2. Timestamp Gaps (ORB+Trading Window 08:30-15:00 ET)

Sessions with gaps > 5 min: **2**  ✅

**Worst 10 gaps:**

| Date | Gap (min) | At time | N gaps in session |
| ------ | --------- | ------- | ----------------- |
| 2024-07-19 | 11.0 | 10:08:00 | 1 |
| 2024-08-02 | 9.0 | 12:03:00 | 1 |

## 3. OHLC Price Sanity

| Check | Count | Status |
|-------|-------|--------|
| H < L (corruption) | 0 | ✅ |
| H < Close | 0 | ✅ |
| H < Open | 0 | ✅ |
| L > Close | 0 | ✅ |
| L > Open | 0 | ✅ |
| Zero-range bars (H==L) | 737 | ⚠️ |
| Zero-volume bars (RTH) | 0 | ✅ |

## 4. Overnight Gap Distribution

Sessions analysed: 922  |  Large gaps (>3%): **0**

| Percentile | Gap |
|------------|-----|
| p50 | 0.002% |
| p95 | 0.143% |
| p99 | 0.597% |
| max | 2.107% |

## 5. Weekend / Holiday Handling

Saturday bars (anomalous): **0**  ✅ PASS
Sunday bars: **54180** (normal — CME Globex opens Sunday 18:00 ET)

## 6. RTH vs ETH Split

| Metric | Value | Expected |
|--------|-------|----------|
| RTH bars (09:30-16:00) | 292,908 (27.9%) | ~28% (6.5h / 23h) |
| RTH volume | 336,694,668 (76.2%) | ~70-80% |
| Total bars | 1,048,575 | — |
| Total volume | 441,890,512 | — |

## 7. VWAP Sanity

RTH bars with VWAP_RTH > 0: 292,143
Violations (VWAP outside session H/L): **0**  (✅)

**Sample sessions (first bar of RTH per day):**

| Date | Open | Session High | Session Low | Close | VWAP_RTH |
| ------ | ------ | ------------ | ----------- | ------ | -------- |
| 2022-12-27 | 13706.5 | 13711.0 | 13551.0 | 13688.5 | 13695.9169921875 |
| 2022-12-28 | 13555.25 | 13651.5 | 13413.75 | 13541.75 | 13549.6669921875 |
| 2022-12-29 | 13540.75 | 13726.5 | 13511.5 | 13537.5 | 13537.0830078125 |
| 2022-12-30 | 13566.5 | 13675.75 | 13510.5 | 13576.25 | 13570.75 |
| 2023-01-03 | 13774.25 | 13837.0 | 13499.75 | 13755.75 | 13765.3330078125 |

## 8. Clean Session Filter

**Total sessions with ORB+trading data**: 766
**Excluded sessions**: 30
**Clean sessions (used by strategy)**: **736**

**Excluded sessions (first 20):**

| Date | Reason |
| ------ | ------ |
| 2023-01-16 | trade bars 241<288 |
| 2023-02-20 | trade bars 241<288 |
| 2023-04-07 | trade bars 16<288 |
| 2023-05-29 | trade bars 241<288 |
| 2023-06-19 | trade bars 241<288 |
| 2023-07-03 | trade bars 256<288 |
| 2023-07-04 | trade bars 241<288 |
| 2023-09-04 | trade bars 241<288 |
| 2023-11-23 | trade bars 241<288 |
| 2023-11-24 | trade bars 256<288 |
| 2024-01-15 | trade bars 241<288 |
| 2024-02-19 | trade bars 241<288 |
| 2024-05-27 | trade bars 241<288 |
| 2024-06-19 | trade bars 241<288 |
| 2024-07-03 | trade bars 256<288 |
| 2024-07-04 | trade bars 241<288 |
| 2024-09-02 | trade bars 241<288 |
| 2024-11-28 | trade bars 241<288 |
| 2024-11-29 | trade bars 256<288 |
| 2024-12-24 | trade bars 256<288 |

*… and 10 more excluded sessions.*

Saved to: `clean_sessions.json`

## 9. Summary & Strategy Decisions

| Check | Result | Action |
|-------|--------|--------|
| Total bars | 101.9% coverage | Use all data |
| Timestamp gaps | 2 sessions | Exclude flagged sessions |
| OHLC integrity | 0 H<L bars | Clean |
| Overnight gaps | 0 >3% | Clean |
| Weekends | 0 bars | Clean |
| RTH/ETH split | 76% RTH vol | Normal |
| VWAP | 0 violations | Clean |
