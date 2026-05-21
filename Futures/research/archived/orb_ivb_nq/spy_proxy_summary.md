## Result Summary: SPY ORB Proxy — Plumbing + Edge Test

### 1. Headline verdict
> **yfinance 5-min data limit**: ~60 days for ALL tickers. Period='2y', '6mo', '3mo' all return empty for SPY. The '730-day ETF exception' does NOT exist in the free API. Confirmed empirically this session.
**DATA_BLOCKED** — only 59 RTH sessions available (gate: < 60 sessions = < 6 months). Partial proof-of-concept results below but NOT statistically conclusive.

Infrastructure options to unblock:
1. **Databento** ($30/mo): NQ 5-min OHLCV + real per-bar delta, 2021–2026 full history
2. **Polygon.io** ($200/mo): tick-level NQ data with true delta
3. **Interactive Brokers API** (free with account): historical 5-min bars, up to ~6 months for futures, no tick delta
4. **NinjaTrader free sim account**: free 5-min data, manual export possible

### 2. Data
- yfinance SPY interval=5m: 2026-02-25 → 2026-05-19
- Regular sessions: **59**
- ORB window (09:30–10:00 ET): 6 bars per session (5-min × 6)
- Trading window (10:00–15:30 ET): ~66 bars per session
- Avg bars/session: 72.8
- Sessions with valid ORB: 59
- Sessions with trade signal: 40

### 3. Trade log summary
| Metric             | Value (gross)         | Value (cost-adj) |
|--------------------|----------------------|------------------|
| Total trades       | 40 | 40 |
| Win rate           | 62.5% | — |
| Avg trade ($)      | $66.44 | $64.44 |
| Avg trade (R)      | — | +0.1842R |
| Largest winner     | $491.00 | — |
| Largest loser      | $-512.00 | — |
| Avg bars (winners) | 35.0 | — |
| Avg bars (losers)  | 33.9 | — |

### 4. Performance metrics
| Metric                       | Value     |
|------------------------------|-----------|
| Net P&L (cost-adj)           | $2,577.65 |
| Annual return (%)            | +23.8% |
| Sharpe (daily, HAC)          | +3.691 |
| MaxDD ($)                    | $-787.43 |
| MaxDD (% of capital)         | -1.6% |
| Profit factor                | 1.845 |
| Return on MaxDD              | 15.13 |
| Exit: TP / SL / time         | 40% / 22% / 38% |

### 5. Statistical tests
| Test                | Result                           |
|---------------------|----------------------------------|
| EV per trade ($)    | $64.44, 95% CI [-12.28, 139.86] |
| EV per trade (R)    | +0.1842R, 95% CI [-0.0807, 0.4359] |
| P(EV$ ≤ 0)          | 0.0480 ✓ |
| P(EV_R ≤ 0)         | 0.0829 |
| MC 95th pct MaxDD   | $-1,790.92 |
| MC median terminal  | $2,583.02 |
| Shuffled MaxDD p95  | $-542.98 |
| AMTP p-value (n=66) | 0.8235 ✗ |

### 6. Alpha vs SPY buy-and-hold
| Metric              | Value   |
|---------------------|---------|
| Alpha (annualized)  | +9.2% |
| Alpha t-stat (HAC)  | +0.48 |
| Beta vs SPY         | 0.223 |
| R²                  | 12.7% |
| Residual Sharpe     | +1.244 |

### 7. Walk-forward (50/50 split)
| Window     | Trades | Sharpe | PF    | P(EV≤0) |
|------------|--------|--------|-------|---------|
| IS 50%     |     16 | +4.400 |  2.05 |  0.1104 |
| OOS 50%    |     24 | +3.054 |  1.67 |  0.1382 |

### 8. Plumbing validation checklist
- ORB window correctly bounded 09:30–10:00 ET: ✗
  - 2026-02-25: ORB H=691.99, L=690.10, range=1.89, bars=6 (09:30:00–10:00:00)
  - 2026-02-26: ORB H=693.30, L=690.42, range=2.88, bars=6 (09:30:00–10:00:00)
  - 2026-02-27: ORB H=684.25, L=681.64, range=2.61, bars=6 (09:30:00–10:00:00)
- Trade entry only after 10:00 ET: ✓
  - Sample: 2026-02-25 entry at 2026-02-25 11:45:00-05:00 @ $692.21 (ORB high $691.99, above=True)
- TP triggered at TP price: ✓
  - 2026-03-09: entry $668.12 → exit $673.05 (TP target $673.05, matches=True, R=1.000)
- SL triggered at SL price: ✓
  - 2026-03-16: entry $671.00 → exit $667.70 (SL target $667.70, matches=True, R=-1.030)
- Time exit at 15:30 ET: ✓
  - 2026-02-25: exit at 2026-02-25 15:30:00-05:00
- Only 1 trade per session: ✓ (max 1 trades in any session)

### 9. Comparison: SPY ORB (no delta) vs Conti NQ (with delta)
> **Caveat**: SPY ≠ NQ. Different vol regime, no delta filter. This validates ORB family edge, not Conti replication.

| Metric          | Conti (NQ, with delta) | SPY proxy (no delta) | Notes |
|-----------------|------------------------|----------------------|-------|
| Win rate        | 58.3%                  | 62.5%                | SPY ~60d sample |
| PF              | 1.31                   | 1.84                 | — |
| Avg trade R     | +0.13R                 | +0.184               | — |
| Sharpe          | ~1.4                   | +3.69                | unreliable at <60 sess |

### 10. Recommendation
**DATA_BLOCKED** — insufficient data for a confident recommendation.

Observed in partial 59-session run:
  - Sharpe=+3.691, PF=1.845, P(EV≤0)=0.0480
  - Weak positive direction in the available window — not conclusive.

**Next step (choose one):**
- **Option A — Databento $30/mo**: Full 5-year NQ replication with real delta. Highest-quality path. Subscribe if committed to futures ORB research.
- **Option B — IBKR API (free)**: ~6 months NQ 5-min via TWS API. Sufficient for basic validation (≥120 sessions). No real-time delta; delta proxy still required.
- **Option C — Pivot strategy**: If ORB is only interesting with real delta (which drives Conti's 58.3% win rate), and free data can't provide delta, consider other intraday strategies accessible with free data.

### 11. n_tests counter
- Start: 65
- SPY ORB proxy: n_tests = 66 (same trial as NQ feasibility — implementation validation)
- End: 66

### 12. Files written
- spy_proxy.py (this script)
- spy_proxy_summary.md (this summary)