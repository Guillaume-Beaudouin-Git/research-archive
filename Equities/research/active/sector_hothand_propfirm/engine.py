"""
engine.py — Hot-hand sector momentum backtest engine.

Spec (from LLM report — do NOT modify):
  Signal  : 20-day cross-sectional momentum (log close-to-close)
  Action  : long single highest-momentum asset if signal > 0, else cash
  Vol     : target 0.15 ann / realized 40-day, cap 3×
  Stop    : daily 1.2% on non-levered return
  Gap fill: if open_t < entry_t-1 × (1 - 0.012), execute at open_t
  Cost    : 8 bp/trade × lever (report model, Phase 4 to challenge)
  Timing  : signal on T-1 close → position entry at T open (L1 compliant)
  Seed    : 42 (all stochastic ops)
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SEED          = 42
LOOKBACK_MOM  = 20       # momentum window (days)
LOOKBACK_VOL  = 40       # realized vol window (days)
VOL_TARGET    = 0.15     # annualized
VOL_CAP       = 3.0      # max leverage multiple
DAILY_STOP    = 0.012    # 1.2% stop on non-levered return
COST_BPS      = 0.0008   # 8 bp per trade × lever (applied when lever changes)
TRADING_DAYS  = 252


def run(
    open_px: pd.DataFrame,   # T×N, open prices, index=Date, cols=tickers
    close_px: pd.DataFrame,  # T×N, adjusted close
    rf: pd.Series,           # daily risk-free rate (decimal, aligned to close_px index)
    *,
    lookback_mom: int  = LOOKBACK_MOM,
    lookback_vol: int  = LOOKBACK_VOL,
    vol_target:   float = VOL_TARGET,
    vol_cap:      float = VOL_CAP,
    daily_stop:   float = DAILY_STOP,
    cost_bps:     float = COST_BPS,
) -> pd.DataFrame:
    """
    Run one backtest pass on the supplied price panel.

    Returns
    -------
    pd.DataFrame with DatetimeIndex and columns:
        ret_gross  : daily strategy return before costs, excess of rf
        ret_net    : daily strategy return after costs, excess of rf
        lever      : realized leverage applied that day
        position   : chosen ticker (or '' for cash)
        equity_net : cumulative compounded equity (starting at 1.0)
        drawdown   : drawdown series (fraction)
    """
    tickers = list(close_px.columns)
    dates   = close_px.index

    # ── log returns (close-to-close) for momentum and vol ─────────────────
    log_ret = np.log(close_px / close_px.shift(1))   # T×N

    # ── signal on T-1 close, acted on T open ──────────────────────────────
    # momentum score: sum of last lookback_mom log-returns (on T-1 basis)
    mom = log_ret.rolling(lookback_mom).sum().shift(1)   # L1: shift 1

    # ── realized vol on T-1 close (for sizing) ────────────────────────────
    rvol_daily = log_ret.rolling(lookback_vol).std().shift(1)   # L1
    # annualize; use portfolio asset vol (chosen asset)
    rvol_ann = rvol_daily * np.sqrt(TRADING_DAYS)

    # ── pre-allocate output arrays ────────────────────────────────────────
    n          = len(dates)
    ret_gross  = np.zeros(n, dtype=float)
    ret_net    = np.zeros(n, dtype=float)
    lever_arr  = np.zeros(n, dtype=float)
    position   = [""] * n

    prev_ticker = ""
    prev_lever  = 0.0

    for i, dt in enumerate(dates):
        # need at least lookback_vol + 1 days of history
        if i < lookback_vol + 1:
            continue

        # ── select asset on T-1 signal ────────────────────────────────────
        mom_scores = mom.iloc[i]
        best_ticker = mom_scores.idxmax()
        best_score  = mom_scores[best_ticker]

        if pd.isna(best_score) or best_score <= 0:
            # cash
            position[i] = ""
            ret_gross[i] = 0.0
            ret_net[i]   = -rf.iloc[i]   # opportunity cost of rf
            lever_arr[i] = 0.0
            prev_ticker  = ""
            prev_lever   = 0.0
            continue

        ticker_idx = tickers.index(best_ticker)

        # ── leverage: vol target ──────────────────────────────────────────
        sig_vol = rvol_ann.iloc[i, ticker_idx]
        if pd.isna(sig_vol) or sig_vol <= 0:
            lever = 1.0
        else:
            lever = min(vol_target / sig_vol, vol_cap)

        # ── entry price: gap-aware ────────────────────────────────────────
        # If open < prev_close × (1 - daily_stop) → execute at open (stop already hit)
        open_t    = open_px.iloc[i][best_ticker]
        close_tm1 = close_px.iloc[i - 1][best_ticker]
        close_t   = close_px.iloc[i][best_ticker]

        if pd.isna(open_t) or pd.isna(close_tm1) or pd.isna(close_t):
            position[i] = ""
            continue

        # Non-levered return for the day
        entry_px = open_t if open_t < close_tm1 * (1 - daily_stop) else close_tm1
        nonlev_ret = (close_t - entry_px) / entry_px

        # ── daily stop ────────────────────────────────────────────────────
        if nonlev_ret < -daily_stop:
            nonlev_ret = -daily_stop   # stop executed at stop price

        # ── gross excess return ───────────────────────────────────────────
        gross_xret = lever * nonlev_ret - rf.iloc[i]

        # ── transaction costs ────────────────────────────────────────────
        # Cost paid when ticker changes or lever changes materially
        ticker_changed = best_ticker != prev_ticker
        lever_changed  = abs(lever - prev_lever) > 0.05 * prev_lever if prev_lever > 0 else lever > 0
        trade_cost = 0.0
        if ticker_changed or lever_changed:
            trade_cost = cost_bps * lever   # 8bp × lever on entry

        net_xret = gross_xret - trade_cost

        ret_gross[i]  = gross_xret
        ret_net[i]    = net_xret
        lever_arr[i]  = lever
        position[i]   = best_ticker
        prev_ticker   = best_ticker
        prev_lever    = lever

    # ── build output DataFrame ────────────────────────────────────────────
    out = pd.DataFrame({
        "ret_gross": ret_gross,
        "ret_net":   ret_net,
        "lever":     lever_arr,
        "position":  position,
    }, index=dates)

    # equity and drawdown
    out["equity_net"] = (1 + out["ret_net"]).cumprod()
    roll_max = out["equity_net"].cummax()
    out["drawdown"] = (out["equity_net"] - roll_max) / roll_max

    return out


def sharpe(ret: pd.Series, ann: int = TRADING_DAYS) -> float:
    """Annualized Sharpe (already excess returns)."""
    if ret.std() == 0:
        return 0.0
    return float(ret.mean() / ret.std() * np.sqrt(ann))


def max_drawdown(equity: pd.Series) -> float:
    roll_max = equity.cummax()
    dd = (equity - roll_max) / roll_max
    return float(dd.min())
