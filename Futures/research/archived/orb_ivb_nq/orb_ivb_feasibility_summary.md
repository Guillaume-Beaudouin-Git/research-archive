## Result Summary: ORB IVB on NQ — Feasibility + Replication

### 1. Headline verdict
**DATA_BLOCKED** — insufficient historical 5-min NQ data via free APIs.
Available RTH sessions: **49** (gate: ≥100).
Full 5-year replication (2021–2026) requires Databento or Polygon intraday futures feed.
Partial proof-of-concept results below where available.

### 2. Data status
- Source: yfinance (59-day intraday limit)
- Date range: 2026-03-11 → 2026-05-19
- RTH sessions available: **49** (gate: ≥100)
- Delta source: proxy: sign(C-O) × vol × |C-O| / (H-L+ε)
- 5-year target (2021–2026) covered: NO — target 2021-2026 (69 of ~1900 days covered)
- **BLOCKER**: yfinance intraday limit = ~59 days. For 5-year history, subscribe to:
  - Databento: NQ 5-min bars ~$30/month (CME Globex, bid-ask, delta available)
  - Polygon.io: NQ continuous futures ~$200/month (full tick-level delta)

### 3. Replication match vs Conti report

| Metric              | Conti report  | Our replication | Match (5%?) |
|---------------------|---------------|-----------------|-------------|
| net_profit_gross    | see Conti   | n/a (data blocker) | n/a        |
| net_profit_cost     | see Conti   | n/a (data blocker) | n/a        |
| win_rate            | see Conti   | n/a (data blocker) | n/a        |
| avg_trade           | see Conti   | n/a (data blocker) | n/a        |
| max_dd              | see Conti   | n/a (data blocker) | n/a        |
| profit_factor       | see Conti   | n/a (data blocker) | n/a        |
| total_trades        | see Conti   | n/a (data blocker) | n/a        |
| annual_return_pct   | see Conti   | n/a (data blocker) | n/a        |

### 4. Full-sample metrics (our replication)
| Total trades       | 37 | — |
| Win rate           | 48.6% | — |
| Avg trade          | $-383.82 | — |
| Sharpe (HAC daily) | -3.328 | — |
| Annual return      | -75.2% | — |
| MaxDD ($)          | $18,609 | — |
| MaxDD (%)          | -18.6% | — |
| Profit factor      | 0.626 | — |
| Alpha vs NQ B&H    | -138.9% ann | — |
| Alpha t-stat (HAC) | -1.58 | — |
| Exit: TP / SL / time | 48.6% / 51.4% / n/a | — |

### 5. Bootstrap & Monte Carlo
- EV per trade ($): **$-383.82**, 95% CI [-976.80, 198.20]
- P(EV ≤ 0): **0.8984** (gate < 0.05: ✗)
- 95th percentile MC MaxDD: $-34,603
- Median terminal P&L: $-14,142

### 6. Walk-forward (OOS years)
| Year | Trades | Sharpe | MaxDD | PF    | P(EV≤0) |
|------|--------|--------|-------|-------|---------|
| —    | insufficient data for walk-forward with 60-day window | — | — | — | — |

### 7. Propfirm gate decision
| Gate                       | Threshold | Value | Pass |
|----------------------------|-----------|-------|------|
| Sharpe HAC                 | > 1.0     | -3.328 | ✗    |
| MaxDD (% of cap)           | > -10%    | -18.6% | ✗    |
| P(EV ≤ 0) bootstrap        | < 0.05    | 0.8984 | ✗    |
| Alpha t_HAC vs NQ B&H      | > 2.0     | -1.58 | ✗    |
| Profit factor (cost-adj)   | > 1.20    | 0.626 | ✗    |
| Walk-forward % positive    | > 75%     | 0/1   | n/a (data blocker)    |

### 8. Replication notes & limitations
1. **Data source**: yfinance provides only ~59 days of 5-min NQ=F intraday bars. Full 2021–2026 replication requires Databento (CME Globex NQ continuous, ~$30/mo) or Polygon (~$200/mo with tick-level data for real delta.
2. **Delta proxy**: real per-bar delta = upticks − downticks (Databento `trades` feed). The proxy `sign(C-O) × vol × |C-O| / (H-L)` is a bar-level approximation. Correlation with real delta is unknown without tick data. This is the primary source of replication divergence.
3. **Delta threshold calibration**: Conti uses `UseCumulativeDelta=false`, `DeltaThreshold=200` in as-tested NinjaTrader params. The proxy is measured in volume-weighted units, not raw tick counts — the threshold may need rescaling when real delta becomes available.
4. **Session boundaries**: NQ futures trade nearly 24h. yfinance bars may include overnight RTH-extension bars. Filter strictly to [08:30, 15:00) ET.
5. **Continuous contract roll**: `NQ=F` on yfinance is front-month continuous. Roll gaps near expiry can create spurious ORB signals on rollover days — production implementation should skip rollover days.

### 9. Recommendation
**BLOCKED on data.** Two paths forward:
1. **Databento** (Priority): $30/mo, NQ 5-min OHLCV + real per-bar delta from `trades` schema. Covers 2021–2026. Subscribe and re-run.
2. **SPY proxy validation** (free): fetch SPY 5-min bars (yfinance 2-year history) and run ORB with delta proxy. SPY and NQ are correlated intraday structures. This won't replicate Conti's $ figures but validates the implementation logic before paying for data.
3. Do NOT deploy or paper trade until at least 200 sessions of OOS data are available.

### 10. n_tests counter
- Start of session: 65
- ORB IVB NQ feasibility: n_tests = 66
- End of session: 66

### 11. Files written
- feasibility.py (this script)
- orb_ivb_feasibility_summary.md (this summary)