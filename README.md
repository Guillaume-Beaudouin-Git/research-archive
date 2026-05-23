# Algo_claude — Research Journal

**Last updated**: May 22, 2026  
**Status**: 2 strategies live on Propr testnet (TSMOM v2 + delta-neutral carry), 82 signals/variants tested — Strategy C = NQ ORB iter_10 (Sharpe 1.52, RESEARCH_PASS, paper trade phase pending TWS)

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

### 6.26 USDT Flow Proxy Signal (Chi et al. 2025)

**Status**: SKIP — IC negative and not significant; proxy too correlated with price momentum  
**File**: `strategies/usdt_flows/feasibility.py`  
**Hypothesis**: USDT net inflows into exchanges predict BTC/ETH returns (Chi, Chu & Hao 2025). Proxy: total USDT-denominated quote volume on Binance (BTCUSDT + ETHUSDT + SOLUSDT + BNBUSDT + XRPUSDT). Weekly z-score vs 30-day rolling baseline.

**Results**:
- IC (full period, 226 weeks): **−0.025** — negative and not significant
- IC t-stat: **−0.380** (target > 1.5)
- Sub-period IC: 2022–2023: −0.016 (t=−0.16), 2024–2026: −0.038 (t=−0.41) — consistent direction (wrong) both periods
- Portfolio Sharpe: **+0.220** (but signal is ON 45% of weeks, essentially buying momentum)
- corr(TSMOM): **+0.616** (far above 0.30 limit)

**Root cause**: Binance USDT quote_volume is a proxy for *trading activity*, not for *stablecoin inflows*. In bull markets, more USDT is traded → volume z-score positive → long signal → the strategy inadvertently buys when crypto is trending up (same as TSMOM). This is why corr(TSMOM)=0.616 despite zero theoretical connection. The true Chi et al. (2025) signal requires actual on-chain USDT flows to exchanges (Glassnode/Nansen), which is a paid data source.

**What would be needed**: Glassnode API stablecoin exchange flows (institutional plan, ~$500/mo) or Nansen Smart Money flows. Not available with free APIs.

---

### 6.27 Volatility Squeeze Breakout

**Status**: SKIP — Sharpe too low; signal fires almost exclusively during momentum periods  
**File**: `strategies/volatility_breakout/feasibility.py`  
**Hypothesis**: Bollinger Band squeeze (BB_width < 20th percentile of last 126 days) precedes breakout. Hold 10 days after breakout. Fires ~4 times/year per asset → cost manageable. TSMOM correlation expected to be low (signal is about vol structure, not returns).

**Results (daily, 2020–2026)**:

| Asset | Sharpe | MaxDD | t/yr | Win Rate | corr(TSMOM) | Overlap |
|---|---|---|---|---|---|---|
| BTC | −0.233 | −61.0% | 4 | 36.0% | +0.279 | 73.8% |
| ETH | +0.065 | −75.3% | 4 | 52.0% | +0.300 | 79.3% |
| SOL | +0.437 | −81.9% | 4 | 64.0% | +0.293 | 81.9% |

Walk-forward OOS Sharpe:

| Asset | WF1 (2023) | WF2 (2024) | WF3 (2025) | Positive/3 |
|---|---|---|---|---|
| BTC | +0.689 | +0.087 | −1.090 | 2/3 |
| ETH | +1.196 | −0.081 | −1.237 | 1/3 |
| SOL | −0.178 | +1.622 | +0.900 | 2/3 |

**Root cause**: The "overlap" column is the key diagnostic — 73–82% of breakout days TSMOM is also long. Squeezes resolve upward primarily during trending markets; flat/bear markets produce fewer breakouts and those that do occur tend to fail. The signal is a weak, lagged momentum filter, not a distinct vol-regime detector. MaxDD 60–82% confirms the strategy rides out momentum crashes fully (no protective mechanism like TSMOM's vol-targeting). corr(TSMOM) is acceptable at 0.28–0.30, but Sharpe is too low to justify the slot.

**What could salvage it**: Combining with a vol-filter (don't enter when realized vol > 50%/yr), or using a tighter hold period (5d instead of 10d). But these would require further optimization and are speculative.

---

### 6.28 MVRV Z-Score as TSMOM Overlay

**Status**: SKIP — scaler reduces TSMOM returns; IC not significant  
**File**: `strategies/mvrv/feasibility.py`  
**Hypothesis**: MVRV Z-score (market-value-to-realized-value) captures on-chain regime. Scale TSMOM position down in overheated markets (high MVRV), up in undervalued markets (low MVRV). Proxy: `(BTC_close - MA200) / rolling_std(BTC_close, 365)` (Toby Ord approximation; no Glassnode key available).

**Scale thresholds tested**:

| MVRV z-score | Scale factor | Time spent |
|---|---|---|
| z < −0.5 (undervalued) | 1.30× | 23.5% of weeks |
| −0.5 ≤ z < 1.0 (neutral) | 1.00× | 45.9% of weeks |
| 1.0 ≤ z < 3.0 (expensive) | 0.70× | 27.7% of weeks |
| z ≥ 3.0 (bubble) | 0.40× | 2.8% of weeks |

**Results (2021–2026, 356 weeks)**:
- IC (MVRV[T] → BTC return[T+1]): **+0.0172**, t-stat **+0.324** (p=0.75) — not significant
- Sub-period IC: 2021–2023: +0.047 (t=+0.58); 2024–2026: −0.032 (t=−0.35) — inconsistent direction
- TSMOM base Sharpe: **0.349** | TSMOM × MVRV Sharpe: **0.250** — scaler hurts
- Sub-period deltas: 2021–2023: Δ=−0.056; 2024–2026: Δ=−0.147 — worse both periods
- corr(TSMOM signal, MVRV proxy): **+0.400** (MVRV and momentum are co-linear — both high in bull markets)

**Root cause**: The MVRV proxy `(close - MA200) / std365` is directionally correlated with the TSMOM signal (+0.40), because both are high when BTC is in a bull run. The scaler therefore reduces position in bull markets (when TSMOM is right) and increases it in bear markets (when TSMOM is wrong) — exactly backwards. The theoretical MVRV effect (overvaluation predicts reversal) is real at multi-year timescales, but at weekly resolution the momentum dominates and the scaler destroys value.

**Proxy quality caveat**: True Glassnode MVRV uses realized cap (the sum of all UTXOs valued at price when last moved). The proxy MA200/std365 is a 0.40-corr approximation. Even if threshold calibration were improved with real Glassnode data, the structural co-linearity with TSMOM would remain.

---

### 6.29 Funding Rate Momentum (Second Derivative)

**Status**: SKIP — IC not significant; positive only in 8-month bear window (insufficient N)  
**File**: `strategies/funding_momentum/feasibility.py`  
**Hypothesis**: Funding rate *trend* (acceleration) is distinct from funding rate *level* (Strategy B). Signal: `trend[T] = fund_7d[T-1] - fund_14d[T-8]`, z-scored vs 60d rolling baseline. Long when z > 0.5 (funding accelerating), flat otherwise. Tests whether the second derivative of sentiment predicts directional returns.

**Data**: HL BTC funding history (8h intervals). Cached CSV 2024-01–2026-05-10 + API fetch for 2023-05–2023-12 bear period. Combined: 14,181 hourly records (2023-05-12 → 2026-05-16).

**Signal statistics**:
- Signal ON (z > 0.5): 28.9% of weeks
- Signal FLAT (z < −0.5): 30.9% of weeks
- Neutral zone (|z| < 0.5): 40.1% of weeks
- corr(funding level, funding trend): +0.40 (partially co-linear, as expected)

**Results**:
- IC: **+0.0091**, t-stat **+0.111** (p=0.91) — not significant
- Sub-period IC: Bear 2023 (8mo): +0.245 (t=+1.26, n=27); Bull 2024–26: −0.027 (t=−0.30, n=124)
- Full Sharpe: **−0.151** | MaxDD: −32.3%
- Bear (2023-05→2023-12): Sharpe **+0.368** | MaxDD −12.1%
- Bull (2024→2026): Sharpe **−0.324** | MaxDD −28.8%
- corr(strategy returns, TSMOM weekly): **+0.073** ← good, but Sharpe is negative
- corr(signal, TSMOM signal): **+0.266**

**Root cause**: Funding rate acceleration correlates with the onset of funding spikes (leverage build-up) rather than with subsequent price direction. In the 2023 bear period, sharp positive funding spikes coincided with local bottoms (short squeezes → relief rallies) → signal appeared predictive. In 2024–26 bull market, funding is persistently elevated with momentum, making the trend signal essentially a lagged momentum proxy that fires late and suffers reversals. The sub-period inconsistency (2023 IC +0.245 vs 2024–26 IC −0.027) is a regime-specific artifact, not a robust signal.

**Data limitation**: HL funding history starts May 2023. The 2023 bear sub-period has only 27 weekly observations — far too few to establish significance (t=+1.26 ≈ p=0.22). The bull sub-period (n=124) is the more reliable estimate.

---

### 6.30 ORB Crypto v2 — Asian Session Range Breakout

**Status**: SKIP — Sharpe=+0.058 at best; negative expectancy across all filter configs  
**File**: `strategies/orb_crypto_v2/feasibility.py`  
**Source**: Adapted from Fabio Valentini's NQ Opening Range Breakout model  
**Hypothesis**: The Asian session (00:00–08:00 UTC) establishes an equilibrium range when US/EU institutions are inactive. A clean breakout above range_high at 08:00 UTC close, confirmed by two bullish body-ratio candles, predicts continuation into the EU/US overlap session. Entry at 12:00 UTC open; TP = entry + 1× range_width; SL = range_low; EOD close at 20:00 UTC.

**Data**: HL 4h candleSnapshot for BTC + ETH (2024-02-04 → 2026-05-14). 831 unique days, 4,980 bars per coin. HL data gap Dec 2022–Dec 2023 limits the available window to bull market only.

**Filter configs tested**:
- No filter (body_ratio > 0.00): 106 trades, 47/yr
- Mild (body_ratio > 0.20): 65 trades, 30/yr
- Strict (body_ratio > 0.40): 30 trades, 16/yr

**Results**:

| Config | Trades | Win rate | Sharpe | MaxDD | P(EV≤0) | Profit factor |
|---|---|---|---|---|---|---|
| no_filter | 106 | 44.3% | −1.693 | −18.6% | 0.917 | 0.698 |
| mild | 65 | 44.6% | −1.809 | −16.8% | 0.951 | 0.582 |
| strict | 30 | 50.0% | +0.058 | −10.5% | 0.576 | 0.908 |

Exit breakdown (no_filter): EOD 48% / TP 32% / SL 20%. The majority of trades close at EOD without hitting either TP or SL — the continuation move simply does not materialize consistently. Avg loss (−1.59%) > avg win (+1.39%) across all configs, producing negative expectancy.

Sub-period Sharpe (strict filter): 2024 +1.953 (n=8), 2025 −0.056 (n=19). No bear-period data available.

**corr(ORB, TSMOM)**: Not computable — insufficient overlap between daily ORB signals (BTC+ETH only, subset of days) and weekly TSMOM universe. Cannot be evaluated as a diversification source.

**Root cause**: The Asian range breakout mechanism was designed for NQ futures, which have a genuine pre-market equilibrium driven by overnight futures positioning and a defined US open catalyst. Crypto trades 24/7 with no session boundaries of comparable institutional significance. The Asian session range is wider than the NQ pre-market range (crypto overnight vol ≈ 1.5–2× intraday vol due to Asian retail), making breakout signals less reliable. The 4h candle resolution adds further noise: a genuine breakout at e.g. 09:00 UTC and a fake breakout at 07:45 UTC produce identical signals at the 4h level.

**Higher-frequency hypothesis**: The mechanism might work at 1h or 30min resolution (authentic ORB timing), but HL candleSnapshot only provides 4h. This is a data limitation of the test, not a definitive proof of mechanism failure. Verdict remains SKIP because positive evidence is absent.

---

### 6.31 AdaptiveTrend — Multi-Timeframe TSMOM with Adaptive Lookback Weights

**Status**: SKIP — adaptive weights ≈ equal weights; larger universe dilutes alpha; no improvement over fixed 28d  
**File**: `strategies/adaptive_trend/feasibility.py`  
**Source**: AdaptiveTrend (arXiv 2602.11708) — reported Sharpe 2.41 on 150+ pairs  
**Hypothesis**: Softmax weights across [14, 28, 56, 112]d lookbacks, driven by rolling 12-week cross-sectional IC, outperform fixed 28d TSMOM on a larger universe (30 assets vs 10).

**Universe**: Top-30 HL perps by 24h volume. 22 tradable on Binance (HYPE, FARTCOIN, MEGA, VVV unavailable).  
**Data**: Binance daily close, 2021-01-01 to 2026-05-14 (1,963 days).

**Results (full period 2021–2026)**:

| Variant | Sharpe | MaxDD | corrA | corrB (carry) |
|---|---|---|---|---|
| TSMOM-10-fixed (baseline replication) | 0.690 | −6.7% | +1.000 | +0.069 |
| Adaptive-10 (same 10 assets, adaptive) | 0.449 | −6.1% | +0.898 | +0.043 |
| Adaptive-30 (full 30-asset, adaptive) | 0.374 | −11.6% | +0.877 | +0.040 |

**Adaptive weight allocation**: All four lookbacks average ≈ 0.250 (uniform). The softmax IC provides no differentiation — there is no "lookback that recently worked" phenomenon in crypto. Rolling IC between lookbacks is flat throughout the test period, confirming that momentum persistence is regime-driven (all lookbacks work/fail simultaneously within each regime) rather than lookback-specific.

**Replication gap**: TSMOM-10-fixed Sharpe 0.690 vs known TSMOM v3 Sharpe 1.33. Explained by universe composition: the top-10 by HL volume includes ZEC, DOGE, AAVE, TON — noisier than the handpicked BTC/ETH/SOL/BNB/XRP focus assets in TSMOM v3. The mechanism is correct; the asset selection is diluted.

**Sub-period Sharpe (TSMOM-10-fixed replica)**: 2021 +1.73, 2022 −1.17 (bear), 2023 +0.87, 2024 +1.47, 2025 +0.04, 2026 −1.13. Highly regime-dependent.

**Root cause of adaptive weight failure**: In crypto, momentum is a single-regime phenomenon — all lookbacks win in bull, all lose in bear. Cross-asset adaptive trend (arXiv paper) benefits from structural diversity between asset classes (equities respond to different lookbacks than commodities). Within single-asset-class crypto, this structural diversity doesn't exist. The adaptive mechanism degenerates to equal weights.

---

### 6.32 Cross-Sectional Breakout — Robot Wealth Market-Neutral Approach

**Status**: SKIP — L/S Sharpe=+0.036; Robot Wealth negative carry correlation NOT confirmed on crypto  
**File**: `strategies/cross_breakout/feasibility.py`  
**Source**: Robot Wealth (2024) — breakout negatively correlated with carry in multi-asset universe  
**Hypothesis**: CS breakout (long top-5 / short bottom-5 by 21d breakout score on top-20 HL perps) is market-neutral by construction, avoiding the β_crypto problem that killed Donchian (6.16). Robot Wealth predicts negative correlation with carry → genuine Strategy B diversifier.

**Signal**: `breakout_score[i] = close[i] / rolling_max_21d(close[i, past]) − 1`  
Positive = near/above recent 21d high (breakout strength). Negative = far below (weakness).

**P&L decomposition**:

| Leg | Sharpe | MaxDD | Note |
|---|---|---|---|
| L/S total | +0.036 | −80.8% | near-zero net edge |
| Long leg (top-5 by score) | +0.294 | −45.8% | weak positive |
| Short leg (bottom-5 by score) | −0.137 | −92.3% | drag, but Sharpe > −0.5 threshold |
| CS breakout long-only | +0.199 | −65.8% | insufficient |

**Correlation analysis**:
- corrA (vs TSMOM): **−0.416** — L/S is anti-correlated with momentum by construction (long recent leaders / short recent laggards = momentum; this signal does the opposite via the short leg)
- corrB (vs carry proxy BTC+ETH funding): **−0.048** — Robot Wealth's negative carry correlation NOT confirmed in crypto

**Sub-period Sharpe (L/S)**:

| Year | Sharpe | Note |
|---|---|---|
| 2021 | −1.243 | strong momentum destroys short leg |
| 2022 | +1.421 | bear reversal: momentum reverses, anti-momentum profits |
| 2023 | −0.895 | recovery hurts |
| 2024 | +0.419 | mild positive |
| 2025 | +1.602 | choppy market favours mean-reversion |
| 2026 YTD | −2.425 | momentum resumes |

**Root cause**: The CS breakout L/S is mean-reversion / anti-momentum in disguise. The short leg bets against crypto losers — which violently mean-revert (same structural finding as 6.3). Year-by-year performance alternates +/− with no stable regime-independent edge. The Robot Wealth negative carry correlation likely holds in a genuinely diversified multi-asset universe (equities, FX, rates, commodities) where breakout and carry respond to different macro factors. In single-class crypto, all strategies are strongly beta_crypto co-linear — breakout scores are momentum proxies, so the carry-breakout orthogonality does not exist. corrB = −0.048 (near zero) confirms this.

---

### 6.33 Monthly TSMOM on 40 Assets (Cost Reduction)

**Status**: SKIP — monthly rebalance reduces cost but also reduces signal freshness; Sharpe 0.381 < threshold  
**File**: `strategies/monthly_tsmom/feasibility.py`  
**Hypothesis**: Weekly TSMOM costs ~3.5%/yr actual (52 × 0.17% × ~40% turnover). Monthly rebalance drops this to ~0.8%/yr, potentially rescuing the edge on a larger universe. Also tests whether adding assets 11–40 by HL volume provides scale benefits.

**Universe**: Top-40 HL perps by 24h notional volume. 27 tradable on Binance with ≥365 days history (HYPE, FARTCOIN, MEGA, VVV, kPEPE, kLUNC, MON, STABLE and other new/exchange-specific coins unavailable).  
**Data**: Binance daily close, 2020-01-01 to 2026-05-14 (27 assets × 2,329 days).  
**Rebalance**: First trading Monday of each calendar month (77 rebalance dates).  
**Signal**: Equal-weight mean of TSMOM at 1m/3m/6m lookbacks, vol-targeted at 15%, long-only top-10.

**Results**:

| Variant | Sharpe | MaxDD | AnnRet | Cost/yr | 2022 |
|---|---|---|---|---|---|
| Monthly-40 | 0.381 | −122.5%† | 15.7% | 0.78% | −1.763 |
| Weekly-40 (same universe) | 0.533 | −127.4%† | 28.6% | ~3.5% | −1.449 |
| TSMOM v3 (focused 10-asset) | 1.33 | −6.9% | — | — | — |

†MaxDD in cumulative log-return terms over 6-year period with vol-targeted positions.

**Sub-period Sharpe**:

| Year | Monthly-40 | Weekly-40 |
|---|---|---|
| 2020 | +1.160 | +0.860 |
| 2021 | +1.181 | +1.671 |
| 2022 | −1.763 | −1.449 ← bear |
| 2023 | +1.044 | +1.626 |
| 2024 | +0.320 | +0.568 |
| 2025 | −0.423 | −0.340 |
| 2026 | −0.601 | −0.373 |

**Walk-forward** (4 windows): 2020=+1.212, 2021=−0.848, 2023=+0.605, 2024=+0.077 — recent deterioration in both variants.

**Root cause**: Monthly rebalance reduces cost drag (0.78%/yr vs 3.5%/yr) but simultaneously reduces signal freshness — positions held 4 weeks on average vs 1 week, capturing trend reversals that weekly TSMOM would exit quickly. Net result: cost saving is offset by stale-signal losses, leaving Sharpe 0.381. The 27-asset extended universe adds noise (ZEC, XMR, PENDLE, APE behave differently from the focused BTC/ETH/SOL/BNB). The TSMOM v3 benchmark (1.33) requires handpicked liquid assets, not a volumetric top-40 ranking.

**Avg turnover per rebalance**: 58.3% of portfolio (higher than expected — most assets replaced each month, eliminating the assumed cost advantage and confirming signal freshness is the real issue).

**Lesson**: The cost advantage of monthly rebalancing is real (0.78% vs 3.5%/yr), but on TSMOM the cost was never the binding constraint — the Sharpe 1.33 from focused TSMOM v3 already accounts for 3.5%/yr cost. Switching to monthly rebalance decreases signal freshness faster than it reduces costs. Confirmed 6.18 (monthly seasonality) finding: monthly-frequency momentum is inherently weaker than weekly in crypto.

---

### 6.34 Crash Recovery — Dip-Buying with Hard Stop-Loss

**Status**: SKIP — post-crash return is WORSE than unconditional; dip-buying has anti-edge in crypto  
**File**: `strategies/crash_recovery/feasibility.py`  
**Hypothesis**: Large-cap crypto -8% in 3 days triggers forced liquidations creating oversold conditions → mean-reversion snap-back within 5 days. Different from 6.2/6.9/6.11: event-triggered only, hard -5% SL prevents blow-up.

**Assets**: BTC, ETH, SOL, BNB, AVAX | Data: Binance daily OHLCV 2018–2026 (3,059 days for BTC/ETH/BNB)

**Threshold sensitivity grid** (all configs fail):

| Threshold | Hold | n/yr | Win Rate | PF | SL rate | t-stat |
|---|---|---|---|---|---|---|
| −5% | 3d | 168.6 | 36.8% | 0.79 | 54.5% | −1.64 |
| −5% | 7d | 152.7 | 28.8% | **0.81** | 67.0% | −1.64 |
| −8% | 5d | 103.4 | 27.7% | 0.74 | 67.7% | −1.54 |
| −10% | 5d | 78.9 | 26.2% | 0.68 | 69.6% | −1.69 |
| −15% | 3d | 37.6 | 28.7% | 0.69 | 68.6% | −0.61 |

**Statistical test (default -8%/5d)**:
- Post-crash 5d mean return: **−0.131%** (negative)
- Unconditional 5d mean return: **+0.384%**
- Ratio: −0.34× (pass threshold: >2.0×) — dips predict worse-than-unconditional returns
- t-stat: **−1.54**, p=0.12 — anti-edge confirmed

**Sub-period breakdown (default -8%/5d)**:

| Year | n | PF | Mean return |
|---|---|---|---|
| 2018 | 118 | 0.57 | −1.68% |
| 2019 | 51 | 1.42 | +1.30% ← only positive year |
| 2020 | 79 | 0.86 | −0.50% |
| 2021 | 170 | 0.82 | −0.72% |
| 2022 | 152 | 0.48 | −2.04% ← worst (bear crashes continue) |
| 2023 | 46 | 1.11 | +0.34% |
| 2024 | 97 | 0.63 | −1.28% |
| 2025 | 109 | 0.84 | −0.52% |

**Walk-forward** (3 windows): PF=0.81, 0.70, 0.71 — consistent failure, no regime where it works.

**Portfolio P&L**: Cumulative −13.4%, Sharpe −0.604 (full-period), −0.943 (active days only).

**Root cause**: Crypto crash dynamics are fundamentally different from equities. In equities, a −8% 3-day crash often reflects institutional forced selling at temporary oversold prices → snap-back. In crypto: (1) crashes are momentum events — weak projects continue falling; (2) the SL rate of 67.7% confirms empirically that after a −8% crash, the next 5 days reach −5% in 2 out of 3 cases; (3) in 2022 bear market, PF=0.48 — the worst environment is exactly the one where the strategy should theoretically "buy cheap." The strategy is long the most liquidation-prone, weakest assets in the market — the opposite of what vol-targeting TSMOM does (which sizes away from high-vol assets). The one year with positive PF (2019, PF=1.42) coincides with a crypto recovery from the 2018 crash — a different regime.

**Structural confirmation**: `post_crash_mean < unconditional_mean` across all 12 threshold × hold_period configurations. This is not a calibration failure — it's a structural property of crypto: dips continue.

**Lesson**: Event-driven dip-buying is a legitimate equity strategy (VIX spike → buy SPX) because equity crashes are liquidity-driven, not sentiment/leverage-driven. Crypto crashes are predominantly leverage liquidation cascades — the crash signal predicts continuation, not reversal. This is the exact opposite direction needed. Confirmed 6.17 (1-month reversal) and 6.9 (vol-regime MR) structural failures.

---

### 6.35 Extreme Funding Rate Reversal (Contrarian)

**Status**: SKIP — IC is NEGATIVE (wrong direction); extreme funding confirms momentum continuation, not reversal  
**File**: `strategies/funding_reversal/feasibility.py`  
**Hypothesis**: When 8h funding rate spikes to extreme positive (z>+2.5), longs are massively overleveraged → forced deleveraging → price DROP within 5 days. When z<−2.0, short squeeze imminent → price RISE. Signal: `funding_8h_zscore[T] = (funding_8h[T-1] - rolling_mean_30d[T-1]) / rolling_std_30d[T-1]`. Normalization: 8h-equivalent rate regardless of HL's interval switching (8h pre-2024, 1h post-2024).

**Assets**: BTC, ETH, SOL | Data: HL funding history (May 2023 – Apr 2026, 25,782 records) + Binance daily prices

**IC analysis (pooled, |z|>0.3 trigger days)**:

| Hold | IC | t-stat | n | Verdict |
|---|---|---|---|---|
| 1d | −0.0261 | −1.046 | 1,607 | FAIL |
| 3d | −0.0566 | −2.267 | 1,604 | FAIL (wrong direction) |
| 5d | −0.0743 | −3.354 | 1,601 | FAIL (wrong direction, significant) |
| 7d | −0.0889 | −4.191 | 1,591 | FAIL (wrong direction, significant) |

IC definition: `spearman(z, -fwd_return)`, so IC<0 means high positive funding → price RISES (opposite of thesis).

**Backtest results (5d default hold)**:
- Total trades: 241 (46.3/yr) | Win rate: 41.5% | PF: **0.587** | SL rate: 26.6%
- SHORT trades (z>+2.5): n=131, PF=**0.411** — extreme funding → price continues UP
- LONG trades (z<−2.0): n=110, PF=**0.756** — extreme negative funding → price continues DOWN
- Portfolio Sharpe: **−1.484** | MaxDD: −16.5%

**Asset breakdown**:

| Asset | n | PF | Direction |
|---|---|---|---|
| BTC | 78 | **1.163** | Exception: faster arbitrage, funding mean-reverts quickly |
| ETH | 86 | 0.615 | FAIL |
| SOL | 77 | 0.393 | FAIL (most leveraged, momentum strongest) |

**Root cause**: Funding rate is a sentiment momentum proxy. High positive funding → longs are right (it's a bull market) → price continues up. The "forced deleveraging" mechanism requires a large spot arbitrage army ready to short perp and buy spot; at 5d horizon, momentum dominates. The IC direction is not just failing — it's significantly negative (t=−4.19 at 7d). Extreme funding confirms momentum continuation, not reversal. BTC exception (PF=1.163) reflects more liquid arbitrage that actually mean-reverts funding, but insufficient n=78 to be reliable.

**Archetype 3 confirmed**: Funding z-score is a momentum proxy, not a reversal indicator. Joins crash recovery (6.34), CS L/S (6.32), short-term reversal (6.17) — all structural continuations, not mean-reversions.

---

### 6.36 Perp-Spot Basis Mean Reversion (He & Manela 2024)

**Status**: SKIP — PF=0.955, IC negative; basis z-score does not predict perp price direction at 5-day horizon  
**File**: `strategies/basis_trading/feasibility.py`  
**Source**: He & Manela (2024), arXiv 2212.06888 — "High Sharpe ratios even for highest trading cost tier on Binance"  
**Hypothesis**: When Binance perp trades at significant premium to spot (basis_z>+1.5), arbitrageurs buy spot + short perp → convergence. Signal: SHORT perp (bet on convergence). Exit when |basis_z|<0.5 (MR complete) OR 10d max. Basis computed self-consistently from same exchange (Binance perp vs Binance spot).

**Assets**: BTC, ETH, SOL | Data: Binance perpetual futures + spot daily OHLCV (2021-01-01 → 2026-05-10, 1,956 days)

**Basis statistics (Binance perp − Binance spot) / spot × 100%**:

| Asset | Mean% | Std% | Max% | Min% | p5% | p95% |
|---|---|---|---|---|---|---|
| BTC | −0.019% | 0.050% | +0.19% | −0.11% | −0.063% | +0.085% |
| ETH | −0.016% | 0.057% | +0.36% | −0.25% | −0.065% | +0.094% |
| SOL | −0.033% | 0.402% | +0.48% | −16.9% | −0.102% | +0.116% |

**IC analysis (pooled)**:

| Hold | IC | t-stat | n | Verdict |
|---|---|---|---|---|
| 3d | −0.0024 | −0.161 | 4,462 | FAIL |
| 5d | −0.0158 | −1.053 | 4,457 | FAIL |
| 7d | −0.0193 | −1.291 | 4,453 | FAIL |
| 10d | −0.0331 | −2.210 | 4,445 | FAIL (wrong direction) |

**Backtest results (10d max hold)**:
- Total trades: 680 (130.6/yr) | Win rate: 48.2% | PF: **0.955** | Trade Sharpe: −0.190
- SHORT trades (basis_z>+1.5): n=349, PF=**0.831** — perp premium → perp continues UP
- LONG trades (basis_z<−1.5): n=331, PF=**1.089** — slight edge on long side
- MR exit rate: **88.7%** | Avg hold: **1.0d** (mean-reversion fires within 1 day — not the signal)
- SL rate: 11.3%

**Asset breakdown**:

| Asset | n | PF | Note |
|---|---|---|---|
| BTC | 244 | 0.892 | Near-zero basis; low n per signal |
| ETH | 226 | **1.472** | Most consistent basis variation |
| SOL | 210 | 0.740 | SOL negative outlier (−16.9% min basis) |

**Sub-period (2021–2026)**:

| Year | n | PF | Mean% |
|---|---|---|---|
| 2021 | 120 | 0.84 | −0.349% |
| 2022 | 121 | 1.26 | +0.441% |
| 2023 | 135 | 0.73 | −0.353% |
| 2024 | 152 | 0.98 | −0.031% |
| 2025 | 115 | 1.32 | +0.370% |
| 2026 | 37 | 0.38 | −1.311% |

**Root cause**: The Binance perp-spot basis is a microstructure artifact, not a durable pricing anomaly. At daily close prices, the basis is extremely small (Std=0.05% for BTC) — well within the bid-ask spread. The 88.7% MR exit rate confirms the z-score reverts within **1 day** (not 10 days as the paper assumed), which means the strategy is entering and exiting in 1-bar windows where cost (0.17% RT) dominates any gross edge. He & Manela (2024) used mark-to-index basis (which can be 0.5–2% during stress) on a specific dataset; at Binance daily close, the signal has near-zero amplitude. ETH's PF=1.472 is the only exception — insufficient n (226 trades) for standalone viability.

**Key distinction from Strategy B (6.13)**: Strategy B earns FUNDING INCOME by holding a delta-neutral perp+spot position (flow). This trade bets on PRICE CONVERGENCE via a directional perp position (stock). At daily granularity, basis has too little amplitude to provide edge after costs.

---

## 7. FX Research — Negative Results (May 2026)

**Asset class expansion initiated 2026-05-19. n_tests running total: 57 (53 crypto + 4 FX).**

Universe: G10 FX — EUR, GBP, JPY, AUD, CAD, CHF, NOK, SEK vs USD (8 pairs).  
Data: yfinance weekly + FRED 3M interbank rates (DTB3, IR3TIB01* series) — monthly granularity.  
Cost: 15 bps RT (institutional FX, mid-point of retail 20 bps / prime 5 bps).  
Period: 2005-01-14 → 2026-05-15. Script: `Forex/research/archived/fx_carry_fred/`, `fx_momentum_monthly/`, `fx_carry_em/`.

### FX-1: Carry FRED 3M G10 — WEAK / untradeable

**Signal**: carry[ccy] = r_3M[foreign] − r_3M[USD], cross-sectional L/S tercile, weekly.  
**Result**: IC=+0.027, t=+2.02 (**WEAK**), Sharpe=−0.13, MaxDD=−53%.

IC is real (forward premium puzzle confirmed at t=2.02, n=1114 weeks). Strategy is not viable as a raw L/S position. Carry crashes during risk-off events destroy full-sample Sharpe:
- GFC 2008: cumret −9%, MaxDD −24%
- EM unwind 2015: cumret −13%, MaxDD −15%
- COVID 2020: cumret −17%, MaxDD −21% in 15 weeks

Root cause: carry premium distribution is right-skewed with fat left tail (negative skewness). Average week is profitable, but sudden unwind events overwhelm the cumulative carry collected. Raw L/S with no crash protection produces negative Sharpe over 21-year sample. Reference: Brunnermeier, Nagel & Pedersen (2008) "Carry Trades and Currency Crashes".

Remaining hypothesis not tested: carry + trend filter (Asness et al. 2009) reduces MaxDD from −53% to ~−20% by identifying reversals before crashes materialize. Not pursued — see structural conclusion below.

### FX-2: CS Momentum 12M-1M G10 — SKIP

**Signal**: cumret[t-12M : t-1M] / vol_12M, cross-sectional rank, L/S tercile, monthly.  
**Result**: IC=−0.024, t=−0.83 (**SKIP**), Sharpe=−0.06, MaxDD=−42%.

Factor is dead in the 2005-2026 G10 sample. IC is slightly negative (not just zero), indicating mild mean-reversion tendency at monthly horizon. Root causes: (a) post-publication crowding — Menkhoff et al. (2012) used pre-2011 data; the strategy has been extensively replicated since publication; (b) central bank FX interventions systematically reverse trends: SNB CHF floor (2011-2015), ECB QE (2015-2018), BOJ Yield Curve Control (2016-2024) all cap appreciation in the winning currencies and create abrupt reversals in momentum positions. SKIP permanently for G10 FX.

### FX-3: TSMOM tanh 12M G10 — SKIP

**Signal**: tanh(cumret_12M / (vol_12M × sqrt(12))), time-series, monthly.  
**Result**: IC=−0.025, t=−0.87 (**SKIP**), Sharpe=−0.13, MaxDD=−23%.

Same conclusion as FX-2. TSMOM does not transfer from crypto to G10 FX at monthly frequency. In crypto, TSMOM works because no central bank anchor exists — momentum can persist 1-2 years. In G10 FX, central banks actively suppress appreciation in winning currencies, creating systematic reversals against the signal direction. The vol-scaling (tanh) reduces MaxDD from −42% to −23% (useful structural confirmation), but does not rescue the negative IC. SKIP permanently.

### FX-4: Carry G10 + EM (BRL, MXN, ZAR, TRY) — SKIP

**Signal**: same carry as FX-1 extended to 12 pairs. FRED EM tickers: IRSTCI01{BRM/MXM/ZAM/TRM}156N — all downloaded successfully.  
**Result**: 1W IC=+0.001, t=+0.06; 4W IC=−0.022, t=−1.67 (**SKIP**). Sharpe=−0.49, MaxDD=−77%.

Adding EM pairs dilutes and then reverses the G10 carry signal. At 1-week horizon: EM carry IC is zero (peso problem — high rates = anticipated depreciation, no FX gain). At 4-week horizon: IC is negative — high-carry EM currencies (TRY 40-50%, BRL 13%) suffer capital losses over 4-week windows larger than the carry compensates. The 2020 COVID EM unwind: MaxDD −21% in 15 weeks, Sharpe −3.71. Propfirm-compatible on COVID MaxDD alone (−21% < −25% threshold) but full-sample Sharpe −0.49 disqualifies. SKIP.

**Structural FX conclusion (carries forward to equities research)**:
> FX carry IC is real in G10 (t=2.02) but requires crash protection incompatible with raw propfirm rules. FX momentum is permanently dead post-Menkhoff-publication in G10 due to central bank anchor effect. EM carry is dominated by periodic unwind events that reverse 12+ months of carry premium in weeks. TSMOM transfers naturally to assets without central bank anchors (crypto, commodities, equity indices) — not to FX.

---

## 8. Multi-Asset TSMOM Research (May 2026) — ARCHIVED

**Verdict: DID NOT SURVIVE METHODOLOGY CORRECTION. Archived after rigorous re-evaluation.**

### 8.1 Research progression

**Universe**: 10 ETFs — SPY, QQQ, EFA, EEM, IWM (equity), TLT, IEF, SHY (bonds), GLD (gold), VNQ (real estate).  
**Signal**: `tsmom = tanh(cumret_12M / (vol_12M × sqrt(12)))`, monthly rebalance, L/S, weight = signal/n_assets. Cost 5 bps RT.  
**Files**: `Equities/research/archived/multi_asset_tsmom/` — full audit trail preserved.

**Feasibility** (`feasibility.py`): Sharpe 0.43, alpha_ann 3.6% (t=2.4 OLS), residual Sharpe 0.54 → **PASSED** preliminary gates.

**Walk-forward** (`walkforward.py`, 16 OOS windows 2010–2025): median OOS Sharpe 0.78, 69% windows positive, 81% alpha-positive → **PASSED** walk-forward.

**Risk overlays** (`risk_overlays.py`): best variant (Overlay B, −5% per-leg stop): Sharpe 0.62, MaxDD −14.0% — failed −10% propfirm MaxDD gate.

**Multi-horizon** (`multi_horizon.py`, HOP 2013 1M+3M+12M ensemble + Overlay B): Sharpe 0.48, MaxDD −14.5%, EuroCrisis MaxDD −7.1% — improved EuroCrisis significantly but still failed MaxDD gate.

### 8.2 Methodology audit — fatal degradation

`methodology_audit.py` applied 5 simultaneous infrastructure fixes (now **canonical for all future strategies**):

| Metric | Original MH+B | Corrected MH+B | Change |
|--------|--------------|----------------|--------|
| Sharpe | 0.48 | **0.21** | −0.27 |
| Ann ret | 4.9% | 1.9% | −3.0pp |
| MaxDD | −14.5% | **−20.7%** | −6.2pp (worse) |
| Alpha t-stat | 2.4 (OLS) | **1.31 (HAC)** | not significant at 5% |
| Residual Sharpe | 0.52 | **0.30** | below 0.40 gate |
| Directional accuracy | — | **52.0%** | below 53% gate |
| Quintile monotonicity | — | non-monotone (Q5 < Q1 by 0.165%) | fail |
| Convexity β | — | +0.13 (t=0.92) | not significant |
| Gates passed | — | **1/6** | FAIL |

**Root cause of degradation**: Fix 2 (excess returns over DTB3) is the dominant driver — stripping the risk-free rate exposes that much of the headline Sharpe was capturing the equity risk premium from long ETF positions, not pure alpha. Fix 1 (daily vol targeting with 63-day lookback) also increases MaxDD from −14.5% to −20.7% because daily realized vol is more responsive than the original monthly rolling(3).std() estimate — the prior framework was systematically *under-estimating* realized volatility, producing an over-levered strategy.

**Methodological lesson**: consistent with Harvey, Liu & Zhu (2016) "...and the Cross-Section of Expected Returns" — a substantial fraction of published "Sharpe 0.5+" strategies do not survive HAC correction and proper excess-return accounting. Our experience directly replicates this empirically: a strategy with OLS alpha t=2.4 becomes t=1.31 under HAC(6), i.e. not significant at 5% once serial correlation in monthly returns is properly accounted for.

> **DSR formula correction (2026-05)**: Both `walkforward.py` and `risk_overlays.py` used `norm.cdf(z)` instead of `norm.sf(z)`, inverting p-values. Corrected. The DSR gate was structurally impossible to pass at n_tests=64 anyway (SR* benchmark ≈ 0.147 monthly; strategies with annualized SR < ~0.9 all fail).

### 8.3 EuroCrisis 2011 root cause (insight preserved)

EuroCrisis was a **risk-off rotation** (equities down, bonds/gold up), not a correlation breakdown. Peak avg pairwise correlation was 0.32 — well below the Overlay C threshold of 0.50. The actual failure mode was **signal latency**: 12M lookback maintained long-equity positions during a multi-month correction. Multi-horizon (1M+3M+12M) partially addressed this — EuroCrisis MaxDD improved from −16.0% to −7.1% — but full-sample MaxDD worsened under corrected methodology.

**Archive location**: `Equities/research/archived/multi_asset_tsmom/` — all JSON results, summary MDs, and the full 5-file research record preserved.

---

## 9. Strategy Performance Summary

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
| 6.26 | USDT Flow Proxy (Chi 2025) | +0.220 (corr=0.616!) | −17.7% | Research | SKIP (IC t=−0.38; proxy ≠ on-chain inflows) |
| 6.27 | Vol Squeeze Breakout | +0.437 (SOL best) | −81.9% | Research | SKIP (Sharpe < 0.8; 80% overlap with TSMOM) |
| 6.28 | MVRV Z-Score Overlay | 0.250 (base 0.349) | −17.8% | Research | SKIP (IC t=+0.32; scaler hurts TSMOM both periods) |
| 6.29 | Funding Rate Momentum | −0.151 | −32.3% | Research | SKIP (IC t=+0.11; bull sub-period negative) |
| 6.30 | ORB Crypto v2 (Asian Range) | +0.058 (strict filter) | −10.5% | Research | SKIP (negative expectancy all configs; EOD exits dominate) |
| 6.31 | AdaptiveTrend (multi-LB TSMOM) | 0.690 (fixed-28d best) | −6.7% | Research | SKIP (adaptive weights=equal; no improvement over TSMOM v3) |
| 6.32 | CS Breakout L/S (Robot Wealth) | +0.036 L/S; +0.199 LO | −80.8% | Research | SKIP (Sharpe~0; corrB=−0.05, carry correlation not confirmed) |
| 6.33 | Monthly TSMOM (40 assets) | 0.381 | −122.5%† | Research | SKIP (monthly rebalance reduces cost but reduces signal freshness; 58% turnover/month) |
| 6.34 | Crash Recovery Dip-Buying | −0.604 (portfolio) | — | Research | SKIP (post-crash mean −0.131% < unconditional 0.384%; SL fires 68%; t=−1.54) |
| 6.35 | Extreme Funding Reversal | −1.484 | −16.5% | Research | SKIP (IC t=−4.19 wrong direction; extreme funding = momentum, not reversal) |
| 6.36 | Perp-Spot Basis MR (He & Manela 2024) | −0.190 (trade) | — | Research | SKIP (PF=0.955; avg hold=1d; basis amplitude too small vs cost) |

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

### On long-only crypto CS strategies — β-dominance (Lesson 11, 2026-05-23)

Any long-only cross-sectional portfolio of crypto perps has portfolio-level correlation ≈ 0.80–0.85 with Strategy A (TSMOM), regardless of signal-level orthogonality. Tested: MAX factor (IC t=3.06, port corr=0.81), ILLIQ factor (IC t=3.60, port corr=0.84), MAX residualized (IC t=3.72, port corr≈0.80+). Root cause: all top liquid crypto perps share β_crypto ≈ 0.65+. Signal-level Spearman IC is necessary but not sufficient — it measures cross-sectional rank correlation, not portfolio market exposure. Residualizing the signal does not residualize the portfolio. **The only structural escape is delta-neutral execution** (long+short perp legs cancel β_crypto). Any future strategy with |ρ_A| < 0.3 must use delta-neutral design. See `Crypto/research/_meta/lesson_11_beta_dominance.md`.

### On event-count ceiling in threshold strategies (Lesson 12, 2026-05-23)

Pre-flight event-count checks must gate both floor (too sparse → underpowered WF) AND ceiling (too dense → cost overflow). PMR basis mean-reversion: IC t=2.86 at 3d, but 1.5σ threshold fires 12.6% of coin-days (912 events in 2024 for 29 coins) → portfolio always fully deployed → mean hold = 2.9 days → ~97%/year cost drag → Sharpe = −0.55 backtest. Signal is real, strategy is not exploitable at retail taker fees. Break-even requires either maker rebates (<0.03% cost) or threshold ≥3.0σ (yields <20 events/year — below minimum gate). Free-data crypto edge orthogonal to A+B is structurally exhausted at this stage.

---

## 10. Research Priorities

### Signal search status — 65 signals/variants tested (53 crypto + 4 FX + 5 multi-asset variants + 1 methodology audit + 1 NQ ORB feasibility pending), crypto FREE-DATA EXHAUSTED

**All free-data candidates tested. Last 15 signals (6.22–6.36) all SKIP:**
- 6.22 Temporal patterns: SKIP (corr(TSMOM)=0.527; no bucket t>2.5 after MTC)
- 6.23 LSTM 4h: SKIP (AUC=0.64 real, but 117 trades/yr × 0.17% cost-killed)
- 6.24 LSTM weekly: SKIP (intraday edge evaporates at weekly frequency)
- 6.25 STR small-cap: SKIP (IC t=0.99 vs Zaremba's predicted >3.0)
- 6.26 USDT flow proxy: SKIP (IC t=−0.38; Binance volume is price momentum, not inflow signal)
- 6.27 Vol squeeze breakout: SKIP (Sharpe ≤ 0.44; 73–82% overlap with TSMOM)
- 6.28 MVRV Z-score overlay: SKIP (IC t=+0.32; proxy corr(TSMOM)=+0.40; scaler reduces Sharpe both sub-periods)
- 6.29 Funding rate momentum: SKIP (IC t=+0.11; bull-era IC negative; regime-specific bear-only pattern)
- 6.30 ORB Crypto v2 (Asian Range): SKIP (Sharpe+0.058 at best; EOD exits dominate; 24/7 market has no session structure; 4h resolution too coarse)
- 6.31 AdaptiveTrend (arXiv 2602.11708): SKIP (adaptive weights=equal; no improvement over fixed 28d; Sharpe 0.449 < 0.690 baseline replication; universe effect negative)
- 6.32 CS Breakout L/S (Robot Wealth): SKIP (L/S Sharpe=0.036; corrB=−0.048 not negative enough; carry correlation hypothesis not confirmed in single-class crypto)
- 6.33 Monthly TSMOM (40 assets): SKIP (Sharpe 0.381 < 0.533 weekly same universe; 58% monthly turnover eliminates cost advantage; recent 2024–2026 deterioration)
- 6.34 Crash Recovery dip-buying: SKIP (post-crash mean −0.131% < unconditional 0.384%; SL fires 68%; PF<1.0 in 7/9 years; t=−1.54 anti-edge)
- 6.35 Extreme Funding Reversal: SKIP (IC t=−4.19 at 7d — wrong direction; extreme funding = momentum continuation, not reversal; PF=0.587)
- 6.36 Perp-Spot Basis MR (He & Manela 2024): SKIP (PF=0.955; IC t=−2.21; avg hold=1d; Binance basis amplitude ~0.05% Std vs 0.17% RT cost)
- 6.37 CS-FS (cross-sectional funding spread, delta-neutral): SKIP (IC t=1.54, below gate t>2.5)
- 6.38 FRA-DN (funding rate acceleration, delta-neutral): SKIP (IC t=1.01, unstable: 2024 IC=+0.051 vs 2025 IC=−0.061)
- 6.39 PMR (perp-spot basis mean-reversion, threshold event-driven): SKIP (IC t=2.86 at 3d PASS, but 912 events/year at 1.5σ → 97%/yr cost drag → Sharpe=−0.55, MaxDD=−65%. Signal real, strategy unexploitable at retail taker fees. See `Crypto/research/archived/other/pmr_basis/POSTMORTEM.md`)
- 6.40–6.42 OAGF (open auction gap fade at 8h settlement bars, Binance 1h perp, maker ALO): SKIP (IC_daily=−0.189 at 1h, direction correct, but t_HAC=−1.17 — gate −2.5. Root cause: 128 events/year at 0.30% threshold too sparse; reaching t=−2.5 requires ~10 years data. HL candle API has only ~7 months of history. See `Crypto/research/archived/other/oagf/POSTMORTEM.md`)
- 6.43–6.44 ETH MVRV + Exchange Netflow (on-chain, CoinMetrics Community free tier, Phase 1 sanity): SKIP (MVRV IC=+0.11 as MOMENTUM signal — wrong direction for mean-reversion hypothesis, corr_A=0.73. Netflow IC collapses to t_HAC≈0 after HAC correction — 90d accumulation regime autocorrelation → effective N≈73 from 3398 daily obs. Gate 1 FAIL. See `Crypto/research/archived/other/eth_mvrv_netflow/POSTMORTEM.md`)
- 6.45 BTC VRP Deribit — Phase 2 IC (unconditional signal test): SKIP (IC=+0.126, t_HAC=2.35 — borderline, sub-period stability 33%, non-overlapping IC≈0. Proceeded to Phase 3 unconditional as per user GO.)
- 6.46–6.47 BTC VRP Deribit — Phase 3 walk-forward (unconditional always-short straddle 30DTE→14DTE, 184 cycles, 2021–2026): ARCHIVE (Sharpe_HAC=−2.68, 0/13 folds positive. Gross=+4.44%/yr, costs=8.89%/yr, net=−4.46%/yr. Cost/gross ratio 200%. Strategy systematically loses: option fees 49% + bid-ask spread 49% = double the gross VRP premium. Stress: LUNA −0.44%, FTX −2.56% (2 cycles). Synthetic COVID worst-case: −38% of notional. Root cause: GATE 1 unit error — Almeida's 14%/yr VRP is in variance units, not % of underlying notional; after B-S conversion, gross is only 4.4%/yr. See `Crypto/research/archived/options/vrp_deribit/DECISION.md`. Lesson 13 added.)

## Crypto Research — Saturation Map (2026-05)

---

### 6.50 Saturation Summary — 156 Tests, 3 Missions, 4 Archived Families

Between January 2026 and May 2026, this research program ran **156 hypothesis tests** across three sequential missions on crypto perpetual futures and options, mapping the extractable alpha available to a systematic retail trader using exclusively public APIs. Methodology throughout: excess returns over cash rate, HAC Newey-West SE (lag-6), walk-forward validation (≥5 folds, 18m train / 6m test / 3m step), multiple-testing correction (AMTP/DSR per López de Prado 2018), and explicit stress tests on tail events.

The structural conclusion is that **free-data retail alpha on 29-coin Binance/HL perpetuals is exhausted**: every remaining candidate edge requires either institutional execution access (options market-maker rebates, maker fills at sustained scale) or paid proprietary data sources. One live strategy was extracted (Strategy A — TSMOM v3, OOS Sharpe 1.33) and one is in testnet validation (Strategy B — delta-neutral 8h carry, proxy Sharpe 2.0). Limitations: data gap in Deribit DVOL pre-2021 constrains VRP analysis to the post-DeFi-summer period; Phase 2 IC sub-period stability (33% of years positive) suggests potential regime shift post-ETF approval; all costs assume taker execution (no rebate access).

---

### 6.51 Missions Table

| Mission | Family | Universe | Best Gross Sharpe | Net Sharpe HAC | MaxDD | Verdict | n_tests |
|---------|--------|----------|-------------------|----------------|-------|---------|---------|
| **V1 OHLCV** (6.01–6.36) | Long-only CS: MAX factor, ILLIQ, OI-MOM, LSTM 4h, calendar (×36 signals) | Binance/HL 29 perps daily OHLCV | 1.45 (TSMOM → Strategy A); ≤0.65 all others | <0.70 (no non-A signal passed gate) | — | STRUCTURAL EXHAUSTION; Strategy A extracted | ~142 |
| **V2 HL maker** (6.37–6.42) | Delta-neutral CS: PMR basis MR, OAGF gap fade, CS-FS, FRA | HL/Binance 29 perps + Deribit settlement prices | ~0.50 pre-cost (PMR vol-target est.); OAGF IC=−0.195 (preflight STOP) | PMR: −0.551; OAGF: no backtest | PMR: −65.02% | ARCHIVE | 142→151 |
| **V2 On-chain** (6.43–6.44) | ETH on-chain: MVRV z-score, exchange Netflow z-score | CoinMetrics ETH daily 2016–2026 | — (Gate 1 fail before backtest) | — | — | GATE 1 FAIL (wrong direction + HAC deflation) | 151→153 |
| **VRP Deribit** (6.45–6.47) | BTC ATM straddle short, daily delta-hedged via HL perp, unconditional 16d hold | Deribit BTC options + HL perp 2021–2026 | 1.45 raw unconditional (pre-cost) | −2.682 (0/13 WF folds positive) | −0.247% portfolio at 1% sizing; synthetic stress: −37.8% notional/position | ARCHIVE | 153→156 |

**VRP stress note**: the −0.247% MaxDD reflects smooth bleeding at 1% sizing/straddle × 2 concurrent. At realistic sizing for a standalone strategy (2% portfolio), synthetic COVID scenario (BTC −50%/24h, IV×3) → −75.7% portfolio, far exceeding the −15% hard-stop threshold.

---

### 6.52 Structural Lessons — Documented as Theorems

#### L11 — β-Dominance in Long-Only Crypto CS (2026-05-23)

**Statement**: For any long-only rank-weighted cross-sectional portfolio over N≥5 liquid crypto perps, portfolio-level corr(TSMOM) ≥ 0.80, independent of signal-level IC orthogonality.

**Mechanism**: All liquid crypto perps share β_crypto ≈ 0.65+. Rank-weighted long-only selection concentrates in high-β large-cap coins regardless of the ranking criterion. Spearman IC measures cross-sectional rank order within a period; portfolio-level correlation measures time-series co-movement across periods. The two statistics operate on orthogonal dimensions — a signal can produce IC=0.09 and portfolio corr(A)=0.81 simultaneously. Residualizing the signal on TSMOM preserves IC (tested: from t=3.06 to t=3.72) but does not residualize the portfolio's market exposure, because realized long-only holdings still share β_crypto.

**Verified by**: MAX factor — IC t=3.06, signal corr_A=−0.38, portfolio corr_A=**0.81**. ILLIQ (Amihud) — IC t=3.60, signal corr_A=+0.13, portfolio corr_A=**0.84**. MAX residualized on TSMOM_28d — IC t=3.72, signal corr_A≈0, portfolio corr_A=**0.80+**. All delta-neutral CS designs tested (CS-FS, PMR, FRA): portfolio corr_A < 0.08.

**Implication for future research**: Testing long-only CS signals for IC is valid for hypothesis generation. Portfolio simulation without delta-neutral execution is invalid — any resulting corr(A) ≥ 0.50 fails the orthogonality gate structurally, not marginally. Requirement: long-K / short-K perpetual pairs, or perpetual/spot pairs for β cancellation.

---

#### L12 — Event-Count Ceiling in Threshold-Driven Strategies (2026-05-23)

**Statement**: For threshold-entry strategies, a statistically significant IC is necessary but not sufficient for viability. The following must both hold: `E[events/yr] ≥ N_floor` (statistical power) AND `E[events/yr] ≤ gross_edge / (RT_cost × mean_hold_turnover)` (cost overflow ceiling).

**Mechanism**: Prior methodology gated only the floor (sufficient events for IC stability). The ceiling gate was absent. PMR basis at |z| ≥ 1.5σ: 12.6% of coin-days trigger → 912 events/yr across N=29 coins → 4.1 closes/day × 0.17% RT = 0.70%/day = **178%/yr cost drag** vs estimated gross ≈ 16–20%/yr. The IC gate passed (signal is real); the ceiling gate would have rejected before any backtest.

**Verified by**: PMR backtest — IC t=2.86 (floor: PASS, threshold ≥18/yr passed); events/yr=912 (ceiling: FAIL); Sharpe_HAC=−0.551, MaxDD=−65.02%, WF%=0/2.

**Implication for future research**: Pre-flight must compute: `ceiling = max_acceptable_annual_cost / RT_cost`. At 0.17% taker and 5%/yr target net edge, ceiling ≈ 29 events/yr per position. Event-count gates must be stated as intervals [N_floor, N_ceiling], not one-sided. OAGF failed the floor (128/yr below power threshold for t_HAC=2.5 at IC=0.19); PMR failed the ceiling (912/yr above cost-overflow threshold).

---

#### L12b — Autocorrelation Deflation of HAC Statistics (2026-05-23)

**Statement**: For signals derived from persistent regime series (autocorrelation half-life > 30 days), naive t-statistics overstate significance by factor ≈ √(N_nominal / N_effective). HAC correction with lag ≥ max(6, 4√T) is not a robustness check — it is the primary test.

**Mechanism**: Newey-West SE grows with the long-run variance ratio Ω/σ². For a series with positive autocorrelation summing to S = Σ_{k=1}^{L} (1 − k/L)·ρ_k, the correction factor is ≈ 1 + 2S. For exchange netflow with 6–18 month accumulation regimes, the effective sample size N_eff ≈ N_nominal / (1 + 2S) ≈ 73 from N_nominal = 3,398.

**Verified by**: ETH exchange netflow IC (fwd-30d) — naive t=2.58 (N=3,398 daily, would reject H0); HAC(4) t=0.11 (N_eff ≈ 73, indistinguishable from noise).

**Implication for future research**: Any on-chain, macro, or sentiment signal with |ρ_1| > 0.3 (daily lag-1 autocorrelation) requires HAC with lag ≥ max(6, 4√T). For weekly signals with persistent regimes, effective N can fall below 50 from samples exceeding 400 observations. If HAC t < 2.5 at any lag choice in [4, 12], treat as FAIL regardless of naive significance.

---

#### L13 — VRP Unit Conversion: Variance Space → Notional P&L (2026-05-23)

**Statement**: Academic VRP estimates expressed in annualized variance units (DVOL² − RV² space) must be converted to percentage of underlying notional via the B-S approximation before comparing to transaction cost models expressed as % of notional.

**Mechanism**: Short straddle B-S P&L approximation: `Gross% ≈ ½ × N'(0) × VRP_var × T_hold / σ_DVOL`. At DVOL=0.61 (BTC 2021–2026 mean), T_hold=16/365, VRP_var=0.0906 annualized: Gross% per cycle ≈ 0.162% → +4.44%/yr. Almeida et al. (2024) report "BTC VRP ≈ 14%/yr" in variance units — this is not the P&L percentage. Prior GATE 1 analysis used this figure directly against a cost model in % of notional, producing an apparent 14%/yr gross vs 8.9%/yr cost narrative. After unit conversion: actual gross = +4.44%/yr vs costs = 8.89%/yr → net = −4.46%/yr.

**Verified by**: VRP Phase 3 walk-forward — gross annual=+4.44%/yr, cost annual=−8.89%/yr (option fees 49% + bid-ask 49% + hedge 2%), net=−4.46%/yr, Sharpe_HAC=−2.682, 0/13 WF folds positive.

**Implication for future research**: When benchmarking against any academic VRP magnitude, verify: (a) variance units vs volatility units vs % notional; (b) whether delta-hedge costs are included; (c) whether the premium is quoted net of B-S model error. At retail taker fees (0.03% + 0.6% bid-ask per straddle leg), the gross VRP premium is retail-inaccessible. Break-even requires institutional option maker rebates (≈ −0.01% instead of +0.03% per contract notional).

---

#### L14 — Testnet / Short-Sample Sharpe Inadmissibility (2026-05-23)

**Statement**: Sharpe estimates from testnet or paper-trading periods with N < 250 observations are statistically inadmissible as portfolio optimization inputs, independent of the point estimate.

**Mechanism**: `SE(SR) ≈ √((1 + SR²/2) / N)`. At SR=9.64 (Strategy B testnet), N=66 daily observations: SE=0.848, 95% CI=[7.98, 11.30]. The CI width of 3.3 Sharpe units exceeds the plausible long-run range for any liquid continuous-trading strategy. Additional structural contamination: testnet lacks institutional arbitrage capital → funding rates diverge from mainnet reality; 3-month sample cannot distinguish structural alpha from regime-specific carry (Feb–May 2026 = high-funding bull phase).

**Verified by**: Strategy B testnet SR=9.64 (N=66) → recalibrated mainnet proxy SR=2.0 (backtest SR=4.10 × [1−0.30 mainnet friction] × [1−0.20 regime normalization] × [1−0.10 live vs backtest] ≈ 2.06). At SR=2.0 vs 9.64, ERC allocation to B drops from ~68% to ~40%, restoring meaningful weight to A and C.

**Implication**: Use SR(B)=2.0 for all portfolio simulation until N≥250 mainnet daily returns accumulate (review trigger: realized mainnet Sharpe outside [1.0, 4.0] over ≥12 months). Portfolio gate for any new strategy D: Sharpe(A+B+C+D) > 1.10 × Sharpe(A+B+C), computed at SR(B)=2.0.

---

### 6.53 Two-Dimensional Saturation Map

Each column is a structurally distinct failure mode. ✗ = confirmed primary cause; (✗) = contributing but secondary; — = not a binding constraint for this family.

| Family | β-Dominance | Autocorr HAC-deflation | Cost Drag | OHLCV-Contaminated | Tail Risk | Stat. Power |
|--------|:---:|:---:|:---:|:---:|:---:|:---:|
| CS long-only OHLCV daily (V1) | **✗** | — | **✗** (LSTM: 20%/yr floor) | **✗** | — | — |
| CS delta-neutral funding (V2 PMR/CS-FS) | — | — | **✗** (PMR: 178%/yr drag) | — | **✗** (MaxDD −65%) | (✗) |
| Event-driven threshold panel (PMR high-freq) | — | — | **✗** | — | **✗** | **✗** (ceiling) |
| Event-driven gap fade (OAGF) | — | — | — | — | — | **✗** (floor: 128/yr) |
| On-chain valuation (MVRV z-score) | **✗** (corr_A=0.73) | (✗) | — | **✗** (momentum signal) | — | (✗) |
| On-chain flow (exchange Netflow) | (✗) (corr_A=0.51) | **✗** (t: 2.58→0.11) | — | — | — | **✗** |
| On-chain adoption (active addresses — untested) | — | **✗** (expected: slow-moving) | — | — | — | **✗** (expected) |
| Options VRP timing (Phase 2 IC) | — | (✗) (sub-period stability 33%) | **✗** | — | **✗** | **✗** (non-overlapping IC≈0) |

**Interpretation**: Cost drag and statistical power are the two most prevalent failure modes (each appearing 5× as primary failures). β-dominance is structural in all long-only CS designs regardless of signal quality. Tail risk is binding for all strategies with short-gamma or leveraged mean-reversion exposure. No tested family failed for fewer than two independent reasons.

---

### 6.54 Untested Compass Categories

Source: `Crypto/research/_meta/compass/crypto_alpha_landscape_2026.md`. Eight categories remain unexplored by this research program.

| Category | Representative Angle | Required Data Source | Feasibility | Binding Constraint |
|----------|---------------------|---------------------|-------------|-------------------|
| 1. Microstructure & OFI | OFI 10-level, Binance Futures WebSocket | WSS tick stream (Binance public, free) | Low (retail) | Sub-second execution requires co-location; retail accessible only as execution timing overlay, not position signal |
| 4. Cross-asset / cross-exchange | BTC price discovery Coinbase→Binance lead-lag (Shu et al. 2023); CS cross-crypto LASSO (Jia et al. 2023) | Multi-venue WebSocket, sub-second timestamps | Medium | Lead-lag window < 5s for HF variant; multi-day CS variant feasible but L11 applies |
| 5. Sentiment / narrative | Fear & Greed z-score divergence vs price; Google Trends crypto | alternative.me API (free); pytrends | Medium | Daily granularity; L12b autocorrelation risk (sentiment regimes persistent); prior V1 fear/greed signal failed at cost/signal ratio |
| 6. Macro / cross-market | ETF flow signal (Farside.co.uk) + stablecoin supply (DeFiLlama) as regime filter | FRED API + DeFiLlama stablecoins endpoint (both free) | Medium | Non-stationary BTC–NDX loading post-ETF inclusion; BTC–QQQ corr peaked at 0.87 (2024); regime signal requires HAC from day 1 |
| 7. Calendar / event-driven | Token unlock cliff short (Keyrock 2024: 16,000+ events); short post-listing micro-cap (Empirica 2024 inversion documented) | TokenUnlocks.app (free); Binance Announcements RSS | Medium | L12 floor applies per coin; 2024 data shows naïve listing-long inverted (−22.7% at 3m); short variant requires per-event statistical screening |
| 8. DEX-specific edges | HLP Hyperliquid vault flow contrarian; Uniswap V3 LP active rebalancing (Loesche et al.: 50% of V3 LPs underperform HODL) | HL API public; Uniswap subgraphs via The Graph (free with rate limit) | Medium | Pure MEV fully saturated by professional searchers; LP management feasible; requires web3.py + gas cost model; IL complicates P&L accounting |
| 9. Alternative data | Wikipedia pageviews z-score (Kristoufek 2013 prior); GitHub commit velocity as dev proxy | Wikimedia REST API + GitHub REST API (both free, no key required) | High | Very low institutional competition; slow-moving series → L12b autocorrelation risk; daily granularity caps signal frequency |
| 10. ML / feature engineering transfer | Cross-sectional SHAP-universal model: OFI+spread+VWAP (Bieganowski-Ślepaczuk 2025 show same SHAP structure across BTC/ETH/SOL/alts) | Binance tick stream (public WebSocket) | Low–Medium | L11 applies unless delta-neutral execution; tick data infra cost; requires TimeSeries CV to avoid regime-shift overfitting |

---

### 6.55 References

1. Almeida, C., Grith, M., Miftachov, M., Wang, C. (2024). "Risk Premia in the Bitcoin Market." arXiv:2410.15195. *(VRP magnitude benchmark; L13 unit error source)*

2. Schmeling, M., Schrimpf, A., Todorov, K. (2023). "Crypto Carry." BIS Working Paper No. 1087. *(Funding carry baseline ~7–8%/yr; Mission 2 prior)*

3. López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley. *(AMTP / Deflated Sharpe Ratio methodology used throughout)*

4. Harvey, C. R., Liu, Y., Zhu, H. (2016). "…and the Cross-Section of Expected Returns." *Review of Financial Studies* 29(1):5–68. *(HAC necessity rationale; t>3 bar for published factors)*

5. Bieganowski, B., Ślepaczuk, R. (2025). "Universal features of price formation in financial markets." arXiv:2602.00776. *(OFI/VWAP SHAP universality across crypto assets; ML transfer prior)*

6. Drogen, S., Hoffstein, C., Otte, J. (2023). "Cross-Sectional Momentum in Crypto Assets." SSRN:4322637. *(30d→7d CS momentum prior; V1 methodology comparison)*

---

**N_tests cumulative: 156** (prior 153 + 1 Phase-2 IC + 2 Phase-3 WF cycles)
**E[max_SR] at N=156: ≈ 4.34** (marginal increase, no meaningful change)

**Extended structural finding** (confirmed across 44 signals): In crypto, all free-data standalone strategies are either:
1. **Regime co-linear with TSMOM** (calendar patterns, adaptive trend, breakout, MVRV, active addresses) — work in bull, fail in bear, corr > 0.4
2. **Cost-inaccessible at retail fees** (LSTM, residual MR, STR, basis MR) — real AUC/IC but n_trades × fee > gross return OR signal amplitude < cost
3. **Mean-reversion into momentum** (crash recovery, CS L/S, funding reversal, basis z-score, MVRV) — funding, basis, and on-chain cycle signals are momentum proxies; reversion bets are anti-edge
4. **Autocorrelation-deflated to zero** (exchange netflow, stablecoin supply) — regime persistence makes effective N << nominal N; HAC destroys t-stat
4. **Cross-sectional orthogonal but Sharpe < 1.0** (XGBoost CS, 0.734) — only approach that escapes TSMOM co-linearity

**Key new finding (6.35+6.36)**: Both extreme funding (6.35) and perp-spot basis (6.36) produce IC in the **wrong direction** — they predict the opposite of what theory suggests. This confirms the archetype: in crypto, both funding and basis are **momentum proxies** (high when sentiment is bullish), not **dislocation indicators** (high when price is stretched beyond equilibrium). Arbitrage convergence does not happen at 5-day horizons.

**Conclusion**: Published multi-asset strategies do not transfer to single-class crypto because the structural properties (regime co-linearity, lack of cross-asset diversification, 24/7 trading, funding-momentum coupling) are fundamentally different. Two strategy archetypes remain untested:
- **Paid data**: Glassnode on-chain stablecoin flows (true mint/burn on-chain, ~$500/mo) — theoretical zero TSMOM corr
- **Alternative prop firm**: FTMO (5% daily DD vs Propr's 3%) — structural ceiling fix, not a new signal

**Crypto free-data exhaustion confirmed (2026-05-23)**: After dedicated orthogonality-focused search (39 signals), the conclusion is definitive — no additional strategy with |ρ_A|<0.3 AND |ρ_B|<0.3 AND Sharpe>0.7 exists in the free-data crypto perp universe. Next viable crypto research requires either paid data (Glassnode) or institutional execution infrastructure (maker rebates).

**Interim Strategy C**: XGBoost CS (6.21, Sharpe 0.734, corr=+0.003) — no better candidate found after 39 signals.

### Immediate
1. **FTMO compatibility analysis** (now Priority #1). FTMO: 5% daily DD limit vs Propr's 3%. Run 44-path simulation with FTMO rules (trailing HWM, 10% profit target, 10% total DD, 5% daily DD). Expected pass rate: 55–65% vs current 39% Propr ceiling. This is the highest-leverage next step given the structural ceiling found in Strategy C search.
2. **Glassnode stablecoin inflow data** (paid, ~$500/mo): Only remaining untested hypothesis with theoretical zero TSMOM correlation. True Tether mint/burn on-chain flows to exchanges. Not testable with free APIs.

### Medium term
3. **Re-examine A+B portfolio**: Carry (B) OOS still only 3 months, Sharpe possibly inflated. Re-run A+B+C(XGBoost) comparison once 6 months OOS accumulates (around Aug 2026).
4. **XGBoost CS improvements**: The accepted Strategy C (6.21) had Sharpe 0.734. Consider feature additions (order book imbalance from HL, open interest) before live deployment.

### NQ ORB Strategy C — RESEARCH_PASS → paper trade phase (May 2026)

**Strategy**: NQ Opening Range Breakout iter_10 = VWAP + A$400 dollar stop + B1.2% gap filter + M1(rng≥30pt).  
**Edge**: Opening range momentum with VWAP confirmation. Signal fires when the 09:30–09:45 ORB close is above/below the cumulative VWAP AND gap is below 1.2% AND range ≥ 30pts. Entry at 09:46, bracket order TP=1.5×range / SL=0.5×range (capped at 20.95pts). Time stop 12:30.

**Backtest** (Kaggle 1-min NQ, Dec 2022–Dec 2025, 346 trades):
| Metric | Value |
|---|---|
| Sharpe (annualised) | 1.52 |
| MaxDD (trailing) | −13.4% |
| Walk-forward (6M train / 3M OOS, 9 windows) | 7/9 positive (78%) |
| OOS total P&L | $41,961 |
| Median OOS Sharpe | 1.720 |

**Research gates**: RESEARCH_PASS (Sharpe≥1.0 ✓, WF≥55% ✓, MaxDD≥−20% ✓, P(EV≤0)<0.05 ✓). MaxDD gate at −10% propfirm threshold: FAIL (−13.4% < −10%).

**Signal refinement** (iter_10 vs iter_05): H3 range quartile (Kruskal-Wallis p≈0.000) was the only statistically robust conditioning variable (Bonferroni k=6, p*=0.0083). M1 filter rng≥30pts adopted: ΔSharpe=+0.31, WF%=78%≥67% baseline. 5 other hypotheses (DOW, VIX, trend, direction, 30-min ORB) all FAIL Bonferroni.

**Propfirm compatibility v2** (stationary block bootstrap L=20, 10K paths × 60 days, fixed DD rules):
| Account | Sizing | C1 P(bust)<10% | C3 P(target)>40% | C4 MaxDD<8% | Binding |
|---|---|---|---|---|---|
| $50K | 5 MNQ | ✓ 0.0% | ✗ 12.3% | ✓ 6.2% | C3 (sizing too small) |
| $50K | 10 MNQ | ✓ 4.2% | ✓ 45.7% | ✗ 12.4% | **C4** |
| $100K | 10 MNQ | ✓ 0.0% | ✗ 12.3% | ✓ 6.2% | C3 (sizing too small) |
| $100K | **20 MNQ** | **✓ 4.0%** | **✓ 46.0%** | **✗ 12.4%** | **C4** |

**No config passes all 4 criteria** — binding constraint is C4 (trailing max_dd=12.4% > 8% buffer threshold). Note: C4 uses trailing DD (peak-to-trough over full backtest). Under actual FIXED propfirm rules, the worst historical 60-day window has a fixed DD of only 2.2% from window start (challenge start) — the strategy never breaches the 10% hard floor in any historical 60-day window. P(daily>5%) = 0.0% at all sizings (structural: dollar stop cap limits max single-trade loss to 0.88% at 20 MNQ/$100K).

**Block bootstrap note**: block P(bust) < iid P(bust) at most sizings (−1.5 to −4.9pp). The strategy's serial correlation structure reduces bust risk relative to iid assumptions.

**Recommended sizing**: **$100K / 20 /MNQ** (best available, 3/4 criteria). E[monthly P&L] = $2,413. Median days to 10% target = 32.

**Live infrastructure**: `Futures/live/strategy_c_live/` — 6 files (config, ibkr_client, signal_engine, log_trade, run_daily, validate). Key design: 1-min bars from IBKR (`useRTH=True`), VWAP computed on 1-min ORB bars (exact match to backtest, closes sim-to-live gap). Validation: Test 2 (signal engine) = 10/10 = 100% match, TP/SL diff = 0.00 pts. Tests 1+3 pending TWS connection.

**Status**: RESEARCH_PASS. Paper trade phase pending TWS validation (Tests 1+3).  
`Futures/research/active/nq_intraday/`. n_tests = 82+. Path: `iter_10_refined.py`, `propfirm_compat_v2.py`.

---

### ORB IVB on NQ — ARCHIVED (May 2026)
5. **Opening Range Breakout on NQ futures** (Fabio Valentini IVB model, Matteo Conti 2024): ARCHIVED. Delta-free variant on Kaggle 1-min data (2022-12-26 to 2025-12-11, 736 clean sessions): **WR 53.4%, PF 0.97 (5m) / 1.02 (1m), Sharpe −0.44 / −0.09, MaxDD −28.6% / −21.6%**. 0/5 propfirm gates passed. Delta filter confirmed to be the edge in Conti's system (WR gap: 53.4% vs Conti 58.3%). Archived — revisit only if Databento subscription ($30/mo, real per-bar delta) becomes warranted. `Futures/research/archived/orb_ivb_nq/`. n_tests = 68.

### Pairs trading cointegration — ARCHIVED (May 2026)
5c. **Pairs trading cointegration** (19 pairs across 4 categories, daily, EG+Johansen+HL+Hurst screening): **0/19 pairs qualify** under rigorous statistical tests. Binding constraint: half-life > 30 days for all pairs (median HL ≈ 200 days). Root causes: (a) expense ratio drift makes same-index ETFs appear non-cointegrated over 15-year samples despite short-run mean reversion; (b) business model divergence makes fundamental equity pairs revert over months, not days. Closest: V/MA (HL=96d, EG p=0.075, Johansen trace 14.19 vs crit 15.49). No backtest triggered (n_tests unchanged at 71). `Equities/research/archived/pairs_cointegration/`. Archived May 2026.

> **Methodological insight**: Classic price-level cointegration (EG + Johansen, daily data, HL ≤ 30 days) does not find statistically valid pairs in a diversified US equity/ETF universe. The academic literature's success relies on high-frequency data, very large automated universes (hundreds of pairs), or structural arbitrage pairs (ADRs, dual-listed, merger arb). A 19-pair daily universe with strict screens is insufficient.

### Pairs trading distance method (Gatev 2006) — ARCHIVED (May 2026)
5d. **Pairs trading distance method (Gatev 2006 / Zhu 2024)** (96-stock SP100 proxy, daily, T20/T100/L75 variants): **All 3 variants FAIL** — Sharpe −0.44 / −0.53 / −0.97, negative alpha (t_HAC −2.2/−2.5). Monthly return: −0.027% to −0.116% vs Zhu 2024 benchmark +0.426%/+0.461%. Walk-forward: 3/9 OOS years positive (33%). The MOM loading confirms correct contrarian implementation (coeff −0.10, t=−9.8, matches Zhu), so failure is structural, not algorithmic. n_tests = 71→74. `Equities/research/archived/pairs_distance_gatev/`. Archived May 2026.

> **Root cause**: (a) **Survivorship bias** — SP100_2015 is a static forward-looking list; stocks that delisted 2012–2024 are absent, inflating past pair quality. (b) **Universe concentration** — 96 stocks vs 500–3000 in CRSP literature; fewer diversifiable pairs reduces the law-of-large-numbers benefit. (c) **Strategy decay post-2013** — academic arbitrage capital eroded the distance-method edge as the strategy became widely known; walk-forward shows 2019–2024 nearly all negative. Daily yfinance data cannot replicate CRSP's survivorship-free universe.

### VIX term structure carry — ARCHIVED (May 2026)
5b. **VIX term structure carry** (VXX/VIXY, daily, 3 variants): Sharpe HAC 0.67 / 0.50 / 0.46 (raw / VT / VT+stop). MaxDD -54.2% / -15.9% / -17.1%. Mild contango regime (29% of days) destroys edge — signal only works at extremes. Alpha vs short-VIXY naïve: t_HAC = 0.71 (timing adds minimal value vs passive variance risk premium harvesting). Archived May 2026. `ETF_Vol/research/archived/vix_term_carry/feasibility.py`. n_tests = 68→71.

> **Methodological insight**: Variance risk premium exists empirically and is observable in VIX term structure, but ACTIVE TIMING of the regime (long backwardation, short contango) does not statistically outperform a static short-VIX position with conservative sizing. The premium is a static factor, not a timeable signal. This generalizes a broader principle: not every persistent return is a tradeable timing signal.

### Cross-sectional sector reversal — ARCHIVED (May 2026)
5f. **Cross-sectional sector reversal** (11 SPDR sector ETFs, weekly rebalance, 4 variants: V1 pure / V2 filtered / V3 VT / V4 both): **All 4 variants strongly FAIL** — best Sharpe −0.60, MaxDD −91.5%, only 3/19 OOS years positive (16%). Alpha vs EW sectors: t_HAC = −3.7 (significant **negative** alpha — strategy actively destroys value). n_tests = 78→82. `Equities/research/archived/sector_reversal_cs/`. Archived May 2026.

> **Root cause — wrong granularity**: Jegadeesh (1990) / Lehmann (1990) documented reversal in **individual stocks** driven by microstructure liquidity provision. At sector ETF level, these effects cancel out by aggregation. Only 11 sectors also provides insufficient cross-sectional dispersion. The 13%/yr annual cost drag (weekly ETF turnover at 4 bps/leg) structurally destroys any residual gross return (~3.3%/yr estimated gross). The SRV factor loading is +0.158 (t=1.02) — correct direction but not significant. The reversal effect at sector level is completely dominated by commodity-sector momentum (XLE/XLB lose −20% to −24% cumulative from failed reversal trades against genuine oil/metals trends). This strategy requires individual stocks with intraday execution, not sector ETFs at weekly frequency.

### Commodity TSMOM (Hurst-Ooi-Pedersen 2017) — ARCHIVED (May 2026)
5e. **Commodity TSMOM** (12 commodity ETFs, daily prices / monthly rebalance, 4 variants: A1/A2 single-horizon + B1/B2 multi-horizon 1M+3M+12M): **All 4 variants FAIL** — best variant (A1, single-horizon) Sharpe 0.39, Ann +1.3%, MaxDD −6.5%. Research gates: 4/6 (fails Sharpe <0.7, AMTP p=0.808). `Commodities/research/archived/commodity_tsmom/`. n_tests = 74→78.

> **Root cause — ETF roll drag vs direct futures**: The HOP 2017 paper uses direct commodity *futures* contracts. ETF proxies (USO, UNG, SLV, etc.) systematically embed negative roll yield in contango markets — the price series reflects daily loss from rolling near-term futures into further-dated contracts. **Critical evidence**: 2022 inflation surge (oil +66%, NG +175% peak gains) produced −0.67% for the strategy, when it should have been the strongest year. The H2 2022 reversal (oil −42% peak→Dec, NG −75%) hurt with monthly rebalance, but the deeper issue is that ETF price-series trend ≠ futures roll-adjusted trend. The directional accuracy (51%) is below the 53% threshold and the AMTP p=0.808 confirms this is indistinguishable from a false positive in a 78-test search. Replicating HOP properly requires futures continuous contract data (Quandl/QuantConnect, $50-200/mo).

### Prop firm expansion
6. **FTMO crypto**: Run 44-path sim with FTMO rules. Key structural differences: trailing HWM (harder to recover), 5% daily limit (more survivable on crash days), scaling plan available. **Priority #2** given the 39% Propr ceiling.

> **n_tests counter**: **82** as of May 2026 (53 crypto + 4 FX + 5 multi-asset variants + 1 methodology audit + 1 NQ ORB SPY proxy + 1 NQ ORB 5-min + 1 NQ ORB 1-min + 3 VIX term carry variants + 3 Gatev pairs variants + 4 commodity TSMOM variants + 4 sector reversal variants = 82 total). Walk-forward windows and feasibility validation are NOT separate trials. DSR renamed → `approx_multi_test_penalty` (honest naming).

### Two-tier validation framework (effective May 2026)

All research uses two distinct pass thresholds reflecting different deployment contexts:

| Gate | **RESEARCH_PASS** (hedge-fund grade) | **PROPFIRM_PASS** (Propr deployment) |
|---|---|---|
| Sharpe HAC | > 0.7 | > 1.0 |
| MaxDD | < −25% | < −10% |
| Walk-forward % positive years | ≥ 50% | ≥ 60% |
| Alpha t_HAC vs SPY | > 1.5 | > 2.0 |
| AMTP p-value | < 0.20 | < 0.10 |
| Corr to BTC | < 0.5 | < 0.3 |
| Worst month | — | > −5% |

**Rationale**: Prior framework used propfirm gates only. This discarded potentially valid diversifiers (e.g. strategies with Sharpe 0.7–1.0 that fail the 1.0 propfirm threshold). The two-tier framework separates "is there real edge here?" (RESEARCH_PASS) from "can this be deployed at Propr today?" (PROPFIRM_PASS). A RESEARCH_PASS result stays in the candidate pool for portfolio construction even if not immediately deployable solo.

**Re-evaluation of archived strategies under new framework:**

| Strategy | Sharpe | MaxDD | WF% pos | Alpha t | AMTP p | Research? | Propfirm? |
|---|---|---|---|---|---|---|---|
| Multi-asset TSMOM (corrected) | 0.21 | −20.7% | ~50% | 1.31 | n/a | FAIL | FAIL |
| VIX carry Variant A (raw) | 0.67 | −54.2% | 71% | 0.71 | 0.674 | FAIL (alpha) | FAIL |
| VIX carry Variant B (VT) | 0.50 | −15.9% | 71% | 0.71 | 0.674 | FAIL (Sharpe) | FAIL |
| Pairs cointegration | — | — | — | — | n/a | FAIL (0 pairs) | FAIL |
| Pairs Gatev (T100 best) | −0.44 | −10.7% | 33% | −2.2 | 1.0 | FAIL | FAIL |
| Commodity TSMOM (A1 best) | 0.39 | −6.5% | 62% | 1.59 vs DBC | 0.808 | FAIL (Sharpe, AMTP) | FAIL |
| Sector reversal CS (V1 best) | −0.60 | −91.5% | 16% | −3.7 vs EW | 1.0 | FAIL (all gates) | FAIL |

No archived strategy passes RESEARCH_PASS. VIX carry Variant A is the closest miss (Sharpe 0.67, WF 71% — fails alpha t threshold 0.71 < 1.5). Commodity TSMOM: 4/6 research gates pass but Sharpe 0.39 < 0.7 and AMTP p=0.808 disqualify it; ETF roll drag is the structural issue (requires futures data to replicate HOP properly).

**Sharpe HAC formula note**: All scripts use `mean/σ × √annual_factor` (standard Sharpe). HAC is applied only to alpha t-stats via regression. The `sharpe_hac()` in commodity TSMOM uses correct LRV extraction (`cov_params[0,0] × n`). Prior scripts use simple daily Sharpe — consistent and correct.

### Methodology standards (effective May 2026)

**All future research scripts MUST apply these 5 fixes simultaneously:**

1. **Excess returns**: subtract daily RF (FRED DTB3: `rf_daily = (1+DTB3/100)^(1/252) - 1`) from all asset returns before any P&L calculation or OLS regression
2. **HAC standard errors**: use `statsmodels sm.OLS().fit(cov_type='HAC', cov_kwds={'maxlags': 6})` for all alpha t-stats; plain OLS t-stats are inadmissible for monthly series with serial correlation
3. **Daily vol targeting**: compute portfolio P&L from daily weights × daily excess returns → 63-day rolling std × √252 → sample at month-ends. Do NOT use `monthly_returns.rolling(3).std()` — that is monthly vol on monthly returns, inconsistent frequency that systematically under-estimates realized vol
4. **TSMOM diagnostics** (when applicable): (a) directional accuracy ≥53% gate, (b) quintile bucket monotonicity (Q5 > Q1), (c) convexity test regressing on |SPY_return| with HAC SE — positive β required for trend-following payoff profile. Note: these are TSMOM-specific; for other strategy types use appropriate IC / bootstrap tests
5. **Honest naming**: `approx_multi_test_penalty` (not "DSR") — the BLP formula is a simplified approximation assuming i.i.d. returns and independent tests; document limitations clearly in every script

---

## 11. Prop Firm Landscape (May 2026)

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

## 12. Quick Start

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
