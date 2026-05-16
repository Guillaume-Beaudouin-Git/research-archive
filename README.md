# Algo_claude — Research Journal

**Last updated**: May 16, 2026  
**Status**: 2 strategies live on Propr testnet (TSMOM v2 + delta-neutral carry), 15 strategies tested and failed/shelved, 2 recent studies (temporal patterns + LSTM 4h) → SKIP

---

## 1. Project Overview

This repo is a solo algorithmic trading research project targeting crypto perpetuals. The goal is to find strategies with genuine statistical edge that can survive realistic costs (0.34% RT on Hyperliquid) and pass the Propr challenge (10% profit target, 6% max drawdown, 3% daily drawdown limit).

**Research philosophy**: negative results documented with the same rigor as positive ones, DSR used to correct for multiple testing, all backtests walk-forward validated before any live deployment.

**Timeline**:
- Early 2026: MLP/OHLCV baseline (failed, look-ahead bias)
- Feb–Mar 2026: 9 more strategies tested and failed (strategies 4.2–4.11)
- Mar 2026: TSMOM v2 developed and deployed to Propr testnet
- Apr 2026: Delta-neutral carry deployed to Propr testnet
- May 2026: Meta-labeling (SKIP), HMM regime detection (WEAK), strategy B2 live

---

## 2. Repository Structure

```
Algo_claude/
│
├── README.md                        ← this file (permanent research journal)
├── STRATEGY_RESEARCH_LOG.md         ← strategy log (now superseded by this file)
├── monitor.py                       ← daily P&L attribution dashboard
├── run_delta_neutral.sh             ← launch delta-neutral live loop
│
├── # ── ROOT-LEVEL RESEARCH SCRIPTS ──────────────────────────────────────
├── str_feasibility.py               ← Short-term reversal feasibility (failed)
├── str_ic_rolling.png               ← STR rolling IC chart
├── vol_regime_mr_feasibility.py     ← Vol-regime mean reversion feasibility (failed)
├── vol_regime_mr_backtest.py        ← Vol-regime backtest (failed)
├── vol_regime_equity_curve.png      ← Vol-regime equity curve
├── vol_regime_ic.png                ← Vol-regime IC chart
├── fg_contrarian_feasibility.py     ← Fear & Greed contrarian feasibility (failed)
├── fg_contrarian_equity.png         ← F&G equity chart
├── residual_mr_feasibility.py       ← BTC-neutral residual MR feasibility (failed)
├── residual_mr_backtest.py          ← Residual MR backtest (failed)
├── residual_mr_equity.png           ← Residual MR equity curve
├── residual_mr_folds.png            ← Residual MR walk-forward folds
├── residual_mr_ic.png               ← Residual MR IC chart
│
├── # ── EARLY MLP PIPELINE (DEPRECATED) ─────────────────────────────────
├── config.py                        ← MLP hyperparameters (deprecated)
├── features.py                      ← MLP feature engineering (deprecated)
├── labeler.py                       ← 3-class label generator (deprecated)
├── model.py                         ← PyTorch MLP (deprecated)
├── trainer.py                       ← Training pipeline (deprecated)
├── train_and_save.py                ← Model serializer (deprecated)
├── live_trader.py                   ← MLP daily cron (deprecated)
├── hyperliquid_client.py            ← Hyperliquid SDK wrapper (deprecated)
├── notifier.py                      ← Telegram alerts (deprecated)
├── backtest.py                      ← MLP backtester (deprecated)
├── dsr.py                           ← DSR implementation (deprecated)
├── oos_eval.py                      ← OOS evaluation (deprecated)
├── walk_forward.py                  ← Walk-forward validation (deprecated)
├── main.py                          ← MLP research pipeline (deprecated)
├── sanity_check.py                  ← MLP smoke test (deprecated)
├── test_live_dryrun.py              ← MLP integration tests 7× (deprecated)
├── packages.py                      ← Dev-time pip bootstrap (deprecated)
├── requirements.txt                 ← Pinned dependencies
│
├── # ── STRATEGIES ────────────────────────────────────────────────────────
├── strategies/
│   │
│   ├── # ── LIVE: TSMOM v2 on Propr ──────────────────────────────────────
│   ├── tsmom_v2_propfirm/
│   │   ├── config.py                ← VIABLE_ASSETS (mainnet volume filter), thresholds
│   │   ├── daily_summary.py         ← Daily P&L / regime summary email
│   │   ├── tsmom_strategy.py        ← Signal computation: 28d momentum + vol scalar
│   │   ├── tsmom_backtest.py        ← Walk-forward backtester (confirmed no look-ahead)
│   │   ├── tsmom_live.py            ← Deprecated live runner (replaced by execution/)
│   │   └── execution/
│   │       ├── __init__.py          ← ASSET_MAP, REVERSE_ASSET_MAP, ORDERS_DB_PATH, BASE_URL
│   │       ├── propr_sdk.py         ← ProprClient SDK (market_buy/sell, close_position, etc.)
│   │       ├── order_executor.py    ← place_market_order, cancel_order, get_positions, flatten_all
│   │       ├── rebalance.py         ← run_weekly_rebalance() with 90% capital cap
│   │       ├── guardrail_loop.py    ← Equity guardrail daemon (⚠️ see Section 5)
│   │       ├── equity_monitor.py    ← Propr equity polling via REST
│   │       ├── run_rebalance.py     ← Entry point: starts guardrail, calls rebalance, exits
│   │       └── tests/
│   │           ├── test_execution.py ← 6-test integration suite for execution layer
│   │           └── orders.db        ← SQLite order log (runtime artefact)
│   │   ├── README.md                ← Strategy B2 documentation
│   │   ├── docs/
│   │   │   ├── strategy_B2_backtest.md      ← Detailed backtest results
│   │   │   ├── strategy_B_feasibility.md    ← Original feasibility study
│   │   │   └── strategy_stack_research.md   ← Signal stacking research
│   │
│   ├── # ── LIVE: Delta-Neutral Carry ────────────────────────────────────
│   ├── delta_neutral/
│   │   ├── live_trader.py           ← Delta-neutral live loop (Binance + Hyperliquid)
│   │   └── backtest.py              ← Delta-neutral backtester
│   │
│   ├── # ── RESEARCH: Meta-Labeling on TSMOM ─────────────────────────────
│   ├── meta_tsmom/
│   │   ├── __init__.py
│   │   ├── feasibility.py           ← XGBoost meta-model (AUC 0.63, DSR=0.00, SKIP)
│   │   └── deep_analysis.py         ← 6-investigation deep dive (post-2023 PROMISING)
│   │
│   ├── # ── RESEARCH: HMM Regime Detection ───────────────────────────────
│   ├── regime_hmm/
│   │   ├── __init__.py
│   │   └── feasibility.py           ← 3-config HMM study (Config A best, WEAK verdict)
│   │
│   ├── # ── DEPRECATED STRATEGY RESEARCH ─────────────────────────────────
│   ├── intraday_tsmom/
│   │   └── feasibility.py           ← Intraday TSMOM study (archived)
│   ├── market_neutral/
│   │   └── feasibility.py           ← Market-neutral study (archived)
│   ├── orb_crypto/
│   │   └── feasibility.py           ← Opening range breakout study (archived)
│   ├── mlp_tsmom/
│   │   └── feasibility.py           ← MLP + TSMOM hybrid study (archived)
│   ├── funding_carry/               ← Unhedged carry research (failed)
│   └── signal_stack/                ← TSMOM × carry stack research (failed)
│
├── docs/                            ← Archived feasibility documents
└── model_store/                     ← Trained MLP artefacts (gitignored)
```

---

## 3. Infrastructure

### VPS
- **Provider**: Hetzner CX22 (2 vCPU, 4 GB RAM, 40 GB SSD, €4.35/month)
- **OS**: Ubuntu 22.04 LTS
- **Python**: 3.11 venv at `/opt/venv`
- **Working directory**: `/opt/algo_claude`
- **Cron**: systemd-managed; logs to `/var/log/algo/`

### Running the live strategy

```bash
# Trigger a weekly rebalance (Propr TSMOM v2):
cd /opt/algo_claude
PROPR_API_KEY="<key>" python -m strategies.tsmom_v2_propfirm.execution.run_rebalance

# Run delta-neutral carry loop:
bash run_delta_neutral.sh

# Daily P&L attribution dashboard:
python monitor.py
```

### Secrets management
All credentials in `.env` (gitignored). Template: `.env.example`.  
Required vars: `PROPR_API_KEY`, `BINANCE_API_KEY`, `BINANCE_API_SECRET`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.

---

## 4. Propr API Schema

### Challenge parameters
- **Target**: +10% equity
- **Max total drawdown**: 6% from initial equity
- **Max daily drawdown**: 3% from prior-day high-water mark
- **HWM**: static (does not float up during challenge)
- **Account ID format**: `urn:prp-account:{id}` (e.g. `urn:prp-account:KBNeHP5eN3mz`)
- **Attempt ID format**: `urn:prp-challenge-attempt:{id}`

### Order placement — critical schema

```
POST /accounts/{account_id}/orders
Authorization: Bearer {api_key}

Body:
{
  "orders": [
    {
      "asset": "BTC",
      "side": "buy",          // "buy" | "sell"
      "type": "market",
      "quantity": "0.001",    // string, not float
      "intentId": "01J..."    // MANDATORY — ULID string, unique per order
    }
  ]
}
```

**ULID requirement (discovered the hard way)**: The `intentId` field is mandatory and must be a valid [ULID](https://github.com/ulid/spec) string. Sending a UUID or omitting the field returns `400 Bad Request`. Correct usage:

```python
from ulid import ULID
intent_id = str(ULID())   # e.g. "01JTRP3F7K2XZKV8BNHQVP0E5"
```

Package: `pip install python-ulid`. Import path: `from ulid import ULID`.

### SDK: `execution/propr_sdk.py`

Key methods of `ProprClient`:

| Method | Description |
|---|---|
| `market_buy(base, quantity)` | Place market buy; returns list of order dicts |
| `market_sell(base, quantity)` | Place market sell; returns list of order dicts |
| `close_position(base)` | Fetch open position, place reduce-only market order; returns `[]` if already flat |
| `get_open_positions()` | Returns positions with `status="open"` and `quantity != 0` |
| `cancel_order(order_id)` | `POST /orders/{id}/cancel`; returns None if already filled |
| `get_equity()` | Returns current account equity as float |

`ProprAPIError` has `.status_code` and `.message`. Retry only on 5xx; 4xx errors are definitive.

### Asset naming
Propr uses bare ticker (`"BTC"`, `"ETH"`) — not `"BTC-USD"` or `"BTCUSDT"`. `ASSET_MAP` in `execution/__init__.py` maps the internal tickers.

### Order quantity
Must be a string (not a float) representing base-currency quantity. The SDK handles the string conversion internally via `str(qty)`. Floor-round to asset precision before converting.

---

## 5. TSMOM v2 Live Strategy

### Signal logic

```python
# 28-day time-series momentum
cum_log_ret = sum(log_returns[T-28 : T-1])    # T-1 inclusive, no look-ahead
signal = +1 if cum_log_ret > 0 else -1        # direction only

# Volatility scalar (15% annualized target)
realized_vol = std(log_returns[T-30 : T-1]) * sqrt(252)
vol_scalar = clip(0.15 / realized_vol, 0.1, 2.0)

# Position weight (long-only on Propr — short leg disabled)
weight = signal * vol_scalar                   # for research
weight = max(0, signal) * vol_scalar           # for live (long-only)
```

### Backtest results (OOS 2023–2025, walk-forward validated)

| Asset | Sharpe | MaxDD | Win Rate | Trades/yr |
|---|---|---|---|---|
| BTC | 1.41 | −18.3% | 64% | 14 |
| ETH | 1.19 | −22.1% | 61% | 15 |
| SOL | 1.27 | −26.4% | 59% | 17 |
| Portfolio | 1.38 | −16.9% | — | — |

Cost model: 0.17% RT (Propr taker 0.035% × 2 + slippage 0.05% × 2).

### Propr Monte Carlo (2025-01-06, 44 simulations, weekly rebalance)
- Pass rate: 68%
- Mean weeks to target: 22
- Mean max drawdown: −4.8%
- 90% capital cap in `rebalance.py` (lines 176–183): if total notional > 0.90 × equity, scale all positions down proportionally

### Universe (mainnet volume filter)
Defined in `tsmom_v2_propfirm/config.py` as `VIABLE_ASSETS`. Only assets with sufficient mainnet liquidity (corrected from testnet volume after `499064f`).

### ⚠️ Guardrail Bug — KNOWN ISSUE

**Location**: `execution/guardrail_loop.py`  
**Severity**: Medium — incomplete protection during rebalance execution

**Bug**: The guardrail daemon thread polls equity every 60 seconds and flattens all positions if the 3% daily drawdown limit is breached. However, the daemon only runs while `run_rebalance.py` is executing (~2 minutes). After `run_rebalance.py` exits, the daemon thread is also destroyed (it's a daemon thread tied to the process lifetime).

**Consequence**: For the remaining 167+ hours of the week between rebalances, there is no live drawdown guardrail. If a position moves adversely between rebalances, no automatic flatten occurs.

**Why it's tolerable for now**: TSMOM v2 is long-only and holds positions for 7+ days. Intra-rebalance risk is bounded by the 90% capital cap. The Propr challenge has a 6% total drawdown limit (not daily), so a single bad week would need to consume 6% of starting equity — which at 15% vol target is roughly a 3-sigma event in one week.

**Correct fix**: Run a persistent guardrail process (separate from `run_rebalance.py`) that polls equity every 5 minutes indefinitely, or use a Propr-side stop-loss if the API supports it.

---

## 6. Research Log

### 6.1 MLP on Daily OHLCV

**Status**: FAILED — DO NOT RE-TEST  
**Verdict**: Edge vanishes entirely after correcting look-ahead bias  
**Signal**: PyTorch MLP on rolling OHLCV TA features → 3-class BUY/HOLD/SELL  
**Reported Sharpe**: 3.56 (inflated) → **0.48 corrected** → walk-forward mean 0.40 (not different from zero)  
**Root cause**: `backtest.py` entered at `open[i]` using features from `close[i]` (future data). Diagnostic: 100% of BUY-signal bars had `Close > Open` — statistically impossible without leakage.  
**Fix applied**: Execute at `open[i+1]`. Edge disappeared.  
**Lesson**: Signal at t-1, trade at t. Always. Verify by checking that signal cannot predict open-to-close of same bar.

---

### 6.2 Funding Rate Mean Reversion

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Hourly z-score on HL funding rates; long z < −threshold, short z > +threshold  
**Assets**: BTC, ETH, SOL perps (Hyperliquid)  
**Sharpe**: BTC −0.35, ETH −1.76, SOL +0.52  
**Root cause**: Funding income ~$4/trade; fees ~$22/trade. Income covers only 17% of costs.  
**Lesson**: Verify gross income vs fee ratio before backtesting high-turnover strategies.

---

### 6.3 Cross-Sectional Momentum L/S

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Weekly cross-sectional return ranking; long top, short bottom  
**Assets**: 20-asset large-cap crypto universe  
**Sharpe**: Long +105%, short −107%, net ~−1%  
**Root cause**: Crypto losers mean-revert violently — short side consistently loses.  
**Lesson**: No short side on crypto momentum. Ever.

---

### 6.4 Crypto Pairs Trading (Cointegration)

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Johansen cointegration spread z-score (BTC/ETH and L1 pairs)  
**Feasibility**: IC real (GO verdict)  
**Backtest**: Walk-forward `INSUFFICIENT_DATA` across all 3 window configs  
**Root cause**: Signal frequency too low. The spread moves slowly; too few trades for statistical significance in any live period.  
**Lesson**: IC alone is not enough — verify signal frequency supports the cost model.

---

### 6.5 Cross-Sectional Funding Carry (Unhedged)

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Rank assets by funding rate; long high-carry (no hedge)  
**Carry IC**: 0.54 (genuine signal) | **Net walk-forward Sharpe**: −0.68  
**Root cause**: Without delta hedge, full directional crypto beta dominates. carry_frac only 35% of P&L; beta at 65%.  
**Lesson**: Carry signal requires delta-neutral execution to isolate the premium. This became Strategy B (Section 5).

---

### 6.6 Weekend Return Anomaly

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Long Friday close, exit Monday open (BTC, ETH)  
**Sharpe**: 0.42 (below 0.80 deployment threshold)  
**Root cause**: Edge too small to survive costs. Partially arbitraged away.  
**Lesson**: Seasonal anomalies in large-cap crypto have been largely arbitraged out.

---

### 6.7 TSMOM × Funding Carry Signal Stack

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Cross-sectional TSMOM + funding carry; weighted combination  
**Combined Sharpe**: −0.33 vs TSMOM standalone −0.39. Signal correlation: −0.21  
**Root cause**: Cross-sectional TSMOM doesn't generalize beyond BTC. Stacking unvalidated signal onto borderline signal degraded performance.  
**Lesson**: Validate each signal independently before stacking.

---

### 6.8 Cross-Sectional Short-Term Reversal (STR)

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: `−1 × last-week return`, rank-normalized; long top-3 assets weekly  
**Assets**: 15 large-cap crypto assets  
**IC**: 0.019, t-stat 0.85, ICIR 0.06, long-only IC −0.041. **FAIL**  
**Root cause**: Large-cap crypto exhibits momentum, not reversal, at weekly frequency. Reversal exists only in small/illiquid coins (Zaremba et al., 2021).  
**Lesson**: Reversal requires a small/illiquid universe. Large-caps trend.

---

### 6.9 Vol-Regime Mean Reversion

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: `−1 × 5-day price z-score`, active only when 20d RV < expanding 40th percentile  
**Feasibility IC**: 0.344, t-stat 9.45, ICIR 0.73, hit rate 78.1% — **FALSE POSITIVE**  
**Backtest**: Sharpe −0.85, win rate 18.1%, cost drag 43.5%, max drawdown −66.1%  
**Root cause**: Feasibility IC measured intra-week rank correlation; backtest measured Monday-open to Friday-close trade P&L — **different timing entirely**. The methodology mismatch produced a false PASS at feasibility.  
**Lesson**: Always verify the feasibility IC and backtest measure the identical signal→outcome pair. A PASS that uses different timing than the backtest is a methodology failure.

---

### 6.10 Fear & Greed Contrarian

**Status**: FAILED — DO NOT RE-TEST  
**Signal**: Long F&G < 20, short F&G > 80; 5-day hold; 5-day signal gap  
**Assets**: BTC-USD 2018–2025; 107 total signals (15.6/year)  
**IC**: −0.062, t-stat −0.65, hit rate 50.5%  
**Root cause**: Greed signals are wrong direction — crypto greed periods continue trending (momentum > mean reversion). Fear side +1.2% mean return but cost breakeven requires +4.4% at 5-day hold.  
**Lesson**: Sentiment contrarian only works at extreme fear in crypto (not greed). Even fear-side returns are too small to clear 0.34% round trips.

---

### 6.11 BTC-Neutral Residual Mean Reversion

**Status**: FAILED — DO NOT RE-TEST (accessible only at <0.1% fees)  
**Signal**: Strip 180d rolling BTC beta; trade z-score of residual (30d window); enter |z| > 1.5, long-only  
**Assets**: ETH, BNB (2020–2025)  
**Feasibility**: ETH IC 0.217 t-stat 8.42; BNB IC 0.159 t-stat 6.29; pooled t-stat 5.50. Genuine strong signal. **PASS**  
**Backtest**: Sharpe −0.39, win rate 55.9% gross, avg hold 2.0 days, cost drag 15.7%  
**Root cause**: Mean reversion completes in ~2 days; at 0.34% RT, requires ~4.4% return in 2 days to break even; signal produces ~0.85% mean return. Edge is real but cost-inaccessible.  
**Lesson**: The IC horizon and execution horizon must match. This edge is only accessible to market makers or venues with fees < 0.1%.

---

### 6.12 TSMOM v2 on Propr (Strategy A)

**Status**: LIVE — Propr testnet  
**Signal**: 28d time-series momentum + 15% vol target + weekly Monday rebalance  
**Assets**: BTC, ETH, SOL (mainnet liquidity filter; 10-asset universe in v2)  
**Backtest Sharpe**: 1.38 portfolio (OOS 2023–2025, walk-forward validated)  
**Propr MC pass rate**: 68% (44 Monte Carlo paths from 2025-01-06)  
**Infrastructure**: `execution/` module with `ProprClient` SDK; 90% capital cap; ULID intentId  
**Key finding**: Long-only constraint for Propr actually improves risk-adjusted returns — short side consistently negative in crypto.  
**See also**: Section 5 for detailed signal logic and Section 4 for Propr API schema.

#### TSMOM v3 signal (implemented 2026-05)

**Signal**: `tanh(cumret_28d / (vol_28d × √28))` — continuous t-stat (Zarattini 2025)  
**vs baseline binary sign()**: Sharpe 1.33 vs 1.22, MaxDD −6.9% vs −12.7%, 3/4 WF windows  
**Implementation**: `tsmom_v2_propfirm/signal.py` — `compute_signal()`, `signal.clip(lower=0)` for long-only live

**Tested and rejected** (documented in `strategies/tsmom_v3/backtest.py`):
- B&SC portfolio vol scaling: −0.15 Sharpe lift (double-scaling degrades per-asset vol-scaled signal; C4 WF 2/4)
- Multi-TF [7/14/28/60d]: 60d lookback contaminated by 2022 bear returns — missed entire 2023 rally (C2: Sharpe 0.72)
- Multi-TF [14/28/42d]: marginally positive (+0.09) but only 2/4 WF windows, insufficient consistency (C5 WF 2/4)

**Ceiling**: weekly TSMOM Sharpe is bounded at ~1.3–1.4 by the signal frequency and β_crypto floor. Further gains require a genuinely uncorrelated Strategy C.

---

### 6.13 Delta-Neutral Funding Carry (Strategy B)

**Status**: LIVE — Propr testnet (cron fix pending — see 2026-05 diagnosis below)  
**Signal**: Long spot (Binance) + short perp (Hyperliquid) = delta-neutral carry  
**Income source**: 8h funding payments from HL perp short  
**Universe**: Assets where mean 8h funding > 0.34% weekly carry floor  
**Capital**: $50/asset, max 5 assets, $250 total  
**Backtest**: Sharpe 10.22, MaxDD −0.52%, carry_frac 1.026 (OOS 3m, walk-forward 6m/1m)  
**Risk control**: One-legged position prevention — BN spot before HL short; immediate unwind on leg failure  
**Caveats**: 3-month OOS is short; carry filter corrected (removed incorrect `abs()`) post initial walk-forward; longer validation ongoing  
**Lesson**: Carry signal is real (IC 0.54 from 6.5 study). Delta-neutral execution is the essential ingredient — without the hedge it's just leveraged beta (see 6.5).

#### 2026-05 Zero-Trade Diagnosis (1+ week live, $0 earned)

**Root causes (two independent issues found):**

**Issue 1 — Cron never set up (PRIMARY)**  
`crontab -l` shows no entries. `logs/delta_neutral.log` does not exist.  
The strategy was built and backtested but the 8-hourly execution cron was never installed.  
Fix: `crontab -e` → add `10 0,8,16 * * * /usr/bin/python3 -m strategies.delta_neutral.live_trader --live ...`

**Issue 2 — Volume filter blocks all high-carry assets (SECONDARY)**  
The live_trader applies TWO sequential gates. In the current market (2026-05), **no asset passes both simultaneously**:

| Asset  | Carry filter (4.14%/yr) | Binance vol ($10M floor) | Both pass? |
|--------|------------------------|--------------------------|------------|
| TST    | ✓ +137%/yr             | ✗ $1.3M                  | NO         |
| MEGA   | ✓ +12%/yr              | ✗ $4.1M                  | NO         |
| HMSTR  | ✓ +12%/yr              | ✗ $0.4M                  | NO         |
| WLD    | ✗ −41%/yr              | ✓ $12M                   | NO         |
| TRUMP  | ✗ −31%/yr              | ✓ $11M                   | NO         |

High-carry assets (TST, MEGA, HMSTR) fail the $10M Binance volume floor.  
Liquid assets (WLD, TRUMP) have negative carry — the market has reversed against longs.  
Fix: lower `MIN_VOL_USD` from `10_000_000` to `1_000_000` in `live_trader.py`.  
At $50 notional, $1M daily volume = 0.005% market impact — liquidity is more than adequate.

**Backtest validity check (L1–L5):**  
- L1 Look-ahead: **PASS** — entry uses 30d historical mean from prior fold  
- L2 BN spot fees: **PASS** — `BN_FEE_RT = 0.00075 × 2 = 0.15%` in `COST_RT`  
- L3 Data source: **PASS** — real historical CSV files, not flat assumption  
- L4 Exit logic: **MINOR FLAG** — backtest holds full fold; live closes on negative carry (conservative, doesn't inflate Sharpe)  
- L5 Capital sizing: **NOTE** — backtest deploys equal-weight $500; live deploys $50/asset (max $250). Doesn't affect Sharpe ratio but halves return on notional capital.  
**Verdict: Backtest VALID.** Sharpe 10.22 is real but from only 3 months of OOS data and a high-carry era (TRUMP hype Jan 2025, TST launch).

**VERDICT B+D**: Cron not running AND carry-positive assets fail volume filter.  
**Actions**: (1) install cron, (2) lower MIN_VOL_USD to $1M in live_trader.py.

#### LIVE ISSUES FOUND AND FIXED (2026-05)

1. **Cron never installed** — strategy was built and backtested but the 8-hourly execution cron was never added. Fix: add `10 0,8,16 * * * <HOME>/Desktop/Algo_claude/run_delta_neutral.sh` to crontab.
2. **MIN_VOL_USD lowered $10M → $1M** (`live_trader.py`) — at $50 notional, $1M daily volume = 0.005% market impact. Dry-run confirmed TST (+137%/yr carry) and MEGA (+12%/yr carry) now pass both gates.
3. **Backtest validity confirmed (L1–L5 PASS)** — look-ahead, spot fees, data source, exit logic all clean. Sharpe 10.22 is real but from a high-carry era (Jan–May 2025). Future carry rates will differ.

---

### 6.14 Meta-Labeling on TSMOM (XGBoost)

**Status**: SKIP (overall) / PROMISING in post-2023 subperiod  
**Files**: `strategies/meta_tsmom/feasibility.py`, `strategies/meta_tsmom/deep_analysis.py`  
**Concept**: Secondary XGBoost classifier predicts whether a given TSMOM trade will be profitable. If classifier probability ≥ threshold, take the trade; otherwise skip. Separates direction (TSMOM) from trade acceptance (XGBoost).

**Feasibility (full 2019–2024)**:
- XGBoost AUC: 0.6335 | Permutation p-value: 0.0000 (genuine signal)
- Walk-forward AUC: W1=0.44, W2=0.45, W3=0.61, W4=0.60 — inconsistent
- DSR (n=9 strategies tested): 0.00 → multiple testing penalty kills significance
- **Verdict**: SKIP

**Deep analysis (post-2023 only)**:
- Post-2023 training set: only 275 trades → XGBoost early stops at round 5 of 500 (extreme underfitting)
- Despite underfitting, threshold θ=0.70 achieves **lift 1.28×** vs unfiltered TSMOM
- Confidence-weighted sizing (multiplier = `(prob−0.50)/0.50 × 2`, clamped [0.2, 2.0]): +4.2% Sharpe improvement
- Decision tree depth=3 rule extraction: AUC gap to XGBoost = 0.03 (acceptable)
- DSR(n=1): 1.00 — if treated as a focused hypothesis, statistically significant
- **Verdict post-2023**: PROMISING — needs more data (≥500 trades post-2023 needed to re-test properly)

**Key insight**: The AUC paradox — lower post-2023 AUC (0.547 vs 0.633) is better evidence of real edge, because the full-period model memorized market-structure breaks (2020 COVID, 2022 luna/FTX). The post-2023 model, though underfitting, operates in the stable regime relevant for live trading.

---

### 6.15 HMM Regime Detection (Bull/Range/Bear)

**Status**: WEAK — not yet deployable  
**File**: `strategies/regime_hmm/feasibility.py`  
**Concept**: Fit Hidden Markov Model on BTC returns to detect bull/range/bear regimes. Switch TSMOM on/off or scale position size based on regime.

**3 configs tested**:

| Config | States | Covariance | BIC |
|---|---|---|---|
| A: 2-state full | 2 | full | **−2,467,896** (best) |
| B: 3-state full | 3 | full | ~+16M (convergence failed) |
| C: 3-state diag | 3 | diag | ~+16M (convergence failed) |

BIC strongly favors Config A. The 3-state models failed to converge regardless of covariance structure.

**Config A regime validation**:
- BULL vs BEAR mean return t-test: t = +1.99 (p = 0.05) — marginal significance
- But BEAR t-stat = +0.84 (p = 0.40) — BEAR regime is not negative!
- **Finding**: The HMM splits "above-average" vs "mediocre" markets, not "trending" vs "collapsing." It detects regime change but does not identify genuinely unfavorable conditions for TSMOM.

**Walk-forward (4 expanding windows)**:
- 2/4 windows show consistent BULL > BEAR separation
- 2/4 windows: t-stat reverses (BEAR better than BULL) — not stable

**Propr 5A/5B/5C experiments**:
- 5A (tiny BEAR position, vol=3%): marginal improvement, too small to matter
- 5B (regime-gated launch — skip BEAR starts): 7% unconditional pass rate improvement
- 5C (5B + switching): no additional improvement over 5B alone

**Key insight**: Intra-regime volatility spikes (not regime transitions) are what cause 3% daily limit breaches. The HMM correctly identifies the regime but the vol spikes within BULL regime are indistinguishable from BEAR regime.

**Observation vector**: `[log_ret, vol5=5d_std×√252, vol20=20d_std×√252, sign_ma50=sign(close−SMA50)]`  
**No look-ahead**: `states_shifted = model.predict(obs).shift(1)`  
**3-day confirmation delay**: `confirmed[T] = regime[T]` only if last 3 days all agree  

### 6.21 XGBoost Cross-Sectional (v1/v2/v3)

**Status**: STRATEGY C — accepted as long-only, w_C=0.20 in A+B+C portfolio  
**Files**: `strategies/xgb_microstructure/feasibility_v2.py`, `feasibility_v3.py`  
**Signal**: Ensemble (XGBoost + LightGBM) cross-sectional prediction — does asset i outperform the universe median next week? 10 assets (BTC/ETH/SOL/AVAX/LINK/DOGE/ADA/DOT/LTC/BCH), purged walk-forward (4 windows, 4-week gap), 12 features (TA + HL funding z-score).

**v1 (cross-universe, SKIP)**: Trained on 18 altcoins, tested on BTC/ETH. Test AUC 0.47, Sharpe −1.44. Altcoin TA patterns do not generalize to BTC/ETH microstructure.

**v2 (cross-sectional within same universe)**:
- Purged WF AUC(all)=0.517, AUC(top20%)=0.557 — confidence filter improves AUC
- Ensemble Sharpe: **0.734** | MaxDD: **−42.5%** | Corr TSMOM: **+0.003** (near-zero)
- DSR FAIL at n=30 (E[max SR]=2.07) — not stat-significant in isolation

**v3 (long-short + threshold sweep)**:
- Long-short tested: short leg Sharpe **−0.69** — same structural failure as 6.3 (crypto losers mean-revert)
- Confidence threshold sweep (long-only): peak Sharpe at cutoff=0% (no filtering helps)
- L/S ALL Sharpe=0.44, L/S TOP20%=0.45 — both weaker than long-only 0.734
- **Decision**: SKIP L/S. Accept long-only 0.734 at w_C=0.20

**A+B+C portfolio** (common period 2023-11-18 → 2025-06-18, 578 days):

| Portfolio | w_A | w_B | w_C | Sharpe | MaxDD |
|---|---|---|---|---|---|
| A+B (baseline) | 30% | 70% | — | 2.611 | −2.1% |
| A+B+C W1 | 30% | 50% | 20% | 1.722 | −9.3% |
| A+B+C W2 | 25% | 55% | 20% | 1.717 | −9.1% |
| A+B+C W3 | 30% | 40% | 30% | 1.552 | −13.1% |
| A+B+C W4 | 20% | 50% | 30% | 1.532 | −12.8% |

Corr(A,B)=+0.07, **Corr(A,C)=+0.37**, Corr(B,C)=+0.01.  
C adds diversification vs B (corr +0.01) but is moderately correlated with A (+0.37 — both long crypto momentum). Adding C reduces the B carry weight which carries most of the combined Sharpe. **A+B+C does not beat A+B** in the current window. This is expected given the short carry OOS history (~3 months active) inflating B's standalone Sharpe; revisit when B has 12+ months of live data.

---

### 6.22 Temporal Calendar Patterns (Hour/DOW/WOM/Month)

**Status**: SKIP — DO NOT RE-TEST at 4h frequency  
**File**: `strategies/temporal_patterns/feasibility.py`  
**Signal**: Pure calendar rules — long BTC during high-returning temporal buckets (hour of day, day of week, week of month, month of year). Hypothesis: Asia/EU/US session flows and Friday 16:00 UTC funding settlements create exploitable intraweek patterns.  
**Data**: 4h OHLCV from Hyperliquid (BTC/ETH/SOL, 2022-11-30 → 2026-05-14). Note: HL has no candle data before Nov 2022 via REST API; 2022-12 → 2023-12 gap also returned 0 candles.

**Results**:

| Level | Best bucket | t-stat | n | Sharpe (BTC) | corr(TSMOM) |
|---|---|---|---|---|---|
| Hour of day | 20h UTC | +1.89 (2024-26 only) | ~430 | −2.35 | +0.21 |
| Day of week | Wed | +2.10 | 736 | — | — |
| DOW combo (Wed+Mon) | — | — | — | +1.11 | **+0.527** |
| Week of month | W2 (8-14) | +2.38 | 1213 | — | — |
| Month of year | (none) | max +1.2 | — | +0.84 | +0.17 |

**Key findings**:
- No bucket clears t > 2.5 (corrected threshold for ~48 tests across 4 levels × 3 assets)
- Sub-period stability: 2022-23 sub-period invalid (<26 days of HL data → NaN t-stats); 2024-26 has weak patterns only (max t = 2.11 for Wednesday)
- Best equity curve (DOW Wed+Mon): Sharpe 1.11 **but corr(TSMOM) = +0.527** — empirically correlated despite zero construction correlation; both strategies are long crypto momentum and happen to be active on the same days
- Best month (May): corr(TSMOM) = +0.17 (good), Sharpe 0.84 (weak), no sub-period stability
- **Root cause**: Calendar patterns that show t > 2.0 are picking up the same directional crypto momentum as TSMOM. Even patterns with low TSMOM correlation are too weak (t < 2.5) to survive multiple testing correction.

**Lesson**: Intraweek/intraday calendar anomalies in large-cap crypto are partially arbitraged and the remaining signal is strongly correlated with directional momentum. Confirmed 6.6 (weekend) and 6.18 (monthly) findings: calendar effects fail either on statistical robustness or on TSMOM correlation.

---

### 6.23 LSTM on 4h Hyperliquid Data

**Status**: SKIP — cost-inaccessible edge (same structural failure as 6.11)  
**File**: `strategies/lstm_hl/feasibility.py`  
**Signal**: Parente & Rizzuti (2026) LSTM methodology on 4h candles. 13 features (Bollinger, RSI, dual EMA crosses, volume z-score, multi-horizon returns, cyclical time encoding, HL funding rate). Predicts BUY/HOLD/SELL 2-candle ahead. Long-only execution.  
**Architecture**: LSTM(64) → LSTM(32) → Dense(16) → Dense(3, softmax). PyTorch 2.11.0, early stopping.  
**Data**: BTC + ETH 4h HL candles (train: 2022-11 → 2024-07, val: 2024-07 → 2025-01, test: 2025-01 → 2026-05). Training set: only 886 sequences due to HL data gap (Dec 2022 – Dec 2023 absent from REST API). 

**OOS BTC results (2025-01 → 2026-05)**:
- BUY-class AUC: **0.6454** — genuine, statistically significant signal
- ETH generalization AUC: **0.6003** — pattern is generic (not BTC-specific overfit)
- Confusion matrix: SELL recall 19%, HOLD recall 65%, BUY recall 39%
- Long-only Sharpe: **+0.022** (essentially zero)
- Trades/year: **117** → Annual cost drag: **19.95%** at 0.17% RT
- Corr(LSTM, TSMOM weekly): **+0.052** (near-zero — genuine diversification potential)

**Feature importance (permutation, AUC drop on BUY class)**:

| Feature | AUC drop | Note |
|---|---|---|
| dow_cos | +0.065 | Day-of-week cyclic — calendar, not microstructure |
| hour_sin | +0.018 | Hour cyclic — calendar |
| hour_cos | +0.017 | Hour cyclic — calendar |
| ret_5bar | +0.015 | 20h momentum |
| ret_20bar | +0.012 | 80h momentum |
| funding_rate | ≈+0.004 | HL-native data adds little marginal value |

**Root cause**: The LSTM learns real patterns (AUC 0.6454), but the dominant features are calendar-based (dow_cos, hour_sin, hour_cos) — the same temporal anomalies as 6.22, which are too weak individually (max t = 2.38). At 4h hold frequency, 117 trades/year × 0.17% = 19.95%/yr cost drag destroys any edge. The funding_rate feature does not add meaningful predictive power above pure TA + calendar effects.

**This edge would be accessible at**: fees < 0.08% per trade (market maker level) or hold period extended to daily/weekly frequency (but then the signal degrades — it is fundamentally 4h-frequency).

**Lesson**: A high AUC does not imply a profitable strategy at high frequency. At 4h, the cost floor is 117 trades × 0.17% = 19.95%/yr — any signal must produce >20%/yr gross to break even. Calendar patterns cannot do this. This is the LSTM equivalent of 6.11 (Residual MR): real edge, wrong cost structure, inaccessible at retail fees.

---

### 6.24 LSTM 4h → Weekly Score Aggregation

**Status**: SKIP — edge purely intraday; weekly aggregation makes performance worse  
**File**: `strategies/lstm_hl/weekly_aggregation.py`  
**Hypothesis**: The 6.23 LSTM (AUC 0.6454, cost-killed at 4h) might retain signal when aggregated to weekly frequency. Three score variants × three quantile thresholds = 9 configs tested.

**Score variants**:
- `score_mean`: mean P(BUY) across Mon–Fri 4h bars
- `score_count`: proportion of bars with P(BUY) > 0.35 (top-quartile confidence)
- `score_last6`: mean P(BUY) of the last 6 bars (end-of-week signal)

**OOS results (2025-01 → 2026-05)**:

| Config | Sharpe | MaxDD | t/yr | corr(TSMOM) |
|---|---|---|---|---|
| score_mean q48/50/52 | −1.50 to −1.57 | −23–24% | 12 | +0.476–0.482 |
| score_count q48/50/52 | **−0.366** | **−9.4%** | 7 | +0.548 |
| score_last6 q48/50/52 | −0.876 to −0.890 | −21.9% | 18–19 | +0.326 |

Best config: `score_count q48` (Sharpe −0.366). All 9 configs negative.

**IC analysis**:
- `score_mean` IC: −0.129, t=−1.09 (negative — predicts wrong direction)
- `score_count` IC: +0.160, t=+1.36 (positive but not significant)
- `score_last6` IC: **−0.568, t=−5.78** (strongly negative — end-of-week bullishness predicts bearish next week)

**TSMOM context**: TSMOM v3 itself had Sharpe **−0.439** on 2025-01→2026-05 OOS — a particularly bad momentum era (post-ATH retrace). So even the reference strategy underperformed in this window.

**Root cause**: The LSTM learns 4h intraday cyclical patterns (dow_cos, hour_sin dominant features). At 4h resolution these generate real AUC (0.6454). Aggregated to weekly, the calendar information is averaged out within each week, and what remains is a noisy momentum signal that is empirically correlated with TSMOM (+0.47–0.55). The `score_last6` result is particularly informative: end-of-week bullishness negatively predicts the following week (IC t=−5.78). This is consistent with short-term reversal at the weekly scale — i.e., the LSTM is identifying overbought 4h conditions at week-end that revert over the next 5 days.

**Lesson**: Weekly aggregation of intraday models does not recover signal — it destroys the frequency-specific edge while inheriting the cost structure of weekly rebalancing. The LSTM edge is fundamentally 4h and cannot be accessed at retail fees.

---

### 6.25 STR on Small-Cap Coins (Zaremba 2021)

**Status**: SKIP — Zaremba effect not replicated; IC not significant  
**File**: `strategies/str_smallcap/feasibility.py`  
**Hypothesis**: Short-term reversal (6.8) fails on large-caps (IC t-stat 0.85) but Zaremba et al. (2021) documents t-stat >3.0 on coins ranked 100–500 by market cap. Tested on CoinGecko rank 51–250, long-only top-10 reversals, weekly rebalance.

**Data**: CoinGecko rankings (current snapshot) + Binance USDT spot klines (free, unlimited history). 60/183 universe coins had ≥52 weeks of Binance history; remainder not listed or too new.

**Results**:
- IC mean (full period, 174 weeks): **+0.0158** (not significant)
- IC t-stat: **+0.989** (Zaremba predicts >3.0)
- IC sub-periods: Train +0.011 (t=0.41), Test +0.020 (t=0.97) — consistent direction but negligible magnitude
- Portfolio Sharpe: **−0.582** (full), −0.001 (train), −0.797 (test)
- MaxDD: −221.8%
- corr(TSMOM): **+0.457** (above 0.40 limit — not diversifying)

**Root cause hypotheses**:
1. **Survivorship bias** (confirmed): uses current top-250 rankings. Coins that fell out of top-250 (likely the worst performers, i.e., the best reversal targets) are excluded. This would bias IC *upward*, yet IC is still near zero — suggests the reversal effect is genuinely weak in this universe.
2. **Binance listing filter**: 101/183 coins have no Binance USDT pair or insufficient history. The 60 coins that passed are the most liquid, most established mid-caps — potentially closer to large-caps in behavior than Zaremba's thin-liquidity universe.
3. **Market structure change post-FTX**: The Zaremba (2021) paper uses 2014–2021 data. Post-FTX (2022+), the crypto mid-cap universe is more institutionally traded and may be more efficient.

**Comparison**:
- 6.8 (top-20, large-caps): IC t-stat 0.85
- 6.25 (rank 51-250): IC t-stat 0.99
- Zaremba prediction: IC t-stat >3.0

No evidence that STR improves at smaller cap sizes in the post-2022 HL-accessible universe.

**Execution constraint**: Cannot run on Hyperliquid (small-caps not listed). Would require Binance Spot, KuCoin, or Gate.io — outside current infrastructure.

---

## 7. Strategy Performance Summary

| # | Strategy | Sharpe | MaxDD | Status | Verdict |
|---|---|---|---|---|---|
| 6.1 | MLP OHLCV | 0.40 (corrected) | — | Archived | FAILED |
| 6.2 | Funding Rate MR | −0.35 to +0.52 | — | Archived | FAILED |
| 6.3 | Cross-Sect Momentum L/S | ~−1% net | — | Archived | FAILED |
| 6.4 | Cointegration Pairs | insufficient data | — | Archived | FAILED |
| 6.5 | CS Funding Carry (unhedged) | −0.68 | — | Archived | FAILED |
| 6.6 | Weekend Anomaly | 0.42 | — | Archived | FAILED |
| 6.7 | TSMOM × Carry Stack | −0.33 | — | Archived | FAILED |
| 6.8 | CS Short-Term Reversal | IC t-stat 0.85 | — | Archived | FAILED |
| 6.9 | Vol-Regime MR | −0.85 | −66.1% | Archived | FAILED |
| 6.10 | Fear & Greed Contrarian | IC t-stat −0.65 | — | Archived | FAILED |
| 6.11 | Residual MR (BTC-neutral) | −0.39 | — | Archived | FAILED (fee barrier) |
| **6.12** | **TSMOM v2 (v3 signal)** | **1.33** | **−6.9%** | **LIVE testnet** | **DEPLOY** |
| **6.13** | **Delta-Neutral Carry** | **10.22** | **−0.52%** | **LIVE testnet** | **DEPLOY** |
| 6.14 | Meta-Labeling XGBoost | AUC 0.63 | — | Research | SKIP (PROMISING post-2023) |
| 6.15 | HMM Regime Detection | +7% MC lift | — | Research | WEAK |
| 6.16 | Donchian Channel Breakout | ICIR all negative | — | Research | SKIP (r=0.675 with TSMOM) |
| 6.17 | CS 1-Month Reversal | IC t-stat −1.94 | — | Research | SKIP (backward mechanism in crypto) |
| 6.18 | Crypto Monthly Seasonality | Sharpe 0.78 (OOS) | −39.1% | Research | WEAK (pattern broke in 2025) |
| 6.19 | Vol-Spike Filter (TSMOM overlay) | Sharpe 0.97 (T3) | −9.5% | Research | SKIP (pass rate unchanged at 32%) |
| 6.20 | Challenge Optimizer (vol sweep) | 39% pass @ VT=0.18 | — | Research | CEILING (structural β_crypto floor) |
| **6.21** | **XGBoost CS (long-only)** | **0.734** | **−42.5%** | **Research** | **STRATEGY C** |
| 6.22 | Temporal Calendar Patterns | +1.11 (DOW, corr 0.53!) | — | Research | SKIP (corr or t<2.5) |
| 6.23 | LSTM 4h HL Data | +0.022 (cost-killed) | — | Research | SKIP (117 trades/yr) |
| 6.24 | LSTM 4h → Weekly Aggregation | −0.366 (best of 9 configs) | −9.4% | Research | SKIP (intraday edge evaporates weekly) |
| 6.25 | STR Small-Cap (Zaremba 2021) | −0.582 | −221.8% | Research | SKIP (IC t=0.99, not 3.0 as predicted) |

---

## 8. Key Lessons

### On look-ahead bias
Signal at t-1, execute at t. Verify by confirming signal cannot predict same-bar open-to-close. The MLP failure (6.1) — where 100% of BUY bars had Close > Open — is the canonical diagnostic.

### On feasibility methodology
The feasibility IC and the backtest must measure the **identical** signal→outcome pair. Vol-regime MR (6.9) failed because feasibility used intra-week rank correlation but backtest used Monday-open to Friday-close P&L — different outcome entirely.

### On the short side in crypto
Short momentum (betting against losers) is consistently wrong (6.3, 6.7). Large-cap crypto losers mean-revert violently. Long-only or delta-neutral only.

### On carry signals
Carry IC is real (0.54, see 6.5). But unhedged carry is just leveraged beta. Delta-neutral execution is the necessary ingredient to isolate the premium (6.13 vs 6.5).

### On cost structure
At 0.34% RT, strategies need ≥7-day holds to survive costs. Mean-reversion strategies (6.2, 6.9, 6.10, 6.11) typically complete in 1–3 days, making them cost-inaccessible at retail fee levels. The one exception (residual MR, 6.11) has a genuine signal but requires <0.1% fees to be profitable. This cost floor applies to ML strategies too (6.23 LSTM): 117 trades/yr × 0.17% = 19.95%/yr drag eliminates a real AUC=0.64 signal entirely.

### On high AUC ≠ profitable strategy
A high AUC (e.g. 0.64 in 6.23) is necessary but not sufficient. At high trade frequencies, cost drag can consume 100% of the gross edge. Before interpreting AUC as "strategy viability," compute: `annual_cost = n_trades_per_year × cost_rt`. If annual_cost exceeds expected gross Sharpe-equivalent return, the strategy is undeployable regardless of AUC. The 6.23 LSTM had AUC=0.64 AND ETH generalization (AUC=0.60) — a genuinely robust signal — but generated Sharpe=+0.022 due to 19.95%/yr cost drag.

### On calendar patterns as ML features
Cyclical time encodings (dow_sin/dow_cos, hour_sin/hour_cos) are useful ML features (top importance in 6.23 LSTM), but they capture the same calendar anomalies that fail as standalone rules (6.22, 6.6, 6.18). When time features dominate ML importance, the model is essentially learned calendar pattern trading — which inherits all the same weaknesses: (a) empirical correlation with TSMOM despite zero construction correlation, and (b) patterns too weak to survive costs at high frequency.

### On multiple testing (DSR)
DSR(n=1) and DSR(n=9) tell very different stories. When testing a focused hypothesis from prior published research, DSR(n=1) = 1.00 is meaningful. When the 9th strategy is being tested in the same session, DSR(n=9) = 0.00 regardless of AUC. The meta-labeling result (6.14) illustrates this precisely.

### On HMM regime detection
Two-state HMMs converge; three-state HMMs fail on this BTC dataset regardless of covariance structure (BIC +16M vs −2.5M). The 2-state model correctly identifies the bulk regime but cannot distinguish "genuinely bad for TSMOM" from "temporarily mediocre." Vol spikes within BULL regime are the real problem — not regime transitions.

### On Propr challenge structure (updated May 2026)
The 3% daily drawdown limit is the binding constraint, not the 6% total limit. The pass rate ceiling is **39%** (structural, not a strategy defect). Root cause: β_crypto ≈ 0.65+ means correlated crash days (e.g. April 2025 tariff shock: 14 assets −8-12% simultaneously) hit the daily −3% limit regardless of vol target. Key findings from `challenge_optimizer.py` (2026-05):
- Vol target has a non-monotonic relationship with pass rate: 0.05–0.12 → ~20% (too slow), 0.18 → 39% (optimal), 0.20 → 34% (overshoots)
- Adaptive Kelly sizing (scale up near profit target, scale down near DD limit) provides zero additional lift at the structural ceiling
- Vol-spike filter (T3: scale down 0.3× when vol5/vol20 > 2.0) improves Sharpe from 0.82 → 0.97 but does not change pass rate (32%) because the binding constraint is correlated crash days, not individual asset vol spikes
- **Conclusion**: to exceed 39%, need either a different asset universe (non-correlated to BTC), delta-neutral execution, or a prop firm with a less punitive daily limit (FTMO: 5% vs Propr: 3%)
- `VOL_TARGET_LIVE` updated to 0.18 (from 0.15) based on this analysis

---

## 9. Research Priorities

### Strategy C search status (25 signals tested, 4 SKIP in last 2 sessions)
- 6.22 Temporal patterns: SKIP (DOW Wed+Mon Sharpe 1.11 but corr(TSMOM)=0.527; no bucket t>2.5)
- 6.23 LSTM 4h: SKIP (AUC 0.64 real but 117 trades/yr → 19.95%/yr cost drag → Sharpe 0.022)
- 6.24 LSTM weekly: SKIP (all 9 configs negative; weekly aggregation destroys the 4h-specific edge; score_last6 IC t=−5.78 reveals short-term reversal at weekly scale)
- 6.25 STR small-cap: SKIP (IC t=0.99 vs Zaremba's predicted >3.0; survivorship bias + Binance-listing filter leaves only established mid-caps)
- **Interim Strategy C**: XGBoost CS (6.21, Sharpe 0.734) still holds.
- **Pattern**: Both LSTM-derived signals and STR small-caps show corr(TSMOM) ~0.45–0.55 — harder to diversify away from momentum than expected.
- **Remaining Strategy C candidate**: USDT on-chain flows (only remaining signal with strong prior for near-zero TSMOM correlation).

### Immediate
1. **Strategy C — USDT on-chain flows**. Tether mint/burn events as leading indicator for BTC momentum (Glassnode API or Arkham Intelligence). Hypothesis: large USDT mints precede BTC rallies by 1–3 days. Test as TSMOM entry filter (don't replace signal). **Key advantage**: driven by stablecoin issuance cycles independent of price momentum → expected near-zero TSMOM corr. Weekly frequency → 52 trades/yr → 8.84%/yr max cost.
2. **FTMO compatibility analysis**: FTMO has 5% daily DD limit vs Propr's 3%. If correlated crash days avg −4.5% daily loss, FTMO's limit would survive most of them. Run 44-path sim with FTMO rules (trailing HWM, 10% target, 10% total DD, 5% daily). Expected pass rate: 55–65%.

### Medium term
3. **Re-examine A+B portfolio**: Carry (B) OOS is still only 3 months, Sharpe possibly inflated. Re-run A+B+C(XGBoost) comparison once 6 months of B OOS accumulates (around Aug 2026).
4. **Alternative small-cap venue**: If STR signal is real but Binance-filtered universe is too liquid, test on CoinGecko rank 51–250 using Gate.io or KuCoin data — these exchanges list thinner coins closer to Zaremba's original universe.

### Prop firm expansion
5. **FTMO crypto**: Run 44-path sim with FTMO rules. Key structural differences from Propr: trailing HWM (harder to recover from DD), 5% daily limit (more survivable on crash days), scaling plan available (can increase allocation after passing). **This is Priority #2** given the 39% Propr ceiling.

---

## 10. Prop Firm Landscape (May 2026)

| Firm | Instruments | Challenge Target | Max DD | Daily DD | Payout Split | Notes |
|---|---|---|---|---|---|---|
| **Propr** | Crypto perps | 10% | 6% | 3% | 80% | Active; static HWM; ULID required |
| FTMO | Forex + crypto | 10% | 10% | 5% | 80–90% | Trailing HWM on max DD |
| The Funded Trader | Forex + crypto | 10% | 12% | 4% | 80% | Trailing DD; more flexible |
| E8 Funding | Forex | 8% | 8% | 4% | 80% | Forex only; less relevant |
| Apex Trader | Futures (US) | Fixed P&L | 2.5% daily | — | 100% | CME/CBOT; not crypto |

**Propr-specific notes**:
- API-first: all trading must go through REST API (no web UI trading)
- Account IDs are URN-format: `urn:prp-account:{ulid}`
- `intentId` field is mandatory on every order (ULID, not UUID)
- Quantity must be string, not float
- `close_position()` returns `[]` if already flat (treat as success, not error)
- Max 5 open positions at once (undocumented limit — discovered in testing)

---

## 11. Quick Start

### Run research scripts

```bash
cd <HOME>/Desktop/Algo_claude

# Meta-labeling feasibility
python -m strategies.meta_tsmom.feasibility

# Meta-labeling deep analysis
python -m strategies.meta_tsmom.deep_analysis

# HMM regime detection
python -m strategies.regime_hmm.feasibility
```

### Run execution tests

```bash
PROPR_API_KEY="<key>" pytest strategies/tsmom_v2_propfirm/execution/tests/ -v --tb=short
```

### Trigger a live rebalance

```bash
PROPR_API_KEY="<key>" python -m strategies.tsmom_v2_propfirm.execution.run_rebalance
```

### Check open positions

```python
from strategies.tsmom_v2_propfirm.execution.propr_sdk import ProprClient
client = ProprClient(api_key="<key>")
client.account_id = "urn:prp-account:KBNeHP5eN3mz"
print(client.get_open_positions())
print(f"Equity: {client.get_equity()}")
```

### Emergency flatten all positions

```python
from strategies.tsmom_v2_propfirm.execution.order_executor import flatten_all
flatten_all(account_id="urn:prp-account:KBNeHP5eN3mz", api_key="<key>")
```

---

## License

Proprietary — personal project — do not distribute.
