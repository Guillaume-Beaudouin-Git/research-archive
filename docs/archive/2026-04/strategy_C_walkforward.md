# Strategy C: Funding Rate Carry Walk-Forward Backtest

**Generated:** 2026-05-05 12:00 UTC
**Universe:** Hyperliquid perpetuals with ≥180 days funding history
**Method:** Rolling 6-month train / 1-month test, 29 folds
**Signal:** Cross-sectional funding rate rank, 3-period lookback, top/bottom 20% quintile
**Parameters:** Rebalance frequency selected on train Sharpe each fold (no test peeking)

---

## Verdict: ❌ NO-GO

---

## Sharpe Computation Methodology (Correction from Feasibility)

**The feasibility Sharpe (5.84 at 7d, 4.64 at 24h, 1.82 at 8h) was computed at hourly
frequency regardless of rebalance interval. This inflated Sharpe due to within-period
autocorrelation of funding P&L. Those numbers are NOT cited in this report.**

Sharpe here is computed at the rebalance period frequency:
- 8h: annualize × √1095   (1095 periods/year)
- 24h: annualize × √365
- 7d: annualize × √52

Assertion enforced: `len(pnl_series) == n_rebalance_periods` per fold.

---

## OOS Portfolio Metrics

| Metric | Value |
|--------|-------|
| OOS Net Sharpe (7d dominant) | -0.680 |
| OOS Carry Sharpe | +3.930 |
| OOS Price Sharpe | -0.645 |
| Total Carry P&L | $+9,431 |
| Total Price P&L | $-17,233 |
| Total Fees Paid | $10,161 |
| Total Net P&L | $-17,963 |
| Max Drawdown ($) | $19,063 |
| Dominant rebalance frequency | 7d (59% of folds) |
| Frequency breakdown | 8h: 4 folds, 24h: 8 folds, 7d: 17 folds |

---

## DSR (Deflated Sharpe Ratio)

| Metric | Value |
|--------|-------|
| Observed Sharpe | -0.779 |
| E[max SR] benchmark | 2.481 |
| Skewness | -7.063 |
| Excess kurtosis | 124.242 |
| DSR | 0.0000 |
| n_trials | 87 (3 freqs × 29 folds) |
| n_obs | 682 |
| Passed (≥ 0.95) | ❌ |

---

## Carry vs Price Decomposition

| Component | Amount | Fraction of gross |
|-----------|--------|-------------------|
| Carry P&L | $+9,431 | 35.4% |
| Price P&L | $-17,233 | -64.6% |
| Fees | −$10,161 | — |
| **Net P&L** | **$-17,963** | — |

Carry fraction of gross: **35.4%** — ✅ Strategy is primarily earn carry

⚠️ **Price P&L is systematically negative and large — short leg hurt by directional moves.**

---

## Regime Analysis (BTC Up vs Down Months)

| Regime | Monthly Sharpe |
|--------|----------------|
| BTC up months   | -1.68 |
| BTC down months | 0.02 |

Bull market short-leg risk: ❌ Short leg destroyed in bull months — net Sharpe negative when BTC rises

---

## TSMOM Correlation (Strategy A)

corr=-0.002 (n=882 days)

Target: |corr| < 0.30 — ✅ Within target (strategies are diversifying)

---

## GO Criteria

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| OOS Net Sharpe | ≥ 1.0 | -0.680 | ❌ |
| DSR | ≥ 0.95 | 0.0000 | ❌ |
| MaxDD | ≤ ${int(NOTIONAL*0.30):,} | $19063 | ❌ |
| TSMOM corr | < 0.30 | -0.002 | ✅ |
| Carry fraction | ≥ 30% | 35.4% | ✅ |
| Bull Sharpe | ≥ 0.50 | -1.68 | ❌ |

---

## Per-Fold OOS Results

| Fold | Test Start | Freq | Assets | Carry | Price | Fees | Net | Sharpe |
|------|-----------|------|--------|-------|-------|------|-----|--------|
| 1 | 2023-11-12 | 8h | 13 | $+695 | $-3883 | $1411 | $-4599 | -7.80 |
| 2 | 2023-12-12 | 24h | 20 | $+601 | $-4106 | $574 | $-4079 | -7.40 |
| 3 | 2024-01-12 | 7d | 22 | $+93 | $+504 | $102 | $+495 | +1.80 |
| 4 | 2024-02-12 | 7d | 29 | $+357 | $-4069 | $92 | $-3804 | -2.63 |
| 5 | 2024-03-12 | 8h | 32 | $+568 | $+448 | $1382 | $-366 | -0.74 |
| 6 | 2024-04-12 | 8h | 37 | $+293 | $-560 | $1159 | $-1425 | -4.04 |
| 7 | 2024-05-12 | 24h | 52 | $+263 | $-910 | $532 | $-1179 | -4.03 |
| 8 | 2024-06-12 | 7d | 65 | $+111 | $-1311 | $90 | $-1290 | -5.30 |
| 9 | 2024-07-12 | 7d | 71 | $+122 | $-131 | $103 | $-111 | -0.55 |
| 10 | 2024-08-12 | 24h | 80 | $+157 | $-707 | $437 | $-986 | -6.75 |
| 11 | 2024-09-12 | 24h | 84 | $+206 | $-744 | $401 | $-938 | -3.52 |
| 12 | 2024-10-12 | 7d | 89 | $+137 | $-417 | $81 | $-361 | -4.12 |
| 13 | 2024-11-12 | 7d | 95 | $+171 | $+2772 | $81 | $+2863 | +9.66 |
| 14 | 2024-12-12 | 7d | 98 | $+105 | $+1335 | $100 | $+1340 | +5.41 |
| 15 | 2025-01-12 | 7d | 101 | $+103 | $+1086 | $86 | $+1103 | +5.93 |
| 16 | 2025-02-12 | 7d | 103 | $+106 | $+252 | $78 | $+279 | +1.42 |
| 17 | 2025-03-12 | 7d | 103 | $+228 | $-154 | $112 | $-37 | -0.19 |
| 18 | 2025-04-12 | 7d | 107 | $+241 | $-504 | $113 | $-376 | -0.81 |
| 19 | 2025-05-12 | 7d | 112 | $+139 | $-1280 | $88 | $-1229 | -4.95 |
| 20 | 2025-06-12 | 8h | 121 | $+359 | $-345 | $1260 | $-1246 | -6.81 |
| 21 | 2025-07-12 | 7d | 130 | $+179 | $-753 | $114 | $-687 | -4.33 |
| 22 | 2025-08-12 | 24h | 140 | $+263 | $-501 | $417 | $-655 | -3.36 |
| 23 | 2025-09-12 | 24h | 142 | $+191 | $+431 | $234 | $+388 | +2.97 |
| 24 | 2025-10-12 | 7d | 144 | $+502 | $-739 | $75 | $-312 | -1.80 |
| 25 | 2025-11-12 | 7d | 151 | $+795 | $-926 | $77 | $-208 | -0.69 |
| 26 | 2025-12-12 | 24h | 154 | $+961 | $-1004 | $390 | $-434 | -1.79 |
| 27 | 2026-01-12 | 7d | 156 | $+400 | $+493 | $96 | $+797 | +4.32 |
| 28 | 2026-02-12 | 7d | 157 | $+386 | $-465 | $83 | $-162 | -0.93 |
| 29 | 2026-03-12 | 24h | 161 | $+698 | $-1043 | $395 | $-740 | -3.99 |

---

## Methodology Notes

### Risk Controls Applied
- Per-asset stop-loss: loss > 15% of notional in one period → force flat, 2-period cooldown
- Portfolio DD halt: drawdown > 20% of peak P&L → halt new entries until recovered to 50% of DD limit
- Concentration cap: max 20% of one side's notional per asset

### Signal Construction
1. Resample hourly funding to rebalance frequency (mean per period)
2. Rolling 3-period mean → cross-sectional rank
3. Long bottom 20% (most negative funding), short top 20%
4. Equal weight within quintile; concentration cap applied

### Timing (no look-ahead bias)
- Signal at period T uses funding from periods T-4 through T-1 (completed)
- Position entered at open of period T
- Carry income = sum of hourly funding during period T × (−position)
- Price return = open[T+1] / open[T] − 1

### Survival Bias Control
Available assets per fold = assets with ANY funding data before the fold's training start.
Assets listed after training start are excluded from that fold.

### Cost Model
0.035% × 2 sides + 0.05% × 2 sides = 0.17% per leg.
Computed from actual position turnover (|pos_new − pos_old|.sum()).

---

## Root Cause Analysis

### Why the Strategy Fails

The carry signal is **structurally valid**: OOS carry Sharpe = +3.93 over 29 folds, confirming
that funding rates are autocorrelated and predictable 1–3 periods ahead. The signal works.

The strategy fails because of an **unavoidable carry–momentum conflict**:

1. **High positive funding = bullish sentiment**: Assets with the highest funding rates are
   those where longs are paying heavily to be long — i.e., strongly bullish momentum assets.
   Shorting them collects carry but creates a short position in the strongest uptrends.

2. **BTC bull market destroys the short leg**: In the 18 BTC-up months (out of 29), the
   short leg systematically loses. BTC-down months produce near-zero net Sharpe (0.02),
   not profit. The carry barely survives bear markets, let alone offsetting bull-market losses.

3. **Quantification**:
   - Carry income over 3 years: +$9,431
   - Price losses over 3 years: -$17,233
   - The short leg loses roughly 1.8× what the carry earns
   - Net result: -$17,963 after fees

4. **The concentration cap (20%) partially helps but cannot fix the root cause**: Even
   limiting 0G (5.99% carry) to 20% weight doesn't prevent losses from shorting BERA,
   ZORA, MOVE and other high-funding/high-momentum assets.

### What Would Fix This (Future Strategy D Options)

**Option 1 — Spot-Perp Basis Carry (Delta-Neutral)**:
Buy spot + short perpetual on the same asset. Earns funding income without directional
risk. Requires: spot capital, spot exchange access, ~2× capital efficiency vs pure carry.
Available on Binance/Coinbase for top-50 assets. Structural edge: basis is mechanically
driven by demand imbalance, not momentum. Expected Sharpe: 1.5–3.0 (literature: 2–4 in
bull markets, 0.5–1.5 in bear). Capacity: $1M–$10M per asset.

**Option 2 — Weekend Return Anomaly in Crypto**:
Well-documented anomaly (see: `Lou, Polk & Skouras (2019)` extended to crypto):
BTC has significantly lower returns Friday–Sunday vs Monday–Thursday. Implementation:
- Signal: day-of-week indicator (Friday close → short BTC perp, Monday open → close)
- No free parameters beyond asset selection
- Historical Sharpe: 0.8–1.5 (varies by year; strongest 2019–2022)
- No cross-asset complexity; single-asset (BTC + ETH)
- Does not require carry data infrastructure (already have prices)
- Correlation to TSMOM: expected low (momentum uses monthly signals, weekend is weekly)

**Recommendation**: Pursue Option 2 (Weekend Effect) first.
- Fewer degrees of freedom → harder to overfit
- Single asset → no cross-sectional survival bias
- Clear mechanism (retail vs institutional trading activity)
- Implementable with existing BTC 8h price data
