"""
iter_d2_mr.py — Strategy D v2: Intraday Mean Reversion on NQ
=============================================================
Hypothesis: ORB continuation (C) and post-ORB mean reversion (D) coexist
as distinct regimes. When C fires → continuation. When C does not fire or
fails → reversion to VWAP dominates.

5 candidates (AXIS 1 only, max 3 modifications per hypothesis):
  D1 — Failed ORB fade: C fired but reversed 0.5R within 30 min
  D2 — VWAP touch fade post-noon (11:30-14:00, 5-min momentum exhaustion)
  D3 — Opening range mid-fade (09:45-11:00, C not fired, range>60pt)
  D4 — Lunch RSI reversal (12:00-13:00, 30-min RSI extremes)
  D5 — Afternoon vol compression breakout (14:00-15:30, BB squeeze)

Kill switch: 5 tested, none beats trades/day ≥ 0.8 AND PF ≥ 1.3 → STOP

n_tests: 153 → 158 (max; each variant = 1 n_test regardless of IC outcome)

Run: /usr/bin/python3 -m Futures.research.active.nq_intraday.analysis.iter_d2_mr
"""
from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import scipy.stats as stats
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).parents[5]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT, append_result,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features, BASE_SL_MULT, BASE_TP_MULT,
)
from Futures.research.active.nq_intraday.analysis.signal_refinements import extended_wf
from Futures.research.active.nq_intraday.analysis.propfirm_compat_v2 import (
    _stationary_block_paths, _simulate_tradeify_eval,
    build_daily_pnl_mnq, TV_TRAILING_DD, TV_EVAL_TARGET,
    MC_PATHS, MC_SEED, AVG_BLOCK_LEN,
)

logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── constants ────────────────────────────────────────────────────────────────
N_TESTS_START  = 153
MNQ_PV         = 2.0
MNQ_COST_RT    = 2.15
NQ_PV          = 20.0
NQ_COST_RT     = 19.0
MNQ_EVAL       = 3
EVAL_DAYS_90   = 90

# iter_10 filters
C_GAP   = 0.012
C_RNG   = 30.0
C_STOP  = 400.0

# Strategy D gate thresholds
GATE_SHARPE    = 1.0
GATE_WF        = 60.0
GATE_PF        = 1.3
GATE_MDD       = -0.10
GATE_WR        = 0.50
GATE_TPD       = 0.8    # trades per day
GATE_CORR      = 0.20   # |corr(D, C)| ≤ 0.20

# Kill switch: 5 variants, none beats:
KILL_SWITCH_TPD = 0.5
KILL_SWITCH_PF  = 1.3

T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1000 = datetime.time(10, 0)
T_1130 = datetime.time(11, 30)
T_1200 = datetime.time(12, 0)
T_1230 = datetime.time(12, 30)
T_1300 = datetime.time(13, 0)
T_1400 = datetime.time(14, 0)
T_1530 = datetime.time(15, 30)
T_1559 = datetime.time(15, 59)


# ─── utilities ────────────────────────────────────────────────────────────────

def sharpe_hac(pnl: pd.Series, annual: float = 252.0) -> float:
    r = pnl.dropna()
    n = len(r)
    if n < 10:
        return np.nan
    mean = float(r.mean())
    if n < 48:
        std = float(r.std(ddof=1))
        return mean / std * np.sqrt(annual) if std > 1e-9 else np.nan
    reg = sm.OLS(r, np.ones(n)).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    lrv = float(reg.cov_params().iloc[0, 0]) * n
    hac = np.sqrt(max(lrv, 1e-24))
    return mean / hac * np.sqrt(annual) if hac > 1e-12 else np.nan


def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain  = delta.clip(lower=0).rolling(period).mean()
    loss  = (-delta.clip(upper=0)).rolling(period).mean()
    rs    = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_bb(series: pd.Series,
               period: int = 20,
               n_std: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
    mid   = series.rolling(period).mean()
    std   = series.rolling(period).std(ddof=1)
    upper = mid + n_std * std
    lower = mid - n_std * std
    return upper, mid, lower


def max_dd_pct(pnl: pd.Series) -> float:
    cum = pnl.cumsum()
    peak = cum.cummax()
    dd = (cum - peak)
    peak_max = float(cum.cummax().max())
    return float(dd.min() / peak_max) if peak_max > 0 else np.nan


def profit_factor(trade_log: pd.DataFrame) -> float:
    wins  = trade_log.loc[trade_log["pnl_usd"] > 0, "pnl_usd"].sum()
    loss  = trade_log.loc[trade_log["pnl_usd"] <= 0, "pnl_usd"].abs().sum()
    return float(wins / loss) if loss > 0 else np.nan


def ic_t_stat(signal: np.ndarray, fret: np.ndarray) -> Tuple[float, float]:
    """Spearman IC and approximate t-stat."""
    mask = np.isfinite(signal) & np.isfinite(fret)
    s, f = signal[mask], fret[mask]
    if len(s) < 10:
        return np.nan, np.nan
    rho, _ = stats.spearmanr(s, f)
    n       = len(s)
    t_stat  = rho * np.sqrt(n - 2) / np.sqrt(max(1 - rho**2, 1e-12))
    return float(rho), float(t_stat)


def daily_returns(trade_log: pd.DataFrame) -> pd.Series:
    """Daily P&L in NQ USD terms (zero on no-trade days)."""
    tl = trade_log.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize()
    daily = tl.groupby("date")["pnl_usd"].sum()
    all_dates = pd.bdate_range(tl["date"].min(), tl["date"].max())
    return daily.reindex(all_dates.normalize(), fill_value=0.0)


def tradeify_eval_90d(trade_log: pd.DataFrame, n_mnq: int = MNQ_EVAL) -> dict:
    daily   = build_daily_pnl_mnq(trade_log, n_mnq)
    pnl_arr = daily.values.astype(float)
    rng     = np.random.default_rng(MC_SEED + 22)
    paths   = _stationary_block_paths(pnl_arr, MC_PATHS, EVAL_DAYS_90,
                                       AVG_BLOCK_LEN, rng)
    r = _simulate_tradeify_eval(paths, TV_TRAILING_DD, TV_EVAL_TARGET, EVAL_DAYS_90)
    return r


def bh_adjust(p_values: list[float]) -> list[float]:
    """Benjamini-Hochberg FDR correction."""
    n   = len(p_values)
    idx = np.argsort(p_values)
    adj = np.array(p_values, dtype=float)
    for rank, i in enumerate(idx, 1):
        adj[i] = min(1.0, p_values[i] * n / rank)
    # enforce monotonicity (from largest rank down)
    for k in range(n - 2, -1, -1):
        adj[idx[k]] = min(adj[idx[k]], adj[idx[k + 1]])
    return adj.tolist()


def corr_with_c(d_log: pd.DataFrame, c_daily: pd.Series) -> float:
    d_daily = daily_returns(d_log)
    common  = c_daily.index.intersection(d_daily.index)
    if len(common) < 20:
        return np.nan
    return float(np.corrcoef(c_daily[common], d_daily[common])[0, 1])


# ─── Strategy C baseline (iter_10) ────────────────────────────────────────────

def build_c_iter10(engine: NQBacktestEngine) -> Tuple[pd.DataFrame, pd.Series]:
    """Rebuild Strategy C iter_10 trade log and daily returns (NQ terms)."""
    from Futures.research.active.nq_intraday.iter_05 import signals_from_features
    feats = build_opening_features(engine.rth)
    feats = feats[feats["rng"] >= C_RNG]
    sigs  = signals_from_features(feats, gap_thresh=C_GAP, dollar_stop=C_STOP)
    c_log, _ = engine.run(sigs)
    c_daily   = daily_returns(c_log)
    return c_log, c_daily


# ─── D1: Failed ORB fade ───────────────────────────────────────────────────────
#
# Economic rationale: The ORB continuation trade (Strategy C) relies on the
# opening range holding as support/resistance. When the trade is entered but
# price reverses back into the range within 30 min (confirming the breakout
# was false), the day transitions from a trending to a mean-reverting regime.
# Fading in the opposite direction with VWAP as target captures this regime
# shift. Expected WR ≥ 50% (mean reversion), corr(D1,C) < 0 by construction.

def ic_d1(engine: NQBacktestEngine, feats_c: pd.DataFrame) -> dict:
    """IC: reversal magnitude at 30-min mark vs subsequent 90-min return."""
    records = []
    c_feats  = feats_c[
        feats_c["vwap_ok"] &
        (feats_c["gap_pct"].abs() <= C_GAP) &
        (feats_c["rng"] >= C_RNG)
    ].copy()

    for _, row in c_feats.iterrows():
        date      = row["date"]
        c_dir     = int(row["direction"])
        c_sig_ts  = row["sig_ts"]
        tz        = c_sig_ts.tzinfo

        # C entry = first bar after 09:45
        future = engine.rth[engine.rth.index > c_sig_ts]
        if future.empty:
            continue
        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        # C sl_pts
        rng    = float(row["rng"])
        sl_pts = min(rng * BASE_SL_MULT, (C_STOP + COST_RT) / POINT_VALUE)

        # 30-min reversal check window: entry_bar → entry_bar + 30 min
        end_check = entry_bar + pd.Timedelta(minutes=30)
        window = engine.rth[
            (engine.rth.index >= entry_bar) &
            (engine.rth.index <= end_check)
        ]
        if window.empty:
            continue

        # Reversal = worst excursion against C direction
        if c_dir == 1:
            worst = float(window["low"].min())
            reversal_mag = max(0.0, entry_price - worst - 0.5 * sl_pts)
        else:
            worst = float(window["high"].max())
            reversal_mag = max(0.0, worst - entry_price - 0.5 * sl_pts)

        if reversal_mag <= 0:
            continue  # no reversal, no D1 signal

        # Future return: 90 min after 30-min mark in D1 direction (-c_dir)
        signal_ts  = end_check
        fut_end_ts = signal_ts + pd.Timedelta(minutes=90)
        fut_window = engine.rth[
            (engine.rth.index > signal_ts) &
            (engine.rth.index <= fut_end_ts)
        ]
        if len(fut_window) < 3:
            continue

        fut_entry = float(fut_window.iloc[0]["open"])
        fut_exit  = float(fut_window.iloc[-1]["close"])
        d1_dir    = -c_dir
        fut_ret   = d1_dir * (fut_exit - fut_entry)  # positive = D1 was right

        records.append({"signal": reversal_mag, "fret": fut_ret})

    if not records:
        return {"n": 0, "ic": np.nan, "t": np.nan}
    df_ic = pd.DataFrame(records)
    rho, t = ic_t_stat(df_ic["signal"].values, df_ic["fret"].values)
    return {"n": len(df_ic), "ic": rho, "t": t}


def build_d1_signals(engine: NQBacktestEngine,
                     feats_c: pd.DataFrame) -> pd.DataFrame:
    """D1 signals: C fired, price reversed 0.5R within 30 min → fade opposite."""
    c_feats = feats_c[
        feats_c["vwap_ok"] &
        (feats_c["gap_pct"].abs() <= C_GAP) &
        (feats_c["rng"] >= C_RNG)
    ].copy()

    rows = []
    for _, row in c_feats.iterrows():
        c_dir    = int(row["direction"])
        c_sig_ts = row["sig_ts"]
        rng      = float(row["rng"])
        sl_pts   = min(rng * BASE_SL_MULT, (C_STOP + COST_RT) / POINT_VALUE)
        rev_thr  = 0.5 * sl_pts

        future = engine.rth[engine.rth.index > c_sig_ts]
        if future.empty:
            continue
        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        end_check = entry_bar + pd.Timedelta(minutes=30)
        window = engine.rth[
            (engine.rth.index >= entry_bar) &
            (engine.rth.index <= end_check)
        ]
        if window.empty:
            continue

        reversed_signal = False
        if c_dir == 1:
            if float(window["low"].min()) <= entry_price - rev_thr:
                reversed_signal = True
        else:
            if float(window["high"].max()) >= entry_price + rev_thr:
                reversed_signal = True

        if not reversed_signal:
            continue

        # D1 signal at end of 30-min check window
        signal_ts = window.index[-1]
        d1_dir    = -c_dir

        # TP: distance to VWAP at signal bar (min 10 pts)
        vwap_sig = float(engine.rth.loc[signal_ts, "vwap_rth"]) if signal_ts in engine.rth.index else np.nan
        if np.isnan(vwap_sig) or vwap_sig <= 0:
            tp_pts = 20.0
        else:
            entry_est = float(engine.rth.loc[signal_ts, "close"])
            tp_pts = max(abs(entry_est - vwap_sig), 10.0)
        tp_pts = min(tp_pts, 40.0)  # cap TP at 40 pts

        # SL: 20 pts fixed (practical, avoids outsized risk from large 2R)
        sl_fixed = 20.0

        # Time stop: 12:30
        d = signal_ts.date()
        exit_ts = pd.Timestamp(d.year, d.month, d.day, 12, 30, 0, tzinfo=signal_ts.tzinfo)

        rows.append({
            "signal_ts": signal_ts,
            "direction": d1_dir,
            "tp_points": tp_pts,
            "sl_points": sl_fixed,
            "exit_time": exit_ts,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── D2: VWAP touch fade post-noon ────────────────────────────────────────────
#
# Economic rationale: Post-noon (11:30-14:00) NQ is typically in a
# consolidation / mean-reverting regime after the opening impulse exhausts.
# When 3+ consecutive 5-min bars trend in one direction and price reaches
# intraday VWAP, momentum exhaustion is likely. Fading against the recent
# push toward VWAP captures the reversion. VWAP acts as a daily magnet
# that price frequently crosses and recrosses in low-information periods.

def _build_5min_rth(df: pd.DataFrame) -> pd.DataFrame:
    rth = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)].copy()
    bars5 = rth.resample("5min", label="right", closed="right").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
        vwap=("vwap_rth", "last"),
    ).dropna(subset=["open"])
    bars5 = bars5[bars5.index.time >= T_0930]
    return bars5


def ic_d2(df: pd.DataFrame) -> dict:
    """IC: (close - VWAP) signed vs next-30min return in fade direction."""
    bars5 = _build_5min_rth(df)
    records = []

    dates = bars5.index.normalize().unique()
    for date in dates:
        day = bars5[bars5.index.normalize() == date]
        window = day[(day.index.time >= T_1130) & (day.index.time <= T_1400)]
        if len(window) < 5:
            continue

        closes = window["close"]
        vwaps  = window["vwap"]
        bar_ret = closes.diff().fillna(0)

        for i in range(2, len(window)):
            # Check 3 consecutive bars same direction
            r3 = bar_ret.iloc[i - 2 : i + 1]
            if not (all(r3 > 0) or all(r3 < 0)):
                continue
            momentum_dir = 1 if all(r3 > 0) else -1

            vwap_i = float(vwaps.iloc[i])
            close_i = float(closes.iloc[i])
            if vwap_i <= 0:
                continue

            # Signal: price must be touching VWAP (within 5 pts)
            if abs(close_i - vwap_i) > 5.0:
                continue

            # Fade direction: opposite to momentum
            d2_dir = -momentum_dir
            signal_val = abs(close_i - vwap_i) + 1.0  # continuous magnitude

            # Future: next 30 min (6 × 5-min bars)
            future_bars = day.iloc[i + 1 : i + 7]
            if len(future_bars) < 3:
                continue
            fut_entry = float(future_bars.iloc[0]["open"])
            fut_exit  = float(future_bars.iloc[-1]["close"])
            fut_ret   = d2_dir * (fut_exit - fut_entry)

            records.append({"signal": signal_val, "fret": fut_ret})

    if not records:
        return {"n": 0, "ic": np.nan, "t": np.nan}
    df_ic = pd.DataFrame(records)
    rho, t = ic_t_stat(df_ic["signal"].values, df_ic["fret"].values)
    return {"n": len(df_ic), "ic": rho, "t": t}


def build_d2_signals(df: pd.DataFrame) -> pd.DataFrame:
    """D2 signals: 3-bar momentum exhaustion touching VWAP → fade."""
    bars5 = _build_5min_rth(df)
    rows = []

    dates = bars5.index.normalize().unique()
    for date in dates:
        day = bars5[bars5.index.normalize() == date]
        window = day[(day.index.time >= T_1130) & (day.index.time <= T_1400)]
        if len(window) < 5:
            continue

        closes = window["close"]
        vwaps  = window["vwap"]
        bar_ret = closes.diff().fillna(0)
        signals_this_day = 0  # max 1 signal per day

        for i in range(2, len(window)):
            if signals_this_day >= 1:
                break
            r3 = bar_ret.iloc[i - 2 : i + 1]
            if not (all(r3 > 0) or all(r3 < 0)):
                continue
            momentum_dir = 1 if all(r3 > 0) else -1

            vwap_i  = float(vwaps.iloc[i])
            close_i = float(closes.iloc[i])
            if vwap_i <= 0 or abs(close_i - vwap_i) > 5.0:
                continue

            signal_ts = window.index[i]
            d2_dir    = -momentum_dir

            # TP: 15 pts (fixed), SL: 15 pts, time stop: 14:30
            d = signal_ts.date()
            tz = signal_ts.tzinfo
            exit_ts = pd.Timestamp(d.year, d.month, d.day, 14, 30, 0, tzinfo=tz)

            rows.append({
                "signal_ts": signal_ts,
                "direction": d2_dir,
                "tp_points": 15.0,
                "sl_points": 15.0,
                "exit_time": exit_ts,
            })
            signals_this_day += 1

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── D3: Opening range mid-fade ───────────────────────────────────────────────
#
# Economic rationale: When the opening range is wide (>60 pts, indicating
# elevated uncertainty) but Strategy C's filters reject the trade (VWAP
# misalignment, excessive gap, or range too large relative to stop), the
# breakout likely lacks conviction. Price tends to revert to the range
# midpoint as the market resolves the opening ambiguity. This is the
# complementary setup to C: same data, opposite outcome.

def ic_d3(engine: NQBacktestEngine, feats_c: pd.DataFrame) -> dict:
    """IC: signed distance from ORB extreme vs midpoint, future 75-min return."""
    # Days where C did NOT fire (filters rejected)
    c_fired_dates = set(
        feats_c[
            feats_c["vwap_ok"] &
            (feats_c["gap_pct"].abs() <= C_GAP) &
            (feats_c["rng"] >= C_RNG)
        ]["date"].values
    )

    records = []
    for _, row in feats_c.iterrows():
        date = row["date"]
        rng  = float(row["rng"])
        if date in c_fired_dates or rng <= 60.0:
            continue

        # ORB range midpoint
        sig_ts    = row["sig_ts"]
        close_945 = float(row["close_price"])
        open_930  = float(row["open_price"])
        orb_high  = max(close_945, open_930)
        orb_low   = min(close_945, open_930)
        midpoint  = (orb_high + orb_low) / 2.0

        d3_dir    = -1 if close_945 > midpoint else 1
        signal_val = abs(close_945 - midpoint) / (rng / 2.0)  # normalized [0,1]

        # Future: 75 min from 09:46
        future = engine.rth[engine.rth.index > sig_ts]
        if future.empty:
            continue
        entry_bar = future.index[0]
        fut_end_ts = entry_bar + pd.Timedelta(minutes=75)
        fut_window = engine.rth[
            (engine.rth.index >= entry_bar) &
            (engine.rth.index <= fut_end_ts)
        ]
        if len(fut_window) < 5:
            continue

        fut_entry = float(fut_window.iloc[0]["open"])
        fut_exit  = float(fut_window.iloc[-1]["close"])
        fut_ret   = d3_dir * (fut_exit - fut_entry)

        records.append({"signal": signal_val, "fret": fut_ret})

    if not records:
        return {"n": 0, "ic": np.nan, "t": np.nan}
    df_ic = pd.DataFrame(records)
    rho, t = ic_t_stat(df_ic["signal"].values, df_ic["fret"].values)
    return {"n": len(df_ic), "ic": rho, "t": t}


def build_d3_signals(engine: NQBacktestEngine,
                     feats_c: pd.DataFrame) -> pd.DataFrame:
    """D3 signals: wide ORB, C not fired → fade to midpoint."""
    c_fired_dates = set(
        feats_c[
            feats_c["vwap_ok"] &
            (feats_c["gap_pct"].abs() <= C_GAP) &
            (feats_c["rng"] >= C_RNG)
        ]["date"].values
    )

    rows = []
    for _, row in feats_c.iterrows():
        date = row["date"]
        rng  = float(row["rng"])
        if date in c_fired_dates or rng <= 60.0:
            continue

        sig_ts    = row["sig_ts"]
        close_945 = float(row["close_price"])
        open_930  = float(row["open_price"])
        orb_high  = max(close_945, open_930)
        orb_low   = min(close_945, open_930)
        midpoint  = (orb_high + orb_low) / 2.0

        d3_dir    = -1 if close_945 > midpoint else 1

        # TP = distance to midpoint from current 09:45 close
        # Entry ≈ 09:46 open ≈ close_945; tp_pts = |close_945 - midpoint|
        tp_pts = max(abs(close_945 - midpoint), 10.0)
        tp_pts = min(tp_pts, 50.0)
        sl_pts = min(20.0, tp_pts * 0.4)  # max 20 pts, ratio ≥ 2.5:1

        d = sig_ts.date()
        tz = sig_ts.tzinfo
        exit_ts = pd.Timestamp(d.year, d.month, d.day, 11, 0, 0, tzinfo=tz)

        rows.append({
            "signal_ts": sig_ts,
            "direction": d3_dir,
            "tp_points": round(tp_pts, 2),
            "sl_points": round(sl_pts, 2),
            "exit_time": exit_ts,
        })

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── D4: Lunch RSI reversal ───────────────────────────────────────────────────
#
# Economic rationale: NQ lunch (12:00-13:30) is characterised by low
# participation, narrow spreads, and mean-reverting price action as market
# makers dominate. RSI extremes on a 30-min timeframe in this window signal
# short-term overextension driven by momentum algos "chasing" into thin
# liquidity. The subsequent 90-min window should revert as European closes
# provide fresh capital and US afternoon institutions re-engage.

def _build_30min_rth(df: pd.DataFrame) -> pd.DataFrame:
    rth = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)].copy()
    bars30 = rth.resample("30min", label="right", closed="right").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna(subset=["open"])
    bars30 = bars30[bars30.index.time >= T_0930]
    return bars30


def ic_d4(df: pd.DataFrame) -> dict:
    """IC: RSI deviation from 50 (inverted) vs next-90min return."""
    bars30 = _build_30min_rth(df)
    rsi    = compute_rsi(bars30["close"], period=14)

    records = []
    dates = bars30.index.normalize().unique()
    for date in dates:
        day     = bars30[bars30.index.normalize() == date]
        day_rsi = rsi[rsi.index.normalize() == date]
        window  = day[(day.index.time >= T_1200) & (day.index.time <= T_1300)]

        for i, (ts, bar) in enumerate(window.iterrows()):
            r = float(day_rsi.get(ts, np.nan))
            if np.isnan(r):
                continue
            if not (r > 65 or r < 35):
                continue

            d4_dir    = 1 if r < 35 else -1
            signal_val = (50 - r) / 50  # positive = oversold, negative = overbought

            # Future: next 90 min
            fut_bars = bars30[(bars30.index.normalize() == date) & (bars30.index > ts)]
            if len(fut_bars) < 2:
                continue
            fut_entry = float(fut_bars.iloc[0]["open"])
            fut_exit  = float(fut_bars.iloc[min(2, len(fut_bars) - 1)]["close"])
            fut_ret   = d4_dir * (fut_exit - fut_entry)

            records.append({"signal": signal_val, "fret": fut_ret})
            break  # 1 signal per day

    if not records:
        return {"n": 0, "ic": np.nan, "t": np.nan}
    df_ic = pd.DataFrame(records)
    rho, t = ic_t_stat(df_ic["signal"].values, df_ic["fret"].values)
    return {"n": len(df_ic), "ic": rho, "t": t}


def build_d4_signals(df: pd.DataFrame) -> pd.DataFrame:
    """D4 signals: 30-min RSI extreme at lunch → reversal trade."""
    bars30 = _build_30min_rth(df)
    rsi    = compute_rsi(bars30["close"], period=14)
    rows   = []

    dates = bars30.index.normalize().unique()
    for date in dates:
        day_rsi = rsi[rsi.index.normalize() == date]
        day     = bars30[bars30.index.normalize() == date]
        window  = day[(day.index.time >= T_1200) & (day.index.time <= T_1300)]

        for ts, bar in window.iterrows():
            r = float(day_rsi.get(ts, np.nan))
            if np.isnan(r) or not (r > 65 or r < 35):
                continue

            d4_dir = 1 if r < 35 else -1
            tz = ts.tzinfo
            d  = ts.date()
            exit_ts = pd.Timestamp(d.year, d.month, d.day, 13, 30, 0, tzinfo=tz)

            rows.append({
                "signal_ts": ts,
                "direction": d4_dir,
                "tp_points": 20.0,
                "sl_points": 15.0,
                "exit_time": exit_ts,
            })
            break  # 1 signal per day

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── D5: Afternoon vol compression breakout ───────────────────────────────────
#
# Economic rationale: In the 14:00-15:30 window, pre-close institutional
# positioning produces directional moves. After a period of volatility
# compression (tight Bollinger Bands), a directional breakout signals
# accumulation of one-sided orders. This is a momentum/breakout edge,
# distinct from mean reversion, but complementary: it fires in the late
# session when C and D1-D4 have all expired (C exits by 12:30).

def ic_d5(df: pd.DataFrame) -> dict:
    """IC: BB breakout direction × magnitude vs next-60min return."""
    bars5 = _build_5min_rth(df)
    bb_period = 20
    bb_std    = 2.0
    upper_bb, mid_bb, lower_bb = compute_bb(bars5["close"], bb_period, bb_std)
    bbw = (upper_bb - lower_bb) / mid_bb.replace(0, np.nan)
    bbw_avg = bbw.rolling(bb_period).mean()

    records = []
    dates = bars5.index.normalize().unique()
    for date in dates:
        day  = bars5[bars5.index.normalize() == date]
        wdow = day[(day.index.time >= T_1400) & (day.index.time <= T_1530)]
        if len(wdow) < 5:
            continue

        for i, (ts, bar) in enumerate(wdow.iterrows()):
            bbw_val  = float(bbw.get(ts, np.nan))
            bbwa_val = float(bbw_avg.get(ts, np.nan))
            upper    = float(upper_bb.get(ts, np.nan))
            lower    = float(lower_bb.get(ts, np.nan))
            close    = float(bar["close"])

            if any(np.isnan(v) for v in [bbw_val, bbwa_val, upper, lower]):
                continue
            if bbwa_val <= 0 or bbw_val >= 0.5 * bbwa_val:
                continue  # no squeeze

            if close > upper:
                d5_dir    = 1
                signal_val = (close - upper) / (bbw_val * mid_bb.get(ts, 1))
            elif close < lower:
                d5_dir    = -1
                signal_val = (lower - close) / (bbw_val * mid_bb.get(ts, 1))
            else:
                continue

            # Future: next 60 min (12 × 5-min bars)
            future_bars = wdow.iloc[i + 1 : i + 13]
            if len(future_bars) < 6:
                continue
            fut_entry = float(future_bars.iloc[0]["open"])
            fut_exit  = float(future_bars.iloc[-1]["close"])
            fut_ret   = d5_dir * (fut_exit - fut_entry)

            records.append({"signal": signal_val, "fret": fut_ret})
            break  # 1 per day

    if not records:
        return {"n": 0, "ic": np.nan, "t": np.nan}
    df_ic = pd.DataFrame(records)
    rho, t = ic_t_stat(df_ic["signal"].values, df_ic["fret"].values)
    return {"n": len(df_ic), "ic": rho, "t": t}


def build_d5_signals(df: pd.DataFrame) -> pd.DataFrame:
    """D5 signals: BB squeeze + breakout in 14:00-15:30 → momentum trade."""
    bars5    = _build_5min_rth(df)
    bb_period = 20
    bb_std    = 2.0
    upper_bb, mid_bb, lower_bb = compute_bb(bars5["close"], bb_period, bb_std)
    bbw     = (upper_bb - lower_bb) / mid_bb.replace(0, np.nan)
    bbw_avg = bbw.rolling(bb_period).mean()
    rows    = []

    dates = bars5.index.normalize().unique()
    for date in dates:
        day  = bars5[bars5.index.normalize() == date]
        wdow = day[(day.index.time >= T_1400) & (day.index.time <= T_1530)]
        if len(wdow) < 5:
            continue

        for ts, bar in wdow.iterrows():
            bbw_val  = float(bbw.get(ts, np.nan))
            bbwa_val = float(bbw_avg.get(ts, np.nan))
            upper    = float(upper_bb.get(ts, np.nan))
            lower    = float(lower_bb.get(ts, np.nan))
            close    = float(bar["close"])

            if any(np.isnan(v) for v in [bbw_val, bbwa_val, upper, lower]):
                continue
            if bbwa_val <= 0 or bbw_val >= 0.5 * bbwa_val:
                continue

            if close > upper:
                d5_dir = 1
                tp_pts = max((upper - lower), 10.0)   # BB width
                sl_pts = max(tp_pts * 0.5, 8.0)
            elif close < lower:
                d5_dir = -1
                tp_pts = max((upper - lower), 10.0)
                sl_pts = max(tp_pts * 0.5, 8.0)
            else:
                continue

            tz = ts.tzinfo
            d  = ts.date()
            exit_ts = pd.Timestamp(d.year, d.month, d.day, 15, 45, 0, tzinfo=tz)

            rows.append({
                "signal_ts": ts,
                "direction": d5_dir,
                "tp_points": round(min(tp_pts, 60.0), 2),
                "sl_points": round(min(sl_pts, 30.0), 2),
                "exit_time": exit_ts,
            })
            break  # 1 per day

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).set_index("signal_ts")


# ─── Walk-forward wrapper for D variants ──────────────────────────────────────

def wf_for_d(engine: NQBacktestEngine, signal_fn) -> dict:
    """Extended WF (6M train / 3M test) for D variants using extended_wf framework."""
    def wrapped_signal_fn(df_1min, params):
        return signal_fn(df_1min)

    # For D variants that use df (not engine), build a minimal wrapper
    return extended_wf(engine, wrapped_signal_fn, max_windows=12)


# ─── Full variant runner ──────────────────────────────────────────────────────

def run_variant(
    engine:    NQBacktestEngine,
    signals:   pd.DataFrame,
    name:      str,
    n_test:    int,
    c_daily:   pd.Series,
    signal_fn,
) -> dict:
    """Run full backtest, WF, metrics, correlation for one D variant."""
    if signals.empty:
        return {"name": name, "n_test": n_test, "n_trades": 0, "sharpe": np.nan,
                "error": "no signals generated"}

    tl, met = engine.run(signals)
    if tl.empty:
        return {"name": name, "n_test": n_test, "n_trades": 0, "sharpe": np.nan,
                "error": "no trades executed"}

    n = len(tl)
    # HAC Sharpe on daily P&L
    d_daily = daily_returns(tl)
    sh  = sharpe_hac(d_daily)
    mdd = max_dd_pct(d_daily)
    pf  = profit_factor(tl)
    wr  = float((tl["pnl_usd"] > 0).sum()) / n
    total_pnl = float(tl["pnl_usd"].sum())

    # Trades per day
    n_trading_days = engine.rth.index.normalize().nunique()
    tpd = n / n_trading_days

    # Correlation with C
    corr_c = corr_with_c(tl, c_daily)

    # Walk-forward
    try:
        wf_res = wf_for_d(engine, signal_fn)
        wf_pct = wf_res.get("wf_pct_positive", np.nan)
    except Exception as e:
        log.warning("WF failed for %s: %s", name, e)
        wf_pct = np.nan

    # Tradeify eval (only if decent)
    p_eval_90d = np.nan
    mean_daily_mnq = np.nan
    if pf >= 1.0 and n >= 30:
        try:
            ev = tradeify_eval_90d(tl, MNQ_EVAL)
            p_eval_90d     = ev.get("p_pass", np.nan)
            mean_daily_mnq = ev.get("mean_daily", np.nan)
        except Exception as e:
            log.warning("Tradeify eval failed for %s: %s", name, e)

    return {
        "name":          name,
        "n_test":        n_test,
        "n_trades":      n,
        "trades_per_day":round(tpd, 3),
        "sharpe":        round(sh, 4) if np.isfinite(sh) else np.nan,
        "max_dd_pct":    round(mdd * 100, 1) if np.isfinite(mdd) else np.nan,
        "profit_factor": round(pf, 3) if np.isfinite(pf) else np.nan,
        "win_rate":      round(wr, 4),
        "total_pnl":     round(total_pnl, 2),
        "wf_pct":        round(wf_pct, 1) if np.isfinite(wf_pct) else np.nan,
        "corr_c":        round(corr_c, 4) if np.isfinite(corr_c) else np.nan,
        "p_eval_90d":    round(p_eval_90d, 1) if np.isfinite(p_eval_90d) else np.nan,
        "mean_daily_mnq": round(mean_daily_mnq, 2) if np.isfinite(mean_daily_mnq) else np.nan,
        "trade_log":     tl,
        "daily_pnl":     d_daily,
    }


def check_gates(r: dict) -> dict[str, bool]:
    return {
        "sharpe":        (r.get("sharpe") or 0) >= GATE_SHARPE,
        "wf":            (r.get("wf_pct") or 0) >= GATE_WF,
        "pf":            (r.get("profit_factor") or 0) >= GATE_PF,
        "mdd":           (r.get("max_dd_pct") or -99) >= GATE_MDD * 100,
        "wr":            (r.get("win_rate") or 0) >= GATE_WR,
        "tpd":           (r.get("trades_per_day") or 0) >= GATE_TPD,
        "corr_c":        abs(r.get("corr_c") or 1.0) <= GATE_CORR,
    }


# ─── Portfolio simulation ──────────────────────────────────────────────────────

def portfolio_c_d(c_tl: pd.DataFrame, d_tl: pd.DataFrame) -> dict:
    """ERC portfolio C+D (NQ terms, equal daily vol weight)."""
    c_daily = daily_returns(c_tl)
    d_daily = daily_returns(d_tl)
    common  = c_daily.index.intersection(d_daily.index)
    c_d     = c_daily[common]
    d_d     = d_daily[common]

    # ERC: inverse vol weighting
    c_vol = float(c_d.std(ddof=1))
    d_vol = float(d_d.std(ddof=1))
    if c_vol <= 0 or d_vol <= 0:
        return {}

    w_c = (1 / c_vol) / (1 / c_vol + 1 / d_vol)
    w_d = 1 - w_c
    # Scale to unit vol (normalise so combined vol ≈ min(c_vol, d_vol))
    port = w_c * c_d + w_d * d_d

    sh  = sharpe_hac(port)
    mdd = max_dd_pct(port)
    corr = float(np.corrcoef(c_d, d_d)[0, 1])

    # Tradeify eval: combine daily MNQ P&L (2 MNQ each for 4 total, ≈ ERC)
    # Use 2 MNQ for C and 2 MNQ for D (total 4, approx ERC)
    c_mnq = build_daily_pnl_mnq(c_tl, 2)
    d_mnq_series = daily_returns(d_tl)
    # Scale D to MNQ: recover NQ pts → MNQ
    d_mnq = d_mnq_series.apply(
        lambda x: ((x + NQ_COST_RT) / NQ_PV) * MNQ_PV * 2 - MNQ_COST_RT * 2
    )
    port_mnq_common = c_mnq.index.intersection(d_mnq.index)
    port_mnq = c_mnq[port_mnq_common] + d_mnq[port_mnq_common]

    rng_p   = np.random.default_rng(MC_SEED + 33)
    paths_p = _stationary_block_paths(
        port_mnq.values.astype(float), MC_PATHS, EVAL_DAYS_90, AVG_BLOCK_LEN, rng_p
    )
    ev_p = _simulate_tradeify_eval(paths_p, TV_TRAILING_DD, TV_EVAL_TARGET, EVAL_DAYS_90)

    return {
        "w_c": round(w_c, 3), "w_d": round(w_d, 3),
        "corr_c_d": round(corr, 4),
        "sharpe":  round(sh, 4) if np.isfinite(sh) else np.nan,
        "max_dd_pct": round(mdd * 100, 1) if np.isfinite(mdd) else np.nan,
        "p_eval_90d": round(ev_p.get("p_pass", np.nan), 1),
        "mean_daily_mnq": round(ev_p.get("mean_daily", np.nan), 2),
    }


# ─── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 72)
    print("Strategy D v2 — Intraday Mean Reversion on NQ")
    print(f"n_tests baseline: {N_TESTS_START}")
    print("=" * 72)

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)
    print(f"Data: {df.index[0].date()} → {df.index[-1].date()}  "
          f"({engine.rth.index.normalize().nunique()} RTH days)\n")

    # Build Strategy C iter_10 baseline
    print("Building Strategy C iter_10 baseline...")
    c_tl, c_daily = build_c_iter10(engine)
    print(f"  C: {len(c_tl)} trades, Sharpe={sharpe_hac(c_daily):.4f}\n")

    feats_c = build_opening_features(engine.rth)

    # ── IC PRE-FLIGHT ───────────────────────────────────────────────────────
    print("─" * 72)
    print("IC PRE-FLIGHT (Spearman rho, t-stat with N obs)")
    print(f"  {'Variant':<8} {'N':>5} {'IC rho':>8} {'t-stat':>8}  {'Signal?'}")
    print("  " + "─" * 50)

    ic_results = {}
    for vname, ic_fn in [
        ("D1", lambda: ic_d1(engine, feats_c)),
        ("D2", lambda: ic_d2(df)),
        ("D3", lambda: ic_d3(engine, feats_c)),
        ("D4", lambda: ic_d4(df)),
        ("D5", lambda: ic_d5(df)),
    ]:
        ic = ic_fn()
        ok = (np.isfinite(ic["t"]) and ic["t"] > 0.8 and ic["n"] >= 20)
        flag = "PROCEED" if ok else "WEAK"
        print(f"  {vname:<8} {ic['n']:>5} {ic['ic']:>8.4f} {ic['t']:>8.3f}  {flag}")
        ic_results[vname] = {"ok": ok, **ic}

    print()

    # ── FULL BACKTESTS ──────────────────────────────────────────────────────
    variant_results  = []
    n_tests_current  = N_TESTS_START
    variants_tested  = 0

    print("─" * 72)
    print("BACKTEST RESULTS")

    def _d1_signal_fn(df_1min: pd.DataFrame) -> pd.DataFrame:
        e2 = NQBacktestEngine(df_1min)
        fc = build_opening_features(e2.rth)
        return build_d1_signals(e2, fc)

    def _d2_signal_fn(df_1min: pd.DataFrame) -> pd.DataFrame:
        return build_d2_signals(df_1min)

    def _d3_signal_fn(df_1min: pd.DataFrame) -> pd.DataFrame:
        e2 = NQBacktestEngine(df_1min)
        fc = build_opening_features(e2.rth)
        return build_d3_signals(e2, fc)

    def _d4_signal_fn(df_1min: pd.DataFrame) -> pd.DataFrame:
        return build_d4_signals(df_1min)

    def _d5_signal_fn(df_1min: pd.DataFrame) -> pd.DataFrame:
        return build_d5_signals(df_1min)

    variant_configs = [
        ("D1", build_d1_signals, {"engine": engine, "feats_c": feats_c}, _d1_signal_fn),
        ("D2", build_d2_signals, {"df": df},                              _d2_signal_fn),
        ("D3", build_d3_signals, {"engine": engine, "feats_c": feats_c}, _d3_signal_fn),
        ("D4", build_d4_signals, {"df": df},                              _d4_signal_fn),
        ("D5", build_d5_signals, {"df": df},                              _d5_signal_fn),
    ]

    for vname, sig_builder, kwargs, wf_sig_fn in variant_configs:
        n_tests_current  += 1
        variants_tested  += 1
        print(f"\n  ── {vname}  (n_test={n_tests_current}) ────────────────────────────")

        # Build signals
        if "engine" in kwargs and "feats_c" in kwargs:
            sigs = sig_builder(kwargs["engine"], kwargs["feats_c"])
        else:
            sigs = sig_builder(kwargs["df"])

        print(f"     Signals generated: {len(sigs)}")

        r = run_variant(engine, sigs, vname, n_tests_current, c_daily, wf_sig_fn)
        variant_results.append(r)

        gates = check_gates(r)
        gate_str = "  ".join(
            f"{k}={'✓' if v else '✗'}" for k, v in gates.items()
        )
        print(f"     N={r.get('n_trades',0)} | Sharpe={r.get('sharpe','n/a')} | "
              f"MaxDD={r.get('max_dd_pct','n/a')}% | PF={r.get('profit_factor','n/a')} | "
              f"WR={r.get('win_rate','n/a'):.1%}")
        print(f"     TPD={r.get('trades_per_day','n/a')} | "
              f"WF%={r.get('wf_pct','n/a')} | "
              f"corr(C,D)={r.get('corr_c','n/a')}")
        print(f"     P(eval 90d @{MNQ_EVAL}MNQ)={r.get('p_eval_90d','n/a')}% | "
              f"E[daily@{MNQ_EVAL}MNQ]=${r.get('mean_daily_mnq','n/a')}")
        print(f"     Gates: {gate_str}")

        append_result({
            "iteration":   vname,
            "sharpe":      r.get("sharpe"),
            "max_dd":      (r.get("max_dd_pct") or 0) / 100,
            "pf":          r.get("profit_factor"),
            "n_trades":    r.get("n_trades"),
            "win_rate":    r.get("win_rate"),
            "total_pnl":   r.get("total_pnl"),
            "wf_pct":      r.get("wf_pct"),
            "trades_per_day": r.get("trades_per_day"),
            "corr_c":      r.get("corr_c"),
            "p_eval_90d":  r.get("p_eval_90d"),
            "n_test":      n_tests_current,
            "ic_rho":      ic_results[vname]["ic"],
            "ic_t":        ic_results[vname]["t"],
            "notes":       f"Strategy D v2: {vname}",
        })

    # ── AMTP-BH ─────────────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("AMTP — Benjamini-Hochberg FDR (all D variants)")

    # p-value from Sharpe t-stat: n_days available (= trading days covered)
    n_days_total = engine.rth.index.normalize().nunique()

    def sharpe_to_p(sh, n):
        if not np.isfinite(sh) or n < 5:
            return 1.0
        t = sh / np.sqrt(252) * np.sqrt(n)
        return float(1 - stats.norm.cdf(t))

    p_values  = [sharpe_to_p(r.get("sharpe", np.nan), n_days_total)
                 for r in variant_results]
    p_adj     = bh_adjust(p_values)

    print(f"  {'Variant':<6} {'Sharpe':>8} {'p_raw':>8} {'p_BH':>8} {'AMTP_pass':>10}")
    for r, p_raw, p_bh in zip(variant_results, p_values, p_adj):
        amtp_ok = p_bh < 0.05
        print(f"  {r['name']:<6} {r.get('sharpe', np.nan):>8.4f} "
              f"{p_raw:>8.4f} {p_bh:>8.4f} {'YES' if amtp_ok else 'NO':>10}")

    # ── KILL SWITCH CHECK ────────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print(f"KILL SWITCH CHECK (5 variants tested: need ≥1 with TPD≥{KILL_SWITCH_TPD} AND PF≥{KILL_SWITCH_PF})")
    survivors = [
        r for r in variant_results
        if (r.get("trades_per_day") or 0) >= KILL_SWITCH_TPD and
           (r.get("profit_factor") or 0) >= KILL_SWITCH_PF
    ]
    if not survivors:
        print("  ► KILL SWITCH TRIGGERED — no variant beats frequency AND PF threshold")
    else:
        print(f"  ► {len(survivors)} variant(s) passed kill switch: "
              f"{[r['name'] for r in survivors]}")

    # ── BEST VARIANT & PORTFOLIO ─────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("SUMMARY TABLE")
    print(f"  {'Var':<4} {'N':>5} {'TPD':>5} {'Sh':>7} {'DD%':>7} {'PF':>6} "
          f"{'WR%':>6} {'WF%':>6} {'corrC':>7} {'P90d%':>7}")
    for r in variant_results:
        print(f"  {r['name']:<4} {r.get('n_trades',0):>5} "
              f"{r.get('trades_per_day',0):>5.2f} "
              f"{r.get('sharpe', float('nan')):>7.3f} "
              f"{r.get('max_dd_pct', float('nan')):>7.1f} "
              f"{r.get('profit_factor', float('nan')):>6.3f} "
              f"{(r.get('win_rate',0)*100):>6.1f} "
              f"{r.get('wf_pct', float('nan')):>6.1f} "
              f"{r.get('corr_c', float('nan')):>7.4f} "
              f"{r.get('p_eval_90d', float('nan')):>7.1f}")

    # Best by Sharpe among variants that at least partially pass
    valid = [r for r in variant_results if np.isfinite(r.get("sharpe") or np.nan)]
    best  = max(valid, key=lambda r: r.get("sharpe", -99)) if valid else None

    port_result = {}
    if best and not best.get("trade_log", pd.DataFrame()).empty:
        gates_best = check_gates(best)
        solo_pass  = all(gates_best.values())
        if solo_pass:
            print(f"\n  {best['name']} passes all solo gates — running portfolio simulation...")
            port_result = portfolio_c_d(c_tl, best["trade_log"])
            print(f"  C+D portfolio: Sharpe={port_result.get('sharpe','n/a')} | "
                  f"MaxDD={port_result.get('max_dd_pct','n/a')}% | "
                  f"P(eval 90d)={port_result.get('p_eval_90d','n/a')}% | "
                  f"corr(C,D)={port_result.get('corr_c_d','n/a')}")
        else:
            print(f"\n  Best variant: {best['name']} — does not pass all solo gates")
            failed_gates = [k for k, v in gates_best.items() if not v]
            print(f"  Failed gates: {failed_gates}")

    # ── END PRINT ────────────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("END PRINT")
    print("=" * 72)

    if not survivors and not best:
        verdict = "KILL_SWITCH"
        b_name  = "N/A"
        b_sh    = b_corr = b_tpd = "N/A"
        p_sh    = p_mdd = p_p90 = "N/A"
        rec     = "KILL_SWITCH"
    elif not survivors:
        # Best exists but didn't pass kill switch
        b_name  = best["name"]
        b_sh    = best.get("sharpe", "N/A")
        b_corr  = best.get("corr_c", "N/A")
        b_tpd   = best.get("trades_per_day", "N/A")
        verdict = "KILL_SWITCH"
        p_sh = p_mdd = p_p90 = "N/A"
        rec  = "KILL_SWITCH"
    elif port_result:
        b_name = best["name"]
        b_sh   = best.get("sharpe", "N/A")
        b_corr = best.get("corr_c", "N/A")
        b_tpd  = best.get("trades_per_day", "N/A")
        gates_best = check_gates(best)
        solo_pass  = all(gates_best.values())
        verdict = "PROPFIRM_PASS" if solo_pass else "RESEARCH_PASS"
        p_sh  = port_result.get("sharpe", "N/A")
        p_mdd = port_result.get("max_dd_pct", "N/A")
        p_p90 = port_result.get("p_eval_90d", "N/A")
        p90_ok = (p_p90 != "N/A") and (p_p90 >= 50.0)
        port_mdd_ok = (p_mdd != "N/A") and (p_mdd >= -10.0)
        port_sh_ok  = (p_sh  != "N/A") and (p_sh  >= 1.7)
        rec = "DEPLOY" if (p90_ok and port_mdd_ok and port_sh_ok) else "RESEARCH_MORE"
    else:
        b_name = best["name"] if best else "N/A"
        b_sh   = best.get("sharpe", "N/A") if best else "N/A"
        b_corr = best.get("corr_c", "N/A") if best else "N/A"
        b_tpd  = best.get("trades_per_day", "N/A") if best else "N/A"
        verdict = "RESEARCH_MORE"
        p_sh = p_mdd = p_p90 = "N/A"
        rec  = "RESEARCH_MORE"

    n_tests_final = n_tests_current
    print(f"\nD_BEST: {b_name} | Sharpe={b_sh} | corr(C,D)={b_corr} | trades/day={b_tpd}")
    print(f"C+D PORTFOLIO: Sharpe={p_sh} | MaxDD={p_mdd}% | P(eval 90d)={p_p90}%")
    print(f"Verdict: {verdict}")
    print(f"Recommendation: {rec}")
    print(f"\nn_tests: {N_TESTS_START} → {n_tests_final}")
    print("=" * 72)


if __name__ == "__main__":
    main()
