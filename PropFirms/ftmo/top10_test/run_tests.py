"""
Run rigorous tests on the 8 testable top-10 FTMO candidates.

Excluded from this run (already studied):
- lit_010 (CIP-EOQ): killed 2026-05-26, L11 gate fail x5 (SR 0.24-0.62 < 0.7 gate).
- lit_014 (Branch overnight): L36 beta-proxy, FTMO sprint p<0.1%, NOT a vehicle.

Tested here (8):
- ang_025: Index overnight gap fill (US500 + GER40)
- ang_019: UK100 morning gap close
- lit_021: Index opening-gap fade (Berkman 2012) — US500
- lit_048: Round-number bounce — EURUSD + USDJPY
- ang_017: US500 lunch fade 11:30-13:30 ET
- ang_024: US500 2-day momentum low-vol VIX<15
- ang_047: EURUSD-GBPUSD divergence pair
- ang_048: US100-US500 ratio MR + VIX>18

For each: signal at T-1 trade at T, FTMO costs + swap, vol target 8%/yr,
HAC lag-6, block bootstrap, DSR, WF >=5, FTMO MC. AMTP across all 8.
"""
from __future__ import annotations

import json
import math
import os
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from framework import (
    FTMO_COST_BPS_RT, FTMO_SWAP_BPS_PER_NIGHT, FTMOResult,
    StrategyResult, hac_tstat, block_bootstrap_sharpe, deflated_sharpe,
    walk_forward_folds, max_drawdown_pct, amtp_bonferroni,
    ftmo_montecarlo, load_rf_daily, vol_target, _sharpe,
)
from data_loaders import (
    load_index_m1, load_index_daily, load_uk100_m5, load_eurusd_m5,
    load_usdjpy_m5, load_fx_daily, load_vix,
)


RESULTS_DIR = Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/top10_test/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Helper: trade-to-daily-PnL aggregator
# ---------------------------------------------------------------------------

def trades_to_daily_pnl(trades: pd.DataFrame, all_dates: pd.DatetimeIndex) -> pd.Series:
    """Convert list of trades to daily PnL series (as fraction of capital).
    Handles tz-mixing and ensures all trade dates land in the output index."""
    if trades.empty:
        return pd.Series(0.0, index=all_dates)
    t = trades.copy()
    ed = pd.to_datetime(t["exit_date"])
    if hasattr(ed.dt, "tz") and ed.dt.tz is not None:
        ed = ed.dt.tz_localize(None)
    t["exit_date"] = ed.dt.normalize()
    pnl_by_date = t.groupby("exit_date")["net_bps"].sum() / 10000.0
    base_idx = pd.DatetimeIndex(all_dates)
    if base_idx.tz is not None:
        base_idx = base_idx.tz_localize(None)
    full_idx = pnl_by_date.index.union(base_idx).sort_values()
    out = pd.Series(0.0, index=full_idx)
    out.loc[pnl_by_date.index] = pnl_by_date.values
    return out


def cost_of_pair(asset_class: str, n_legs: int = 1) -> float:
    """Per-trade RT cost in bps; n_legs=2 for pair trades."""
    return n_legs * FTMO_COST_BPS_RT[asset_class]


# ---------------------------------------------------------------------------
# Strategy 1: ang_025 — Index overnight gap fill (US500 + GER40)
# ---------------------------------------------------------------------------

def strat_ang_025() -> tuple[pd.Series, dict]:
    """For each day, if overnight gap > 1.5*sigma_30d, fade direction.
    Entry at open T, target = close_T-1, stop = open_T + 1.0*sigma*sign(gap), exit close T.
    Conservative tick-order: if both target and stop bracketed by day OHLC, assume stop hit first.
    """
    trades = []
    for symbol in ["US500", "GER40"]:
        try:
            d = load_index_daily(symbol)
        except FileNotFoundError:
            continue
        d["close_prev"] = d["close"].shift(1)
        d["gap"] = (d["open"] - d["close_prev"]) / d["close_prev"]
        d["abs_gap_std30"] = d["gap"].abs().rolling(30, min_periods=10).std()
        for date, row in d.iterrows():
            if pd.isna(row["close_prev"]) or pd.isna(row["abs_gap_std30"]):
                continue
            thr = 1.5 * row["abs_gap_std30"]
            if abs(row["gap"]) < thr:
                continue
            side = -1 if row["gap"] > 0 else 1  # fade
            entry = row["open"]
            target = row["close_prev"]
            stop_dist = abs(row["gap"]) * entry  # 1.0 * gap as stop
            if side == -1:  # short on gap up
                stop = entry + stop_dist
                target_hit = row["low"] <= target
                stop_hit = row["high"] >= stop
            else:  # long on gap down
                stop = entry - stop_dist
                target_hit = row["high"] >= target
                stop_hit = row["low"] <= stop
            # Conservative: if both touched, assume stop hit
            if target_hit and stop_hit:
                exit_px = stop
            elif target_hit:
                exit_px = target
            elif stop_hit:
                exit_px = stop
            else:
                exit_px = row["close"]
            gross_bps = side * (exit_px - entry) / entry * 10000.0
            cost_bps = cost_of_pair("Index_CFD_major", 1)
            net_bps = gross_bps - cost_bps  # no swap, intraday
            trades.append({"exit_date": date, "asset": symbol, "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 2: ang_019 — UK100 morning gap close
# ---------------------------------------------------------------------------

def strat_ang_019() -> tuple[pd.Series, dict]:
    """UK100 09:00 GMT entry, fade overnight gap, exit 12:00 GMT or fill."""
    df = load_uk100_m5()
    if df.empty:
        return pd.Series(0.0, index=pd.date_range("2018-01-01", "2024-12-31", freq="B")), {"n_trades": 0, "trades_df": pd.DataFrame()}
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    # daily aggregates for prev close
    daily_close = df["close"].resample("1D").last()
    daily_close_prev = daily_close.shift(1)
    # locate 09:00 GMT bar for each day (use 08:00-09:00 range as proxy)
    df["hour"] = df.index.hour
    df["date"] = df.index.normalize()
    open_900 = df[df["hour"] == 8].groupby("date")["open"].first()  # 08:00 bar = UK open ~08:00 GMT
    # session_window: 09:00 to 12:00 GMT
    sess = df[(df["hour"] >= 8) & (df["hour"] < 12)]
    high_sess = sess.groupby("date")["high"].max()
    low_sess = sess.groupby("date")["low"].min()
    close_sess = sess[sess["hour"] == 11].groupby("date")["close"].last()
    # gap sigma
    gap = (open_900 - daily_close_prev) / daily_close_prev
    gap_sigma = gap.abs().rolling(30, min_periods=10).std()
    trades = []
    for date in open_900.index:
        if pd.isna(daily_close_prev.get(date)) or pd.isna(gap_sigma.get(date)):
            continue
        g = gap.get(date)
        if pd.isna(g):
            continue
        thr = 1.5 * gap_sigma.get(date)
        if abs(g) < thr:
            continue
        side = -1 if g > 0 else 1
        entry = open_900.get(date)
        target = daily_close_prev.get(date)
        stop_dist = abs(g) * entry
        if side == -1:
            stop = entry + stop_dist
            target_hit = low_sess.get(date, 1e10) <= target
            stop_hit = high_sess.get(date, -1e10) >= stop
        else:
            stop = entry - stop_dist
            target_hit = high_sess.get(date, -1e10) >= target
            stop_hit = low_sess.get(date, 1e10) <= stop
        if target_hit and stop_hit:
            exit_px = stop
        elif target_hit:
            exit_px = target
        elif stop_hit:
            exit_px = stop
        else:
            exit_px = close_sess.get(date, entry)
        gross_bps = side * (exit_px - entry) / entry * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": "UK100", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2024-12-31", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 3: lit_021 — Index opening-gap fade (Berkman 2012) on US500
# ---------------------------------------------------------------------------

def strat_lit_021() -> tuple[pd.Series, dict]:
    """First 30-min range outsize → fade. Entry 10:00 ET, exit 11:30 ET or hit."""
    df = load_index_m1("US500")
    df = df.sort_index()
    df["hour"] = df.index.hour
    df["date"] = df.index.normalize()
    # Use 14:30 UTC = 09:30 ET (EDT); approximate, accept 1h DST error
    open_bars = df[df["hour"] == 14].copy()
    close_1000 = df[df["hour"] == 15].copy()
    close_1130 = df[df["hour"] == 16].copy()
    # 30-min range from 14:30-15:00 UTC
    sess_30 = df[(df["hour"] == 14)]
    or_high_30 = sess_30.groupby("date")["high"].max()
    or_low_30 = sess_30.groupby("date")["low"].min()
    or_open_30 = sess_30.groupby("date")["open"].first()
    or_close_30 = sess_30.groupby("date")["close"].last()
    or_range_30 = (or_high_30 - or_low_30) / or_open_30
    or_dir_30 = np.sign(or_close_30 - or_open_30)
    or_range_avg30d = or_range_30.rolling(30, min_periods=10).mean()
    # Entry at 10:00 ET = 15:00 UTC, exit 11:30 ET = 16:30 UTC
    entry_px = df[df["hour"] == 15].groupby("date")["open"].first()
    exit_px = df[df["hour"] == 16].groupby("date")["close"].last()
    # Intraday high/low between 15:00 and 16:30 UTC for stop checks
    sess_post = df[(df["hour"] >= 15) & (df["hour"] < 17)]
    sess_high = sess_post.groupby("date")["high"].max()
    sess_low = sess_post.groupby("date")["low"].min()
    trades = []
    for date in entry_px.index:
        if pd.isna(or_range_30.get(date)) or pd.isna(or_range_avg30d.get(date)):
            continue
        if or_range_30.get(date) < 1.5 * or_range_avg30d.get(date):
            continue
        if pd.isna(entry_px.get(date)) or pd.isna(exit_px.get(date)):
            continue
        side = -int(or_dir_30.get(date))
        if side == 0:
            continue
        e_px = entry_px.get(date)
        x_px = exit_px.get(date)
        gross_bps = side * (x_px - e_px) / e_px * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": "US500", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 4: lit_048 — Round-number bounce EURUSD/USDJPY (DAILY simplification)
# ---------------------------------------------------------------------------

def strat_lit_048() -> tuple[pd.Series, dict]:
    """Simplified daily proxy: at each open, distance to nearest 50-pip level
    on EURUSD (every 0.0050) and JPY (every 0.50). If open within 5 pips of level,
    fade direction of bar open vs level. Hold 1 day, exit at next open.
    """
    trades = []
    eu = load_eurusd_m5()
    if not eu.empty:
        daily_e = eu.resample("1D").agg({"open": "first", "high": "max",
                                          "low": "min", "close": "last"}).dropna()
        for date in daily_e.index[:-1]:
            try:
                o = daily_e.loc[date, "open"]
                next_o = daily_e.loc[daily_e.index[daily_e.index.get_loc(date) + 1], "open"]
            except (KeyError, IndexError):
                continue
            mod = (o * 10000) % 50  # pips mod 50
            dist = min(mod, 50 - mod)
            if dist > 5:  # not near a round level
                continue
            # Above the level: open mod>25 → open is closer to level from above → expect fade down
            side = -1 if mod < 25 else 1
            gross_bps = side * (next_o - o) / o * 10000.0
            cost_bps = cost_of_pair("FX_major", 1)
            swap_bps = FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
            net_bps = gross_bps - cost_bps + swap_bps
            trades.append({"exit_date": daily_e.index[daily_e.index.get_loc(date) + 1],
                           "asset": "EURUSD", "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    jp = load_usdjpy_m5()
    if not jp.empty:
        daily_j = jp.resample("1D").agg({"open": "first", "high": "max",
                                          "low": "min", "close": "last"}).dropna()
        for date in daily_j.index[:-1]:
            try:
                o = daily_j.loc[date, "open"]
                next_o = daily_j.loc[daily_j.index[daily_j.index.get_loc(date) + 1], "open"]
            except (KeyError, IndexError):
                continue
            # JPY levels every 0.50 ⇒ measure in pips/100
            mod = (o * 100) % 50
            dist = min(mod, 50 - mod)
            if dist > 5:
                continue
            side = -1 if mod < 25 else 1
            gross_bps = side * (next_o - o) / o * 10000.0
            cost_bps = cost_of_pair("FX_major", 1)
            swap_bps = FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
            net_bps = gross_bps - cost_bps + swap_bps
            trades.append({"exit_date": daily_j.index[daily_j.index.get_loc(date) + 1],
                           "asset": "USDJPY", "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "caveat": "Daily simplification — true round-number microstructure needs M1 tick data"}


# ---------------------------------------------------------------------------
# Strategy 5: ang_017 — US500 lunch fade 11:30-13:30 ET
# ---------------------------------------------------------------------------

def strat_ang_017() -> tuple[pd.Series, dict]:
    """Fade morning momentum (09:30-11:30 ET) at 11:30 ET, exit 13:30 ET."""
    df = load_index_m1("US500")
    df = df.sort_index()
    df["hour"] = df.index.hour
    df["date"] = df.index.normalize()
    # 09:30 ET ≈ 14:30 UTC EDT or 13:30 UTC EST; use 14:30 UTC (handles US summer half)
    # Morning window: 14:30-16:30 UTC; exit 18:30 UTC
    open_morn = df[df["hour"] == 14].groupby("date")["open"].first()
    end_morn = df[df["hour"] == 16].groupby("date")["close"].last()
    entry_lunch = df[df["hour"] == 16].groupby("date")["close"].last()  # entry at end of morning
    exit_lunch = df[df["hour"] == 18].groupby("date")["close"].last()  # exit 18:30 UTC = 13:30 ET
    trades = []
    for date in open_morn.index:
        e1 = open_morn.get(date)
        e2 = end_morn.get(date)
        en = entry_lunch.get(date)
        ex = exit_lunch.get(date)
        if any(pd.isna(x) for x in [e1, e2, en, ex]):
            continue
        mom = (e2 - e1) / e1
        if abs(mom) < 0.003:  # 0.3% threshold
            continue
        side = -int(np.sign(mom))
        gross_bps = side * (ex - en) / en * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": "US500", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 6: ang_024 — US500 2-day momentum low-vol VIX<15
# ---------------------------------------------------------------------------

def strat_ang_024() -> tuple[pd.Series, dict]:
    """If VIX[T-1] < 15: long if 2d return T-1 to T-3 positive, short if negative.
    Entry open T, exit close T+1. 2 nights swap."""
    d = load_index_daily("US500")
    vix = load_vix()["^VIX"].rename("vix")
    df = d.join(vix.reindex(d.index).ffill(), how="left")
    df["close_prev"] = df["close"].shift(1)
    df["close_prev3"] = df["close"].shift(3)
    df["mom_2d"] = (df["close_prev"] - df["close_prev3"]) / df["close_prev3"]
    df["vix_prev"] = df["vix"].shift(1)
    df["next_close"] = df["close"].shift(-1)
    trades = []
    for date, row in df.iterrows():
        if any(pd.isna(row[c]) for c in ["mom_2d", "vix_prev", "open", "next_close"]):
            continue
        if row["vix_prev"] >= 15:
            continue
        if abs(row["mom_2d"]) < 0.005:  # 0.5% threshold to reduce noise
            continue
        side = int(np.sign(row["mom_2d"]))
        entry = row["open"]
        exit_p = row["next_close"]
        gross_bps = side * (exit_p - entry) / entry * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        swap_bps = 2 * FTMO_SWAP_BPS_PER_NIGHT["Index_CFD_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        # exit_date = next bday
        try:
            exit_date = df.index[df.index.get_loc(date) + 1]
        except (KeyError, IndexError):
            continue
        trades.append({"exit_date": exit_date, "asset": "US500", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 2})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 7: ang_047 — EURUSD-GBPUSD divergence pair
# ---------------------------------------------------------------------------

def strat_ang_047() -> tuple[pd.Series, dict]:
    """5-day return divergence z-score. |z|>1.5 → trade pair convergence.
    Hold 3 days, 2 legs x 2 nights = 4 swap legs total."""
    eu = load_fx_daily("EURUSD")
    gb = load_fx_daily("GBPUSD")
    if eu.empty or gb.empty:
        return pd.Series(0.0, index=pd.date_range("2018-01-01", "2026-05-29", freq="B")), {"n_trades": 0, "trades_df": pd.DataFrame()}
    common = eu.index.intersection(gb.index)
    eu = eu.loc[common]
    gb = gb.loc[common]
    eu["r5"] = (eu["close"] / eu["close"].shift(5) - 1.0)
    gb["r5"] = (gb["close"] / gb["close"].shift(5) - 1.0)
    div = (eu["r5"] - gb["r5"])
    div_z = (div - div.rolling(60, min_periods=20).mean()) / div.rolling(60, min_periods=20).std()
    div_z = div_z.shift(1)  # signal at T-1
    trades = []
    holding_days = 3
    for i, date in enumerate(common):
        z = div_z.get(date)
        if pd.isna(z) or abs(z) < 1.5:
            continue
        if i + holding_days >= len(common):
            break
        exit_date = common[i + holding_days]
        # short EURUSD long GBPUSD when z > 1.5 (EUR over-performed → expect convergence)
        eu_side = -1 if z > 0 else 1
        gb_side = +1 if z > 0 else -1
        eu_e = eu.loc[date, "open"]
        eu_x = eu.loc[exit_date, "close"]
        gb_e = gb.loc[date, "open"]
        gb_x = gb.loc[exit_date, "close"]
        eu_gross = eu_side * (eu_x - eu_e) / eu_e * 10000.0
        gb_gross = gb_side * (gb_x - gb_e) / gb_e * 10000.0
        gross_bps = (eu_gross + gb_gross) / 2.0  # equal-weight basket
        cost_bps = cost_of_pair("FX_major", 2)
        swap_bps = 2 * holding_days * FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": exit_date, "asset": "EUR-GBP", "side": eu_side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 2 * holding_days})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Strategy 8: ang_048 — US100-US500 ratio MR + VIX>18
# ---------------------------------------------------------------------------

def strat_ang_048() -> tuple[pd.Series, dict]:
    """Log-ratio US100/US500 z-score |z|>1.5 + VIX>18 → ratio MR.
    Hold 5 days, 2 legs x 4 nights = 8 swap legs."""
    nq = load_index_daily("US100")
    es = load_index_daily("US500")
    vix = load_vix()["^VIX"]
    common = nq.index.intersection(es.index)
    nq = nq.loc[common]
    es = es.loc[common]
    vix_aligned = vix.reindex(common).ffill()
    log_ratio = np.log(nq["close"] / es["close"])
    z = (log_ratio - log_ratio.rolling(60, min_periods=20).mean()) / log_ratio.rolling(60, min_periods=20).std()
    z = z.shift(1)
    vix_lag = vix_aligned.shift(1)
    trades = []
    holding_days = 5
    for i, date in enumerate(common):
        zi = z.get(date)
        vi = vix_lag.get(date)
        if pd.isna(zi) or pd.isna(vi) or abs(zi) < 1.5 or vi < 18:
            continue
        if i + holding_days >= len(common):
            break
        exit_date = common[i + holding_days]
        # if z > 0, NDX overperformed → short NDX long SPX (ratio MR)
        nq_side = -1 if zi > 0 else 1
        es_side = +1 if zi > 0 else -1
        nq_e = nq.loc[date, "open"]
        nq_x = nq.loc[exit_date, "close"]
        es_e = es.loc[date, "open"]
        es_x = es.loc[exit_date, "close"]
        nq_gross = nq_side * (nq_x - nq_e) / nq_e * 10000.0
        es_gross = es_side * (es_x - es_e) / es_e * 10000.0
        gross_bps = (nq_gross + es_gross) / 2.0
        cost_bps = cost_of_pair("Index_CFD_major", 2)
        swap_bps = 2 * holding_days * FTMO_SWAP_BPS_PER_NIGHT["Index_CFD_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": exit_date, "asset": "NDX-SPX", "side": nq_side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 2 * holding_days})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# ---------------------------------------------------------------------------
# Universal evaluator: signal_at_T-1 vol-target then stats
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Modifications (mod #1 per parent, within L24 "3 mods max" budget)
# ---------------------------------------------------------------------------

def strat_ang_025_flip() -> tuple[pd.Series, dict]:
    """MOD #1 of ang_025: flip sign — go WITH the gap (continuation/momentum) instead of fade.
    Same filter, entry, exit, costs. Only `side` flipped."""
    trades = []
    for symbol in ["US500", "GER40"]:
        try:
            d = load_index_daily(symbol)
        except FileNotFoundError:
            continue
        d["close_prev"] = d["close"].shift(1)
        d["gap"] = (d["open"] - d["close_prev"]) / d["close_prev"]
        d["abs_gap_std30"] = d["gap"].abs().rolling(30, min_periods=10).std()
        for date, row in d.iterrows():
            if pd.isna(row["close_prev"]) or pd.isna(row["abs_gap_std30"]):
                continue
            thr = 1.5 * row["abs_gap_std30"]
            if abs(row["gap"]) < thr:
                continue
            # FLIPPED: go WITH the gap
            side = 1 if row["gap"] > 0 else -1
            entry = row["open"]
            # No reverse target; exit at close
            exit_px = row["close"]
            gross_bps = side * (exit_px - entry) / entry * 10000.0
            cost_bps = cost_of_pair("Index_CFD_major", 1)
            net_bps = gross_bps - cost_bps
            trades.append({"exit_date": date, "asset": symbol, "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "sign_flip: gap continuation instead of fade; exit at close"}


def strat_ang_024_flip() -> tuple[pd.Series, dict]:
    """MOD #1 of ang_024: flip sign — in low-vol regime (VIX<15), fade 2-day return instead of momentum."""
    d = load_index_daily("US500")
    vix = load_vix()["^VIX"].rename("vix")
    df = d.join(vix.reindex(d.index).ffill(), how="left")
    df["close_prev"] = df["close"].shift(1)
    df["close_prev3"] = df["close"].shift(3)
    df["mom_2d"] = (df["close_prev"] - df["close_prev3"]) / df["close_prev3"]
    df["vix_prev"] = df["vix"].shift(1)
    df["next_close"] = df["close"].shift(-1)
    trades = []
    for date, row in df.iterrows():
        if any(pd.isna(row[c]) for c in ["mom_2d", "vix_prev", "open", "next_close"]):
            continue
        if row["vix_prev"] >= 15:
            continue
        if abs(row["mom_2d"]) < 0.005:
            continue
        # FLIPPED: fade 2-day return
        side = -int(np.sign(row["mom_2d"]))
        entry = row["open"]
        exit_p = row["next_close"]
        gross_bps = side * (exit_p - entry) / entry * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        swap_bps = 2 * FTMO_SWAP_BPS_PER_NIGHT["Index_CFD_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        try:
            exit_date = df.index[df.index.get_loc(date) + 1]
        except (KeyError, IndexError):
            continue
        trades.append({"exit_date": exit_date, "asset": "US500", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 2})
    tr_df = pd.DataFrame(trades)
    all_dates = pd.date_range("2018-01-01", "2026-05-29", freq="B")
    daily = trades_to_daily_pnl(tr_df, all_dates)
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "sign_flip: fade 2-day return in low-vol regime"}


STRATEGIES = [
    ("ang_025", "Index overnight gap fill (US500+GER40)", strat_ang_025, "Index_CFD_major"),
    ("ang_019", "UK100 morning gap close", strat_ang_019, "Index_CFD_major"),
    ("lit_021", "Index opening-gap fade — Berkman 2012 (US500)", strat_lit_021, "Index_CFD_major"),
    ("lit_048", "Round-number bounce — EURUSD/USDJPY", strat_lit_048, "FX_major"),
    ("ang_017", "US500 lunch fade 11:30-13:30 ET", strat_ang_017, "Index_CFD_major"),
    ("ang_024", "US500 2-day momentum low-vol", strat_ang_024, "Index_CFD_major"),
    ("ang_047", "EURUSD-GBPUSD divergence pair", strat_ang_047, "FX_major"),
    ("ang_048", "US100-US500 ratio MR + VIX>18", strat_ang_048, "Index_CFD_major"),
    # Modifications (mod #1 of parent)
    ("ang_025_flip", "MOD: Index gap CONTINUATION (US500+GER40)", strat_ang_025_flip, "Index_CFD_major"),
    ("ang_024_flip", "MOD: US500 2-day REVERSAL low-vol", strat_ang_024_flip, "Index_CFD_major"),
]


def evaluate(sid: str, name: str, daily_pnl: pd.Series, meta: dict,
             rf_daily: pd.Series, sizing: str = "vol_target") -> StrategyResult:
    """Apply sizing scheme, compute all stats, run FTMO MC.

    sizing options:
    - "vol_target": daily vol-target 8%/yr, 63d lookback, max leverage 5x
    - "fixed": no leverage scaling — 1 unit per trade (FTMO-native sizing proxy)
    """
    res = StrategyResult(id=sid, name=name)
    res.n_trades = meta.get("n_trades", 0)
    res.notes = meta.get("caveat", "")
    if sizing == "fixed":
        res.notes = (res.notes + f" | sizing=FIXED 1x").strip(" |")

    # Keep zeros — proper Sharpe normalisation over calendar time.
    bdays = pd.date_range(daily_pnl.index.min(), daily_pnl.index.max(), freq="B")
    daily_pnl = daily_pnl.reindex(bdays).fillna(0.0)
    n_active = int((daily_pnl != 0).sum())
    if n_active < 30:
        res.notes = (res.notes + f" | n_active_trade_days={n_active}<30 — too sparse").strip(" |")
        res.n_days = n_active
        return res

    if sizing == "vol_target":
        daily_pnl_vt = vol_target(daily_pnl, target_annual=0.08, lookback=63)
        daily_pnl_vt = daily_pnl_vt.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    elif sizing == "fixed":
        daily_pnl_vt = daily_pnl.copy()
    else:
        raise ValueError(f"sizing must be 'vol_target' or 'fixed', got {sizing!r}")
    res.n_days = len(daily_pnl_vt)

    if res.n_days < 100:
        res.notes = (res.notes + " | post-voltarget n_days<100").strip(" |")
        return res

    # Win rate / wl ratio from raw trades
    trades_df = meta.get("trades_df", pd.DataFrame())
    if not trades_df.empty:
        wins = trades_df[trades_df["net_bps"] > 0]
        losses = trades_df[trades_df["net_bps"] < 0]
        res.win_rate = len(wins) / len(trades_df) if len(trades_df) > 0 else 0.0
        avg_win = wins["net_bps"].mean() if len(wins) > 0 else 0.0
        avg_loss = abs(losses["net_bps"].mean()) if len(losses) > 0 else 1.0
        res.wl_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        res.mean_bps_per_trade_gross = trades_df["gross_bps"].mean()
        res.mean_bps_per_trade_net = trades_df["net_bps"].mean()
        avg_cost = trades_df["cost_bps"].mean() + abs(trades_df["swap_bps"].mean())
        gross_abs = abs(trades_df["gross_bps"].mean()) if len(trades_df) > 0 else 0.0
        res.cost_gate_ratio = gross_abs / avg_cost if avg_cost > 0 else 0.0

    # Sharpe (gross is daily_pnl pre-vol target; net is post)
    res.sharpe_gross = _sharpe(daily_pnl.values, n_per_year=252)
    res.sharpe_net = _sharpe(daily_pnl_vt.values, n_per_year=252)

    # Excess returns vs RF
    rf_aligned = rf_daily.reindex(daily_pnl_vt.index).ffill()
    excess = daily_pnl_vt - rf_aligned.fillna(0.0)
    res.sharpe_excess = _sharpe(excess.values, n_per_year=252)
    res.hac_t_excess = hac_tstat(excess.values, lag=6)
    res.hac_t_net = hac_tstat(daily_pnl_vt.values, lag=6)

    # Equity & MaxDD
    equity = (1.0 + daily_pnl_vt).cumprod()
    res.max_dd_pct = max_drawdown_pct(equity.values)

    # Block bootstrap CI on Sharpe
    bs = block_bootstrap_sharpe(daily_pnl_vt.values, n_boot=2000, block_len=5)
    res.bootstrap_sr_mean = bs["sr_mean"]
    res.bootstrap_sr_lo95 = bs["sr_lo95"]
    res.bootstrap_sr_hi95 = bs["sr_hi95"]

    # DSR — single-trial perspective; AMTP handles cross-strategy multiplicity
    skew = float(pd.Series(daily_pnl_vt).skew())
    kurt = float(pd.Series(daily_pnl_vt).kurtosis() + 3)  # excess + 3 = raw kurtosis
    dsr = deflated_sharpe(res.sharpe_excess, len(daily_pnl_vt), n_trials=1,
                          skew=skew, kurt=kurt)
    res.dsr = dsr["dsr"]
    res.dsr_passes = dsr["dsr_passes"]

    # Walk-forward ≥5 folds
    wf = walk_forward_folds(excess, n_folds=5, min_train_years=2.0)
    res.wf_n_folds = len(wf)
    if wf:
        pass_count = sum(1 for f in wf if f["sr_test"] > 0)
        sign_count = sum(1 for f in wf if f["sign_consistent"])
        res.wf_pass_rate = pass_count / len(wf)
        res.wf_sign_consistent_pct = sign_count / len(wf)

    # FTMO Monte Carlo
    ftmo_res = ftmo_montecarlo(daily_pnl_vt, n_runs=3000, max_days_per_phase=365)
    res.ftmo_p_pass_p1 = ftmo_res.p_pass_p1
    res.ftmo_p_pass_p1_p2 = ftmo_res.p_pass_p1_p2
    res.ftmo_p_bust = ftmo_res.p_bust_dll + ftmo_res.p_bust_mll
    res.ftmo_median_days_p1 = ftmo_res.median_days_pass_p1

    # Gates (apply BEFORE AMTP; AMTP applied at run_all)
    res.research_pass = (res.sharpe_excess > 0.7 and res.max_dd_pct > -0.25
                         and res.wf_pass_rate > 0.50)
    res.propfirm_pass = (res.sharpe_excess > 1.0 and res.max_dd_pct > -0.10
                         and res.wf_pass_rate > 0.60)
    return res


def run_all():
    rf_daily = load_rf_daily()
    results = []
    for sid, name, fn, asset_class in STRATEGIES:
        print(f"\n[{sid}] {name}")
        try:
            daily_pnl, meta = fn()
            print(f"  n_trades raw: {meta['n_trades']}")
            r = evaluate(sid, name, daily_pnl, meta, rf_daily)
            # save trade-level for inspection
            if "trades_df" in meta and not meta["trades_df"].empty:
                meta["trades_df"].to_csv(RESULTS_DIR / f"trades_{sid}.csv", index=False)
            daily_pnl.to_csv(RESULTS_DIR / f"daily_pnl_{sid}.csv", header=["pnl_frac"])
            print(f"  SR_excess={r.sharpe_excess:.2f}  MaxDD={r.max_dd_pct*100:.1f}%  "
                  f"WF_pass={r.wf_pass_rate*100:.0f}%  HAC_t={r.hac_t_excess:.2f}  "
                  f"DSR={r.dsr:.2f}  p_pass_FTMO={r.ftmo_p_pass_p1*100:.1f}%")
        except Exception as e:
            import traceback; traceback.print_exc()
            r = StrategyResult(id=sid, name=name, notes=f"ERROR: {e}")
        results.append(r)

    # AMTP — Bonferroni across 8 tests on the excess-return HAC t-stat
    t_stats = [r.hac_t_excess for r in results]
    p_corrected = amtp_bonferroni(t_stats, alpha=0.05)
    for r, p in zip(results, p_corrected):
        r.amtp_p_value = p

    # Save aggregate CSV
    df = pd.DataFrame([asdict(r) for r in results])
    df = df.sort_values("sharpe_excess", ascending=False)
    out_csv = RESULTS_DIR / "summary_top10_rigorous.csv"
    df.to_csv(out_csv, index=False)
    print(f"\nSaved: {out_csv}")

    # Print compact summary table
    cols = ["id", "n_trades", "n_days", "sharpe_excess", "max_dd_pct",
            "wf_pass_rate", "hac_t_excess", "dsr", "amtp_p_value",
            "ftmo_p_pass_p1", "ftmo_p_pass_p1_p2", "research_pass", "propfirm_pass",
            "cost_gate_ratio"]
    print("\n=== SUMMARY (rigorous test) ===")
    print(df[cols].to_string(index=False))


if __name__ == "__main__":
    run_all()
