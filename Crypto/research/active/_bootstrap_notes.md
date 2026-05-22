# Phase 0 Bootstrap Notes
*Generated: 2026-05-22 — Read: README.md, strategies/tsmom_v2_propfirm/, strategies/delta_neutral/, data/cache.py, Futures/research/active/nq_intraday/, Crypto/research/archived/, Portfolio/integration/, Portfolio/risk/*

---

## 1. Ten Lessons from Live and Archived Strategies

1. **Signal at T-1, trade at T — always.** The MLP (6.1) had 100% of BUY bars with Close > Open after correction. Enforce via `.rolling().sum().shift(1)`. Any IC computed at a different timing than the backtest trade is a methodology failure (6.9 vol-regime MR: intra-week IC ≠ Monday-open→Friday-close P&L).

2. **Crypto short side structurally fails.** Large-cap crypto losers mean-revert violently (6.3 CS L/S, 6.7 TSMOM×carry stack, 6.32 CS breakout). Long-only or delta-neutral only. Never bet against crypto losers in a cross-sectional long/short.

3. **Cost floor is 0.17% RT. At retail, only holds ≥ 7d survive.** Residual MR (6.11) had genuine IC (t=8.42) but 2-day mean-reversion completes too fast: 0.17% RT × 2 = 0.34% vs 0.85% mean return. LSTM 4h (6.23) had AUC=0.644 but 117 trades/yr × 0.17% = 19.95%/yr drag. Always compute `annual_cost = n_trades/yr × 0.17%` before proceeding.

4. **Carry signal requires delta-neutral execution.** Unhedged carry (6.5) produced Sharpe −0.68 because β_crypto (65% of P&L) dominated carry_frac (35%). Adding delta-neutral construction turned this into Strategy B (Sharpe 10.22). Same signal, opposite outcome depending on execution structure.

5. **Free-data crypto strategies are structurally exhausted.** After 53 crypto signals, three failure archetypes cover everything: (a) regime co-linear with TSMOM (corr > 0.4), (b) cost-inaccessible at retail fees, (c) mean-reversion against momentum (sentiment = momentum proxy). Only XGBoost CS (6.21, Sharpe 0.734) escaped TSMOM co-linearity.

6. **HAC standard errors collapse significance.** Multi-asset TSMOM went from OLS t=2.4 → HAC t=1.31 (not significant). Excess returns subtraction cost 3 Sharpe points. All future alpha t-stats use `sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})`. Plain OLS is inadmissible.

7. **Funding and basis spikes are momentum proxies, not dislocation indicators.** Extreme funding reversal (6.35): IC at 7d = −4.19, meaning extreme positive funding → price CONTINUES UP. Perp-spot basis (6.36): PF=0.955, avg hold=1d, basis amplitude 0.05% vs 0.17% RT cost. Both confirm: in crypto, sentiment indicators predict continuation, not reversal.

8. **Walk-forward instability kills research-grade strategies.** Vol-squeeze breakout (6.27) WF: 2023 +0.689, 2024 +0.087, 2025 −1.09 (BTC). Monthly TSMOM (6.33) WF: 2020 +1.21, 2021 −0.85, 2023 +0.61, 2024 +0.08. Must see ≥50% positive WF windows AND no recent deterioration trend.

9. **ETF proxies ≠ direct futures — roll drag destroys commodity TSMOM.** HOP 2017 produces Sharpe on direct futures; USO/UNG/SLV embed negative roll yield in contango, turning Sharpe 0.39 from a structurally sound mechanism (5e). Any strategy using ETF proxies for futures-driven returns must validate data source compatibility.

10. **Universe ≥ 30 perps and individual asset verification is mandatory.** AdaptiveTrend (6.31) on top-30 by HL volume added noise (HYPE, FARTCOIN, VVV unavailable on Binance); XGBoost CS worked on a curated 10-asset universe. When going to ≥30, screen for Binance ADV > $50M and ≥2 years of continuous history. Small N (< 30 instruments in CS, < 100 trades total) is insufficient for statistical inference.

---

## 2. Three Recurring Failure Patterns to Avoid

### Pattern A — Feasibility-Backtest Timing Mismatch
**The trap**: IC is computed at one time granularity, backtest trades at a different one.
**Example**: 6.9 vol-regime MR — feasibility IC measured intra-week rank correlation (IC=0.344, t=9.45, PASS); backtest measured Monday-open→Friday-close P&L (Sharpe −0.85, FAIL). The IC horizon and execution horizon were different.
**Prevention**: The signal→outcome pair must be identical at feasibility and backtest: same look-forward period, same entry/exit price, same lag structure. Write both in the same `compute_signal()` function and validate that IC uses the same `.shift(1)` as the backtest does.

### Pattern B — Retail Cost Inaccessibility (n_trades × fee > gross return)
**The trap**: Genuine IC / AUC but strategy requires too-frequent trading at 0.17% RT.
**Examples**: LSTM 4h (6.23, AUC=0.644 → 19.95%/yr cost drag), Residual MR (6.11, IC t=8.42 → 2-day hold → 0.34% RT destroys edge), Funding MR (6.2, income $4/trade vs $22/trade fees).
**Prevention**: Before running a full backtest, compute: `cost_breakeven_gross_return = n_expected_trades_per_year × 0.17%`. If > 5% annualized, the hold period must be ≥ 7 days. For daily-rebalancing cross-sectional strategies on 30 assets with ~60% monthly turnover: `turnover × 0.17% × 12 ≈ 12%/yr drag minimum`. Signal must overcome this.

### Pattern C — Sentiment/Dislocation Indicator is Actually Momentum Proxy
**The trap**: Contrarian hypothesis fails because the "dislocation" signal is co-linear with trend.
**Examples**: Extreme funding reversal (6.35, IC t=−4.19 at 7d — wrong direction); Perp-spot basis MR (6.36, PF=0.955, IC negative); Crash recovery dip-buying (6.34, post-crash mean −0.131% < unconditional 0.384%); MVRV proxy (6.28, corr(MVRV, TSMOM)=+0.40 — both high in bull markets); USDT flow proxy (6.26, IC t=−0.38, corr(TSMOM)=0.616 — volume IS momentum).
**Prevention**: For any contrarian hypothesis, first verify IC direction is positive (long when signal says dip). A negative IC at t=3/5/7d confirms wrong mechanism before any backtest. Check `corr(signal, BTC_return_28d)` — if > 0.3, it's a momentum proxy, not a contrarian signal.

---

## 3. Code Conventions Confirmed

**Module header**:
```python
"""
<module>.py — <short description>
==================================
<extended description>

Usage:
    python -m Crypto.research.active.<slug>.<module>
"""
from __future__ import annotations
```

**Constants**: Named at module top, SCREAMING_SNAKE_CASE. No magic numbers inline.
```python
COST_RT      = 0.0017        # 0.17% round-trip taker + slippage
LOOKBACK_DAYS = 28
BARS_PER_YEAR = 365
```

**Type hints**: Everywhere on public functions. Return type on every function.

**NumPy-style docstrings** on public functions with Parameters, Returns, Notes sections (see `data/cache.py` as canonical example).

**Seeds**: `rng = np.random.default_rng(42)` for bootstraps. `np.random.seed(42)` where required by third-party libs (XGBoost etc).

**Logging**: `log = logging.getLogger(__name__)` per module. No bare `print()` in library code.

**Signal look-ahead prevention**:
```python
# rolling(L).sum() at t covers [t-L+1 : t]; shift(1) → [t-L : t-1]
signal = log_returns.rolling(LOOKBACK_DAYS).sum().shift(1)
```

**HAC standard errors**:
```python
reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
lrv = float(reg.cov_params().iloc[0, 0]) * n
hac_std = np.sqrt(max(lrv, 1e-24))
sharpe_hac = mean / hac_std * np.sqrt(252)
```

**results.json**: Keyed by `iteration` string (e.g. `"iter_01"`), updated via `append_result(result)` from engine module. Fields: `iteration`, `n_tests`, `description`, `sharpe_daily_hac`, `max_dd_pct`, `wf_pct_positive`, `verdict`.

**Iteration numbering**: `iter_01.py`, `iter_02.py`, ... max 3 post-v1 modifications. Each file is self-contained, imports from `engine.py`.

**Verdict strings**: `"IMPROVE"`, `"WEAK"`, `"RESEARCH_PASS"`, `"PROPFIRM_PASS"`, `"SKIP"`, `"ARCHIVE"`.

**Test functions**: Unit tests on `compute_signal()`, PnL accounting, vol-targeting logic. Keep in `tests/` subfolder or at bottom of engine under `if __name__ == "__main__"` guard.

**File structure** (strictly follow):
```
Crypto/research/active/<strategy_slug>/
├── HYPOTHESIS.md
├── engine.py
├── data_loader.py
├── iter_01.py     ← baseline
├── iter_02.py     ← modification 1 (max 3 post-v1)
├── iter_03.py     ← modification 2
├── walk_forward.py
├── analysis/
│   ├── ic_feasibility.py
│   ├── regime_conditional.py
│   ├── sensitivity_grid.py
│   ├── deflated_sharpe.py
│   ├── bootstrap_ci.py
│   └── correlation_vs_A_B.py
├── live/
│   ├── compute_signal.py
│   ├── paper_logger.py
│   └── reconcile.py
├── plots/
├── results.json
└── DECISION.md
```

---

## 4. Data Infrastructure Available and Reusable

**`data/cache.py`** — MANDATORY reuse:
- `get_cached_or_fetch(ticker, start, end, interval, source='yfinance', max_age_days=1.0)` → DataFrame
  - Keyed by hash of (ticker, start, end, interval, source) → `data/raw/yf_{ticker}_{interval}_{hash}.parquet`
  - Metadata in `data/metadata/yf_{ticker}_{interval}_{hash}.json`
  - Cache invalidates after `max_age_days` (set to 30+ for historical data)
- `load_nq_1min()` → NQ 1-min DataFrame (NQ-specific, not needed for crypto)
- Pattern to extend: add `get_cached_or_fetch_binance()` for Binance futures API (follows same parquet pattern)

**Already cached locally** (`data/raw/`):
- NQ 1-min parquet (Dec 2022 → Dec 2025)
- Multiple yfinance ETF/equity parquets from multi-asset/FX/equity research

**Funding data** (`data/funding_carry/`):
- CSV files per asset: `{ASSET}_funding.csv` with `timestamp`, `funding_rate_1h` columns
- Available: TST, MEGA, WLD, STX, BIO, TRUMP, HMSTR (from Strategy B)
- HL API: `GET https://api.hyperliquid.xyz/info` with `{"type": "fundingHistory", "coin": "{asset}", "startTime": ts_ms}`

**Binance futures OHLCV**:
- `python-binance` or direct REST: `GET https://fapi.binance.com/fapi/v1/klines?symbol={asset}USDT&interval=1d&limit=1000`
- No auth required for public endpoints
- Must extend `get_cached_or_fetch` to support Binance futures source

**Universe** (≥30 perps, ADV > $50M):
- Top 30+ by HL 24h volume: BTC, ETH, SOL, BNB, XRP, DOGE, ADA, AVAX, DOT, LINK, UNI, ATOM, ETC, XLM, LTC, BCH, FIL, MATIC, APT, ARB, OP, INJ, SUI, TIA, NEAR, TON, WIF, JUP, PYTH, SEI, AAVE, CRV, COMP
- Must filter on Binance futures listing + ADV > $50M at time of research
- Available from HL info API: `{"type": "metaAndAssetCtxs"}` returns all perp metadata + 24h volume

**Strategy A/B returns** (for correlation computation):
- Strategy A: `strategies/tsmom_v2_propfirm/` — rerun backtest on historical prices to get daily returns
- Strategy B: `strategies/delta_neutral/backtest.py` — produces 8h funding returns, resample to daily
- Portfolio/risk/correlation.py: loads and aligns both return series for correlation analysis

---

## 5. Three Pre-Selected Research Angles

### Angle 1 — Open Interest Cross-Sectional Momentum (OI-MOM)
**Economic mechanism**: Change in open interest reflects new capital commitment, not price-return momentum. OI growth = informed demand flowing into an asset (new longs AND new shorts add to OI). Cross-sectional OI growth z-score captures which assets are receiving new capital flows independent of where prices are going.
**Why distinct from TSMOM**: TSMOM uses cumulative log return as signal. OI can grow during downtrends (new shorts entering), making OI-MOM structurally orthogonal to price-momentum. In commodity markets (Bessembinder et al.), OI growth predicts positive risk-adjusted returns — informed traders preferentially enter high-conviction positions.
**Hypothesis**: Assets in top-quartile by 7d OI growth z-score outperform bottom-quartile over 7-14d forward window, net of costs.
**Data**: Binance futures `/fapi/v1/openInterest` historical endpoint + HL `metaAndAssetCtxs`. Free, high quality.
**Correlation expectation**: Low with TSMOM (OI orthogonal to price direction). Low with carry (funding level vs OI flow are different signals).
**Failure condition**: If OI growth z-score IC < 0.02 at 7d, fail GATE 2.
**Key risk**: OI is partially co-linear with price momentum in trend markets (OI rises with uptrends). Must check sub-period stability (bull 2024 vs bear 2022).

### Angle 2 — Cross-Sectional Realized Skewness Premium
**Economic mechanism**: Kumar (2009), Bali, Cakici & Whitelaw (2011): investors overweight positively-skewed assets (lottery preference), bidding them up and producing subsequent underperformance. Short high-positive-skew assets (lottery demand premium), long low-skew/negative-skew assets.
**Why distinct from TSMOM**: Realized skewness of returns is orthogonal to cumulative return direction. A trending asset can have low skew (many small wins, few large losses). A reversing asset can have high positive skew (one large spike return). The signal captures distribution shape, not direction.
**Hypothesis**: Assets in top-quartile by 30d realized skewness produce negative alpha (overpriced lottery demand), bottom-quartile produce positive alpha. Long-only: buy bottom-quartile skewness assets.
**Data**: Computable from free daily OHLCV (already cached for Binance universe). Skewness = standardized third moment over rolling 30-day window.
**Correlation expectation**: Should be orthogonal to TSMOM and carry by construction.
**Failure condition**: IC (skewness rank → 7d forward return rank, negatively coded) < 0.02, fail GATE 2.
**Key risk**: Skewness is noisy at daily frequency over 30d windows (few data points). May need 60d window to stabilize estimate, reducing signal freshness.

### Angle 3 — HL Native Liquidation Signal (LIQ-CS)
**Economic mechanism**: Hyperliquid reports real-time liquidations via API. When a large liquidation event occurs on a specific asset (large notional of positions forcibly closed by the exchange), the sudden supply/demand shock creates temporary mispricing — prices overshoot in the direction of liquidation. The recovery from this overshoot creates a predictable edge if entered at the right timing.
**Why distinct from TSMOM and crash recovery (6.34)**: 6.34 used price drops as the signal — which are correlated with TSMOM. LIQ-CS uses the actual liquidation volume/notional as the signal, not the price drop. Liquidations can happen in up-trending markets too (short squeezes liquidating short positions). Cross-sectional: rank assets by recent liquidation intensity, trade mean-reversion from the most-liquidated assets.
**Hypothesis**: Assets in top-quintile by 24h liquidation volume z-score exhibit excess mean-reversion over 3-7d forward window, outperforming assets with low liquidation activity.
**Data**: HL `/info` API with `{"type": "liquidations"}` or via WebSocket. Free, HL-native data not available elsewhere.
**Correlation expectation**: Should be orthogonal to TSMOM (liquidations happen in both directions, not just crashes). Orthogonal to carry (funding rate is independent of liquidation events).
**Failure condition**: IC at 3d or 5d < 0.02 (note shorter hold needed given event-driven nature), fail GATE 2. Check cost arithmetic first: must confirm >7d holds survive at 0.17% RT, or that enough trades per asset exist to offset execution costs.
**Key risk**: Liquidation data availability — HL API may not provide sufficient historical depth (< 2 years) or granularity. Will verify in PHASE 2 data collection.

---

## 6. Gates and Constraints Summary (Quick Reference)

| Gate | Metric | Threshold |
|------|--------|-----------|
| RESEARCH_PASS | Sharpe HAC | > 0.7 |
| RESEARCH_PASS | MaxDD | > −25% |
| RESEARCH_PASS | Walk-forward % positive | ≥ 50% |
| PROPFIRM_PASS | Sharpe HAC | > 1.0 |
| PROPFIRM_PASS | MaxDD | > −10% |
| PROPFIRM_PASS | Walk-forward % positive | ≥ 60% |
| Orthogonality | corr(new, A) | < 0.3 |
| Orthogonality | corr(new, B) | < 0.3 |
| GATE 2 | IC mean (7d, HAC) | > 0.02 and p < 0.10 |

**Costs**: 0.17% RT (crypto taker + slippage). Funding modeled per-position.
**n_tests cumulative**: **142** (from NQ intraday results.json iter_10 as of May 2026 — use this for AMTP/DSR calculation).
**Vol target**: 10% annualized (EWMA, cap 2× leverage per asset).
**Universe**: ≥ 30 perps, Binance ADV 30d > $50M, ≥ 2yr history (2024-01 → 2026-05 minimum).
**Walk-forward config**: 18m train / 6m test, step 3m (rolling).

---

## GATE 0 STATUS: COMPLETE

All 7 bootstrap sections read and internalized. Bootstrap notes produced with all 5 required deliverables:
- ✅ 10 lessons from live + archived strategies
- ✅ 3 recurring failure patterns (timing mismatch, cost inaccessibility, sentiment=momentum)
- ✅ Code conventions confirmed (type hints, NumPy docstrings, shift(1), HAC, results.json)
- ✅ Data infra catalogued (cache.py mandatory, Binance futures + HL API, parquet patterns)
- ✅ 3 research angles: OI-MOM, Realized Skewness Premium, HL Liquidation Signal

**Awaiting "GO PHASE 1" to begin hypothesis selection and literature scan.**
