# Signal Stack Research: TSMOM × Funding Carry

**Generated:** 2026-05-05 UTC
**Universe:** 48–143 Hyperliquid perpetuals (≥180 days history, expanding)
**Walk-forward:** 12m train / 1m test, 23 folds
**Rebalance:** Weekly (21 × 8h bars)
**Baseline:** Standalone cross-sectional TSMOM (28d lookback, vol-scaled, top/bottom quintile)

---

## Hypothesis

TSMOM identifies price trend direction; cross-sectional carry rank identifies crowded positioning
(high positive funding = longs paying heavily = crowded long). Combining should yield:
- Higher precision on longs (trend + flow alignment)
- Lower directional risk on shorts (avoid shorting into consensus longs with momentum)
- Net: higher Sharpe than either signal alone

---

## Methods Tested

### Method 1 — Intersection (Hard Gate)
- **Long**: TSMOM > 0 AND carry_rank < 0.20 (most negative funding, least crowded long)
- **Short**: TSMOM < 0 AND carry_rank > 0.80 (most positive funding, most crowded)
- Equal-weight within each leg. May have fewer positions than standalone.

### Method 2 — Multiplicative Score
- **Score**: `tsmom_signal × (−carry_rank_pct + 0.5) × 2`
- High score = strong positive momentum + anti-crowded = long candidate
- Long top quartile, short bottom quartile by score. Equal-weight.

### Standalone TSMOM (Baseline)
- Cross-sectional rank by TSMOM score (vol-scaled 28d return)
- Long top quintile, short bottom quintile. Equal-weight.
- Expected OOS Sharpe: ~1.41 (per prior TSMOM backtest on BTC+SOL, adjusted for cross-sectional)

---

## OOS Results Summary

| Method | Total Net P&L | Sharpe (weekly) | vs Standalone |
|--------|---------------|-----------------|---------------|
| Method 1: Intersection | $-4,786 | -0.330 | +0.056 |
| Method 2: Multiplicative | $-10,140 | -1.746 | -1.361 |
| Standalone TSMOM | $-2,765 | -0.385 | — |

---

## Correlation Between Methods

| Pair | Correlation |
|------|-------------|
| Method 1 vs Standalone | -0.010 |
| Method 2 vs Standalone | -0.206 |
| Method 1 vs Method 2 | 0.086 |

---

## Method Selection (Train Period)

| Method Selected | % of Folds |
|-----------------|-----------|
| Method 1 | 78% |
| Method 2 | 22% |

---

## Conclusion

**Hypothesis PARTIALLY confirmed.** Method 1 (Intersection) achieves OOS Sharpe -0.33, improving over standalone TSMOM (-0.39) by +0.06, but below the 1.41 GO threshold.

---

## GO Criteria Assessment

| Criterion | Required | Result | Pass? |
|-----------|----------|--------|-------|
| Best combined Sharpe > standalone | > 1.41 | -0.330 | ❌ |
| Correlation to standalone | Any | -0.010 | — |
| Hypothesis validated | combined > 1.41 | -0.33 (fails) | ❌ |

---

## Methodology Notes

### TSMOM Signal Construction
- Lookback: 84 × 8h bars (28 days)
- Vol-scaling: 15% annual target, vol = pct_change(1).rolling(84).std() × √(3×365)
- Signal: sign(ret_84) × 0.15 / vol_84, clipped at ±3
- No look-ahead: signal at bar T uses prices from bars T-84 through T-1

### Carry Signal Construction
- 8h funding rate: hourly funding resampled to 8h (sum per period)
- Rolling 3-period mean cross-sectional rank (pct=True, 0→1)
- High rank (→1) = high positive funding = crowded longs = short candidate in Method 1
- No look-ahead: signal at bar T uses funding from bars T-3 through T-1

### Walk-Forward Protocol
- Fold structure: 12m rolling train, 1m test
- Asset universe per fold: assets with any price data before fold train_start (survival bias control)
- Method selection: Methods 1 & 2 compete on train Sharpe; selected method frozen on test
- Standalone TSMOM always run on test for direct comparison (no selection needed)
- Cost: 0.17% per leg (0.035% taker + 0.05% slippage) × 2 sides = 0.34% round-trip on turnover

### Per-Fold Results
 fold test_start   test_end  n_assets best_method  train_sharpe
    1 2024-05-12 2024-06-12        48     method1          0.20
    2 2024-06-12 2024-07-12        50     method1         -0.11
    3 2024-07-12 2024-08-12        51     method1         -1.32
    4 2024-08-12 2024-09-12        54     method1          0.46
    5 2024-09-12 2024-10-12        56     method1         -1.18
    6 2024-10-12 2024-11-12        59     method1         -1.23
    7 2024-11-12 2024-12-12        69     method1         -0.50
    8 2024-12-12 2025-01-12        75     method1         -1.13
    9 2025-01-12 2025-02-12        82     method2         -0.68
   10 2025-02-12 2025-03-12        88     method1         -0.13
   11 2025-03-12 2025-04-12        90     method2         -0.43
   12 2025-04-12 2025-05-12        96     method2         -0.79
   13 2025-05-12 2025-06-12       100     method2          0.48
   14 2025-06-12 2025-07-12       104     method1         -0.53
   15 2025-07-12 2025-08-12       107     method2         -0.99
   16 2025-08-12 2025-09-12       108     method1         -1.71
   17 2025-09-12 2025-10-12       108     method1         -1.14
   18 2025-10-12 2025-11-12       111     method1          0.44
   19 2025-11-12 2025-12-12       118     method1          0.68
   20 2025-12-12 2026-01-12       125     method1         -0.08
   21 2026-01-12 2026-02-12       132     method1         -1.39
   22 2026-02-12 2026-03-12       141     method1         -0.87
   23 2026-03-12 2026-04-12       143     method1         -0.27
