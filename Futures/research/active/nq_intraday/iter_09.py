"""
iter_09.py — Differential Diagnostic + Signal Strength Variable Sizing
========================================================================
Part A: Forensic analysis of the 3 negative WF windows (Dec 2023, Mar 2024, Sep 2024)
        vs 6 positive windows. Compute 5 market-regime metrics per window, t-test
        positive vs negative, identify statistical discriminator if any.

Part B: Signal strength composite scoring + variable contract sizing by quartile.
        3 variants: 9a (1.0/0.75/0.5/0.25), 9b (skip Q1), 9c (top-half only).

Build on: iter_08 8b (vol_ratio < 0.7 + A$400 + B1.2%) — current best variant.

Gates for PROPFIRM_READY:
  Sharpe > 1.30, MaxDD <= -20%, WF% >= 75%, PF > 1.30, P(EV<=0) < 0.02

n_tests: 123 + 3 = 126
"""

from __future__ import annotations

import datetime
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parents[4]))
from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE, COST_RT,
    append_result, load_results,
)
from Futures.research.active.nq_intraday.iter_05 import build_opening_features
from Futures.research.active.nq_intraday.iter_08 import (
    compute_vol_ratio, fetch_vix, enrich_features,
    build_iter08_signals, _strip_tz,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

N_TESTS_BASE = 123

# iter_08 8b production params
PROD_GAP         = 0.012
PROD_DSTOP       = 400.0
PROD_VOL_THRESH  = 0.7

# iter_08 8b reference metrics
REF = {"iteration": "iter_08_8b", "sharpe": 1.251, "max_dd": -0.245,
       "pf": 1.314, "wf_pct": 67.0, "n_trades": 513, "p_ev_zero": 0.015}

# WF windows from iter_07/iter_08 (6M train / 3M test), OOS end dates
WF_WINDOWS = [
    {"oos_end": "2023-09-27", "positive": True},
    {"oos_end": "2023-12-27", "positive": False},
    {"oos_end": "2024-03-27", "positive": False},
    {"oos_end": "2024-06-27", "positive": True},
    {"oos_end": "2024-09-27", "positive": False},
    {"oos_end": "2024-12-27", "positive": True},
    {"oos_end": "2025-03-27", "positive": True},
    {"oos_end": "2025-06-27", "positive": True},
    {"oos_end": "2025-09-27", "positive": True},
]
WF_TEST_MO = 3

T_0930 = datetime.time(9, 30)
T_0945 = datetime.time(9, 45)
T_1030 = datetime.time(10, 30)
T_1245 = datetime.time(12, 45)
T_1559 = datetime.time(15, 59)


# ─────────────────────────────────────────────────────────────────────────────
# Part A helpers — regime metrics per session
# ─────────────────────────────────────────────────────────────────────────────

def compute_session_metrics(df: pd.DataFrame,
                            feats: pd.DataFrame) -> pd.DataFrame:
    """
    Compute per-session regime metrics for all RTH sessions.

    Metrics:
      trend_ratio        — |close_RTH - open_RTH| / (high_RTH - low_RTH)  [0-1]
      realized_vol       — stdev(5min RTH returns) × sqrt(78)
      open_day_corr_sign — sign(opening move) == sign(09:45→12:30 return)  [0/1]
      first15_vol_ratio  — first-15min volume / 20d trailing avg
      vwap_cross_count   — # of VWAP crosses in first 60min after 09:45

    Returns DataFrame indexed by date with one row per session.
    """
    rth = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)].copy()
    dates = sorted(rth.index.normalize().unique())

    # 5-min resampled for realized vol
    rth_5min = rth.resample("5min").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna(subset=["close"])

    # Trailing 20d first-15min volume
    daily_first15 = {}
    for d in dates:
        day = rth[rth.index.normalize() == d]
        t_end = pd.Timestamp(
            d.year, d.month, d.day, 9, 45, 0, tzinfo=day.index.tzinfo
        ) if not day.empty else None
        t_start = pd.Timestamp(
            d.year, d.month, d.day, 9, 30, 0, tzinfo=day.index.tzinfo
        ) if not day.empty else None
        if t_start and t_end:
            seg = day[(day.index >= t_start) & (day.index <= t_end)]
            daily_first15[d] = float(seg["volume"].sum()) if not seg.empty else np.nan

    first15_series = pd.Series(daily_first15)
    first15_avg20  = first15_series.rolling(20, min_periods=5).mean().shift(1)

    records = []
    for d in dates:
        day = rth[rth.index.normalize() == d]
        if len(day) < 10:
            continue

        # --- Trend ratio ---
        open_rth  = float(day.iloc[0]["open"])
        close_rth = float(day.iloc[-1]["close"])
        high_rth  = float(day["high"].max())
        low_rth   = float(day["low"].min())
        day_range = high_rth - low_rth
        trend_ratio = abs(close_rth - open_rth) / day_range if day_range > 0 else np.nan

        # --- Realized vol (5-min returns) ---
        day_5min = rth_5min[rth_5min.index.normalize() == d]
        if len(day_5min) >= 4:
            rets_5min = day_5min["close"].pct_change().dropna()
            rv = float(rets_5min.std() * np.sqrt(78)) if len(rets_5min) >= 3 else np.nan
        else:
            rv = np.nan

        # --- Opening signal → intraday direction correlation ---
        opening = day[(day.index.time >= T_0930) & (day.index.time <= T_0945)]
        if len(opening) >= 2:
            open_p  = float(opening.iloc[0]["open"])
            close_p = float(opening.iloc[-1]["close"])
            open_move = close_p - open_p
        else:
            open_move = np.nan

        t_end_trade = pd.Timestamp(
            d.year, d.month, d.day, 12, 30, 0, tzinfo=day.index.tzinfo
        )
        post_open = day[
            (day.index > opening.index[-1] if len(opening) > 0 else day.index[0]) &
            (day.index <= t_end_trade)
        ] if len(opening) > 0 else pd.DataFrame()
        if len(post_open) >= 2 and np.isfinite(open_move) and open_move != 0:
            intraday_ret = float(post_open.iloc[-1]["close"]) - float(post_open.iloc[0]["open"])
            same_sign = 1 if (open_move * intraday_ret) > 0 else 0
        else:
            same_sign = np.nan

        # --- First-15min volume ratio ---
        first15_vol = daily_first15.get(d, np.nan)
        avg20       = float(first15_avg20.get(d, np.nan))
        vol_ratio   = first15_vol / avg20 if (np.isfinite(first15_vol) and np.isfinite(avg20)
                                              and avg20 > 0) else np.nan

        # --- VWAP cross count in first 60min after 09:45 ---
        t_start_60 = pd.Timestamp(d.year, d.month, d.day, 9, 45, 0, tzinfo=day.index.tzinfo)
        t_end_60   = pd.Timestamp(d.year, d.month, d.day, 10, 45, 0, tzinfo=day.index.tzinfo)
        window_60  = day[(day.index > t_start_60) & (day.index <= t_end_60)]
        if len(window_60) >= 2 and "vwap_rth" in window_60.columns:
            prices  = window_60["close"].values
            vwaps   = window_60["vwap_rth"].values
            above   = prices > vwaps
            crosses = int(np.sum(np.diff(above.astype(int)) != 0))
        else:
            crosses = np.nan

        records.append({
            "date":          d,
            "trend_ratio":   trend_ratio,
            "realized_vol":  rv,
            "open_day_same": same_sign,
            "first15_vol_r": vol_ratio,
            "vwap_crosses":  crosses,
        })

    return pd.DataFrame(records).set_index("date")


def assign_windows(session_metrics: pd.DataFrame) -> pd.DataFrame:
    """
    Tag each session with the WF window it belongs to (OOS test period).
    Returns session_metrics with 'wf_window' and 'window_positive' columns.
    """
    sm = session_metrics.copy()
    sm["wf_window"]   = None
    sm["window_positive"] = None

    for w in WF_WINDOWS:
        oos_end   = pd.Timestamp(w["oos_end"])
        oos_start = oos_end - pd.DateOffset(months=WF_TEST_MO)
        idx_naive = _strip_tz(sm.index.to_series()).dt.normalize()
        mask = (idx_naive > oos_start) & (idx_naive <= oos_end)
        sm.loc[mask.values, "wf_window"]       = w["oos_end"]
        sm.loc[mask.values, "window_positive"] = w["positive"]

    return sm.dropna(subset=["wf_window"])


def print_diagnostic_table(sm_windowed: pd.DataFrame) -> Optional[str]:
    """
    Compute per-window means of each metric, compare pos vs neg, run t-tests.
    Returns name of best discriminator (highest |t|), or None.
    """
    metrics = ["trend_ratio", "realized_vol", "open_day_same", "first15_vol_r", "vwap_crosses"]
    metric_labels = {
        "trend_ratio":   "Trend ratio",
        "realized_vol":  "Realized vol",
        "open_day_same": "Open→Day corr",
        "first15_vol_r": "First-15m vol ratio",
        "vwap_crosses":  "VWAP cross count",
    }

    # Per-window means
    window_stats = []
    for w in WF_WINDOWS:
        wdata = sm_windowed[sm_windowed["wf_window"] == w["oos_end"]]
        row   = {"window": w["oos_end"], "positive": w["positive"], "n": len(wdata)}
        for m in metrics:
            row[m] = float(wdata[m].mean()) if wdata[m].notna().sum() > 3 else np.nan
        window_stats.append(row)

    ws_df = pd.DataFrame(window_stats)

    print("\n" + "=" * 110)
    print("PART A — DIFFERENTIAL DIAGNOSTIC: Regime metrics per WF window")
    print("=" * 110)
    header = f"  {'Window':<12} {'Status':<6} {'N':>4}  "
    for m in metrics:
        header += f"{metric_labels[m]:>20}"
    print(header)
    print("  " + "-" * 106)
    for _, row in ws_df.iterrows():
        status = "POS ✓" if row["positive"] else "NEG ✗"
        line   = f"  {str(row['window']):<12} {status:<6} {int(row['n']):>4}  "
        for m in metrics:
            val = row[m]
            line += f"{val:>20.4f}" if np.isfinite(val) else f"{'—':>20}"
        print(line)

    # Pos vs neg group means
    pos_rows = ws_df[ws_df["positive"] == True]
    neg_rows = ws_df[ws_df["positive"] == False]

    print("  " + "-" * 106)
    line_pos = f"  {'Mean POS':<12} {'':6} {'':>4}  "
    line_neg = f"  {'Mean NEG':<12} {'':6} {'':>4}  "
    line_dif = f"  {'Difference':<12} {'':6} {'':>4}  "
    for m in metrics:
        pm = float(pos_rows[m].mean())
        nm = float(neg_rows[m].mean())
        diff = pm - nm
        line_pos += f"{pm:>20.4f}" if np.isfinite(pm) else f"{'—':>20}"
        line_neg += f"{nm:>20.4f}" if np.isfinite(nm) else f"{'—':>20}"
        line_dif += f"{diff:>+20.4f}" if (np.isfinite(pm) and np.isfinite(nm)) else f"{'—':>20}"
    print(line_pos)
    print(line_neg)
    print(line_dif)

    # T-tests
    print("\n  T-tests (positive vs negative window means):")
    print(f"  {'Metric':<22} {'Mean POS':>10} {'Mean NEG':>10} {'Diff':>10} {'t-stat':>8} {'p-value':>9}")
    print("  " + "-" * 75)

    best_t  = 0.0
    best_m  = None
    t_stats = {}
    for m in metrics:
        pos_vals = pos_rows[m].dropna().values
        neg_vals = neg_rows[m].dropna().values
        if len(pos_vals) < 2 or len(neg_vals) < 2:
            t_stats[m] = np.nan
            continue
        try:
            t, p = stats.ttest_ind(pos_vals, neg_vals, equal_var=False)
        except Exception:
            t, p = np.nan, np.nan
        t_stats[m] = t
        pm = float(np.mean(pos_vals))
        nm = float(np.mean(neg_vals))
        flag = " ***" if (np.isfinite(p) and p < 0.10) else ""
        print(f"  {metric_labels[m]:<22} {pm:>10.4f} {nm:>10.4f} {pm-nm:>+10.4f} "
              f"{t:>8.3f} {p:>9.4f}{flag}")
        if np.isfinite(t) and abs(t) > abs(best_t):
            best_t = t
            best_m = m

    print()
    if best_m and abs(best_t) > 2.0:
        print(f"  DISCRIMINATOR FOUND: '{metric_labels[best_m]}' |t|={abs(best_t):.2f} > 2.0")
        print(f"  → Positive windows have {metric_labels[best_m]} "
              f"{'higher' if best_t > 0 else 'lower'} than negative windows.")
        return best_m
    elif best_m and abs(best_t) > 1.5:
        print(f"  WEAK SIGNAL: '{metric_labels[best_m]}' |t|={abs(best_t):.2f} (1.5-2.0 range)")
        print("  → Suggestive but not conclusive. Marginal discriminator.")
        return best_m
    else:
        max_t_str = f"|t|={abs(best_t):.2f}" if best_m else "no data"
        print(f"  NO CLEAR DISCRIMINATOR: max {max_t_str} < 1.5")
        print("  → The 3 negative windows appear to be stochastic variance, not regime-driven.")
        print("  → No new filter warranted from diagnostic.")
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Part B helpers — signal strength composite + variable sizing
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal_strength(df: pd.DataFrame,
                             feats_rich: pd.DataFrame) -> pd.DataFrame:
    """
    Compute signal strength composite for each signal in feats_rich.

    Metrics (all causal — only use data available at 09:45):
      opening_move_strength = |close_09:45 - open_09:30| / atr_5d_30min
      volume_strength       = volume_first_15min / mean_volume_first_15min_20d
      vwap_distance         = |close_09:45 - vwap_at_09:45| / opening_range

      signal_strength = opening_move_strength × volume_strength × (1 + vwap_distance)

    Returns feats_rich with 'signal_strength' column added.
    """
    rth = df[(df.index.time >= T_0930) & (df.index.time <= T_1559)].copy()

    # ── 30-min ATR (5d rolling) — causal ──
    # Use daily high-low as proxy for "30-min ATR" to keep it simple and fast
    # (true 30-min ATR would require resampling to 30-min bars per day)
    daily_hi  = rth["high"].resample("B").max()
    daily_lo  = rth["low"].resample("B").min()
    daily_atr = daily_hi - daily_lo
    atr_5d    = daily_atr.rolling(5, min_periods=3).mean().shift(1)

    # ── First-15min volume (09:30-09:44) ──
    def first15_vol(day_df):
        t_end = pd.Timestamp(
            day_df.index[0].year, day_df.index[0].month, day_df.index[0].day,
            9, 44, 59, tzinfo=day_df.index[0].tzinfo
        )
        seg = day_df[day_df.index <= t_end]
        return float(seg["volume"].sum()) if not seg.empty else np.nan

    dates = sorted(rth.index.normalize().unique())
    first15_map = {}
    for d in dates:
        day = rth[rth.index.normalize() == d]
        first15_map[d] = first15_vol(day)

    first15_series = pd.Series(first15_map)
    first15_avg20  = first15_series.rolling(20, min_periods=5).mean().shift(1)

    # ── Merge onto features ──
    f = feats_rich.copy()
    f["date_naive"] = _strip_tz(f["date"]).dt.normalize()

    # ATR 5d
    atr_df = atr_5d.reset_index()
    atr_df.columns = ["date_naive", "atr_5d"]
    atr_df["date_naive"] = pd.to_datetime(atr_df["date_naive"]).dt.normalize().dt.tz_localize(None)
    f = f.merge(atr_df, on="date_naive", how="left")

    # First-15min vol
    vol15_df = first15_series.reset_index()
    vol15_df.columns = ["date_naive", "first15_vol"]
    vol15_df["date_naive"] = pd.to_datetime(vol15_df["date_naive"]).dt.normalize().dt.tz_localize(None)
    f = f.merge(vol15_df, on="date_naive", how="left")

    vol15avg_df = first15_avg20.reset_index()
    vol15avg_df.columns = ["date_naive", "first15_avg20"]
    vol15avg_df["date_naive"] = pd.to_datetime(vol15avg_df["date_naive"]).dt.normalize().dt.tz_localize(None)
    f = f.merge(vol15avg_df, on="date_naive", how="left")

    # ── Compute components ──
    # opening_move_strength = opening range / atr_5d
    f["open_move_str"] = f["rng"] / f["atr_5d"].replace(0, np.nan)

    # volume_strength = first15_vol / first15_avg20
    f["vol_str"] = f["first15_vol"] / f["first15_avg20"].replace(0, np.nan)

    # vwap_distance = |close_09:45 - vwap| / opening_range
    f["vwap_dist"] = (f["close_price"] - f["vwap_at_sig"]).abs() / f["rng"].replace(0, np.nan)

    # Composite: clamp components to reasonable range to avoid outliers
    # dominating the score
    f["open_move_str"] = f["open_move_str"].clip(0, 5)
    f["vol_str"]       = f["vol_str"].clip(0, 5)
    f["vwap_dist"]     = f["vwap_dist"].clip(0, 3)

    f["signal_strength"] = (
        f["open_move_str"] *
        f["vol_str"] *
        (1 + f["vwap_dist"])
    )

    # Rank into quartiles (1=weakest, 4=strongest)
    valid = f["signal_strength"].notna() & (f["signal_strength"] > 0)
    f.loc[valid, "strength_quartile"] = pd.qcut(
        f.loc[valid, "signal_strength"], q=4, labels=[1, 2, 3, 4]
    ).astype(float)
    f.loc[~valid, "strength_quartile"] = np.nan

    log.info(f"Signal strength: min={f['signal_strength'].min():.3f}  "
             f"median={f['signal_strength'].median():.3f}  "
             f"max={f['signal_strength'].max():.3f}  "
             f"NaN={f['signal_strength'].isna().sum()}")

    # Quartile distribution
    for q in [1, 2, 3, 4]:
        n = (f["strength_quartile"] == q).sum()
        log.info(f"  Quartile Q{q}: {n} signals")

    return f.drop(columns=["date_naive"])


def build_variable_sized_signals(feats_strength: pd.DataFrame,
                                  sizing_map: Dict[int, float],
                                  label: str = "") -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Build signals with variable contract sizing based on signal strength quartile.
    Returns (signals_df, signals_with_contracts_df).

    sizing_map: {quartile: contracts}  e.g. {1: 0.25, 2: 0.5, 3: 0.75, 4: 1.0}
    Quartile 0 = NaN strength → use 0.5 as fallback.

    Returns signals DataFrame with 'contracts' column for custom run.
    """
    # Base signals: iter_08 8b (A$400 + B1.2% + vol_ratio < 0.7)
    base_sigs = build_iter08_signals(
        feats_strength,
        vol_ratio_thresh=PROD_VOL_THRESH,
        label=f"{label}_base",
    )
    if base_sigs.empty:
        return pd.DataFrame(), pd.DataFrame()

    # Attach quartile info
    feats_idx = feats_strength.set_index("sig_ts")

    contracts_col = []
    keep = []
    for sig_ts, _ in base_sigs.iterrows():
        if sig_ts in feats_idx.index:
            q = feats_idx.loc[sig_ts, "strength_quartile"]
            q = int(q) if np.isfinite(q) else 0
        else:
            q = 0

        c = sizing_map.get(q, 0.5)   # default 0.5 for unknown
        if c == 0.0:
            keep.append(False)
            contracts_col.append(0.0)
        else:
            keep.append(True)
            contracts_col.append(c)

    base_sigs["contracts"] = contracts_col
    filtered = base_sigs[keep].copy()

    skipped = (~np.array(keep)).sum()
    log.info(f"[{label}] Variable sizing: {len(base_sigs)} base → "
             f"{len(filtered)} kept ({skipped} skipped by sizing_map=0)")
    return filtered, feats_strength


def run_variable_sized(engine: NQBacktestEngine,
                       signals: pd.DataFrame) -> Tuple[pd.DataFrame, dict]:
    """
    Run backtest with per-signal contract sizing.
    trade P&L = pnl_pts × POINT_VALUE × contracts - COST_RT × contracts
    """
    if signals.empty or "contracts" not in signals.columns:
        return pd.DataFrame(), {}

    trades: List[dict] = []

    for sig_ts, sig in signals.iterrows():
        direction  = int(sig["direction"])
        tp_pts     = float(sig["tp_points"])
        sl_pts     = float(sig["sl_points"])
        exit_ts    = sig["exit_time"]
        contracts  = float(sig.get("contracts", 1.0))

        future = engine.rth[engine.rth.index > sig_ts]
        if future.empty:
            continue

        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])

        if direction == 1:
            tp_price = entry_price + tp_pts
            sl_price = entry_price - sl_pts
        else:
            tp_price = entry_price - tp_pts
            sl_price = entry_price + sl_pts

        window = engine.rth[
            (engine.rth.index >= entry_bar) & (engine.rth.index <= exit_ts)
        ]

        exit_price  = None
        exit_reason = "time"
        bars_held   = 0

        for bar_ts, bar in window.iterrows():
            bars_held += 1
            bar_h = float(bar["high"])
            bar_l = float(bar["low"])

            if direction == 1:
                if bar_l <= sl_price:
                    exit_price, exit_reason = sl_price, "sl"
                    break
                if bar_h >= tp_price:
                    exit_price, exit_reason = tp_price, "tp"
                    break
            else:
                if bar_h >= sl_price:
                    exit_price, exit_reason = sl_price, "sl"
                    break
                if bar_l <= tp_price:
                    exit_price, exit_reason = tp_price, "tp"
                    break

        if exit_price is None:
            if window.empty:
                continue
            exit_price  = float(window.iloc[-1]["close"])
            exit_reason = "time"

        pnl_pts  = direction * (exit_price - entry_price)
        pnl_usd  = pnl_pts * POINT_VALUE * contracts - COST_RT * contracts

        trades.append({
            "signal_ts":   sig_ts,
            "entry_ts":    entry_bar,
            "exit_ts":     bar_ts if exit_reason != "time" else window.index[-1],
            "direction":   direction,
            "entry_price": entry_price,
            "exit_price":  exit_price,
            "exit_reason": exit_reason,
            "pnl_pts":     round(pnl_pts, 4),
            "pnl_usd":     round(pnl_usd, 2),
            "bars_held":   bars_held,
            "contracts":   contracts,
        })

    tl  = pd.DataFrame(trades)
    met = engine.metrics(tl) if not tl.empty else {}
    return tl, met


def per_quartile_breakdown(trade_log: pd.DataFrame,
                           feats_strength: pd.DataFrame) -> pd.DataFrame:
    """
    Show per-quartile win rate, avg trade, cumulative P&L.
    """
    if trade_log.empty:
        return pd.DataFrame()

    feats_idx = feats_strength.set_index("sig_ts")
    tl = trade_log.copy()

    quarters = []
    for sig_ts in tl["signal_ts"]:
        q = np.nan
        if sig_ts in feats_idx.index:
            q_val = feats_idx.loc[sig_ts, "strength_quartile"]
            q = float(q_val) if np.isfinite(q_val) else np.nan
        quarters.append(q)
    tl["quartile"] = quarters

    rows = []
    for q in [1.0, 2.0, 3.0, 4.0]:
        sub = tl[tl["quartile"] == q]
        if len(sub) == 0:
            rows.append({"quartile": f"Q{int(q)}", "n": 0,
                        "win_rate": np.nan, "avg_trade": np.nan,
                        "cum_pnl": np.nan, "contracts_avg": np.nan})
            continue
        winners = sub[sub["pnl_usd"] > 0]
        rows.append({
            "quartile":      f"Q{int(q)}",
            "n":             len(sub),
            "win_rate":      len(winners) / len(sub),
            "avg_trade":     float(sub["pnl_usd"].mean()),
            "cum_pnl":       float(sub["pnl_usd"].sum()),
            "contracts_avg": float(sub["contracts"].mean()),
        })

    return pd.DataFrame(rows)


def evaluate_variable(engine: NQBacktestEngine,
                      signals: pd.DataFrame,
                      feats_strength: pd.DataFrame,
                      label: str,
                      n_test: int,
                      sizing_map: Dict[int, float]) -> Tuple[dict, pd.DataFrame]:
    """Full evaluation with variable sizing."""
    if signals.empty or len(signals) < 10:
        return {"iteration": label, "n_trades": 0, "verdict": "SKIP"}, pd.DataFrame()

    tl, met  = run_variable_sized(engine, signals)
    boot     = engine.bootstrap_ev(tl) if not tl.empty else {}
    qb       = per_quartile_breakdown(tl, feats_strength)

    sh  = met.get("sharpe_daily_hac") or 0
    pf  = met.get("profit_factor")    or 0
    mdd = met.get("max_dd_pct")       or 0
    n   = met.get("n_trades", 0)
    p   = boot.get("p_ev_zero", 1.0)

    if sh >= 1.30 and mdd >= -0.20 and pf >= 1.30 and p < 0.02:
        verdict = "PROPFIRM_PASS"
    elif sh >= 1.0 and mdd >= -0.25 and pf >= 1.20:
        verdict = "RESEARCH_PASS"
    elif sh >= 0.5:
        verdict = "IMPROVE"
    else:
        verdict = "SKIP"

    result = {
        "iteration": label,
        "n_tests":   n_test,
        **met,
        **boot,
        "verdict":   verdict,
    }
    append_result(result)
    return result, qb


def print_row(r: dict) -> None:
    sh  = r.get("sharpe_daily_hac") or 0
    mdd = r.get("max_dd_pct") or 0
    pf  = r.get("profit_factor") or 0
    n   = r.get("n_trades", 0)
    p   = r.get("p_ev_zero") or 1.0
    vd  = r.get("verdict", "?")
    dsh = sh  - REF["sharpe"]
    dmdd= (mdd - REF["max_dd"]) * 100
    print(f"  {r.get('iteration','?'):<22} Sh={sh:+.3f}({dsh:+.3f})  "
          f"MaxDD={mdd*100:+.1f}%({dmdd:+.1f}pp)  "
          f"PF={pf:.3f}  N={n}  P(EV≤0)={p:.3f}  → {vd}")


def print_quartile_table(qb: pd.DataFrame, label: str) -> None:
    if qb.empty:
        return
    print(f"\n  Per-quartile breakdown ({label}):")
    print(f"  {'Quartile':<10} {'N':>5} {'WR':>8} {'Avg trade$':>12} {'Cum P&L$':>12} {'Avg ctrs':>10}")
    print("  " + "-" * 60)
    for _, row in qb.iterrows():
        if row["n"] == 0:
            print(f"  {row['quartile']:<10} {'—':>5}")
            continue
        print(f"  {row['quartile']:<10} {int(row['n']):>5} {row['win_rate']*100:>7.1f}% "
              f"{row['avg_trade']:>12.1f} {row['cum_pnl']:>12.0f} "
              f"{row['contracts_avg']:>10.2f}")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    log.info("=== Iter 09 — Differential Diagnostic + Signal Strength Sizing ===")

    df     = load_nq_1min()
    engine = NQBacktestEngine(df)

    log.info("Building opening features...")
    feats = build_opening_features(engine.rth)
    log.info(f"Features: {len(feats)} total  |  VWAP ok: {feats['vwap_ok'].sum()}")

    log.info("Computing vol ratio for iter_08 8b base...")
    vol_ratio = compute_vol_ratio(df)
    log.info("Fetching VIX...")
    vix_5d = fetch_vix(str(df.index.min().date()), str(df.index.max().date()))
    feats_rich = enrich_features(feats, vol_ratio, vix_5d)

    n_test = N_TESTS_BASE

    # ─────────────────────────────────────────────────────────────────────────
    # PART A — Differential diagnostic
    # ─────────────────────────────────────────────────────────────────────────
    log.info("Part A: Computing per-session regime metrics...")
    session_metrics = compute_session_metrics(df, feats)
    sm_windowed     = assign_windows(session_metrics)

    log.info(f"Session metrics: {len(session_metrics)} sessions, "
             f"{len(sm_windowed)} in WF windows")

    discriminator = print_diagnostic_table(sm_windowed)

    # ─────────────────────────────────────────────────────────────────────────
    # PART B — Signal strength variable sizing
    # ─────────────────────────────────────────────────────────────────────────
    log.info("Part B: Computing signal strength composite...")
    feats_strength = compute_signal_strength(df, feats_rich)

    # Quartile P&L breakdown at 1.0 contract to see if quartiles differ
    log.info("Building quartile diagnostic (1.0c per signal)...")
    base_sigs = build_iter08_signals(feats_strength, vol_ratio_thresh=PROD_VOL_THRESH,
                                      label="iter_09_base_diag")

    # Add quartile to base signals for diagnostic
    feats_idx = feats_strength.set_index("sig_ts")
    qdiag_trades = []
    for sig_ts, sig in base_sigs.iterrows():
        future = engine.rth[engine.rth.index > sig_ts]
        if future.empty:
            continue
        entry_bar   = future.index[0]
        entry_price = float(future.iloc[0]["open"])
        direction   = int(sig["direction"])
        tp_pts      = float(sig["tp_points"])
        sl_pts      = float(sig["sl_points"])
        exit_ts_    = sig["exit_time"]

        if direction == 1:
            tp_price = entry_price + tp_pts
            sl_price = entry_price - sl_pts
        else:
            tp_price = entry_price - tp_pts
            sl_price = entry_price + sl_pts

        window = engine.rth[(engine.rth.index >= entry_bar) & (engine.rth.index <= exit_ts_)]
        exit_price = None
        exit_reason = "time"
        for bar_ts, bar in window.iterrows():
            bh, bl = float(bar["high"]), float(bar["low"])
            if direction == 1:
                if bl <= sl_price:
                    exit_price, exit_reason = sl_price, "sl"; break
                if bh >= tp_price:
                    exit_price, exit_reason = tp_price, "tp"; break
            else:
                if bh >= sl_price:
                    exit_price, exit_reason = sl_price, "sl"; break
                if bl <= tp_price:
                    exit_price, exit_reason = tp_price, "tp"; break
        if exit_price is None:
            exit_price = float(window.iloc[-1]["close"]) if not window.empty else entry_price

        pnl_usd = direction * (exit_price - entry_price) * POINT_VALUE - COST_RT
        q = np.nan
        if sig_ts in feats_idx.index:
            q = feats_idx.loc[sig_ts, "strength_quartile"]
            q = float(q) if np.isfinite(q) else np.nan
        qdiag_trades.append({
            "signal_ts": sig_ts, "direction": direction,
            "entry_price": entry_price, "exit_price": exit_price,
            "exit_reason": exit_reason, "pnl_usd": round(pnl_usd, 2),
            "contracts": 1.0, "quartile": q,
        })

    qdiag_df = pd.DataFrame(qdiag_trades)

    print("\n" + "=" * 80)
    print("PART B — SIGNAL STRENGTH QUARTILE ANALYSIS (1.0c per signal, diagnostic)")
    print("=" * 80)
    qb_diag = per_quartile_breakdown(qdiag_df, feats_strength)
    if not qb_diag.empty:
        qb_diag2 = qb_diag.copy()
        qb_diag2["contracts_avg"] = 1.0
        print_quartile_table(qb_diag2, "equal-weight baseline")

        # T-test Q4 vs Q1 avg trade
        q4_trades = qdiag_df[qdiag_df["quartile"] == 4.0]["pnl_usd"].values
        q1_trades = qdiag_df[qdiag_df["quartile"] == 1.0]["pnl_usd"].values
        if len(q4_trades) > 5 and len(q1_trades) > 5:
            t, p = stats.ttest_ind(q4_trades, q1_trades, equal_var=False)
            print(f"\n  Q4 vs Q1 avg trade t-test: t={t:.3f}, p={p:.4f}")
            if p < 0.10:
                print("  → Q4 significantly better than Q1. Signal strength IS discriminating.")
            else:
                print("  → Q4 not significantly better than Q1. Signal strength may not discriminate.")

    # ── Variant 9a: 1.0/0.75/0.5/0.25 ──
    print("\n" + "=" * 80)
    print("VARIANT 9a — Variable sizing 1.0/0.75/0.5/0.25 (full retention)")
    print("=" * 80)
    n_test += 1
    sizing_9a = {1: 0.25, 2: 0.50, 3: 0.75, 4: 1.00, 0: 0.50}
    sigs_9a, _ = build_variable_sized_signals(feats_strength, sizing_9a, "iter_09_9a")
    r_9a, qb_9a = evaluate_variable(engine, sigs_9a, feats_strength, "iter_09_9a", n_test, sizing_9a)
    print_row(r_9a)
    print_quartile_table(qb_9a, "iter_09_9a")

    # ── Variant 9b: 1.0/0.75/0.5/skip Q1 ──
    print("\n" + "=" * 80)
    print("VARIANT 9b — Variable sizing 1.0/0.75/0.5/skip (skip Q1)")
    print("=" * 80)
    n_test += 1
    sizing_9b = {1: 0.00, 2: 0.50, 3: 0.75, 4: 1.00, 0: 0.50}
    sigs_9b, _ = build_variable_sized_signals(feats_strength, sizing_9b, "iter_09_9b")
    r_9b, qb_9b = evaluate_variable(engine, sigs_9b, feats_strength, "iter_09_9b", n_test, sizing_9b)
    print_row(r_9b)
    print_quartile_table(qb_9b, "iter_09_9b")

    # ── Variant 9c: top half only ──
    print("\n" + "=" * 80)
    print("VARIANT 9c — Top half only (skip Q1+Q2)")
    print("=" * 80)
    n_test += 1
    sizing_9c = {1: 0.00, 2: 0.00, 3: 0.75, 4: 1.00, 0: 0.00}
    sigs_9c, _ = build_variable_sized_signals(feats_strength, sizing_9c, "iter_09_9c")
    r_9c, qb_9c = evaluate_variable(engine, sigs_9c, feats_strength, "iter_09_9c", n_test, sizing_9c)
    print_row(r_9c)
    print_quartile_table(qb_9c, "iter_09_9c")

    # ─────────────────────────────────────────────────────────────────────────
    # Final comparison table
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("COMPARISON TABLE")
    print("=" * 80)
    print(f"  {'Variant':<22} {'Sharpe':>8} {'MaxDD':>8} {'PF':>6} {'N':>5} "
          f"{'P(EV≤0)':>9} {'Verdict'}")
    print("  " + "-" * 72)
    ref = REF
    print(f"  {'iter_08_8b (ref)':<22} {ref['sharpe']:>8.3f} "
          f"{ref['max_dd']*100:>7.1f}% {ref['pf']:>6.3f} {ref['n_trades']:>5} "
          f"{'0.015':>9}  REFERENCE")
    for r in [r_9a, r_9b, r_9c]:
        if r.get("n_trades", 0) == 0:
            continue
        sh  = r.get("sharpe_daily_hac") or 0
        mdd = r.get("max_dd_pct") or 0
        pf  = r.get("profit_factor") or 0
        n   = r.get("n_trades", 0)
        p   = r.get("p_ev_zero") or 1.0
        vd  = r.get("verdict", "?")
        dsh = sh - ref["sharpe"]
        dmdd= (mdd - ref["max_dd"]) * 100
        print(f"  {r.get('iteration','?'):<22} {sh:>+8.3f} {mdd*100:>7.1f}% "
              f"{pf:>6.3f} {n:>5} {p:>9.3f}  {vd}  (ΔSh={dsh:+.3f}, ΔMaxDD={dmdd:+.1f}pp)")

    # ─────────────────────────────────────────────────────────────────────────
    # Final conclusions
    # ─────────────────────────────────────────────────────────────────────────
    best_var = max([r_9a, r_9b, r_9c],
                   key=lambda r: (r.get("sharpe_daily_hac") or 0))
    best_sh  = best_var.get("sharpe_daily_hac") or 0
    best_mdd = best_var.get("max_dd_pct") or 0
    best_pf  = best_var.get("profit_factor") or 0
    best_p   = best_var.get("p_ev_zero") or 1.0

    part_a_success = discriminator is not None
    part_b_success = (best_sh > REF["sharpe"] + 0.05 and best_pf > REF["pf"] + 0.02)

    propfirm_gates = (
        best_sh  >= 1.30 and
        best_mdd >= -0.20 and
        best_pf  >= 1.30 and
        best_p   <  0.02
    )

    print("\n" + "=" * 80)
    print("FINAL CONCLUSIONS")
    print("=" * 80)

    print(f"\n1. Differential diagnostic:")
    if part_a_success:
        print(f"   Negative windows characterized by '{discriminator}' — filter proposed.")
    else:
        print("   No statistically clear discriminator — accept negative windows as stochastic variance.")
        print("   The 3 failures are within expected variance for a 67% win-rate strategy.")

    print(f"\n2. Variable sizing:")
    if part_b_success:
        print(f"   Quartile separation confirmed. Best: {best_var.get('iteration')} "
              f"Sharpe={best_sh:.3f}, PF={best_pf:.3f}")
    else:
        print("   Signal strength composite does not meaningfully improve performance.")
        print("   Fixed sizing (iter_08 8b) remains optimal.")

    print(f"\n3. Decision:")
    if propfirm_gates and (part_a_success or part_b_success):
        print("   DECISION A: iter_09 PROPFIRM READY at 1.0 contract sizing.")
        print(f"   → Best: {best_var.get('iteration')} Sh={best_sh:.3f}, "
              f"MaxDD={best_mdd*100:.1f}%, PF={best_pf:.3f}")
        print("   → Commit iter_09 and upgrade paper trading to full contract sizing.")
    elif part_b_success or part_a_success:
        print("   DECISION B: Marginal upgrade from iter_09.")
        print("   → Decision B remains (0.25 contracts) but with refined signal/sizing.")
        print("   → Continue paper trading iter_05 base. Re-evaluate after 30 live trades.")
    else:
        print("   DECISION C: iter_05/iter_08 is the asymptotic version.")
        print("   → Accept Decision B (0.25 contracts). Move to Portfolio integration.")
        print("   → Next session: populate Portfolio/ with A/B live returns + C backtest proxy.")
        print("   → Compute first portfolio Sharpe, correlation matrix, ERC sizing.")

    print(f"\n4. Next iteration roadmap:")
    if propfirm_gates:
        print("   iter_10: Live paper trading pipeline setup + position monitoring")
    elif part_b_success:
        print("   iter_10: Extended WF re-run with variable sizing to confirm WF% >= 75%")
    else:
        print("   Portfolio integration session: load A/B/C returns, compute portfolio stats")
        print("   Consider iter_10 only if 30 live trades show different pattern")

    print(f"\nn_tests: {N_TESTS_BASE} → {n_test}")
    print("DO NOT COMMIT — await review.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log.exception("iter_09 failed")
        sys.exit(1)
