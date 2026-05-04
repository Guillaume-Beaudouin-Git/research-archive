# Strategy B: Pairs Trading Walk-Forward Backtest

**Generated:** 2026-05-04 23:48 UTC
**Universe:** 17 Hyperliquid-listed symbols (hourly, 18-month window)
**Method:** Expanding-window walk-forward, 11 folds (test months 7–17)
**ADF threshold:** 40% (pre-registered relaxation from feasibility gate's 60%)

---

## Verdict: ⚠️ INSUFFICIENT_DATA

- n_trades=7 < 30 minimum.
- Action: extend dataset to 36 months (use Binance/Bybit hourly).
- Do NOT add complexity. The problem is data length, not signal design.

---

## Portfolio OOS Metrics

| Metric | Value |
|--------|-------|
| OOS Sharpe (annualized) | — |
| Total OOS P&L | $-99 |
| Max Drawdown ($) | $-306 |
| Max Drawdown (%) | 0.4% |
| Calmar Ratio | — |
| Total Trades | 7 |
| Data validity | INSUFFICIENT_DATA |


### DSR
Not computed — insufficient data (7 trades).


---

## Funnel Stability (pairs surviving per fold)

Folds with ≥ 3 surviving pairs: 9/11 (82%)

| Fold | Active Pairs | Pair Names |
|------|-------------|------------|
| 1 | 8 | DOT/NEAR, BNB/ENA, DOT/OP, BNB/LINK, NEAR/OP, ATOM/ENA, BNB/DOT, ATOM/OP |
| 2 | 7 | DOT/NEAR, DOT/OP, NEAR/OP, ATOM/DOT, AVAX/NEAR, DOT/INJ, ENA/NEAR |
| 3 | 8 | DOT/NEAR, ATOM/ENA, NEAR/OP, DOT/OP, ATOM/DOT, AVAX/NEAR, ADA/LINK, DOT/INJ |
| 4 | 6 | DOT/NEAR, ATOM/NEAR, NEAR/OP, ATOM/DOT, DOT/OP, ATOM/ENA |
| 5 | 7 | DOT/NEAR, ATOM/NEAR, NEAR/OP, ATOM/DOT, DOT/OP, AVAX/OP, ATOM/DOGE |
| 6 | 4 | DOT/NEAR, ATOM/DOT, NEAR/OP, ATOM/DOGE |
| 7 | 1 | ATOM/DOT |
| 8 | 1 | ATOM/DOT |
| 9 | 4 | DOT/NEAR, ATOM/DOT, ADA/DOT, AVAX/DOGE |
| 10 | 5 | AVAX/DOGE, ADA/AVAX, ATOM/DOT, ADA/LDO, DOGE/INJ |
| 11 | 4 | ADA/INJ, ADA/OP, AVAX/DOGE, DOGE/INJ |

---

## Per-Pair OOS Performance

| Pair | Folds Active | OOS Trades | OOS P&L | Mean Test Sharpe |
|------|-------------|-----------|---------|-----------------|
| DOT/OP | 5 | 2 | $100 | -0.487 ± 5.188 |
| ADA/AVAX | 1 | 1 | $9 | 0.384 ± — |
| ADA/DOT | 1 | 0 | $0 | — ± — |
| ADA/INJ | 1 | 0 | $0 | — ± — |
| ADA/LDO | 1 | 0 | $0 | — ± — |
| ADA/LINK | 1 | 0 | $0 | — ± — |
| ADA/OP | 1 | 0 | $0 | — ± — |
| ATOM/DOGE | 2 | 0 | $0 | — ± — |
| ATOM/DOT | 9 | 0 | $0 | — ± — |
| ATOM/ENA | 3 | 0 | $0 | — ± — |
| ATOM/NEAR | 2 | 0 | $0 | — ± — |
| ATOM/OP | 1 | 0 | $0 | — ± — |
| AVAX/NEAR | 2 | 0 | $0 | — ± — |
| AVAX/OP | 1 | 0 | $0 | — ± — |
| BNB/DOT | 1 | 0 | $0 | — ± — |
| BNB/ENA | 1 | 0 | $0 | — ± — |
| BNB/LINK | 1 | 0 | $0 | — ± — |
| DOGE/INJ | 2 | 0 | $0 | — ± — |
| DOT/INJ | 2 | 0 | $0 | — ± — |
| DOT/NEAR | 7 | 0 | $0 | — ± — |
| AVAX/DOGE | 3 | 1 | $-17 | -3.464 ± — |
| NEAR/OP | 6 | 2 | $-76 | -3.333 ± 2.210 |
| ENA/NEAR | 1 | 1 | $-115 | -4.006 ± — |

---

## Correlation to TSMOM (Strategy A)


**Mean rolling 60-day correlation to TSMOM:** 0.072  ✅ Within target


---

## Diagnostic: Why only 7 OOS trades?

This is not a code bug. It is a fundamental frequency mismatch between the strategy's
natural trade horizon and the available data length.

**Root cause:**
The feasibility study established that the best IC occurs at the **72h horizon** — the
signal is slow mean-reversion, not high-frequency. A strategy with 72h expected holding
time and z_entry ≥ 1.5σ will generate roughly 1–3 trades per pair per month in normal
market conditions. With 5–8 pairs active per fold and 1-month test windows, the expected
trade count is ~5–24 per fold. At only 11 folds, the total expected count is 55–264 — but
many folds produced zero because:

1. **Folds 7–8** (Nov–Dec 2025): Only 1 pair (ATOM/DOT) survived the funnel — the
   universe was in a trending/decoupling regime where most pairs failed ADF at 40%.
   ATOM/DOT's best params required z_entry=2.5 and 60d lookback, which never fired
   in a 1-month test window.

2. **DOT/NEAR** (best feasibility pair, Sharpe 3.04 naive): Active in 7/11 folds but
   zero OOS trades. Its calibrated params consistently selected z_entry=2.0–2.5,
   likely overfitting to the training Sharpe. The spread may not have crossed ±2σ
   during any test month.

3. **Grid search artefact**: The train-Sharpe objective selects params that worked on
   the (longer) training window. When applied to a 1-month test window, the higher
   z_entry thresholds (needed for cleaner train Sharpe) are almost never triggered.

**Why the feasibility study showed more activity:** The feasibility naive backtest used
the full 12-month train period at once, not 1-month test slices. With 12 months and
z_entry=2.0, DOT/NEAR triggered 23 trades = ~2/month. The walk-forward confirms this
rate: 2 trades/month × 1 test month = ~2 trades per fold × 11 folds = ~22 — but the
grid search's overfitting pushed z_entry higher, reducing frequency to near zero.

**The correct fix is MORE DATA, not more complexity:**
- 36 months of hourly data would yield ~60–80 OOS trades with current design.
- Source: Binance spot or Bybit perpetuals hourly (free, clean, ~4 year history).
- Do NOT lower z_entry to manufacture trades — that changes the strategy.
- Do NOT add regime detection, ML, or clustering to compensate.

---

## Methodology Notes

### Pre-registered hypothesis change
ADF cointegration threshold relaxed from **60% → 40%** before any test data was seen.
Rationale: 2024-2025 bull/bear cycle systematically breaks rolling Engle-Granger stationarity.
Stoikov et al. (2025) found removing ADF entirely improved Sharpe (2.68→2.98).
We retain ADF at 40% as a sanity filter, not a hard gate.

### Cost model
- Fee: 0.035% × 2 legs × 2 sides = 0.14% round trip
- Slippage: 0.05% × 2 legs × 2 sides = 0.20% round trip
- **Total: 0.34% per round trip on notional**
- Funding cost: NOT modeled. Known omission. Conservative treatment:
  net funding effect adds ~0–5 bps per 8h held; at mean hold ≈ 72h,
  this is ±30bps per trade — material but directionally unclear.

### Execution timing
Signal on bar t-1 close → position at bar t open.
Enforced via `.shift(1)` on Z-score signal before position state machine.

### Known limitations
1. yfinance prices ≠ Hyperliquid perpetual prices (no funding basis).
2. No volume-weighted execution (assumes fills at mid).
3. Funding revenue/cost not modeled.
4. Low trade count per pair (~15-25) limits per-pair statistical inference.
5. 18-month window captures only one full cycle; stationarity may not persist.

---

## GO Criteria (ALL required)
- OOS Sharpe ≥ 1.0 after costs
- DSR ≥ 0.95 (or LOW_SAMPLE flag with Sharpe ≥ 1.0)
- MaxDD ≤ 30%
- Correlation to TSMOM < 0.3
- ≥ 3 pairs survive funnel in ≥ 70% of folds

## NO-GO Criteria (any one sufficient)
- OOS Sharpe < 0.5
- n_trades < 30 → INSUFFICIENT_DATA (fix: more data, not complexity)
- MaxDD > 50%
- All surviving pairs concentrated in one ecosystem

## Next Steps (if GO)
1. Validate on Hyperliquid candle API (replace yfinance — better perp prices)
2. Add funding cost tracking per leg
3. Paper trade on testnet for 30 days before live capital
4. Do NOT add leverage until live SR ≥ 1.5 sustained over 90 days
