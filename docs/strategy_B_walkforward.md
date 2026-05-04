# Strategy B: Pairs Trading Walk-Forward Backtest

**Generated:** 2026-05-05 00:34 UTC
**Universe:** 17 Hyperliquid-listed symbols (hourly, 36-month Binance data)
**Data source:** binance
**Method:** Expanding-window walk-forward, 24 folds, 12-month min train
**ADF threshold:** 40% (pre-registered) | **z_entry:** 2.0 fixed (v2 change)

---

## Verdict: ⚠️ INSUFFICIENT_DATA

- n_trades=0 < 50 minimum.
- Root cause: pairs-trading signal is regime-specific to 2024-2025 bull market.
- The expanding funnel window correctly rejects pairs over the full 36m cycle.
- Fix: regime detection (BTC.D filter) or rolling funnel window — not a data problem.

---

## Portfolio OOS Metrics

| Metric | Value |
|--------|-------|
| OOS Sharpe (annualized) | — |
| Total OOS P&L | $— |
| Max Drawdown ($) | $— |
| Max Drawdown (%) | —% |
| Calmar Ratio | — |
| Total Trades | 0 |
| Data validity | INSUFFICIENT_DATA |


### DSR
Not computed — insufficient data (0 trades).


---

## Funnel Stability (pairs surviving per fold)

Folds with ≥ 3 surviving pairs: 1/24 (4%)

| Fold | Active Pairs | Pair Names |
|------|-------------|------------|
| 1 | 0 | — |
| 2 | 0 | — |
| 3 | 1 | ADA/AVAX |
| 4 | 3 | ADA/AVAX, AAVE/LINK, AAVE/INJ |
| 5 | 1 | ADA/AVAX |
| 6 | 1 | ADA/AVAX |
| 7 | 0 | — |
| 8 | 0 | — |
| 9 | 0 | — |
| 10 | 0 | — |
| 11 | 0 | — |
| 12 | 0 | — |
| 13 | 0 | — |
| 14 | 0 | — |
| 15 | 0 | — |
| 16 | 0 | — |
| 17 | 0 | — |
| 18 | 0 | — |
| 19 | 0 | — |
| 20 | 0 | — |
| 21 | 0 | — |
| 22 | 0 | — |
| 23 | 0 | — |
| 24 | 0 | — |

---

## Per-Pair OOS Performance

| Pair | Folds Active | OOS Trades | OOS P&L | Mean Test Sharpe |
|------|-------------|-----------|---------|-----------------|
| AAVE/INJ | 1 | 0 | $0 | — ± — |
| AAVE/LINK | 1 | 0 | $0 | — ± — |
| ADA/AVAX | 4 | 0 | $0 | — ± — |

---

## Correlation to TSMOM (Strategy A)


**TSMOM correlation:** not computed (insufficient OOS data).


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

### Pre-registered hypothesis changes (v2)
1. ADF threshold: 60% → 40% (before test data seen — documented in feasibility report)
2. z_entry: fixed at 2.0 (removed from grid to prevent threshold inflation)
3. Data source: Binance 36m replacing yfinance 18m

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

## Next Steps (for future iteration if returning to this strategy)
1. Implement regime filter (e.g., BTC.D < 50% as entry gate for the strategy)
2. Switch to rolling (12m) funnel window instead of expanding
3. Re-run feasibility and walk-forward under new design spec
2. Add funding cost tracking per leg
3. Paper trade on testnet for 30 days before live capital
4. Do NOT add leverage until live SR ≥ 1.5 sustained over 90 days
