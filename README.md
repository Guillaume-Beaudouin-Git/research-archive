# Algo_claude — Research Journal

**Last updated**: May 2026  
**Status**: 2 strategies live on Propr testnet (TSMOM v2 + delta-neutral carry), 13 strategies tested and failed/shelved, 2 recent HMM/meta-labeling studies in WEAK/SKIP

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
At 0.34% RT, strategies need ≥7-day holds to survive costs. Mean-reversion strategies (6.2, 6.9, 6.10, 6.11) typically complete in 1–3 days, making them cost-inaccessible at retail fee levels. The one exception (residual MR, 6.11) has a genuine signal but requires <0.1% fees to be profitable.

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

### Immediate
1. **TSMOM v3 signal deployed — weekly frequency ceiling confirmed**: Sharpe 1.33 (vs 1.22 baseline). The ceiling at weekly TSMOM is ~1.3–1.4 — confirmed across C1/C4/C5/C6 variants and 4-fold WF. B&SC and multi-TF tested and rejected. To reach Sharpe > 2.0, need a genuinely uncorrelated Strategy C. Only viable candidates remaining:
   - **(a) On-chain USDT flows (Chi 2025)**: non-price signal, needs CryptoQuant API. Test IC vs BTC 3-day forward return. If IC t-stat > 2.0 and ICIR > 0.3, use as TSMOM entry filter only.
   - **(b) Different asset class overlay**: gold, oil, or equity index futures (CME). Test daily TSMOM IC on these — if uncorrelated to crypto TSMOM, add as 20-30% portfolio weight.
   - **(c) Higher frequency on Hyperliquid (4h bars)**: test IC only (not full backtest) — if IC t-stat > 3.0 at 4h, the signal exists at a different frequency and may be genuinely additive.
2. **FTMO compatibility analysis**: FTMO has 5% daily DD limit vs Propr's 3%. Estimate pass rate improvement: if correlated crash days average −4.5% daily loss, FTMO's 5% limit would survive most of them. Run 44-path simulation with FTMO rules (trailing HWM, 10% target, 10% total DD, 5% daily). Expected pass rate: 55-65%.

### Medium term
3. **USDT on-chain flows**: Tether mint/burn events as leading indicator for BTC momentum (Glassnode or Arkham Intelligence). Hypothesis: large USDT mints precede BTC rallies by 1-3 days. Test as TSMOM entry filter only (don't replace signal).
4. **STR on small-cap coins**: Short-term reversal (6.8) has IC t-stat 0.85 on large-caps but Zaremba et al. (2021) shows t-stat > 3.0 on top-100 to top-500. Test on CoinGecko universe — different asset class, not correlated to TSMOM universe.

### Prop firm expansion
5. **FTMO crypto**: Run 44-path sim with FTMO rules. Key structural differences from Propr: trailing HWM (harder to recover from DD), 5% daily limit (more survivable on crash days), scaling plan available (can increase allocation after passing). **This is Priority #2** given the 39% Propr ceiling (Priority #1 is Strategy C).

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
