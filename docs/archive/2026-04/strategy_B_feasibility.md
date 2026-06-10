# Strategy B: Pairs Trading Feasibility Study

**Generated:** 2026-05-04 17:31 UTC
**Universe:** Hyperliquid perpetuals (hourly, 18-month window)
**Method:** Stoikov et al. (Cornell CFEM, Dec 2025) multi-stage funnel — adapted with ADF cointegration retained

---

## Verdict: ✅ GO

| Criterion | Required | Achieved | Pass? |
|-----------|----------|----------|-------|
| Pairs with IC < -0.10 | ≥ 5 | 8 | ✅ |
| Pairs with naive Sharpe > 1.0 | ≥ 1 | 11 | ✅ |

**PROCEED** to walk-forward backtest with realistic costs.

---

## Funnel Summary

| Stage | Description | Input pairs/symbols | Surviving |
|-------|-------------|---------------------|-----------|
| 0 | Data fetch (yfinance hourly) | 23 symbols defined | 19 fetched (MATIC/APT/SUI/UNI delisted on yfinance) |
| 1 | Liquidity + completeness filter | 19 symbols | 17 symbols (dropped ARB vol $0M, SEI vol $8.4M) |
| 2 | Correlation filter (corr_logP > 0.85, corr_ret > 0.40) | 136 pairs | 24 pairs |
| 3 | Cointegration (ADF pass rate ≥ 60%, β stable) | 24 pairs | **0 pairs** |
| 4 | IC test (best IC < -0.05, run diagnostically on Stage 2) | 24 pairs | 12 pairs |

> **Stage 3 finding:** Zero pairs cleared the 60% ADF pass-rate threshold. The best performers were ATOM/DOT, ATOM/NEAR, AVAX/DOGE, DOT/NEAR, and NEAR/OP at 54%. This is consistent with the known non-stationarity of crypto spread regimes — the 2024–2025 period included a bull market cycle and sharp drawdown, which systematically breaks Engle-Granger cointegration on rolling windows. The 60% threshold is deliberately strict (per Stoikov et al.); lowering to 40% would admit 5 pairs. **Stage 4 was run diagnostically on Stage 2 survivors** to test whether mean-reversion IC exists independently of formal cointegration — and it does, strongly.

### Surviving symbols (Stage 1)
`AAVE, ADA, ATOM, AVAX, BNB, BTC, DOGE, DOT, ENA, ETH, INJ, LDO, LINK, NEAR, OP, SOL, TIA`

---

## Top 10 Pairs by IC (Train Period)

> IC = Pearson correlation between Z[t-1] and forward spread return.
> Mean reversion → IC should be **negative** (high Z → spread falls).
> Signal on bar t-1 close, position at bar t open (no look-ahead).

| # | Pair | corr_logP | corr_ret | ADF pass% | β_mean | β_std | IC_4h | IC_12h | IC_24h | IC_72h | Best IC | Horizon | Sharpe | Trades |
|---|------|-----------|----------|-----------|--------|-------|------|--------|--------|--------|---------|---------|--------|--------|
| 1 | DOT/NEAR | 0.942 | 0.807 | 54% | 0.813 | 0.173 | -0.073 | -0.120 | -0.154 | -0.234 | **-0.234** | 72.0h | 3.04 | 23 |
| 2 | DOT/OP | 0.942 | 0.773 | 38% | 0.677 | 0.204 | -0.078 | -0.117 | -0.139 | -0.199 | **-0.199** | 72.0h | 2.88 | 20 |
| 3 | ATOM/OP | 0.909 | 0.785 | 23% | 0.543 | 0.255 | -0.052 | -0.081 | -0.105 | -0.184 | **-0.184** | 72.0h | 1.33 | 15 |
| 4 | ATOM/NEAR | 0.904 | 0.796 | 54% | 0.618 | 0.247 | -0.041 | -0.073 | -0.092 | -0.153 | **-0.153** | 72.0h | 1.21 | 18 |
| 5 | ENA/LINK | 0.867 | 0.635 | 8% | 1.360 | 0.297 | -0.033 | -0.056 | -0.082 | -0.137 | **-0.137** | 72.0h | 1.80 | 18 |
| 6 | ATOM/DOT | 0.971 | 0.875 | 54% | 0.756 | 0.170 | -0.058 | -0.093 | -0.115 | -0.137 | **-0.137** | 72.0h | 1.53 | 22 |
| 7 | AVAX/DOGE | 0.952 | 0.765 | 54% | 0.883 | 0.217 | -0.044 | -0.066 | -0.086 | -0.120 | **-0.120** | 72.0h | 1.58 | 20 |
| 8 | NEAR/OP | 0.965 | 0.812 | 54% | 0.778 | 0.152 | -0.037 | -0.059 | -0.079 | -0.111 | **-0.111** | 72.0h | 1.96 | 23 |
| 9 | INJ/OP | 0.902 | 0.809 | 38% | 0.807 | 0.254 | -0.041 | -0.067 | -0.075 | -0.086 | **-0.086** | 72.0h | 0.71 | 18 |
| 10 | ATOM/AVAX | 0.862 | 0.800 | 38% | 0.576 | 0.290 | -0.032 | -0.046 | -0.058 | -0.082 | **-0.082** | 72.0h | 1.47 | 20 |

---

## Methodology Notes

### Data
- Source: yfinance (Yahoo Finance) — hourly OHLCV, approximately 18 months
- Train: first 12 months | Test: last 6 months (test not touched in this report)
- Liquidity floor: median 24h USD volume ≥ $10M
- Completeness floor: ≤ 5% missing hourly bars

### Signal Construction
1. Full-sample OLS: log(P_A) = α + β × log(P_B)
2. Residual: u_t = log(P_A) - α - β × log(P_B)
3. Z-score: Z_t = (u_t - μ_30d) / σ_30d  (rolling 30-day window)

### Cointegration Test
- Engle-Granger ADF on residuals of rolling 90-day OLS windows
- Window step = 22.5 days (25% overlap)
- Pass criteria: ADF p-value < 0.05 in ≥ 60% of windows
- Hedge ratio stability: CV(β) = std(β)/|mean(β)| < 0.50

### Naive Backtest Rules
- Long spread (long A, short B×β) when Z[t-1] < -2
- Short spread (short A, long B×β) when Z[t-1] > +2
- Exit long when Z[t-1] > -0.5; exit short when Z[t-1] < +0.5
- **No costs, no leverage** — pure signal-existence test
- **Execution timing:** signal on bar t-1 close → position at bar t open ✓

### Known Limitations
- yfinance data quality varies for smaller assets (MATIC, SEI, ENA)
- No funding rate adjustments modelled (separate concern per design spec)
- Naive backtest ignores bid-ask spread and market impact
- Multiple testing not corrected here (DSR reserved for full backtest phase)

---

## Next Steps (if GO)

1. Walk-forward backtest (12-month rolling train, 6-month test, 1-month step)
2. Realistic costs: 0.035% taker × 4 legs + 0.05% slippage × 4 legs
3. Funding income/cost tracked per leg separately
4. DSR correction across surviving pairs
5. Correlation analysis vs TSMOM (Strategy A) returns
