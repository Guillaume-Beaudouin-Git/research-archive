"""
Movement / signal constructions for the intraday-momentum grid (see PREREGISTRATION.md §5-7).
Each function returns (sig, sl_dist, tp_dist, max_hold, meta) ready for
`engine_lib.run_cell` / `engine.backtest.run_backtest_vectorized`. All windows are causal;
the engine enforces the T-1/T execution lag centrally. Session-bleed is prevented by only
firing a trigger when enough bars remain before session end for the chosen horizon
(`bars_to_session_end` guard, identical mechanism to `mr_intraday_grille_2026-08`).
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
MR_GRID = HERE.parents[0] / "mr_intraday_grille_2026-08"
sys.path.insert(0, str(REPO / "yt_strategy_replications"))
sys.path.insert(0, str(MR_GRID))
from engine import indicators as ind
import engine_lib as EL
from engine import backtest as BT

ATR_N = 20
BIG = 1.0e6  # BIG sentinel (matches engine_lib.BIG convention: effectively-disabled sl/tp)


def _ordinal(df):
    return df.groupby("session_date").cumcount().to_numpy()


def _bars_to_end(df):
    return EL.bars_to_session_end(df)


def _rest_hold(symbol, bars_per_day):
    return bars_per_day[symbol] - 4  # operational def of "rest of session" (PREREG §5)


def _atr_bracket(df, sl_mult, tp_mult, n=ATR_N):
    a = ind.atr(df["high"], df["low"], df["close"], n=n)
    return (sl_mult * a).to_numpy(), (tp_mult * a).to_numpy()


def _time_only(n_rows):
    return np.full(n_rows, BIG), np.full(n_rows, BIG)


def _apply_hold_guard(trigger_mask: np.ndarray, bars_to_end: np.ndarray, required: int) -> np.ndarray:
    return trigger_mask & (bars_to_end >= required)


# --------------------------------------------------------------------------------------------
# Session-capped runner: for constructions where the TRIGGER bar itself varies day-to-day
# (construction B — the breakout timing is data-dependent, unlike A/C/D's fixed-ordinal
# trigger), a single scalar `max_hold` cannot simultaneously (a) let an early breakout run to
# session close and (b) guarantee a late breakout's forward search never reads into the NEXT
# session's rows (the concatenated df has no gap marker the engine's plain forward-scan can see).
# Fix: search with a generous engine-level max_hold (>= one full session), then truncate any
# trade whose exit fell in a different session_date than its entry back to that entry session's
# LAST bar close (reason='session_end') -- the honest intraday-flat force-close, not a guard that
# silently starves late-session breakouts (the bug this replaces: requiring the FULL rest-of-
# session length available at the trigger made K=4 breakouts empty for every instrument, since no
# candidate bar for K=4 could also satisfy "bars-to-end >= bars_per_day-4").

def run_backtest_session_capped(df, sig, sl_dist, tp_dist, engine_max_hold, allow_long, allow_short):
    tr = BT.run_backtest_vectorized(df, sig, sl_dist=sl_dist, tp_dist=tp_dist, cost_rt=0.0,
                                    max_hold=engine_max_hold, allow_long=allow_long, allow_short=allow_short)
    if tr.empty:
        return tr
    sess = df["session_date"]
    entry_sess = sess.reindex(tr["entry_time"]).to_numpy()
    exit_sess = sess.reindex(tr["exit_time"]).to_numpy()
    bleed = exit_sess != entry_sess
    if not bleed.any():
        return tr
    last_close = df.groupby("session_date")["close"].last()
    last_time = df.groupby("session_date").apply(lambda g: g.index[-1])
    tr = tr.copy()
    idx = np.where(bleed)[0]
    sdates = entry_sess[idx]
    tr.loc[tr.index[idx], "exit_px"] = last_close.reindex(sdates).to_numpy()
    tr.loc[tr.index[idx], "exit_time"] = last_time.reindex(sdates).to_numpy()
    tr.loc[tr.index[idx], "reason"] = "session_end"
    direction = tr["direction"].to_numpy(float)
    entry_px = tr["entry_px"].to_numpy(float)
    exit_px = tr["exit_px"].to_numpy(float)
    tr["ret_gross"] = direction * (exit_px / entry_px - 1.0)
    return tr


def run_cell_capped(df, sig, sl_dist, tp_dist, engine_max_hold, scale, cost_rt, n_trials):
    """Same reporting contract as engine_lib.run_cell, but routed through
    run_backtest_session_capped so late-day triggers (construction B) are force-closed at the
    entry session's last bar instead of bleeding forward-scan into the next session."""
    days = pd.DatetimeIndex(df["session_date"].drop_duplicates().to_numpy())

    def bt(allow_long, allow_short):
        return run_backtest_session_capped(df, sig, sl_dist, tp_dist, engine_max_hold, allow_long, allow_short)

    tr_both = bt(True, True); tr_long = bt(True, False); tr_short = bt(False, True)
    n_trades = int(len(tr_both))
    out = {"n_trades": n_trades}
    if n_trades < 10:
        out.update({f"{p}_{s}": float("nan") for p in ("gross", "gross_long", "gross_short", "net")
                    for s in ("sr", "t", "wf", "dsr")})
        return out
    g_both = EL.leg_metrics(EL.trade_daily(tr_both, scale, 0.0, days), EL.PPY_DAILY, n_trials)
    g_long = EL.leg_metrics(EL.trade_daily(tr_long, scale, 0.0, days), EL.PPY_DAILY, n_trials)
    g_short = EL.leg_metrics(EL.trade_daily(tr_short, scale, 0.0, days), EL.PPY_DAILY, n_trials)
    net = EL.leg_metrics(EL.trade_daily(tr_both, scale, cost_rt, days), EL.PPY_DAILY, n_trials)
    gross_bps_per_trade = float(tr_both["ret_gross"].mean() * 1e4) if n_trades else float("nan")
    out.update({
        "gross_sr": g_both["sharpe"], "gross_t": g_both["hac_t"], "gross_wf": g_both["wf"],
        "gross_dsr": g_both["dsr"], "gross_bps_per_trade": gross_bps_per_trade,
        "long_sr": g_long["sharpe"], "long_t": g_long["hac_t"],
        "short_sr": g_short["sharpe"], "short_t": g_short["hac_t"],
        "net_sr": net["sharpe"], "net_t": net["hac_t"],
        "avg_bars_held": float(tr_both["bars_held"].mean()),
        "frac_sl": float((tr_both["reason"] == "sl").mean()),
        "frac_tp": float((tr_both["reason"] == "tp").mean()),
        "frac_time": float((tr_both["reason"].isin(["time", "open_end", "session_end"])).mean()),
        "win_rate": float((tr_both["ret_gross"] > 0).mean()),
    })
    return out


# ------------------------------------------------------------- A: Gao early-window return

def construction_a(df: pd.DataFrame, K: int, H: str, exit_type: str, bars_per_day: dict, symbol: str):
    ordinal = _ordinal(df)
    bte = _bars_to_end(df)
    win_open = df.groupby("session_date")["open"].transform("first")
    close_at_boundary = df.loc[ordinal == K - 1].groupby("session_date")["close"].first()
    close_full = df["session_date"].map(close_at_boundary)
    window_ret = (close_full / win_open - 1.0).to_numpy()

    trigger = (ordinal == K - 1)
    max_hold = 8 if H == "8bars" else _rest_hold(symbol, bars_per_day)
    trigger = _apply_hold_guard(trigger, bte, max_hold)

    direction = np.where(window_ret > 0, 1.0, np.where(window_ret < 0, -1.0, 0.0))
    sig = np.where(trigger, direction, 0.0)

    if exit_type == "X1":
        sl, tp = _time_only(len(df))
    elif exit_type == "X2":
        sl, tp = _atr_bracket(df, 1.0, 1.5)
    else:
        raise ValueError(exit_type)
    return sig, sl, tp, max_hold, {"K": K, "H": H, "exit": exit_type}


# ------------------------------------------------------------- B: ORB breakout

def construction_b(df: pd.DataFrame, K: int, exit_type: str, bars_per_day: dict, symbol: str):
    ordinal = _ordinal(df)
    bte = _bars_to_end(df)
    or_high = df.loc[ordinal < K].groupby("session_date")["high"].max()
    or_low = df.loc[ordinal < K].groupby("session_date")["low"].min()
    or_high_full = df["session_date"].map(or_high).to_numpy()
    or_low_full = df["session_date"].map(or_low).to_numpy()
    close = df["close"].to_numpy()

    candidate = ordinal >= K
    brk_up = candidate & (close > or_high_full)
    brk_dn = candidate & (close < or_low_full)
    brk_any = brk_up | brk_dn
    cum = pd.Series(brk_any).groupby(df["session_date"].to_numpy()).cumsum().to_numpy()
    first_trigger = brk_any & (cum == 1)

    # Breakout timing is data-dependent (unlike A/C/D's fixed-ordinal trigger) -> only a small
    # minimum-tail guard here (session-close force-exit is handled by run_cell_capped, not by
    # requiring the full rest-of-session length be available AT the trigger -- that guard made
    # every K=4 cell empty, see signals.py module docstring on run_backtest_session_capped).
    MIN_TAIL = 1
    first_trigger = _apply_hold_guard(first_trigger, bte, MIN_TAIL)

    direction = np.where(brk_up, 1.0, np.where(brk_dn, -1.0, 0.0))
    sig = np.where(first_trigger, direction, 0.0)

    or_width = or_high_full - or_low_full
    if exit_type == "X2":
        sl, tp = _atr_bracket(df, 1.0, 1.5)
    elif exit_type == "X4":
        sl, tp = 0.5 * or_width, 1.5 * or_width
    else:
        raise ValueError(exit_type)
    engine_max_hold = bars_per_day[symbol]  # generous upper bound; run_cell_capped truncates bleed
    return sig, sl, tp, engine_max_hold, {"K": K, "H": "rest", "exit": exit_type, "_capped": True}


# ------------------------------------------------------------- C: gap continuation

def construction_c(df: pd.DataFrame, g0: float, H: str, exit_type: str, bars_per_day: dict, symbol: str):
    ordinal = _ordinal(df)
    bte = _bars_to_end(df)
    sess_open = df.groupby("session_date")["open"].first()
    sess_close = df.groupby("session_date")["close"].last()
    gap = (sess_open - sess_close.shift(1)).reindex(sess_open.index)
    sigma = gap.rolling(20, min_periods=20).std(ddof=0).shift(1)
    gap_z = (gap / sigma)
    gap_z_full = df["session_date"].map(gap_z).to_numpy()
    gap_full = df["session_date"].map(gap).to_numpy()

    trigger0 = (ordinal == 0)
    direction = np.where(gap_full > 0, 1.0, np.where(gap_full < 0, -1.0, 0.0))
    thresh_ok = np.abs(gap_z_full) >= g0
    trigger = trigger0 & thresh_ok & np.isfinite(gap_z_full)

    max_hold = 8 if H == "8bars" else _rest_hold(symbol, bars_per_day)
    trigger = _apply_hold_guard(trigger, bte, max_hold)
    sig = np.where(trigger, direction, 0.0)

    if exit_type == "X1":
        sl, tp = _time_only(len(df))
    elif exit_type == "X2":
        sl, tp = _atr_bracket(df, 1.0, 1.5)
    else:
        raise ValueError(exit_type)
    return sig, sl, tp, max_hold, {"g0": g0, "H": H, "exit": exit_type}, gap_z_full


# ------------------------------------------------------------- D: prior-session range position

def construction_d(df: pd.DataFrame, p_hi: float, p_lo: float, H: str, bars_per_day: dict, symbol: str):
    ordinal = _ordinal(df)
    bte = _bars_to_end(df)
    g = df.groupby("session_date")
    s_high = g["high"].max(); s_low = g["low"].min(); s_close = g["close"].last()
    pos = ((s_close - s_low) / (s_high - s_low)).shift(1)  # prior session's position, causal
    pos_full = df["session_date"].map(pos).to_numpy()

    trigger0 = (ordinal == 0)
    direction = np.where(pos_full >= p_hi, 1.0, np.where(pos_full <= p_lo, -1.0, 0.0))
    trigger = trigger0 & (direction != 0.0) & np.isfinite(pos_full)

    max_hold = 8 if H == "8bars" else _rest_hold(symbol, bars_per_day)
    trigger = _apply_hold_guard(trigger, bte, max_hold)
    sig = np.where(trigger, direction, 0.0)

    sl, tp = _time_only(len(df))
    return sig, sl, tp, max_hold, {"p_hi": p_hi, "p_lo": p_lo, "H": H, "exit": "X1"}
