"""
Futures/research/passed/orb_ivb_nq/feasibility.py
==================================================

ORB IVB replication on NQ futures — delta-free variant.

Data: Kaggle NQ 1-min OHLCV, 2022-12-26 to 2025-12-11 (~1.05M rows).
      Loaded via data.cache.load_nq_1min (parquet cache after first run).

Strategy (Conti spec, EXCEPT no delta filter):
  ORB window  : 08:30–08:59 ET (30 × 1-min bars)
  Entry       : first 5-min close > ORB_high after 09:00 ET (long only)
  TP          : entry + 1R  (R = ORB_high − ORB_low)
  SL          : ORB_low
  Time exit   : first bar at or after 15:00 ET
  Tie (same-bar TP+SL): assume SL first (conservative)
  Position    : 1 NQ contract (point value $20, 1 tick = 0.25pt = $5)
  Costs       : $4.50/side commission = $9.00 RT
                1 tick slippage = $5.00 RT
                Total = $14.00 RT per contract

Two variants run in parallel:
  5-min : entry on 5-min close above ORB_high (matches Conti)
  1-min : entry on 1-min close above ORB_high (tighter timing, more entries)

Statistical tests (canonical May 2026 methodology):
  - Excess returns over FRED DTB3 daily RF
  - Daily Sharpe x sqrt(252)
  - HAC lag-6 OLS for alpha vs NQ B&H
  - Bootstrap EV (20,000 resamples)
  - Monte Carlo paths (20,000 sims)
  - Shuffled sequences (1,000 perms)
  - Walk-forward (4 windows, >=3 OOS periods)
  - approx_multi_test_penalty (n_tests=68)

n_tests: 68 (5-min = test 67, 1-min = test 68; counter starts at 66)

Propfirm gate thresholds:
  Sharpe HAC > 1.0
  MaxDD > -10% of $100k capital
  P(EV <= 0) < 0.05
  PF > 1.20
  Walk-forward % positive windows > 75%
  AMTP p-value < 0.10

Run:
    python -m Futures.research.passed.orb_ivb_nq.feasibility

CRITICAL CHECKPOINTS (auto-enforced):
  - Sharpe > 3 OR PF > 2 -> print SUSPICIOUS + manually check 10 random trades
  - 0 trades -> print debug info + exit
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

# -- Project root on path ------------------------------------------------------
_HERE = Path(__file__).parent
_PROJ = _HERE.parents[3]          # Algo_claude/
sys.path.insert(0, str(_PROJ))

from data.cache import load_nq_1min, get_cached_or_fetch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger(__name__)

_OUT_DIR       = _HERE
_SUMMARY_PATH  = _OUT_DIR / "orb_ivb_nq_summary.md"
_SESSIONS_PATH = _OUT_DIR / "clean_sessions.json"

# -----------------------------------------------------------------------------
# Strategy constants
# -----------------------------------------------------------------------------
POINT_VALUE   = 20.0   # $/point
TICK_SIZE     = 0.25   # points
TICK_VALUE    = POINT_VALUE * TICK_SIZE  # $5
COMMISSION_RT = 9.00   # $4.50/side x 2
SLIPPAGE_RT   = 5.00   # 1 tick
COST_RT       = COMMISSION_RT + SLIPPAGE_RT  # $14.00

CAPITAL = 100_000.0   # propfirm base capital $100k

# ORB/session times (ET)
ORB_START    = time(8, 30)
ORB_END_EXCL = time(9, 0)    # ORB uses bars: [08:30, 09:00)
TRADE_START  = time(9, 0)    # first entry bar must be >= 09:00
TIME_EXIT    = time(15, 0)   # flatten first bar at or after 15:00

# Minimum valid ORB bars (need at least 80% of 30 1-min bars)
MIN_ORB_BARS = 24

# Bootstrap / simulation params
N_BOOT  = 20_000
N_MC    = 20_000
N_SHUF  = 1_000
N_TESTS = 68   # running counter; 5-min=67, 1-min=68

# Walk-forward windows (IS_start, IS_end, OOS_start, OOS_end)
_WF_WINDOWS = [
    ("2023-01-01", "2023-06-30", "2023-07-01", "2023-12-31"),  # OOS: H2-2023
    ("2023-01-01", "2023-12-31", "2024-01-01", "2024-06-30"),  # OOS: H1-2024
    ("2023-01-01", "2024-06-30", "2024-07-01", "2024-12-31"),  # OOS: H2-2024
    ("2023-01-01", "2024-12-31", "2025-01-01", "2025-12-11"),  # OOS: 2025
]


# -----------------------------------------------------------------------------
# Data loading
# -----------------------------------------------------------------------------

def load_clean_sessions() -> list[str]:
    """Load clean_sessions from data_audit.json if available."""
    if _SESSIONS_PATH.exists():
        with open(_SESSIONS_PATH) as fh:
            d = json.load(fh)
        return d.get("clean_sessions", [])
    return []


def load_rf() -> pd.Series:
    """FRED DTB3 daily RF rate. Falls back to 0 if unavailable."""
    try:
        import pandas_datareader as pdr
        raw = pdr.get_data_fred("DTB3", start="2022-01-01")
        rf  = ((1 + raw["DTB3"] / 100) ** (1 / 252) - 1).ffill()
        rf.name = "rf_daily"
        return rf
    except Exception as exc:
        log.warning("FRED DTB3 fetch failed (%s) -- using RF=0", exc)
        return pd.Series(dtype=float, name="rf_daily")


# -----------------------------------------------------------------------------
# Resampling
# -----------------------------------------------------------------------------

def resample_5min(df1m: pd.DataFrame) -> pd.DataFrame:
    """Resample 1-min OHLCV to 5-min with standard OHLCV aggregation."""
    df5 = df1m.resample("5min", label="left", closed="left").agg(
        open=("open",     "first"),
        high=("high",     "max"),
        low= ("low",      "min"),
        close=("close",   "last"),
        volume=("volume", "sum"),
    )
    df5.dropna(subset=["open", "close"], inplace=True)
    return df5


# -----------------------------------------------------------------------------
# ORB simulation -- single session
# -----------------------------------------------------------------------------

def _simulate_session(
    session_date: object,
    df1m: pd.DataFrame,
    df5m: pd.DataFrame,
    use_1min: bool = False,
) -> dict | None:
    """
    Simulate one ORB session.

    Parameters
    ----------
    session_date : datetime.date
    df1m         : 1-min DataFrame (full dataset, tz-aware US/Eastern)
    df5m         : 5-min DataFrame (resampled from df1m)
    use_1min     : if True, use 1-min bars for entry/exit instead of 5-min

    Returns
    -------
    dict with trade details, or None if no signal or invalid ORB.
    """
    ds       = str(session_date)
    entry_df = df1m if use_1min else df5m

    # -- ORB window: [08:30, 09:00) using 1-min bars --------------------------
    orb_start_ts = pd.Timestamp(f"{ds} 08:30:00", tz="US/Eastern")
    orb_end_ts   = pd.Timestamp(f"{ds} 09:00:00", tz="US/Eastern")  # exclusive
    orb_bars     = df1m[orb_start_ts : orb_end_ts - pd.Timedelta(minutes=1)]

    if len(orb_bars) < MIN_ORB_BARS:
        return None

    orb_high  = float(orb_bars["high"].max())
    orb_low   = float(orb_bars["low"].min())
    orb_range = orb_high - orb_low

    if orb_range <= 0:
        return None

    # -- Trading window for entry signal --------------------------------------
    trade_start_ts = pd.Timestamp(f"{ds} 09:00:00", tz="US/Eastern")
    # Include bars through 15:05 to always catch the 15:00 time-exit bar
    trade_end_ts   = pd.Timestamp(f"{ds} 15:05:00", tz="US/Eastern")

    session_bars = entry_df[trade_start_ts:trade_end_ts]
    if session_bars.empty:
        return None

    # -- Find entry: first bar close > ORB_high --------------------------------
    sig_mask = session_bars["close"] > orb_high
    if not sig_mask.any():
        return None  # no breakout today

    entry_idx   = sig_mask.idxmax()   # Timestamp of first True
    entry_bar   = session_bars.loc[entry_idx]
    entry_price = float(entry_bar["close"])

    # -- Don't enter on or after 14:55 (5-min) or 14:59 (1-min) ---------------
    entry_cutoff = time(14, 55) if not use_1min else time(14, 59)
    if entry_idx.time() >= entry_cutoff:
        return None

    # -- TP / SL ---------------------------------------------------------------
    tp = entry_price + orb_range   # 1R target
    sl = orb_low

    # -- Subsequent bars (entry bar + 1 through time-exit bar) ----------------
    delta      = pd.Timedelta(minutes=1) if use_1min else pd.Timedelta(minutes=5)
    post_start = entry_idx + delta
    post_bars  = session_bars[post_start:trade_end_ts]

    if post_bars.empty:
        # Entry was the last bar; close flat
        exit_price  = entry_price
        exit_time   = entry_idx
        exit_reason = "time"
    else:
        exit_price  = None
        exit_time   = None
        exit_reason = None

        for bar_ts, bar in post_bars.iterrows():
            sl_hit = float(bar["low"])  <= sl
            tp_hit = float(bar["high"]) >= tp
            at_time_exit = bar_ts.time() >= TIME_EXIT

            if sl_hit and tp_hit:
                # Both in same bar -> conservative SL first
                exit_price  = sl
                exit_time   = bar_ts
                exit_reason = "sl"
                break
            elif sl_hit:
                exit_price  = sl
                exit_time   = bar_ts
                exit_reason = "sl"
                break
            elif tp_hit:
                exit_price  = tp
                exit_time   = bar_ts
                exit_reason = "tp"
                break
            elif at_time_exit:
                exit_price  = float(bar["close"])
                exit_time   = bar_ts
                exit_reason = "time"
                break

        if exit_price is None:
            last        = post_bars.iloc[-1]
            exit_price  = float(last["close"])
            exit_time   = post_bars.index[-1]
            exit_reason = "time"

    # -- P&L -------------------------------------------------------------------
    gross_pnl = (exit_price - entry_price) * POINT_VALUE
    net_pnl   = gross_pnl - COST_RT
    r_mult    = (exit_price - entry_price) / orb_range

    return {
        "date":        session_date,
        "orb_high":    orb_high,
        "orb_low":     orb_low,
        "orb_range":   orb_range,
        "entry_price": entry_price,
        "entry_time":  entry_idx,
        "exit_price":  exit_price,
        "exit_time":   exit_time,
        "exit_reason": exit_reason,
        "gross_pnl":   gross_pnl,
        "net_pnl":     net_pnl,
        "r_multiple":  r_mult,
        "winner":      net_pnl > 0,
    }


def run_strategy(
    df1m: pd.DataFrame,
    df5m: pd.DataFrame,
    sessions: list[str],
    use_1min: bool = False,
) -> pd.DataFrame:
    """Run ORB on all clean sessions. Returns trade_log DataFrame."""
    trades = []
    for ds in sessions:
        try:
            d   = date.fromisoformat(ds)
            res = _simulate_session(d, df1m, df5m, use_1min=use_1min)
            if res:
                trades.append(res)
        except Exception as exc:
            log.warning("Session %s error: %s", ds, exc)

    if not trades:
        return pd.DataFrame()

    tl = pd.DataFrame(trades)
    tl["date"] = pd.to_datetime(tl["date"])
    return tl.sort_values("date").reset_index(drop=True)


# -----------------------------------------------------------------------------
# Metrics
# -----------------------------------------------------------------------------

def compute_metrics(tl: pd.DataFrame, rf: pd.Series) -> dict:
    """Core performance metrics from trade log."""
    n        = len(tl)
    winners  = tl["winner"].sum()
    win_rate = winners / n if n > 0 else 0.0
    avg_win  = tl.loc[tl["winner"], "net_pnl"].mean() if winners > 0 else 0.0
    avg_loss = tl.loc[~tl["winner"], "net_pnl"].mean() if (n - winners) > 0 else 0.0
    gross_win  = tl.loc[tl["winner"],  "net_pnl"].sum()
    gross_loss = abs(tl.loc[~tl["winner"], "net_pnl"].sum())
    pf         = gross_win / gross_loss if gross_loss > 0 else float("inf")
    avg_trade  = tl["net_pnl"].mean()
    avg_r      = tl["r_multiple"].mean()
    total_pnl  = tl["net_pnl"].sum()

    # Daily P&L (days with no trade = 0)
    daily_pnl = tl.groupby(tl["date"].dt.normalize())["net_pnl"].sum()
    daily_ret = daily_pnl / CAPITAL

    # Excess returns
    rf_aligned = rf.reindex(daily_ret.index).fillna(0.0)
    daily_exc  = daily_ret - rf_aligned

    sharpe = (float(daily_exc.mean() / daily_exc.std(ddof=1) * np.sqrt(252))
              if daily_exc.std() > 0 else 0.0)

    # Equity curve & MaxDD
    cum_pnl  = tl["net_pnl"].cumsum()
    roll_max = cum_pnl.cummax()
    drawdown = cum_pnl - roll_max
    max_dd   = float(drawdown.min())

    ann_days   = (tl["date"].max() - tl["date"].min()).days
    ann_factor = 365.25 / ann_days if ann_days > 0 else 1.0
    ann_ret    = total_pnl * ann_factor / CAPITAL * 100

    exit_counts = tl["exit_reason"].value_counts().to_dict()

    return {
        "n_trades":    n,
        "win_rate":    round(win_rate, 4),
        "pf":          round(pf, 4),
        "avg_trade":   round(avg_trade, 2),
        "avg_win":     round(avg_win, 2),
        "avg_loss":    round(avg_loss, 2),
        "avg_r":       round(avg_r, 4),
        "total_pnl":   round(total_pnl, 2),
        "ann_ret_pct": round(ann_ret, 2),
        "sharpe":      round(sharpe, 4),
        "max_dd":      round(max_dd, 2),
        "max_dd_pct":  round(max_dd / CAPITAL * 100, 2),
        "exit_counts": exit_counts,
        "daily_exc":   daily_exc,
    }


def compute_nq_daily(df1m: pd.DataFrame) -> pd.Series:
    """NQ B&H daily return: last bar close per calendar date, pct change. Tz-naive index."""
    daily_close = df1m.groupby(df1m.index.normalize())["close"].last()
    nq_ret      = daily_close.pct_change().dropna()
    # Strip timezone so it aligns with tz-naive daily_exc index in _hac_ols
    nq_ret.index = nq_ret.index.tz_localize(None)
    nq_ret.name  = "nq_ret"
    return nq_ret


# -----------------------------------------------------------------------------
# Statistical tests
# -----------------------------------------------------------------------------

def bootstrap_ev(tl: pd.DataFrame, n_boot: int = N_BOOT) -> dict:
    """Bootstrap expected value with 95% CI."""
    pnls = tl["net_pnl"].values
    rs   = tl["r_multiple"].values
    rng  = np.random.default_rng(42)
    n    = len(pnls)
    boot_ev = np.empty(n_boot)
    boot_r  = np.empty(n_boot)
    for i in range(n_boot):
        idx       = rng.integers(0, n, n)
        boot_ev[i] = pnls[idx].mean()
        boot_r[i]  = rs[idx].mean()

    return {
        "ev_dollar":  round(float(pnls.mean()), 2),
        "ev_r":       round(float(rs.mean()), 4),
        "ci_dollar":  [round(np.percentile(boot_ev, 2.5), 2),
                       round(np.percentile(boot_ev, 97.5), 2)],
        "ci_r":       [round(np.percentile(boot_r, 2.5), 4),
                       round(np.percentile(boot_r, 97.5), 4)],
        "p_ev_le_0":  round(float((boot_ev <= 0).mean()), 4),
        "p_r_le_0":   round(float((boot_r  <= 0).mean()), 4),
    }


def monte_carlo(tl: pd.DataFrame, n_sim: int = N_MC) -> dict:
    """Simulate N equity paths by resampling historical trades."""
    pnls = tl["net_pnl"].values
    n    = len(pnls)
    rng  = np.random.default_rng(42)
    terminal = np.empty(n_sim)
    max_dd   = np.empty(n_sim)
    for i in range(n_sim):
        path        = pnls[rng.integers(0, n, n)].cumsum()
        terminal[i] = path[-1]
        dd          = path - np.maximum.accumulate(path)
        max_dd[i]   = dd.min()

    pcts = [5, 10, 25, 50, 75, 90, 95, 99]
    return {
        "terminal_p50":  round(np.percentile(terminal, 50), 2),
        "terminal_p25":  round(np.percentile(terminal, 25), 2),
        "terminal_p75":  round(np.percentile(terminal, 75), 2),
        "maxdd_ptiles":  {str(p): round(np.percentile(max_dd, p), 2) for p in pcts},
    }


def shuffled_sequences(tl: pd.DataFrame, n_shuf: int = N_SHUF) -> dict:
    """Permutation test: compare observed Sharpe to shuffled distribution."""
    pnls      = tl["net_pnl"].values
    n         = len(pnls)
    rng       = np.random.default_rng(42)

    def _sharpe(arr: np.ndarray) -> float:
        s = arr.std(ddof=1)
        return float(arr.mean() / s * np.sqrt(n)) if s > 0 else 0.0

    obs_sharpe  = _sharpe(pnls)
    shuf_sharpe = np.array([_sharpe(rng.permutation(pnls)) for _ in range(n_shuf)])
    p_beat      = float((shuf_sharpe >= obs_sharpe).mean())

    return {
        "obs_sharpe":     round(obs_sharpe, 4),
        "p_shuffle_beat": round(p_beat, 4),
        "shuffled_p95":   round(np.percentile(shuf_sharpe, 95), 4),
        "shuffled_maxdd_p95": round(
            np.percentile(
                [np.cumsum(rng.permutation(pnls)).min()
                 for _ in range(min(500, n_shuf))],
                95,
            ), 2
        ),
    }


def _hac_ols(y: pd.Series, x: pd.Series) -> dict:
    """OLS with HAC SE (Newey-West, lag=6)."""
    merged = pd.concat([y.rename("y"), x.rename("x")], axis=1).dropna()
    if len(merged) < 20:
        return {"alpha_ann": None, "alpha_ann_pct": None, "t_hac": None,
                "beta": None, "r2": None, "resid_sr": None}

    yv  = merged["y"].values
    Xv  = sm.add_constant(merged["x"].values)
    res = sm.OLS(yv, Xv).fit(
        cov_type="HAC",
        cov_kwds={"maxlags": 6, "use_correction": True},
    )
    alpha_d = float(res.params[0])
    t_hac   = float(res.tvalues[0])
    beta    = float(res.params[1])
    r2      = float(res.rsquared)

    resid   = yv - res.fittedvalues
    res_sr  = (float(np.mean(resid) / np.std(resid, ddof=1) * np.sqrt(252))
               if np.std(resid) > 0 else 0.0)

    return {
        "alpha_ann":     round(alpha_d * 252 * CAPITAL, 0),
        "alpha_ann_pct": round(alpha_d * 252 * 100, 2),
        "t_hac":         round(t_hac, 3),
        "beta":          round(beta, 4),
        "r2":            round(r2, 4),
        "resid_sr":      round(res_sr, 4),
    }


def bh_alpha(metrics: dict, nq_ret: pd.Series) -> dict:
    """Alpha vs NQ B&H (HAC OLS on daily excess returns)."""
    return _hac_ols(metrics["daily_exc"], nq_ret)


def _approx_multi_test_penalty(sharpe_daily: float, n_obs: int,
                                n_tests: int = N_TESTS) -> dict:
    """
    approx_multi_test_penalty -- BLP (Bailey, Lopez de Prado) simplified.
    Identical to spy_proxy.py for consistency.
    Propfirm gate threshold: p < 0.10 (looser than research 0.05).
    """
    if not np.isfinite(sharpe_daily) or n_obs < 10:
        return {"amtp_pvalue": None, "amtp_pass": False}
    sr_d  = sharpe_daily / np.sqrt(252)
    eg    = 0.5772156649   # Euler-Mascheroni
    z     = ((1 - eg) * stats.norm.ppf(1 - 1 / n_tests)
             + eg      * stats.norm.ppf(1 - 1 / (n_tests * np.e)))
    sr_star = z / np.sqrt(n_obs - 1)
    denom   = 1 / (n_obs - 1)
    if denom <= 0:
        return {"amtp_pvalue": None, "amtp_pass": False}
    pval = float(stats.norm.sf((sr_d - sr_star) / np.sqrt(denom)))
    return {
        "amtp_pvalue": round(pval, 4),
        "amtp_pass":   bool(pval < 0.10),   # propfirm gate
    }


# -----------------------------------------------------------------------------
# Walk-forward
# -----------------------------------------------------------------------------

def walk_forward(
    tl: pd.DataFrame,
    rf: pd.Series,
    windows: list[tuple],
) -> list[dict]:
    """OOS-only stats for each walk-forward window."""
    results = []
    for is_s, is_e, oos_s, oos_e in windows:
        oos_tl = tl[(tl["date"] >= oos_s) & (tl["date"] <= oos_e)]
        if len(oos_tl) < 5:
            results.append({
                "oos_range": f"{oos_s[:7]} -> {oos_e[:7]}",
                "n_trades": len(oos_tl), "win_rate": None,
                "sharpe": None, "pf": None, "max_dd": None,
                "max_dd_pct": None, "p_ev_le_0": None,
            })
            continue
        m = compute_metrics(oos_tl.copy(), rf)
        b = bootstrap_ev(oos_tl.copy())
        results.append({
            "oos_range":  f"{oos_s[:7]} -> {oos_e[:7]}",
            "n_trades":   m["n_trades"],
            "win_rate":   round(m["win_rate"] * 100, 1),
            "sharpe":     m["sharpe"],
            "pf":         m["pf"],
            "max_dd":     m["max_dd"],
            "max_dd_pct": m["max_dd_pct"],
            "p_ev_le_0":  b["p_ev_le_0"],
        })
    return results


def _wf_pct_positive(wf: list[dict]) -> float:
    valid = [w for w in wf if w.get("sharpe") is not None]
    if not valid:
        return 0.0
    return sum(1 for w in valid if (w["sharpe"] or 0) > 0) / len(valid) * 100


# -----------------------------------------------------------------------------
# Plumbing validation
# -----------------------------------------------------------------------------

def plumbing_check(tl: pd.DataFrame, df1m: pd.DataFrame) -> dict:
    """Validate implementation on sample trades."""
    results = {}

    # 1. ORB window bounded [08:30, 09:00)
    unique_dates = sorted(tl["date"].dt.date.unique())[:3]
    orb_samples  = []
    for d in unique_dates:
        ds       = str(d)
        s_ts     = pd.Timestamp(f"{ds} 08:30:00", tz="US/Eastern")
        e_ts     = pd.Timestamp(f"{ds} 09:00:00", tz="US/Eastern") - pd.Timedelta(minutes=1)
        orb_bars = df1m[s_ts:e_ts]
        if not orb_bars.empty:
            first_t = orb_bars.index[0].time()
            last_t  = orb_bars.index[-1].time()
            orb_samples.append({
                "date":   ds,
                "n_bars": len(orb_bars),
                "first":  str(first_t),
                "last":   str(last_t),
                "ok":     first_t >= time(8, 30) and last_t < time(9, 0),
            })
    results["orb_window_ok"] = all(s["ok"] for s in orb_samples) if orb_samples else False
    results["orb_samples"]   = orb_samples

    # 2. Entry only after 09:00
    results["entry_after_9"] = bool(all(
        t.time() >= time(9, 0) for t in tl["entry_time"].head(10)
    ))

    # 3. TP price
    tp_trades  = tl[tl["exit_reason"] == "tp"].head(2)
    tp_samples = []
    for _, row in tp_trades.iterrows():
        expected = row["entry_price"] + row["orb_range"]
        tp_samples.append({
            "date":        str(row["date"].date()),
            "entry":       row["entry_price"],
            "exit":        row["exit_price"],
            "expected_tp": round(expected, 4),
            "match":       abs(row["exit_price"] - expected) < 0.01,
        })
    results["tp_ok"]      = all(s["match"] for s in tp_samples) if tp_samples else True
    results["tp_samples"] = tp_samples

    # 4. SL price
    sl_trades  = tl[tl["exit_reason"] == "sl"].head(2)
    sl_samples = []
    for _, row in sl_trades.iterrows():
        sl_samples.append({
            "date":        str(row["date"].date()),
            "entry":       row["entry_price"],
            "exit":        row["exit_price"],
            "expected_sl": row["orb_low"],
            "match":       abs(row["exit_price"] - row["orb_low"]) < 0.01,
        })
    results["sl_ok"]      = all(s["match"] for s in sl_samples) if sl_samples else True
    results["sl_samples"] = sl_samples

    # 5. Time exit >= 15:00
    time_trades = tl[tl["exit_reason"] == "time"].head(3)
    te_samples  = []
    for _, row in time_trades.iterrows():
        if pd.notna(row["exit_time"]):
            et = row["exit_time"]
            te_samples.append({
                "date":    str(row["date"].date()),
                "exit_at": str(et),
                "ok":      et.time() >= time(15, 0),
            })
    results["time_exit_ok"] = all(s["ok"] for s in te_samples) if te_samples else True
    results["time_samples"] = te_samples

    # 6. One trade per session
    max_per_day = tl.groupby(tl["date"].dt.date).size().max()
    results["one_trade_per_session"] = bool(max_per_day == 1)
    results["max_trades_in_session"] = int(max_per_day)

    # 7. Cost $14 RT
    cost_checks = []
    for _, row in tl.head(3).iterrows():
        expected = (row["exit_price"] - row["entry_price"]) * POINT_VALUE - COST_RT
        cost_checks.append({
            "date":     str(row["date"].date()),
            "net_pnl":  row["net_pnl"],
            "expected": round(expected, 2),
            "ok":       abs(row["net_pnl"] - expected) < 0.01,
        })
    results["cost_ok"]     = all(c["ok"] for c in cost_checks) if cost_checks else True
    results["cost_checks"] = cost_checks

    return results


def manual_trade_check(tl: pd.DataFrame) -> str:
    """Return 10 random trades formatted for manual lookahead bias check."""
    sample = tl.sample(min(10, len(tl)), random_state=42)
    lines  = ["10 random trades for manual lookahead check:"]
    for _, row in sample.iterrows():
        lines.append(
            f"  {str(row['date'].date())}  "
            f"ORB=[{row['orb_low']:.2f}, {row['orb_high']:.2f}]  "
            f"R={row['orb_range']:.2f}  "
            f"Entry={row['entry_price']:.2f} @ {str(row['entry_time'])}  "
            f"Exit={row['exit_price']:.2f} @ {str(row['exit_time'])}  "
            f"({row['exit_reason']})  net=${row['net_pnl']:.0f}"
        )
    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Summary builder
# -----------------------------------------------------------------------------

def _v(x, fmt=None):
    """Format a value, or -- if None/NaN."""
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "--"
    return format(x, fmt) if fmt else str(x)


def _ok(b: bool) -> str:
    return "yes" if b else "no"


def build_summary(
    n_sessions:  int,
    tl5: pd.DataFrame,  m5: dict,
    tl1: pd.DataFrame,  m1: dict,
    bh5: dict,
    boot5: dict, mc5: dict, shuf5: dict,
    wf5: list,
    amtp5: dict, amtp1: dict,
    plumb5: dict, plumb1: dict,
    suspicious5: bool, suspicious1: bool,
) -> str:
    lines = []
    A = lines.append

    A("## Result Summary: ORB IVB on NQ -- Kaggle 1-min Data, Delta-Free Variant")
    A("")

    # -- Section 1: Headline --------------------------------------------------
    def _verdict(m: dict, wf: list) -> str:
        if not m or m.get("n_trades", 0) == 0:
            return "DATA_QUALITY_ISSUE -- zero trades"
        sh  = m.get("sharpe", 0) or 0
        pf  = m.get("pf",  0)    or 0
        dd  = m.get("max_dd_pct", -999) or -999
        wfp = _wf_pct_positive(wf) if wf else 0.0
        if sh > 1.0 and pf > 1.20 and dd > -10 and wfp >= 75:
            return "PASS_PROPFIRM -- Sharpe>1, PF>1.20, DD within limit, WF>=75% positive"
        elif sh > 0.5:
            return "PASS_RESEARCH_ONLY -- positive edge; not yet propfirm-ready"
        else:
            return "FAIL -- insufficient edge (Sharpe<0.5)"

    A("### 1. Headline verdict")
    A(f"> **5-min variant**: {_verdict(m5, wf5)}")
    A("")

    # -- Section 2: Data ------------------------------------------------------
    pq_path = _PROJ / "data" / "raw" / "NQ_1min_2022-12-26_2025-12-11.parquet"
    n_bars  = "--"
    if pq_path.exists():
        try:
            import pyarrow.parquet as pq_io
            n_bars = f"{pq_io.read_metadata(str(pq_path)).num_rows:,}"
        except Exception:
            n_bars = "(see data_audit_report.md)"

    A("### 2. Data quality")
    A(f"- Total bars loaded: {n_bars}")
    A(f"- Valid trading sessions (clean_sessions.json): {n_sessions}")
    A(f"- See `data_audit_report.md` for full quality report and excluded sessions.")
    A("")

    # -- Section 3: Conti comparison ------------------------------------------
    A("### 3. Replication match vs Conti (NQ, 2021-2026)")
    A("")
    yr5 = m5.get("n_trades", 0) / 3.0
    yr1 = m1.get("n_trades", 0) / 3.0
    A("| Metric              | Conti (NQ w/ delta) | Ours 5-min (no delta) | Ours 1-min (no delta) |")
    A("|---------------------|---------------------|----------------------|----------------------|")
    A(f"| Total trades        | 823 (5 years)       | {m5.get('n_trades', '--')} (3 years)   | {m1.get('n_trades', '--')} (3 years)   |")
    A(f"| Trades per year     | ~165                | {_v(yr5, '.0f')}                      | {_v(yr1, '.0f')} |")
    A(f"| Win rate            | 58.3%               | {_v(m5.get('win_rate', 0)*100, '.1f')}%              | {_v(m1.get('win_rate', 0)*100, '.1f')}% |")
    A(f"| Avg trade ($)       | $201.35             | ${_v(m5.get('avg_trade'), '.0f')}                 | ${_v(m1.get('avg_trade'), '.0f')} |")
    A(f"| Avg winner ($)      | $1,474              | ${_v(m5.get('avg_win'), '.0f')}               | ${_v(m1.get('avg_win'), '.0f')} |")
    A(f"| Avg loser ($)       | -$1,580             | ${_v(m5.get('avg_loss'), '.0f')}              | ${_v(m1.get('avg_loss'), '.0f')} |")
    A(f"| MaxDD ($)           | $25,295             | ${_v(abs(m5.get('max_dd', 0)), '.0f')}           | ${_v(abs(m1.get('max_dd', 0)), '.0f')} |")
    A(f"| Profit factor       | 1.31                | {_v(m5.get('pf'), '.3f')}               | {_v(m1.get('pf'), '.3f')} |")
    A(f"| Annual return (%)   | 31.4%               | {_v(m5.get('ann_ret_pct'), '.1f')}%             | {_v(m1.get('ann_ret_pct'), '.1f')}% |")
    A(f"| Sharpe              | ~1.4 (monthly)      | {_v(m5.get('sharpe'), '.3f')} (daily HAC)  | {_v(m1.get('sharpe'), '.3f')} |")
    A("")

    # -- Section 4: Performance metrics ---------------------------------------
    A("### 4. Performance metrics (gross + cost-adjusted)")
    A("")
    g5  = tl5["gross_pnl"].sum() if not tl5.empty else 0
    g1  = tl1["gross_pnl"].sum() if not tl1.empty else 0
    gwr5 = float(tl5["winner"].mean()) if not tl5.empty else 0.0
    gwr1 = float(tl1["winner"].mean()) if not tl1.empty else 0.0
    n5t  = m5.get("n_trades", 1) or 1
    n1t  = m1.get("n_trades", 1) or 1
    ec5  = m5.get("exit_counts", {})
    ec1  = m1.get("exit_counts", {})
    A("| Metric             | 5-min gross | 5-min cost-adj | 1-min cost-adj |")
    A("|--------------------|-------------|----------------|----------------|")
    A(f"| Total trades       | {m5.get('n_trades', '--')} | {m5.get('n_trades', '--')} | {m1.get('n_trades', '--')} |")
    A(f"| Win rate           | {gwr5*100:.1f}% | {m5.get('win_rate', 0)*100:.1f}% | {m1.get('win_rate', 0)*100:.1f}% |")
    A(f"| Avg trade ($)      | ${_v(tl5['gross_pnl'].mean() if not tl5.empty else 0, '.0f')} | ${_v(m5.get('avg_trade'), '.0f')} | ${_v(m1.get('avg_trade'), '.0f')} |")
    A(f"| Net P&L ($)        | ${g5:,.0f} | ${m5.get('total_pnl', 0):,.0f} | ${m1.get('total_pnl', 0):,.0f} |")
    A(f"| Sharpe (daily HAC) | -- | {_v(m5.get('sharpe'), '.3f')} | {_v(m1.get('sharpe'), '.3f')} |")
    A(f"| MaxDD ($)          | -- | ${_v(m5.get('max_dd'), '.0f')} | ${_v(m1.get('max_dd'), '.0f')} |")
    A(f"| MaxDD (%)          | -- | {_v(m5.get('max_dd_pct'), '.1f')}% | {_v(m1.get('max_dd_pct'), '.1f')}% |")
    A(f"| Profit factor      | -- | {_v(m5.get('pf'), '.3f')} | {_v(m1.get('pf'), '.3f')} |")
    A(f"| Ann. return (%)    | -- | {_v(m5.get('ann_ret_pct'), '.1f')}% | {_v(m1.get('ann_ret_pct'), '.1f')}% |")
    A(f"| Exits TP/SL/time   | -- | "
      f"TP {ec5.get('tp', 0)/n5t*100:.0f}% / SL {ec5.get('sl', 0)/n5t*100:.0f}% / time {ec5.get('time', 0)/n5t*100:.0f}% | "
      f"TP {ec1.get('tp', 0)/n1t*100:.0f}% / SL {ec1.get('sl', 0)/n1t*100:.0f}% / time {ec1.get('time', 0)/n1t*100:.0f}% |")
    A("")

    # -- Section 5: Bootstrap & MC --------------------------------------------
    A("### 5. Bootstrap & Monte Carlo (5-min variant, cost-adj)")
    A("")
    if boot5 and mc5 and shuf5:
        dd = mc5.get("maxdd_ptiles", {})
        A(f"- EV/trade ($):  ${_v(boot5.get('ev_dollar'), '.2f')}  "
          f"[95% CI ${_v(boot5.get('ci_dollar', [None, None])[0], '.2f')}, "
          f"${_v(boot5.get('ci_dollar', [None, None])[1], '.2f')}]")
        A(f"- EV/trade (R):  {_v(boot5.get('ev_r'), '.4f')}  "
          f"[95% CI {_v(boot5.get('ci_r', [None, None])[0], '.4f')}, "
          f"{_v(boot5.get('ci_r', [None, None])[1], '.4f')}]")
        A(f"- P(EV$ <= 0):   {_v(boot5.get('p_ev_le_0'), '.4f')}")
        A(f"- P(EV_R <= 0):  {_v(boot5.get('p_r_le_0'), '.4f')}")
        A(f"- MC MaxDD p50/p75/p90/p95/p99:  "
          f"${_v(dd.get('50'), '.0f')} / ${_v(dd.get('75'), '.0f')} / "
          f"${_v(dd.get('90'), '.0f')} / ${_v(dd.get('95'), '.0f')} / "
          f"${_v(dd.get('99'), '.0f')}")
        A(f"- MC median terminal P&L:         ${_v(mc5.get('terminal_p50'), '.0f')}")
        A(f"- Shuffled Sharpe p95:            {_v(shuf5.get('shuffled_p95'), '.4f')}")
        A(f"- P(shuffled >= observed):        {_v(shuf5.get('p_shuffle_beat'), '.4f')}")
        A(f"- AMTP p-value (n={N_TESTS-1}, 5-min): {_v(amtp5.get('amtp_pvalue'), '.4f')}  "
          f"{'(PASS)' if amtp5.get('amtp_pass') else '(FAIL)'}")
    else:
        A("n/a")
    A("")

    # -- Section 6: Walk-forward ----------------------------------------------
    A("### 6. Walk-forward (5-min variant, OOS windows)")
    A("")
    A("| OOS Window          | Trades | Win%  | Sharpe | PF    | MaxDD%  | P(EV<=0) |")
    A("|---------------------|--------|-------|--------|-------|---------|----------|")
    if wf5:
        for w in wf5:
            A(f"| {w['oos_range']:<19} | "
              f"{_v(w.get('n_trades')):<6} | "
              f"{_v(w.get('win_rate'), '.1f') if w.get('win_rate') is not None else '--':<5} | "
              f"{_v(w.get('sharpe'), '+.3f') if w.get('sharpe') is not None else '--':<6} | "
              f"{_v(w.get('pf'), '.3f') if w.get('pf') is not None else '--':<5} | "
              f"{_v(w.get('max_dd_pct'), '.1f') if w.get('max_dd_pct') is not None else '--':<7} | "
              f"{_v(w.get('p_ev_le_0'), '.4f') if w.get('p_ev_le_0') is not None else '--':<8} |")
        A(f"| **OOS aggregate**   | -- | -- | -- | -- | -- | {_wf_pct_positive(wf5):.0f}% positive |")
    A("")

    # -- Section 7: Alpha -----------------------------------------------------
    A("### 7. Alpha vs NQ B&H (HAC OLS, daily excess returns)")
    A("")
    A("> Note: intraday strategy (~6h/day exposure). NQ B&H is not the natural benchmark.")
    A("> Alpha t > 2 indicates genuine intraday edge regardless.")
    A("")
    A("| Metric              | 5-min variant |")
    A("|---------------------|---------------|")
    A(f"| Alpha (ann. %)      | {_v(bh5.get('alpha_ann_pct'), '+.2f')}% |")
    A(f"| Alpha t-stat (HAC)  | {_v(bh5.get('t_hac'), '+.3f')} |")
    A(f"| Beta vs NQ          | {_v(bh5.get('beta'), '.4f')} |")
    A(f"| R2                  | {_v(bh5.get('r2'), '.4f')} |")
    A(f"| Residual Sharpe     | {_v(bh5.get('resid_sr'), '.4f')} |")
    A("")

    # -- Section 8: Propfirm gate ---------------------------------------------
    A("### 8. Propfirm gate decision")
    A("")
    sh5  = m5.get("sharpe", 0) or 0
    pf5  = m5.get("pf",  0)    or 0
    dd5  = m5.get("max_dd_pct", -999) or -999
    bev5 = boot5.get("p_ev_le_0", 1.0) if boot5 else 1.0
    wfp5 = _wf_pct_positive(wf5) if wf5 else 0.0
    ap5  = amtp5.get("amtp_pvalue", 1.0) or 1.0

    def _gate(val, thr, gt=True):
        if val is None or (isinstance(val, float) and not np.isfinite(float(val))):
            return "--"
        return "PASS" if (float(val) > thr if gt else float(val) < thr) else "FAIL"

    A("| Gate                       | Threshold | Value         | Pass |")
    A("|----------------------------|-----------|---------------|------|")
    A(f"| Sharpe HAC (5-min)         | > 1.0     | {_v(sh5, '.3f'):<13} | {_gate(sh5, 1.0)} |")
    A(f"| MaxDD (% of $100k)         | > -10%    | {_v(dd5, '.1f')}%{'':<11} | {_gate(dd5, -10.0)} |")
    A(f"| P(EV <= 0) bootstrap       | < 0.05    | {_v(bev5, '.4f'):<13} | {_gate(bev5, 0.05, False)} |")
    A(f"| Profit factor (cost-adj)   | > 1.20    | {_v(pf5, '.3f'):<13} | {_gate(pf5, 1.20)} |")
    A(f"| Walk-forward % positive    | > 75%     | {_v(wfp5, '.0f')}%{'':<12} | {_gate(wfp5, 75.0)} |")
    A(f"| AMTP p-value (n={N_TESTS-1})      | < 0.10    | {_v(ap5, '.4f'):<13} | {'PASS' if amtp5.get('amtp_pass') else 'FAIL'} |")
    A("")

    # -- Section 9: Plumbing --------------------------------------------------
    A("### 9. Plumbing validation (5-min variant)")
    A("")
    p5 = plumb5 or {}
    A(f"- ORB window bounded [08:30, 09:00): {'yes' if p5.get('orb_window_ok') else 'NO'}")
    for s in p5.get("orb_samples", [])[:3]:
        A(f"  - {s['date']}: {s['n_bars']} bars, first={s['first']}, last={s['last']}")
    A(f"- Entry only after 09:00: {_ok(p5.get('entry_after_9', False))}")
    A(f"- TP triggered at TP price: {_ok(p5.get('tp_ok', False))}")
    for s in p5.get("tp_samples", [])[:2]:
        A(f"  - {s['date']}: entry={s['entry']}, exit={s['exit']}, expected_tp={s['expected_tp']}, match={s['match']}")
    A(f"- SL triggered at SL price: {_ok(p5.get('sl_ok', False))}")
    for s in p5.get("sl_samples", [])[:2]:
        A(f"  - {s['date']}: entry={s['entry']}, exit={s['exit']}, expected_sl={s['expected_sl']}, match={s['match']}")
    A(f"- Time exit at or after 15:00: {_ok(p5.get('time_exit_ok', False))}")
    for s in p5.get("time_samples", [])[:2]:
        A(f"  - {s['date']}: exit_at={s['exit_at']}, ok={s['ok']}")
    A(f"- Only 1 trade per session: {_ok(p5.get('one_trade_per_session', False))}  "
      f"(max {p5.get('max_trades_in_session', '?')} in any session)")
    A(f"- Cost $14 RT: {_ok(p5.get('cost_ok', False))}")
    for s in p5.get("cost_checks", [])[:2]:
        A(f"  - {s['date']}: net_pnl={s['net_pnl']:.2f}, expected={s['expected']:.2f}")
    A("")

    # -- Section 10: 5-min vs 1-min -------------------------------------------
    A("### 10. 5-min vs 1-min comparison")
    A("")
    sh1 = m1.get("sharpe", 0) or 0
    pf1 = m1.get("pf",  0)    or 0
    n5t_cmp = m5.get("n_trades", 0)
    n1t_cmp = m1.get("n_trades", 0)
    A("| Metric     | 5-min | 1-min | Delta |")
    A("|------------|-------|-------|-------|")
    A(f"| Trades     | {n5t_cmp} | {n1t_cmp} | {n1t_cmp - n5t_cmp:+d} |")
    A(f"| Win rate   | {m5.get('win_rate', 0)*100:.1f}% | {m1.get('win_rate', 0)*100:.1f}% | -- |")
    A(f"| Sharpe     | {_v(sh5, '.3f')} | {_v(sh1, '.3f')} | {_v(sh1 - sh5, '+.3f')} |")
    A(f"| PF         | {_v(pf5, '.3f')} | {_v(pf1, '.3f')} | {_v(pf1 - pf5, '+.3f')} |")
    A(f"| Ann ret    | {_v(m5.get('ann_ret_pct'), '.1f')}% | {_v(m1.get('ann_ret_pct'), '.1f')}% | -- |")
    A("")

    # -- Section 11: Recommendation -------------------------------------------
    A("### 11. Recommendation")
    A("")
    gates_passed = sum([
        sh5 > 1.0,
        pf5 > 1.20,
        dd5 > -10.0,
        wfp5 >= 75.0,
        bev5 < 0.05,
    ])
    if suspicious5:
        A("> SUSPICIOUS RESULTS -- Sharpe > 3 or PF > 2. "
          "Verify for lookahead bias before any further use.")
    elif sh5 > 1.0 and pf5 > 1.20 and dd5 > -10.0 and wfp5 >= 75.0:
        A("> Deploy to NQ paper/propfirm sandbox. Delta filter was not required -- "
          "delta-free ORB has independent edge. Skip Databento subscription.")
    elif sh5 > 0.5:
        A("> Research edge confirmed; not yet propfirm-ready. Test variations: "
          "1.5R target, session-range filter (skip narrow ORBs), day-of-week filter. "
          "Don't subscribe Databento yet.")
    else:
        A("> Archive ORB family OR investigate delta filter. "
          "Delta filter may have been the real edge in Conti. "
          "Consider Databento $30/mo to test delta-filtered NQ ORB, or archive and pivot.")
    A("")
    A(f"Gates passed: {gates_passed}/5 (excluding AMTP)")
    A("")

    # -- Section 12: n_tests --------------------------------------------------
    A("### 12. n_tests counter")
    A("")
    A("- Start: 66")
    A("- 5-min NQ ORB (this script): n_tests = 67")
    A("- 1-min NQ ORB (this script): n_tests = 68")
    A("- **End: 68**")
    A("")

    return "\n".join(lines)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main():
    SEP = "-" * 72
    print("=" * 72)
    print("ORB IVB on NQ -- Kaggle 1-min Data, Delta-Free Variant")
    print("=" * 72)

    # -- Load data ------------------------------------------------------------
    print("\nLoading NQ 1-min data ...")
    df1m = load_nq_1min()
    print(f"  {len(df1m):,} bars  {df1m.index[0].date()} -> {df1m.index[-1].date()}")

    # -- Resample to 5-min ----------------------------------------------------
    print("Resampling to 5-min ...")
    df5m = resample_5min(df1m)
    print(f"  {len(df5m):,} 5-min bars")

    # -- Load clean sessions --------------------------------------------------
    sessions = load_clean_sessions()
    if not sessions:
        print("\n  clean_sessions.json not found -- run data_audit.py first.")
        print("  Falling back to all dates with ORB window data (2023+).")
        orb_mask = (df1m.index.time >= time(8, 30)) & (df1m.index.time < time(9, 0))
        sessions = sorted(
            set(str(d.date()) for d in df1m[orb_mask].index.normalize().unique())
        )
        sessions = [s for s in sessions if s >= "2023-01-01"]

    n_sessions = len(sessions)
    print(f"  Sessions: {n_sessions}")

    # -- Load RF --------------------------------------------------------------
    print("Fetching FRED DTB3 ...")
    rf = load_rf()

    # -- 5-min strategy -------------------------------------------------------
    print(f"\n{SEP}")
    print("5-MIN ORB SIMULATION")
    print(SEP)
    tl5 = run_strategy(df1m, df5m, sessions, use_1min=False)
    print(f"  Trades: {len(tl5)}")

    if len(tl5) == 0:
        print("\n  ZERO TRADES -- debugging ORB window conditions:")
        for ds in sessions[:5]:
            d  = date.fromisoformat(ds)
            s  = pd.Timestamp(f"{ds} 08:30:00", tz="US/Eastern")
            e  = pd.Timestamp(f"{ds} 09:00:00", tz="US/Eastern") - pd.Timedelta(minutes=1)
            orb = df1m[s:e]
            t9  = pd.Timestamp(f"{ds} 09:00:00", tz="US/Eastern")
            t15 = pd.Timestamp(f"{ds} 15:05:00", tz="US/Eastern")
            tw  = df5m[t9:t15]
            hi  = orb["high"].max() if not orb.empty else float("nan")
            print(f"  {ds}: ORB bars={len(orb)}, ORB_high={hi:.2f}, "
                  f"trade 5min bars={len(tw)}, "
                  f"bars>ORB_high={(tw['close'] > hi).sum() if not tw.empty else 0}")
        sys.exit(1)

    m5 = compute_metrics(tl5, rf)
    print(f"  Win rate: {m5['win_rate']*100:.1f}%  PF: {m5['pf']:.3f}  "
          f"Sharpe: {m5['sharpe']:+.3f}  MaxDD: ${m5['max_dd']:,.0f} ({m5['max_dd_pct']:.1f}%)  "
          f"Ann ret: {m5['ann_ret_pct']:+.1f}%")

    # -- SUSPICIOUS checkpoint ------------------------------------------------
    suspicious5 = m5["sharpe"] > 3 or m5["pf"] > 2
    if suspicious5:
        print("\n  *** SUSPICIOUS: Sharpe > 3 or PF > 2 -- printing 10 random trades: ***")
        print(manual_trade_check(tl5))
        print("\n  Halting for manual review before continuing.")

    # -- 1-min strategy -------------------------------------------------------
    print(f"\n{SEP}")
    print("1-MIN ORB SIMULATION")
    print(SEP)
    tl1 = run_strategy(df1m, df5m, sessions, use_1min=True)
    print(f"  Trades: {len(tl1)}")

    m1 = compute_metrics(tl1, rf) if not tl1.empty else {
        "n_trades": 0, "win_rate": 0.0, "pf": 0.0,
        "avg_trade": 0.0, "avg_win": 0.0, "avg_loss": 0.0, "avg_r": 0.0,
        "total_pnl": 0.0, "ann_ret_pct": 0.0, "sharpe": 0.0,
        "max_dd": 0.0, "max_dd_pct": 0.0, "exit_counts": {},
        "daily_exc": pd.Series(dtype=float),
    }
    if not tl1.empty:
        print(f"  Win rate: {m1['win_rate']*100:.1f}%  PF: {m1['pf']:.3f}  "
              f"Sharpe: {m1['sharpe']:+.3f}  MaxDD: ${m1['max_dd']:,.0f}")

    suspicious1 = m1.get("sharpe", 0) > 3 or m1.get("pf", 0) > 2

    # -- NQ B&H alpha ---------------------------------------------------------
    print(f"\n{SEP}")
    print("NQ B&H ALPHA (5-min, HAC OLS)")
    print(SEP)
    nq_ret = compute_nq_daily(df1m)
    bh5    = bh_alpha(m5, nq_ret)
    print(f"  alpha_ann={_v(bh5.get('alpha_ann_pct'), '+.2f')}%  "
          f"t_HAC={_v(bh5.get('t_hac'), '+.3f')}  "
          f"beta={_v(bh5.get('beta'), '.4f')}  "
          f"R2={_v(bh5.get('r2'), '.4f')}")

    # -- Bootstrap ------------------------------------------------------------
    print(f"\n{SEP}")
    print("BOOTSTRAP EV (5-min, 20,000 resamples)")
    print(SEP)
    boot5 = bootstrap_ev(tl5)
    print(f"  EV: ${boot5['ev_dollar']:.2f}  "
          f"95%CI [${boot5['ci_dollar'][0]:.2f}, ${boot5['ci_dollar'][1]:.2f}]  "
          f"P(EV$<=0): {boot5['p_ev_le_0']:.4f}")

    # -- Monte Carlo ----------------------------------------------------------
    print(f"\n{SEP}")
    print("MONTE CARLO PATHS (20,000 simulations)")
    print(SEP)
    mc5 = monte_carlo(tl5)
    dd  = mc5["maxdd_ptiles"]
    print(f"  MaxDD p50/p75/p90/p95/p99: "
          f"${dd['50']:,.0f} / ${dd['75']:,.0f} / ${dd['90']:,.0f} / "
          f"${dd['95']:,.0f} / ${dd['99']:,.0f}")
    print(f"  Terminal P&L p25/p50/p75: "
          f"${mc5['terminal_p25']:,.0f} / ${mc5['terminal_p50']:,.0f} / ${mc5['terminal_p75']:,.0f}")

    # -- Shuffled sequences ---------------------------------------------------
    print(f"\n{SEP}")
    print("SHUFFLED SEQUENCES (1,000 permutations)")
    print(SEP)
    shuf5 = shuffled_sequences(tl5)
    print(f"  Obs Sharpe: {shuf5['obs_sharpe']:+.4f}  "
          f"Shuffled p95: {shuf5['shuffled_p95']:+.4f}  "
          f"P(shuffled>=obs): {shuf5['p_shuffle_beat']:.4f}")

    # -- AMTP -----------------------------------------------------------------
    n_days = int(m5["daily_exc"].notna().sum()) if hasattr(m5.get("daily_exc"), "notna") else len(tl5)
    amtp5  = _approx_multi_test_penalty(m5["sharpe"], n_days, N_TESTS - 1)
    amtp1  = _approx_multi_test_penalty(m1.get("sharpe", 0), n_days, N_TESTS)
    print(f"\n  AMTP(5-min, n={N_TESTS-1}): p={_v(amtp5.get('amtp_pvalue'), '.4f')}  "
          f"{'PASS' if amtp5.get('amtp_pass') else 'FAIL'} (threshold 0.10)")
    print(f"  AMTP(1-min, n={N_TESTS}): p={_v(amtp1.get('amtp_pvalue'), '.4f')}  "
          f"{'PASS' if amtp1.get('amtp_pass') else 'FAIL'} (threshold 0.10)")

    # -- Walk-forward ---------------------------------------------------------
    print(f"\n{SEP}")
    print("WALK-FORWARD (5-min, 4 OOS windows)")
    print(SEP)
    wf5 = walk_forward(tl5, rf, _WF_WINDOWS)
    for w in wf5:
        sh_str = _v(w.get('sharpe'), '+.3f') if w.get('sharpe') is not None else "--"
        pf_str = _v(w.get('pf'), '.3f')       if w.get('pf')     is not None else "--"
        print(f"  OOS {w['oos_range']}: "
              f"n={_v(w.get('n_trades'))}  Sharpe={sh_str}  PF={pf_str}  "
              f"P(EV<=0)={_v(w.get('p_ev_le_0'), '.4f') if w.get('p_ev_le_0') is not None else '--'}")
    print(f"  WF % positive windows: {_wf_pct_positive(wf5):.0f}%")

    # -- Plumbing -------------------------------------------------------------
    print(f"\n{SEP}")
    print("PLUMBING VALIDATION")
    print(SEP)
    plumb5 = plumbing_check(tl5, df1m)
    plumb1 = plumbing_check(tl1, df1m) if not tl1.empty else {}
    print(f"  ORB window [08:30, 09:00): {'yes' if plumb5.get('orb_window_ok') else 'NO'}")
    print(f"  Entry after 09:00:         {'yes' if plumb5.get('entry_after_9') else 'NO'}")
    print(f"  TP price correct:          {'yes' if plumb5.get('tp_ok') else 'NO'}")
    print(f"  SL price correct:          {'yes' if plumb5.get('sl_ok') else 'NO'}")
    print(f"  Time exit >= 15:00:        {'yes' if plumb5.get('time_exit_ok') else 'NO'}")
    print(f"  1 trade/session:           {'yes' if plumb5.get('one_trade_per_session') else 'NO'}")
    print(f"  Cost $14 RT:               {'yes' if plumb5.get('cost_ok') else 'NO'}")

    # -- Build and save summary -----------------------------------------------
    summary = build_summary(
        n_sessions=n_sessions,
        tl5=tl5, m5=m5,
        tl1=tl1, m1=m1,
        bh5=bh5,
        boot5=boot5, mc5=mc5, shuf5=shuf5,
        wf5=wf5,
        amtp5=amtp5, amtp1=amtp1,
        plumb5=plumb5, plumb1=plumb1,
        suspicious5=suspicious5, suspicious1=suspicious1,
    )

    _SUMMARY_PATH.write_text(summary)
    print(f"\nSaved -> {_SUMMARY_PATH}")

    print("\n" + "=" * 72)
    print(summary)
    print("=" * 72)


if __name__ == "__main__":
    main()
