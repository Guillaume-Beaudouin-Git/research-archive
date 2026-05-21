## Result Summary: ORB IVB on NQ -- Kaggle 1-min Data, Delta-Free Variant

### 1. Headline verdict
> **5-min variant**: FAIL -- insufficient edge (Sharpe<0.5)

### 2. Data quality
- Total bars loaded: 1,048,575
- Valid trading sessions (clean_sessions.json): 736
- See `data_audit_report.md` for full quality report and excluded sessions.

### 3. Replication match vs Conti (NQ, 2021-2026)

| Metric              | Conti (NQ w/ delta) | Ours 5-min (no delta) | Ours 1-min (no delta) |
|---------------------|---------------------|----------------------|----------------------|
| Total trades        | 823 (5 years)       | 601 (3 years)   | 619 (3 years)   |
| Trades per year     | ~165                | 200                      | 206 |
| Win rate            | 58.3%               | 53.4%              | 51.9% |
| Avg trade ($)       | $201.35             | $-19                 | $11 |
| Avg winner ($)      | $1,474              | $991               | $1019 |
| Avg loser ($)       | -$1,580             | $-1177              | $-1076 |
| MaxDD ($)           | $25,295             | $28638           | $21573 |
| Profit factor       | 1.31                | 0.966               | 1.021 |
| Annual return (%)   | 31.4%               | -3.8%             | 2.3% |
| Sharpe              | ~1.4 (monthly)      | -0.439 (daily HAC)  | -0.092 |

### 4. Performance metrics (gross + cost-adjusted)

| Metric             | 5-min gross | 5-min cost-adj | 1-min cost-adj |
|--------------------|-------------|----------------|----------------|
| Total trades       | 601 | 601 | 619 |
| Win rate           | 53.4% | 53.4% | 51.9% |
| Avg trade ($)      | $-5 | $-19 | $11 |
| Net P&L ($)        | $-2,790 | $-11,204 | $6,674 |
| Sharpe (daily HAC) | -- | -0.439 | -0.092 |
| MaxDD ($)          | -- | $-28638 | $-21573 |
| MaxDD (%)          | -- | -28.6% | -21.6% |
| Profit factor      | -- | 0.966 | 1.021 |
| Ann. return (%)    | -- | -3.8% | 2.3% |
| Exits TP/SL/time   | -- | TP 47% / SL 43% / time 9% | TP 47% / SL 45% / time 8% |

### 5. Bootstrap & Monte Carlo (5-min variant, cost-adj)

- EV/trade ($):  $-18.64  [95% CI $-124.68, $88.72]
- EV/trade (R):  -0.0579  [95% CI -0.1449, 0.0289]
- P(EV$ <= 0):   0.6333
- P(EV_R <= 0):  0.9022
- MC MaxDD p50/p75/p90/p95/p99:  $-40744 / $-30096 / $-23438 / $-20145 / $-15947
- MC median terminal P&L:         $-11152
- Shuffled Sharpe p95:            -0.3420
- P(shuffled >= observed):        1.0000
- AMTP p-value (n=67, 5-min): 0.9989  (FAIL)

### 6. Walk-forward (5-min variant, OOS windows)

| OOS Window          | Trades | Win%  | Sharpe | PF    | MaxDD%  | P(EV<=0) |
|---------------------|--------|-------|--------|-------|---------|----------|
| 2023-07 -> 2023-12  | 103    | 57.3  | -0.686 | 0.941 | -11.6   | 0.6008   |
| 2024-01 -> 2024-06  | 95     | 53.7  | -0.827 | 0.920 | -10.9   | 0.6349   |
| 2024-07 -> 2024-12  | 102    | 53.9  | +0.052 | 1.038 | -18.3   | 0.4430   |
| 2025-01 -> 2025-12  | 192    | 51.6  | -0.650 | 0.928 | -26.6   | 0.6649   |
| **OOS aggregate**   | -- | -- | -- | -- | -- | 25% positive |

### 7. Alpha vs NQ B&H (HAC OLS, daily excess returns)

> Note: intraday strategy (~6h/day exposure). NQ B&H is not the natural benchmark.
> Alpha t > 2 indicates genuine intraday edge regardless.

| Metric              | 5-min variant |
|---------------------|---------------|
| Alpha (ann. %)      | -41.76% |
| Alpha t-stat (HAC)  | -3.383 |
| Beta vs NQ          | 0.4840 |
| R2                  | 0.1770 |
| Residual Sharpe     | -0.0000 |

### 8. Propfirm gate decision

| Gate                       | Threshold | Value         | Pass |
|----------------------------|-----------|---------------|------|
| Sharpe HAC (5-min)         | > 1.0     | -0.439        | FAIL |
| MaxDD (% of $100k)         | > -10%    | -28.6%            | FAIL |
| P(EV <= 0) bootstrap       | < 0.05    | 0.6333        | FAIL |
| Profit factor (cost-adj)   | > 1.20    | 0.966         | FAIL |
| Walk-forward % positive    | > 75%     | 25%             | FAIL |
| AMTP p-value (n=67)      | < 0.10    | 0.9989        | FAIL |

### 9. Plumbing validation (5-min variant)

- ORB window bounded [08:30, 09:00): yes
  - 2022-12-28: 30 bars, first=08:30:00, last=08:59:00
  - 2022-12-29: 30 bars, first=08:30:00, last=08:59:00
  - 2022-12-30: 30 bars, first=08:30:00, last=08:59:00
- Entry only after 09:00: yes
- TP triggered at TP price: yes
  - 2022-12-28: entry=13610.25, exit=13637.5, expected_tp=13637.5, match=True
  - 2022-12-29: entry=13574.25, exit=13634.0, expected_tp=13634.0, match=True
- SL triggered at SL price: yes
  - 2022-12-30: entry=13592.0, exit=13559.25, expected_sl=13559.25, match=True
  - 2023-01-03: entry=13782.5, exit=13741.25, expected_sl=13741.25, match=True
- Time exit at or after 15:00: yes
  - 2023-01-06: exit_at=2023-01-06 15:00:00-05:00, ok=True
  - 2023-01-12: exit_at=2023-01-12 15:00:00-05:00, ok=True
- Only 1 trade per session: yes  (max 1 in any session)
- Cost $14 RT: yes
  - 2022-12-28: net_pnl=531.00, expected=531.00
  - 2022-12-29: net_pnl=1181.00, expected=1181.00

### 10. 5-min vs 1-min comparison

| Metric     | 5-min | 1-min | Delta |
|------------|-------|-------|-------|
| Trades     | 601 | 619 | +18 |
| Win rate   | 53.4% | 51.9% | -- |
| Sharpe     | -0.439 | -0.092 | +0.346 |
| PF         | 0.966 | 1.021 | +0.055 |
| Ann ret    | -3.8% | 2.3% | -- |

### 11. Recommendation

> Archive ORB family OR investigate delta filter. Delta filter may have been the real edge in Conti. Consider Databento $30/mo to test delta-filtered NQ ORB, or archive and pivot.

Gates passed: 0/5 (excluding AMTP)

### 12. n_tests counter

- Start: 66
- 5-min NQ ORB (this script): n_tests = 67
- 1-min NQ ORB (this script): n_tests = 68
- **End: 68**
