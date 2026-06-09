"""
Path 1 mods + Path 2 next-10 strategies.

Path 1 mods (within L24 "3 mods max" budget):
- ang_025_flip mod #2: gap > 2.5σ
- ang_025_flip mod #3: gap aligned with prev-day direction
- ang_047 mod #1: |z| > 2.0
- ang_047 mod #2: 1-day hold (less swap)
- ang_047 mod #3: VIX > 18 conditioning

Path 2 next-10 (event-driven family, different from top-10):
- lit_012: Pre-NFP USD drift (Brusa 2019) — EURUSD short T-1 → NFP release
- lit_013: Pre-FOMC equity drift (Lucca-Moench 2015) — US500 long T-1 → FOMC release
- ang_006: EURUSD pre-FOMC drift — mirror of lit_013 on FX
- ang_018: GER40 post-US-open lag fade (15:30-17:00 CET)
- lit_020: Intraday momentum US500 (Heston-Korajczyk-Sadka)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from framework import FTMO_COST_BPS_RT, FTMO_SWAP_BPS_PER_NIGHT
from data_loaders import (
    load_index_m1, load_index_daily, load_eurusd_m5,
    load_fx_daily, load_vix, _strip_tz,
)

NEWS_EVENTS_PATH = "<HOME>/Desktop/Algo_claude/Forex/research/archived/strategy_f2_asian_breakout/news_events_2020_2025.csv"


def cost_of_pair(asset_class: str, n_legs: int = 1) -> float:
    return n_legs * FTMO_COST_BPS_RT[asset_class]


def trades_to_daily_pnl(trades: pd.DataFrame, all_dates: pd.DatetimeIndex) -> pd.Series:
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


# ---------------------------------------------------------------------------
# Event calendar
# ---------------------------------------------------------------------------

def load_event_dates(event_type: str) -> pd.DataFrame:
    df = pd.read_csv(NEWS_EVENTS_PATH, comment="#")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["dt_utc"] = pd.to_datetime(
        df["date"].dt.strftime("%Y-%m-%d") + " " + df["time_utc"].fillna("00:00"),
        errors="coerce")
    return df[df["event_type"] == event_type][["date", "dt_utc", "time_utc"]].copy()


# ===========================================================================
# Path 1 — Modifications
# ===========================================================================

def strat_ang_025_flip_mod2():
    """ang_025_flip MOD #2: tighter filter gap > 2.5σ."""
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
            thr = 2.5 * row["abs_gap_std30"]
            if abs(row["gap"]) < thr:
                continue
            side = 1 if row["gap"] > 0 else -1
            entry, exit_px = row["open"], row["close"]
            gross_bps = side * (exit_px - entry) / entry * 10000.0
            cost_bps = cost_of_pair("Index_CFD_major", 1)
            net_bps = gross_bps - cost_bps
            trades.append({"exit_date": date, "asset": symbol, "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "MOD #2: gap > 2.5σ (tighter filter)"}


def strat_ang_025_flip_mod3():
    """ang_025_flip MOD #3: gap aligned with prev-day return direction."""
    trades = []
    for symbol in ["US500", "GER40"]:
        try:
            d = load_index_daily(symbol)
        except FileNotFoundError:
            continue
        d["close_prev"] = d["close"].shift(1)
        d["gap"] = (d["open"] - d["close_prev"]) / d["close_prev"]
        d["abs_gap_std30"] = d["gap"].abs().rolling(30, min_periods=10).std()
        d["prev_day_return"] = d["close"].shift(1) / d["open"].shift(1) - 1.0
        for date, row in d.iterrows():
            if any(pd.isna(row[c]) for c in ["close_prev", "abs_gap_std30", "prev_day_return"]):
                continue
            thr = 1.5 * row["abs_gap_std30"]
            if abs(row["gap"]) < thr:
                continue
            if np.sign(row["gap"]) != np.sign(row["prev_day_return"]):
                continue
            side = 1 if row["gap"] > 0 else -1
            entry, exit_px = row["open"], row["close"]
            gross_bps = side * (exit_px - entry) / entry * 10000.0
            cost_bps = cost_of_pair("Index_CFD_major", 1)
            net_bps = gross_bps - cost_bps
            trades.append({"exit_date": date, "asset": symbol, "side": side,
                           "gross_bps": gross_bps, "cost_bps": cost_bps,
                           "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "MOD #3: gap aligned with prev-day direction"}


def _ang_047_core(z_threshold: float, holding_days: int, vix_floor: float = 0.0):
    """Generic core for ang_047 mods."""
    eu = load_fx_daily("EURUSD")
    gb = load_fx_daily("GBPUSD")
    if eu.empty or gb.empty:
        return pd.DataFrame()
    common = eu.index.intersection(gb.index)
    eu = eu.loc[common]; gb = gb.loc[common]
    vix_lag = None
    if vix_floor > 0:
        vix = load_vix()["^VIX"]
        vix_lag = vix.reindex(common).ffill().shift(1)
    eu["r5"] = (eu["close"] / eu["close"].shift(5) - 1.0)
    gb["r5"] = (gb["close"] / gb["close"].shift(5) - 1.0)
    div = eu["r5"] - gb["r5"]
    div_z = (div - div.rolling(60, min_periods=20).mean()) / div.rolling(60, min_periods=20).std()
    div_z = div_z.shift(1)
    trades = []
    for i, date in enumerate(common):
        z = div_z.get(date)
        if pd.isna(z) or abs(z) < z_threshold:
            continue
        if vix_lag is not None:
            v = vix_lag.get(date)
            if pd.isna(v) or v < vix_floor:
                continue
        if i + holding_days >= len(common):
            break
        exit_date = common[i + holding_days]
        eu_side = -1 if z > 0 else 1
        gb_side = +1 if z > 0 else -1
        eu_e = eu.loc[date, "open"]; eu_x = eu.loc[exit_date, "close"]
        gb_e = gb.loc[date, "open"]; gb_x = gb.loc[exit_date, "close"]
        eu_gross = eu_side * (eu_x - eu_e) / eu_e * 10000.0
        gb_gross = gb_side * (gb_x - gb_e) / gb_e * 10000.0
        gross_bps = (eu_gross + gb_gross) / 2.0
        cost_bps = cost_of_pair("FX_major", 2)
        swap_bps = 2 * holding_days * FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": exit_date, "asset": "EUR-GBP", "side": eu_side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 2 * holding_days})
    return pd.DataFrame(trades)


def strat_ang_047_mod1():
    tr_df = _ang_047_core(z_threshold=2.0, holding_days=3)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "MOD #1: |z| > 2.0 (tighter)"}


def strat_ang_047_mod2():
    tr_df = _ang_047_core(z_threshold=1.5, holding_days=1)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "MOD #2: 1-day hold (swap 6→2 leg-nights)"}


def strat_ang_047_mod3():
    tr_df = _ang_047_core(z_threshold=1.5, holding_days=3, vix_floor=18.0)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df,
                   "modification": "MOD #3: VIX > 18 conditioning"}


# ===========================================================================
# Path 2 — next-10 event-driven
# ===========================================================================

def _find_exit_at_time(intraday_df: pd.DataFrame, event_dt: pd.Timestamp):
    """Return first M5/M1 bar open at or after event_dt."""
    bars = intraday_df[intraday_df.index >= event_dt]
    if len(bars) == 0 or (bars.index[0] - event_dt) > pd.Timedelta(hours=4):
        return None
    return bars.iloc[0]["open"]


def strat_lit_012():
    """Pre-NFP USD drift — Brusa 2019.
    Short EURUSD at close T-1, exit at NFP release 13:30 UTC."""
    eu_m5 = load_eurusd_m5()
    if eu_m5.empty:
        return pd.Series(0.0, index=pd.date_range("2020-01-01", "2025-12-31", freq="B")), \
               {"n_trades": 0, "trades_df": pd.DataFrame()}
    daily_e = eu_m5.resample("1D").agg({"open": "first", "high": "max",
                                         "low": "min", "close": "last"}).dropna()
    nfp = load_event_dates("NFP_US")
    trades = []
    for _, row in nfp.iterrows():
        nfp_date = row["date"]
        prev_dates = daily_e.index[daily_e.index < nfp_date]
        if len(prev_dates) == 0:
            continue
        t_minus_1 = prev_dates[-1]
        entry_px = daily_e.loc[t_minus_1, "close"]
        # NFP release at 13:30 UTC
        release_dt = pd.Timestamp(nfp_date) + pd.Timedelta(hours=13, minutes=30)
        exit_px = _find_exit_at_time(eu_m5, release_dt)
        if exit_px is None:
            continue
        side = -1  # short EURUSD = long USD (pre-NFP USD drift positive per Brusa)
        gross_bps = side * (exit_px - entry_px) / entry_px * 10000.0
        cost_bps = cost_of_pair("FX_major", 1)
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": pd.Timestamp(nfp_date), "asset": "EURUSD",
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2020-01-01", "2025-12-31", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


def strat_lit_013():
    """Pre-FOMC equity drift — Lucca-Moench 2015.
    Long US500 at close T-1, exit at FOMC release time."""
    us500 = load_index_m1("US500")
    daily_500 = us500.resample("1D").agg({"open": "first", "high": "max",
                                           "low": "min", "close": "last"}).dropna()
    fomc = load_event_dates("FOMC")
    trades = []
    for _, row in fomc.iterrows():
        fomc_date = row["date"]
        prev_dates = daily_500.index[daily_500.index < fomc_date]
        if len(prev_dates) == 0:
            continue
        t_minus_1 = prev_dates[-1]
        entry_px = daily_500.loc[t_minus_1, "close"]
        time_str = row["time_utc"] if pd.notna(row["time_utc"]) else "19:00"
        try:
            hours, mins = time_str.split(":")
        except (ValueError, AttributeError):
            hours, mins = "19", "00"
        release_dt = pd.Timestamp(fomc_date) + pd.Timedelta(hours=int(hours), minutes=int(mins))
        exit_px = _find_exit_at_time(us500, release_dt)
        if exit_px is None:
            continue
        side = 1
        gross_bps = side * (exit_px - entry_px) / entry_px * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT["Index_CFD_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": pd.Timestamp(fomc_date), "asset": "US500",
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


def strat_ang_006():
    """EURUSD pre-FOMC drift — mirror of lit_013 on FX. Long EURUSD (USD weakens pre-FOMC)."""
    eu_m5 = load_eurusd_m5()
    if eu_m5.empty:
        return pd.Series(0.0, index=pd.date_range("2020-01-01", "2025-12-31", freq="B")), \
               {"n_trades": 0, "trades_df": pd.DataFrame()}
    daily_e = eu_m5.resample("1D").agg({"open": "first", "high": "max",
                                         "low": "min", "close": "last"}).dropna()
    fomc = load_event_dates("FOMC")
    trades = []
    for _, row in fomc.iterrows():
        fomc_date = row["date"]
        prev_dates = daily_e.index[daily_e.index < fomc_date]
        if len(prev_dates) == 0:
            continue
        t_minus_1 = prev_dates[-1]
        entry_px = daily_e.loc[t_minus_1, "close"]
        time_str = row["time_utc"] if pd.notna(row["time_utc"]) else "19:00"
        try:
            hours, mins = time_str.split(":")
        except (ValueError, AttributeError):
            hours, mins = "19", "00"
        release_dt = pd.Timestamp(fomc_date) + pd.Timedelta(hours=int(hours), minutes=int(mins))
        exit_px = _find_exit_at_time(eu_m5, release_dt)
        if exit_px is None:
            continue
        side = 1
        gross_bps = side * (exit_px - entry_px) / entry_px * 10000.0
        cost_bps = cost_of_pair("FX_major", 1)
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT["FX_major"]
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": pd.Timestamp(fomc_date), "asset": "EURUSD",
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2020-01-01", "2025-12-31", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


def strat_ang_018():
    """GER40 post-US-open lag fade (15:30-17:00 CET = 14:30-16:00 UTC summer-equiv).
    Signal: GER40 14:30-15:30 UTC return; fade if |return| > 0.5%; exit 16:00 UTC."""
    try:
        ger40 = load_index_m1("GER40")
    except FileNotFoundError:
        p = "<HOME>/Desktop/Algo_claude/data/panels/m5_indices/GER40_m1_panel.parquet"
        ger40 = pd.read_parquet(p)
        ger40 = _strip_tz(ger40)
        if "open" not in ger40.columns:
            return pd.Series(0.0, index=pd.date_range("2020-01-01", "2026-05-29", freq="B")), \
                   {"n_trades": 0, "trades_df": pd.DataFrame()}
    ger40 = ger40.sort_index()
    ger40 = ger40[~ger40.index.duplicated(keep="first")]
    h = ger40.index.hour
    ger40["hour"] = h
    ger40["date"] = ger40.index.normalize()
    open_1430 = ger40[ger40["hour"] == 14].groupby("date")["open"].first()
    close_1530 = ger40[ger40["hour"] == 15].groupby("date")["close"].last()
    open_1530 = ger40[ger40["hour"] == 15].groupby("date")["open"].first()
    close_1600 = ger40[ger40["hour"] == 16].groupby("date")["close"].last()
    trades = []
    for date in open_1430.index:
        e1 = open_1430.get(date); e2 = close_1530.get(date)
        en = open_1530.get(date); ex = close_1600.get(date)
        if any(pd.isna(x) for x in [e1, e2, en, ex]):
            continue
        mom = (e2 - e1) / e1
        if abs(mom) < 0.005:
            continue
        side = -int(np.sign(mom))  # fade
        gross_bps = side * (ex - en) / en * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": "GER40", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2020-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


def strat_lit_020():
    """Heston-Korajczyk-Sadka intraday momentum US500.
    Signal: 14:30-16:30 UTC (09:30-11:30 ET) return; continue at 17:00-18:00 UTC."""
    us500 = load_index_m1("US500")
    us500 = us500.sort_index()
    us500["hour"] = us500.index.hour
    us500["date"] = us500.index.normalize()
    open_1430 = us500[us500["hour"] == 14].groupby("date")["open"].first()
    close_1630 = us500[us500["hour"] == 16].groupby("date")["close"].last()
    open_1700 = us500[us500["hour"] == 17].groupby("date")["open"].first()
    close_1800 = us500[us500["hour"] == 18].groupby("date")["close"].last()
    trades = []
    for date in open_1430.index:
        e1 = open_1430.get(date); e2 = close_1630.get(date)
        en = open_1700.get(date); ex = close_1800.get(date)
        if any(pd.isna(x) for x in [e1, e2, en, ex]):
            continue
        mom = (e2 - e1) / e1
        if abs(mom) < 0.003:
            continue
        side = int(np.sign(mom))  # continuation
        gross_bps = side * (ex - en) / en * 10000.0
        cost_bps = cost_of_pair("Index_CFD_major", 1)
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": "US500", "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    tr_df = pd.DataFrame(trades)
    daily = trades_to_daily_pnl(tr_df, pd.date_range("2018-01-01", "2026-05-29", freq="B"))
    return daily, {"n_trades": len(tr_df), "trades_df": tr_df}


# Registry for run_tests_v2.py
NEW_STRATEGIES = [
    # Path 1 — Mods
    ("ang_025_flip_mod2", "MOD: gap continuation 2.5σ", strat_ang_025_flip_mod2, "Index_CFD_major"),
    ("ang_025_flip_mod3", "MOD: gap aligned with prev-day", strat_ang_025_flip_mod3, "Index_CFD_major"),
    ("ang_047_mod1", "MOD: EUR-GBP div |z|>2.0", strat_ang_047_mod1, "FX_major"),
    ("ang_047_mod2", "MOD: EUR-GBP div hold=1d", strat_ang_047_mod2, "FX_major"),
    ("ang_047_mod3", "MOD: EUR-GBP div VIX>18", strat_ang_047_mod3, "FX_major"),
    # Path 2 — next-10 event-driven
    ("lit_012", "Pre-NFP USD drift (Brusa 2019)", strat_lit_012, "FX_major"),
    ("lit_013", "Pre-FOMC equity drift (Lucca-Moench 2015)", strat_lit_013, "Index_CFD_major"),
    ("ang_006", "EURUSD pre-FOMC drift (mirror)", strat_ang_006, "FX_major"),
    ("ang_018", "GER40 post-US-open lag fade", strat_ang_018, "Index_CFD_major"),
    ("lit_020", "Intraday momentum US500 (Heston-Korajczyk)", strat_lit_020, "Index_CFD_major"),
]
