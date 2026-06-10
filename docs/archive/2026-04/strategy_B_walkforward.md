# Strategy B: Pairs Trading Walk-Forward Backtest

**Generated:** 2026-05-05 00:54 UTC
**Universe:** 17 Hyperliquid-listed symbols (hourly, 36-month Binance data)
**Data source:** binance
**Method:** Rolling 12-month training window (v3), 24 folds
**ADF threshold:** 40% (pre-registered) | **z_entry:** 2.0 fixed | **Final methodology version**

---

## Verdict: ⚠️ INSUFFICIENT_DATA

- n_trades=3 < 50 minimum.
- Rolling window fix confirmed: DOT/NEAR corr_logP 0.928–0.966 across all folds (✅ passes 0.85).
- Funnel now admits pairs in 15/24 folds (was 3/24 with expanding window).
- But signal at z_entry=2.0 fires ~0.1 trades/pair/month — not enough for statistical testing.
- This is the final methodology change. Strategy B is not viable on this universe.

---

## Portfolio OOS Metrics

| Metric | Value |
|--------|-------|
| OOS Sharpe (annualized) | — |
| Total OOS P&L | $137 |
| Max Drawdown ($) | $-221 |
| Max Drawdown (%) | 0.3% |
| Calmar Ratio | — |
| Total Trades | 3 |
| Data validity | INSUFFICIENT_DATA |


### DSR
Not computed — insufficient data (3 trades).


---

## Funnel Stability (pairs surviving per fold)

Folds with ≥ 3 surviving pairs: 5/24 (21%)

| Fold | Active Pairs | Pair Names |
|------|-------------|------------|
| 1 | 0 | — |
| 2 | 1 | BNB/NEAR |
| 3 | 2 | ADA/AVAX, BNB/NEAR |
| 4 | 0 | — |
| 5 | 0 | — |
| 6 | 1 | ADA/AVAX |
| 7 | 1 | ADA/AVAX |
| 8 | 1 | AVAX/OP |
| 9 | 0 | — |
| 10 | 1 | ATOM/OP |
| 11 | 1 | NEAR/OP |
| 12 | 2 | NEAR/OP, AVAX/DOT |
| 13 | 1 | NEAR/OP |
| 14 | 4 | ATOM/DOT, INJ/NEAR, ADA/DOGE, ADA/LINK |
| 15 | 0 | — |
| 16 | 3 | ATOM/DOT, NEAR/OP, ATOM/AVAX |
| 17 | 1 | ADA/DOGE |
| 18 | 0 | — |
| 19 | 1 | ATOM/DOT |
| 20 | 2 | DOT/NEAR, ADA/LDO |
| 21 | 2 | ADA/OP, ADA/INJ |
| 22 | 4 | ADA/LDO, AVAX/DOGE, ADA/OP, ADA/INJ |
| 23 | 4 | AVAX/DOGE, ADA/LDO, ADA/INJ, DOGE/INJ |
| 24 | 3 | AVAX/DOGE, DOGE/INJ, ADA/INJ |

---

## Per-Pair OOS Performance

| Pair | Folds Active | OOS Trades | OOS P&L | Mean Test Sharpe |
|------|-------------|-----------|---------|-----------------|
| DOT/NEAR | 1 | 1 | $175 | 3.503 ± — |
| NEAR/OP | 4 | 1 | $78 | 2.064 ± — |
| ADA/AVAX | 3 | 0 | $0 | — ± — |
| ADA/DOGE | 2 | 0 | $0 | — ± — |
| ADA/INJ | 4 | 0 | $0 | — ± — |
| ADA/LDO | 3 | 0 | $0 | — ± — |
| ADA/LINK | 1 | 0 | $0 | — ± — |
| ADA/OP | 2 | 0 | $0 | — ± — |
| ATOM/AVAX | 1 | 0 | $0 | — ± — |
| ATOM/DOT | 3 | 0 | $0 | — ± — |
| ATOM/OP | 1 | 0 | $0 | — ± — |
| AVAX/DOT | 1 | 0 | $0 | — ± — |
| AVAX/OP | 1 | 0 | $0 | — ± — |
| BNB/NEAR | 2 | 0 | $0 | — ± — |
| DOGE/INJ | 2 | 0 | $0 | — ± — |
| INJ/NEAR | 1 | 0 | $0 | — ± — |
| AVAX/DOGE | 3 | 1 | $-116 | -2.607 ± — |

---

## Correlation to TSMOM (Strategy A)


**Mean rolling 60-day correlation to TSMOM:** -0.079  ✅ Within target


---

## Root Cause Analysis: Why the Funnel Fails on 36-Month Data

The walk-forward uses an **expanding window** starting from May 2023. The funnel's
Stage 2 (`corr_logP > 0.85`) is computed over the full expanding training window.
This is correct and conservative — but it reveals a critical finding:

**The pairs-trading signal identified in feasibility is regime-specific.**

| Pair | corr_logP (full 36m) | corr_logP (recent 18m) | corr_logP (first 18m) |
|------|---------------------|------------------------|----------------------|
| DOT/NEAR | **0.670** ❌ | 0.954 ✅ | 0.584 ❌ |
| ATOM/OP  | 0.925 ✅ | 0.963 ✅ | 0.564 ❌ |

DOT/NEAR — the strongest feasibility pair (naive Sharpe 3.04) — has `corr_logP = 0.670`
over the full 36-month window, failing the 0.85 threshold. The 2023–mid 2024 BTC
dominance phase (BTC.D from 38% → 58%) drove massive altcoin divergence. During that
regime, DOT fell 62% while NEAR fell 51% — substantial divergence in log levels.

The expanding window correctly identifies that the strong 2024–2025 correlation is
**not a structural feature** of this pair, but rather a bull-market correlation regime.
When the training window encompasses a full cycle (bear + bull), the pair fails the
stage-2 filter, preventing deployment in the test period.

**This is the intended behavior of a rigorous out-of-sample test.**

### What the feasibility study measured

The feasibility study was (correctly) conducted on the most recent 18 months (Nov 2024
→ Nov 2025), which captured the tail of the bull market and the subsequent consolidation.
That period had unusually high cross-asset correlation among altcoins. The walk-forward
confirms this edge is not persistent across a full market cycle.

### Implication for strategy design

A production pairs-trading strategy on Hyperliquid would require:
1. **Regime detection**: only enter pairs when cross-asset correlation is in the
   "high correlation regime" (BTC dominance < 50%, or some explicit regime signal).
2. **Rolling (not expanding) funnel window**: use the most recent 12 months for
   correlation/cointegration tests, not the full expanding history. The expanding
   window design is appropriate for trend-following (TSMOM) but not for mean-reversion
   strategies where the relevant relationship is local, not historical.
3. Both options add significant complexity. Per our research protocol, these belong in
   a future design iteration — not bolted on to salvage this backtest.

---

## Methodology Notes

### Pre-registered hypothesis changes
- v2: ADF threshold 60%→40%; z_entry fixed at 2.0; data source Binance 36m
- v3: Rolling 12-month training window (final change — corrects to standard design)

### Cost model
- Fee: 0.035% × 2 legs × 2 sides = 0.14% round trip
- Slippage: 0.05% × 2 legs × 2 sides = 0.20% round trip
- **Total: 0.34% per round trip on notional**
- Funding cost: NOT modeled (known omission).

### Execution timing
Signal on bar t-1 close → position at bar t open.
Enforced via `.shift(1)` on Z-score signal.

---

## GO Criteria (ALL required)
- OOS Sharpe ≥ 1.0 after costs
- DSR ≥ 0.95
- MaxDD ≤ 30%
- Correlation to TSMOM < 0.3
- ≥ 3 pairs survive funnel in ≥ 70% of folds

## NO-GO Criteria (any one sufficient)
- OOS Sharpe < 0.5
- n_trades < 50 → INSUFFICIENT_DATA
- MaxDD > 50%
- All surviving pairs concentrated in one ecosystem

---

## Strategy B verdict: Not viable

**Reason:** After three progressively rigorous OOS tests (v1: 18m yfinance, v2: 36m
Binance expanding, v3: 36m Binance rolling), the strategy produced 3, 0, and 3 OOS
trades respectively — never reaching the 50-trade minimum for statistical inference.
With z_entry=2.0 (literature standard), the slow 72h mean-reversion signal generates
approximately 0.1 trades/pair/month, requiring ~500 pair-months to reach 50 trades.
Our universe and data length cannot support this.

**What was learned:**
1. The feasibility IC signal (DOT/NEAR IC=−0.234, naive Sharpe 3.04) is real within
   the 2024–2025 alt-coin bull market, but is regime-specific rather than structural.
2. A rigorous expanding/rolling OOS test correctly distinguishes regime-coincidence
   from persistent edge: pairs that look good in-sample fire too rarely out-of-sample.
3. Z-score mean-reversion at 72h horizon requires either a much larger universe
   (50+ pairs) or significantly lower z_entry (1.0–1.2σ), both of which introduce
   complexity or overfit risk beyond the scope of this feasibility protocol.

**Recommended next strategy:** Funding rate basis strategy (already partially explored
in `funding_backtest.py`). The funding rate signal has a natural trade frequency
(8-hourly settlements), does not require cointegration, and the edge (carry capture on
perpetuals) is structural rather than regime-dependent. Alternatively: weekend return
effect on crypto (documented anomaly, simple implementation).
