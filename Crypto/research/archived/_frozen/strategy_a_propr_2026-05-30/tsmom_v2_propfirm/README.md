# TSMOM v2 — Prop-Firm Adapted Variant

Time-Series Momentum adapted for prop-firm evaluation constraints (Breakout / HyroTrader rules).

---

## Changes from v1

| Dimension | v1 | v2 |
|-----------|----|----|
| Universe | BTC, ETH, SOL (3 assets) | 14 assets (see below) |
| Rebalance | Monthly | Weekly (every Monday UTC 00:00) |
| Signal | sign(28-day return) | sign(28-day return) — **unchanged** |
| Direction | Long + Short | **Long-only** (shorts suppressed) |
| Vol target | 15% fixed | 15% live / 35% challenge (via `CHALLENGE_MODE` flag) |
| Vol lookback | 30-day | **20-day** (faster response to regime changes) |
| Daily DD limit | None | **4.5%** auto-flatten kill switch |
| Total DD limit | None | **9.0%** auto-flatten kill switch |
| Stop-loss | None | Hard stop at `entry × (1 − 2 × daily_vol)` on exchange |
| Challenge tracking | None | SQLite: `trading_days_counter`, `challenge_pnl_tracker` |

### Why long-only?
v1 backtest showed short crypto TSMOM does not generate positive alpha after
realistic costs (0.17% round-trip). Crypto bear markets are sharp and brief;
by the time the 28-day signal flips negative, the drawdown is largely over.
Suppressing shorts also avoids unlimited-loss risk that prop firms penalise.

### Universe (14 assets)
Core: **BTC, ETH, SOL**
Top Hyperliquid perps by open interest: **AVAX, LINK, DOGE, ADA, DOT, UNI, LTC, BCH, MATIC, OP** (May 2022), **ARB** (Mar 2023)

Assets with limited history are handled gracefully — they contribute to the
portfolio only once sufficient warm-up data exists.

---

## File Structure

```
strategies/tsmom_v2_propfirm/
├── config.py        # All parameters — universe, vol targets, guardrails
├── signal.py        # compute_signal() + apply_weekly_rebalance()
├── sizing.py        # compute_vol_scalars(), compute_positions(),
│                    # apply_guardrails(), compute_stop_price()
├── backtest_v2.py   # Full backtest (run directly: python backtest_v2.py)
├── README.md        # This file
└── __init__.py      # Public API exports
```

---

## Running the Backtest

```bash
cd ~/Desktop/Algo_claude
source <HOME>/Desktop/Unholy\ returns/Python3.12.9/myenv/bin/activate
python -m strategies.tsmom_v2_propfirm.backtest_v2
```

Output files are written to `outputs/`:
- `tsmom_v2_equity_drawdown.png` — equity curve + drawdown panel
- `tsmom_v2_monthly_heatmap.png` — monthly returns heatmap
- `tsmom_v2_per_asset_sharpe.png` — per-asset Sharpe bar chart

---

## Backtest Results (2019–2024, 15% vol target)

Data quality note: yfinance log returns are clipped at ±1.0 (max ±172% daily) to
handle listing-day artifacts for newer tokens (UNI, OP, ARB).

| Metric | v1 (3 assets, monthly) | v2 (14 assets, weekly) |
|--------|------------------------|------------------------|
| Sharpe (portfolio) | 1.37 | **1.84** |
| Ann Return | — | **+22.8%** |
| Max DD (unguarded) | — | **−13.5%** |
| Calmar | — | **1.70** |
| Avg active days / 30d | — | **25.9 ✓** (≥8 required) |
| Trades / year | ~15 | **~49** |
| Return correlation v1↔v2 | — | **0.67** |
| Walk-forward folds positive | — | **10/10** (avg Sharpe 2.00) |

**Per-asset Sharpe (top performers):** SOL 1.88 · BTC 1.57 · ETH 1.47 · AVAX 1.27 · DOGE 1.36

**2022 bear year:** portfolio returned +1.2% while BTC B&H did −64.3%

**Max DD note:** The −13.5% portfolio max DD occurs over multiple days in 2024's
volatility spike. In live trading, the 9% total DD guardrail flattens all positions
before reaching this level. Individual 6-month walk-forward folds show max DD
of −3.1% to −9.1% — well within guardrail limits for most periods.

---

## Prop-Firm Guardrail Logic

```
Before every order (live):
    daily_dd = (current_equity - day_start_equity) / day_start_equity
    total_dd = (current_equity - peak_equity) / peak_equity

    if daily_dd ≤ −4.5% OR total_dd ≤ −9.0%:
        flatten_all_positions()   ← kill switch
        log("Guardrail breached")
        halt_trading_for_day()

Position size = min(vol_target_size, guardrail_headroom)
```

Stop-loss at order fill:
```
stop_price = entry_price × (1 − 2 × daily_vol)
```
where `daily_vol = ann_vol / √365` computed from the 20-day rolling window.

---

## Challenge Mode

Set `CHALLENGE_MODE = True` in `config.py` to switch to 35% vol target.
This approximately 2.3× levers up all positions, aiming to reach the
10% profit target faster at the cost of higher DD risk.

**Warning:** challenge mode reduces the guardrail buffer. Monitor daily.

---

## No Look-Ahead Guarantee

```
signal(t)     = 1 if sum(log_returns[t−28 : t−1]) > 0  else 0
vol_scalar(t) = clip(vol_target / std(log_returns[t−20 : t−1]) × √365, 0.1, 2.0)
position(t)   = signal(t) × vol_scalar(t)        ← uses data through t−1 only
net_return(t) = position(t) × arith_return(t)    ← earns t's return
```

Both `.shift(1)` calls in `signal.py` and `sizing.py` enforce the 1-day
execution lag. Positions change only on Mondays; between rebalances they
are carried forward from the last Monday unchanged.
