"""
Conditioner / entry-logic / exit-logic building blocks for the intraday-MR exhaustive grid.
Reuses the shared, already-tracked engine (yt_strategy_replications/engine): indicators,
vectorised bracket backtest, HAC/DSR/bootstrap/fold stats. This module only adds the NEW
axes (anchors, entries, exits) that the prior MR studies did not sweep — see PREREGISTRATION.md.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import indicators as ind
from engine import backtest as BT
from engine import stats as S

TARGET_VOL = 0.15
VOL_K = 20
CAP = 3.0

# ---------------------------------------------------------------- anchors (means)

def anchor_vwma(df: pd.DataFrame, k: int) -> pd.Series:
    return ind.vwma(df["close"], df["tick_volume"].clip(lower=1e-6), k)


def anchor_ivol_ma(df: pd.DataFrame, k: int) -> pd.Series:
    """Inverse-realized-vol-weighted moving average: bars with a wide true range count less."""
    tr = ind.true_range(df["high"], df["low"], df["close"]).clip(lower=1e-9)
    w = 1.0 / tr
    wc = (df["close"] * w).rolling(k, min_periods=k).sum()
    wsum = w.rolling(k, min_periods=k).sum()
    return wc / wsum


def anchor_session_open(df: pd.DataFrame) -> pd.Series:
    return df.groupby("session_date")["open"].transform("first")


def anchor_session_vwap(df: pd.DataFrame) -> pd.Series:
    pv = df["close"] * df["tick_volume"].clip(lower=0.0)
    cum_pv = pv.groupby(df["session_date"]).cumsum()
    cum_v = df["tick_volume"].clip(lower=0.0).groupby(df["session_date"]).cumsum().replace(0.0, np.nan)
    return cum_pv / cum_v


def anchor_prior_close(df: pd.DataFrame) -> pd.Series:
    last_close = df.groupby("session_date")["close"].last()
    prior = last_close.shift(1)
    return df["session_date"].map(prior)


# ---------------------------------------------------------------- deviation metrics

def dist_atr(level: pd.Series, anchor: pd.Series, atr: pd.Series) -> pd.Series:
    return (level - anchor) / atr


def dist_zscore(level: pd.Series, k: int) -> pd.Series:
    m = level.rolling(k, min_periods=k).mean()
    sd = level.rolling(k, min_periods=k).std(ddof=0)
    return (level - m) / sd


def percentile_rank(level: pd.Series, k: int) -> pd.Series:
    """Vectorised (numpy stride-view) rolling percentile rank of the last value in-window."""
    arr = level.to_numpy(float)
    n = arr.size
    out = np.full(n, np.nan)
    if n >= k:
        win = np.lib.stride_tricks.sliding_window_view(arr, k)
        last = win[:, -1:]
        out[k - 1:] = (win <= last).mean(axis=1) * 100.0
    return pd.Series(out, index=level.index)


def price_level(df: pd.DataFrame, kind: str) -> pd.Series:
    if kind == "close":
        return df["close"]
    if kind == "open":
        return df["open"]
    if kind == "typical":
        return (df["high"] + df["low"] + df["close"]) / 3.0
    if kind == "median":
        return (df["high"] + df["low"]) / 2.0
    raise ValueError(kind)


# ---------------------------------------------------------------- session-end guard (intraday-flat)

def bars_to_session_end(df: pd.DataFrame) -> np.ndarray:
    g = df.groupby("session_date")
    ordinal = g.cumcount().to_numpy()
    size = g["close"].transform("size").to_numpy()
    return size - 1 - ordinal


# ---------------------------------------------------------------- entry logic

def entry_cross(dist: np.ndarray, z0: float, mode: str = "signed") -> tuple[np.ndarray, np.ndarray]:
    if mode == "signed":
        return dist <= -z0, dist >= z0
    lo, hi = z0  # percentile mode: z0 is (p_lo, p_hi)
    return dist <= lo, dist >= hi


def entry_confirm(dist: np.ndarray, z0: float, mode: str = "signed") -> tuple[np.ndarray, np.ndarray]:
    prev = np.empty_like(dist); prev[0] = np.nan; prev[1:] = dist[:-1]
    if mode == "signed":
        long = (prev <= -z0) & (dist > -z0)
        short = (prev >= z0) & (dist < z0)
        return long, short
    lo, hi = z0
    long = (prev <= lo) & (dist > lo)
    short = (prev >= hi) & (dist < hi)
    return long, short


def entry_reversal_candle(dist: np.ndarray, z0: float, open_: np.ndarray, close_: np.ndarray,
                          mode: str = "signed") -> tuple[np.ndarray, np.ndarray]:
    long0, short0 = entry_cross(dist, z0, mode)
    return long0 & (close_ > open_), short0 & (close_ < open_)


def signal_from_masks(long_mask: np.ndarray, short_mask: np.ndarray, no_entry: np.ndarray) -> np.ndarray:
    sig = np.where(long_mask, 1.0, np.where(short_mask, -1.0, 0.0))
    sig = np.where(no_entry, 0.0, sig)
    return sig


# ---------------------------------------------------------------- exit logic (sl/tp distance arrays)

BIG = 1.0e6  # effectively-disabled sl/tp distance for time-stop-only exits


def exit_atr_bracket(atr: pd.Series, sl_mult: float, tp_mult: float):
    sl = (sl_mult * atr).to_numpy()
    tp = (tp_mult * atr).to_numpy()
    return sl, tp


def exit_mean_revert(level: pd.Series, anchor: pd.Series, atr: pd.Series, sl_mult: float,
                     fraction: float = 1.0):
    tp = (fraction * (level - anchor).abs()).to_numpy()
    sl = (sl_mult * atr).to_numpy()
    return sl, tp


def exit_time_only(n: int):
    return np.full(n, BIG), np.full(n, BIG)


# ---------------------------------------------------------------- vol targeting + daily P&L + metrics

def vol_target_scale(df: pd.DataFrame, bars_per_year: float, k: int = VOL_K,
                     target_vol: float = TARGET_VOL, cap: float = CAP) -> pd.Series:
    r = df["close"].pct_change()
    rv = r.rolling(k, min_periods=k).std(ddof=0) * np.sqrt(bars_per_year)
    return (target_vol / rv).shift(1).clip(upper=cap).reindex(df.index)


def trade_daily(trades: pd.DataFrame, scale: pd.Series, cost_rt: float, all_days: pd.DatetimeIndex) -> pd.Series:
    if trades.empty:
        return pd.Series(0.0, index=all_days)
    s = np.nan_to_num(scale.reindex(trades["entry_time"]).to_numpy(), nan=0.0)
    ret = s * (trades["ret_gross"].to_numpy() - cost_rt)
    day = pd.DatetimeIndex(trades["exit_time"]).normalize()
    dr = pd.Series(ret, index=day).groupby(level=0).sum()
    return dr.reindex(all_days, fill_value=0.0)


def leg_metrics(dr: pd.Series, ppy: float, n_trials: int = 396) -> dict:
    dr = dr[dr.index.notna()]
    arr = dr.to_numpy()
    if (arr != 0).sum() < 10:
        return dict(sharpe=float("nan"), hac_t=float("nan"), hac_mean_bps=float("nan"),
                    dsr=float("nan"), wf=float("nan"), n_days=int((arr != 0).sum()))
    hm, ht = S.hac_tstat(arr, lags=6)
    dsr = S.deflated_sharpe_ratio(arr, n_trials=n_trials, periods_per_year=ppy)
    folds = S.fold_metrics(arr, n_folds=5, periods_per_year=ppy)
    return dict(sharpe=S.sharpe_ratio(arr, ppy), hac_t=ht, hac_mean_bps=hm * 1e4,
                dsr=dsr.get("dsr", float("nan")), wf=folds["wf_score"], n_days=int((arr != 0).sum()))


PPY_DAILY = 252.0  # the decision series is ONE observation per trading DAY (L47):
# never annualise it by bars_per_year (that annualises the intraday vol-target rolling
# window instead, a different quantity) or by sqrt(252) applied twice.


def run_cell(df: pd.DataFrame, sig: np.ndarray, sl_dist: np.ndarray, tp_dist: np.ndarray,
            max_hold: int, scale: pd.Series, cost_rt: float, bars_per_year: float,
            n_trials: int = 396) -> dict:
    days = pd.DatetimeIndex(df["session_date"].drop_duplicates().to_numpy())

    def bt(allow_long, allow_short):
        return BT.run_backtest_vectorized(df, sig, sl_dist=sl_dist, tp_dist=tp_dist, cost_rt=0.0,
                                          max_hold=max_hold, allow_long=allow_long, allow_short=allow_short)

    tr_both = bt(True, True); tr_long = bt(True, False); tr_short = bt(False, True)
    n_trades = int(len(tr_both))
    out = {"n_trades": n_trades}
    if n_trades < 10:
        out.update({f"{p}_{s}": float("nan") for p in ("gross", "gross_long", "gross_short", "net")
                    for s in ("sr", "t", "wf", "dsr")})
        return out
    # Sharpe/DSR/WF are computed on the DAILY-aggregated P&L series -> annualise by
    # PPY_DAILY=252 (L47), never by `bars_per_year` (that annualises the intraday
    # vol-target rolling window, a different quantity, and inflates SR by sqrt(bars/day)).
    g_both = leg_metrics(trade_daily(tr_both, scale, 0.0, days), PPY_DAILY, n_trials)
    g_long = leg_metrics(trade_daily(tr_long, scale, 0.0, days), PPY_DAILY, n_trials)
    g_short = leg_metrics(trade_daily(tr_short, scale, 0.0, days), PPY_DAILY, n_trials)
    net = leg_metrics(trade_daily(tr_both, scale, cost_rt, days), PPY_DAILY, n_trials)
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
        "frac_time": float((tr_both["reason"].isin(["time", "open_end"])).mean()),
        "win_rate": float((tr_both["ret_gross"] > 0).mean()),
    })
    return out
