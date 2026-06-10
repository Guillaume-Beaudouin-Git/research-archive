# Strategy D: Weekend Return Anomaly (BTC Perpetual)

**Generated:** 2026-05-05 UTC
**Universe:** BTC-USDT perpetual (Hyperliquid)
**Signal:** Day-of-week indicator — no free parameters
**Trade:** Short BTC perpetual Friday 16:00 UTC → Monday 00:00 UTC (56h hold)
**Income:** Short price P&L + funding income (shorts collect positive funding)
**Cost:** 0.34% round-trip per trade
**Notional:** $10,000 per trade
**Sharpe scale:** weekly (×√52)

---

## Verdict: ❌ NO-GO

---

## Overall Metrics

| Metric | Value |
|--------|-------|
| Trades | 159 |
| Total Net P&L | $+2,230 |
| Total Price P&L | $-1,093 |
| Total Funding Income | $+8,729 |
| Total Fees | −$5,406 |
| Win Rate | 51% |
| **Sharpe (weekly)** | **0.418** |
| Max Drawdown ($) | $2,257 |
| Max Drawdown (% of notional) | 22.6% |

---

## GO Criteria

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| Sharpe (weekly) | ≥ 1.0 | 0.418 | ❌ |
| Max Drawdown | ≤ 30% of notional | 22.6% | ✅ |

---

## Year-by-Year Breakdown

 year  n_trades  total_net  price_pnl  funding_pnl   fees win_rate  sharpe  max_dd
 2023        37     -211.0     -682.0       1729.0 1258.0      41%   -0.20  1280.0
 2024        52     1363.0    -1668.0       4799.0 1768.0      62%    0.89  1136.0
 2025        52     -474.0     -747.0       2041.0 1768.0      46%   -0.24  2154.0
 2026        18     1552.0     2004.0        161.0  612.0      56%    2.10   390.0

---

## Decomposition

| Component | Amount | % of gross |
|-----------|--------|------------|
| Price P&L | $-1,093 | -11.1% |
| Funding Income | $+8,729 | 88.9% |
| Fees | −$5,406 | — |
| **Net P&L** | **$+2,230** | — |

---

## Methodology Notes

### Signal Construction
- Entry trigger: Friday 16:00 UTC bar (weekday=4, hour=16)
- Entry price: open of next bar (Saturday 00:00 UTC)
- Exit price: open of Monday 00:00 UTC bar (56h after signal)
- Position: SHORT (−1 × notional)
- No look-ahead bias: signal uses only day-of-week (no price data in signal)

### Funding Income
- BTC 8h funding rates from Hyperliquid (each row = avg 1h rate × 8h window)
- Short position collects: +funding_rate × 8h × notional per 8h period
- Weekend window: 7 funding periods (Sat 00:00, Sat 08:00, Sat 16:00, Sun 00:00, Sun 08:00, Sun 16:00, Sun 24:00/Mon 00:00 [excluded, exit point])
- Summed: total_funding_rate × 8 × notional

### Cost Model
- 0.035% taker fee × 2 sides + 0.05% slippage × 2 sides = 0.34% round-trip
- Applied per trade on full notional

### Mechanism (Weekend Effect)
- Documented in crypto literature (extension of Lou, Polk & Skouras 2019):
  BTC tends to underperform Friday close → Monday open vs weekday periods
- Proposed drivers: lower institutional participation on weekends, retail deleveraging,
  options gamma unwind Friday close, reduced liquidity amplifying directional moves
- No parameters: signal is purely calendar-based, requiring no calibration window

---

## Notes

- Data from Hyperliquid (first available: 2023-04-20)
- Full history used: no walk-forward needed (no parameters to select)
- Correlation to TSMOM (Strategy A, 28d signal): expected low (weekly vs monthly signal)
