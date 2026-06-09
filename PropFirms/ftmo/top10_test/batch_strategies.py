"""
Parameterized batch strategy factory for testing 100+ FTMO candidates.

Families:
- event_drift: pre-event drift (entry close T-1, exit at release)
- post_event_rev: post-event reversal (entry at release, exit 60-120min later)
- intraday_mom: intraday momentum/MR at specific time windows
- pair_mr: cross-asset pair mean reversion (z-score)
- gap_variant: open gap fade/continuation with threshold variants
- calendar: turn-of-month, day-of-week, holiday effects
- multi_event: stack multiple event types on single asset
"""
from __future__ import annotations

import glob
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from framework import FTMO_COST_BPS_RT, FTMO_SWAP_BPS_PER_NIGHT
from data_loaders import (
    load_index_m1, load_index_daily, load_eurusd_m5, load_fx_daily,
    load_vix, _strip_tz,
)

# ===========================================================================
# Cached data loaders
# ===========================================================================

_DATA_CACHE = {}

def _cache(key, fn):
    if key not in _DATA_CACHE:
        _DATA_CACHE[key] = fn()
    return _DATA_CACHE[key]


M5_INDICES_DIR = "<HOME>/Desktop/Algo_claude/data/panels/m5_indices"
DUKAS_M5_DIR = "<HOME>/Desktop/Algo_claude/Forex/data/cache/dukascopy_m5"
FTMO_RESEARCH_DIR = "<HOME>/Desktop/Algo_claude/data/ftmo_research"
NEWS_EVENTS_PATH = "<HOME>/Desktop/Algo_claude/Forex/research/archived/strategy_f2_asian_breakout/news_events_2020_2025.csv"


def get_m1(symbol: str) -> pd.DataFrame:
    return _cache(f"m1_{symbol}", lambda: load_index_m1(symbol).sort_index())


def get_m5_dukas(symbol: str) -> pd.DataFrame:
    def _load():
        files = sorted(glob.glob(f"{DUKAS_M5_DIR}/{symbol}_*_M5.parquet"))
        if not files:
            return pd.DataFrame()
        parts = [pd.read_parquet(p) for p in files]
        df = pd.concat(parts).sort_index()
        df.index = pd.to_datetime(df.index)
        df = _strip_tz(df)
        return df[~df.index.duplicated(keep="first")]
    return _cache(f"m5_dukas_{symbol}", _load)


def get_eurusd_m5() -> pd.DataFrame:
    return _cache("eurusd_m5", lambda: load_eurusd_m5())


def get_daily(symbol: str) -> pd.DataFrame:
    """Get daily OHLC for an instrument, preferring M1 → resample."""
    if symbol in {"US500", "US100", "US30", "GER40", "BTCUSD", "XAUUSD",
                  "AUDJPY", "AUDUSD", "EURGBP", "EURJPY", "EURUSD",
                  "GBPUSD", "NZDUSD", "USDCAD", "USDCHF", "USDJPY"}:
        def _make():
            df = get_m1(symbol)
            return df.resample("1D").agg({"open": "first", "high": "max",
                                          "low": "min", "close": "last"}).dropna()
        return _cache(f"daily_{symbol}", _make)
    # M5 dukas based
    if symbol in {"CADJPY", "EURCHF", "GBPJPY", "XAGUSD", "USOIL", "UKOIL", "NGAS", "UK100"}:
        def _make():
            df = get_m5_dukas(symbol)
            if df.empty:
                return pd.DataFrame()
            return df.resample("1D").agg({"open": "first", "high": "max",
                                          "low": "min", "close": "last"}).dropna()
        return _cache(f"daily_{symbol}", _make)
    return pd.DataFrame()


def get_events(event_type: str) -> pd.DataFrame:
    def _load():
        df = pd.read_csv(NEWS_EVENTS_PATH, comment="#")
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        return df[df["event_type"] == event_type][["date", "time_utc"]].copy()
    return _cache(f"events_{event_type}", _load)


def get_vix_d1() -> pd.DataFrame:
    return _cache("vix_d1", lambda: load_vix())


# ===========================================================================
# Helpers
# ===========================================================================

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


# ===========================================================================
# Spec
# ===========================================================================

@dataclass
class StratSpec:
    id: str
    name: str
    family: str
    asset_class: str
    params: dict = field(default_factory=dict)


# ===========================================================================
# Family handlers
# ===========================================================================

def _bar_at_time_or_close(intraday_df: pd.DataFrame, event_dt: pd.Timestamp,
                          max_lag_hours: float = 4) -> Optional[float]:
    bars = intraday_df[intraday_df.index >= event_dt]
    if len(bars) == 0:
        return None
    if (bars.index[0] - event_dt) > pd.Timedelta(hours=max_lag_hours):
        return None
    return float(bars.iloc[0]["open"])


def family_event_drift(params):
    """Pre-event drift: enter close T-1, exit at event release.
    params: event_type, instrument, side, hold_intraday_only, asset_class
    """
    event_type = params["event_type"]
    instrument = params["instrument"]
    side = params["side"]
    asset_class = params["asset_class"]

    events = get_events(event_type)
    if events.empty:
        return pd.DataFrame()
    daily = get_daily(instrument)
    if daily.empty:
        return pd.DataFrame()
    intraday = get_m1(instrument) if instrument in {"US500", "US100", "US30", "GER40",
        "AUDJPY", "AUDUSD", "EURGBP", "EURJPY", "EURUSD", "GBPUSD", "NZDUSD",
        "USDCAD", "USDCHF", "USDJPY", "XAUUSD", "BTCUSD"} else get_m5_dukas(instrument)

    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        prev_dates = daily.index[daily.index < ev_date]
        if len(prev_dates) == 0:
            continue
        t_minus_1 = prev_dates[-1]
        entry_px = daily.loc[t_minus_1, "close"]

        time_str = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = time_str.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        release_dt = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        exit_px = _bar_at_time_or_close(intraday, release_dt)
        if exit_px is None or pd.isna(entry_px) or entry_px <= 0:
            continue

        gross_bps = side * (exit_px - entry_px) / entry_px * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT.get(asset_class, -3.0)  # 1 night
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": instrument,
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    return pd.DataFrame(trades)


def family_post_event_rev(params):
    """Post-event reversal: enter at release, exit hold_hours later. Side reverses first-hour move.
    params: event_type, instrument, side, hold_hours, asset_class
    """
    event_type = params["event_type"]
    instrument = params["instrument"]
    hold_hours = params.get("hold_hours", 2)
    asset_class = params["asset_class"]

    events = get_events(event_type)
    if events.empty:
        return pd.DataFrame()
    intraday = get_m1(instrument) if instrument in {"US500", "US100", "US30", "GER40",
        "AUDJPY", "AUDUSD", "EURGBP", "EURJPY", "EURUSD", "GBPUSD", "NZDUSD",
        "USDCAD", "USDCHF", "USDJPY", "XAUUSD", "BTCUSD"} else get_m5_dukas(instrument)
    if intraday.empty:
        return pd.DataFrame()

    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        time_str = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = time_str.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        release_dt = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        # Entry at first bar AFTER release
        entry_px = _bar_at_time_or_close(intraday, release_dt + pd.Timedelta(minutes=1))
        # Get first-15min direction
        peek_dt = release_dt + pd.Timedelta(minutes=15)
        peek_px = _bar_at_time_or_close(intraday, peek_dt)
        # Exit at hold_hours later
        exit_dt = release_dt + pd.Timedelta(hours=hold_hours)
        exit_px = _bar_at_time_or_close(intraday, exit_dt)
        if any(x is None or pd.isna(x) for x in [entry_px, peek_px, exit_px]):
            continue
        # Use the first-15min direction as predictor, then FADE
        direction = np.sign(peek_px - entry_px)
        if direction == 0:
            continue
        side = -int(direction)  # FADE post-event impulse
        # Re-entry at peek_px (15 min post-release)
        gross_bps = side * (exit_px - peek_px) / peek_px * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        net_bps = gross_bps - cost_bps  # intraday, no swap
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": instrument,
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    return pd.DataFrame(trades)


def family_intraday_mom(params):
    """Intraday signal-window then trade-window.
    params: instrument, sig_hh_mm_start, sig_hh_mm_end, trade_end_hh_mm,
            threshold, side_fn ('mom' or 'fade'), asset_class.

    Signal: P(sig_end) - P(sig_start) / P(sig_start)
    Entry: at sig_end (same instant as signal end → no look-ahead)
    Exit: at trade_end
    """
    instrument = params["instrument"]
    sig_start = params["sig_start"]  # (hour, minute)
    sig_end = params["sig_end"]
    trade_end = params["trade_end"]
    threshold = params["threshold"]
    side_dir = params["side_dir"]  # 'mom' (continuation) or 'fade' (reversal)
    asset_class = params["asset_class"]

    df = get_m1(instrument) if instrument in {"US500", "US100", "US30", "GER40",
        "AUDJPY", "AUDUSD", "EURGBP", "EURJPY", "EURUSD", "GBPUSD", "NZDUSD",
        "USDCAD", "USDCHF", "USDJPY", "XAUUSD", "BTCUSD"} else get_m5_dukas(instrument)
    if df.empty:
        return pd.DataFrame()
    h = df.index.hour
    m = df.index.minute

    mask_s = (h == sig_start[0]) & (m == sig_start[1])
    mask_e = (h == sig_end[0]) & (m == sig_end[1])
    mask_x = (h == trade_end[0]) & (m == trade_end[1])

    def _per_date_open(mask):
        sub = df[mask].copy()
        if sub.empty:
            return pd.Series(dtype=float)
        sub["date"] = sub.index.normalize()
        return sub.groupby("date")["open"].first()

    sig_start_px = _per_date_open(mask_s)
    sig_end_px = _per_date_open(mask_e)
    exit_px_s = _per_date_open(mask_x)

    trades = []
    for date in sig_start_px.index:
        e1 = sig_start_px.get(date); en = sig_end_px.get(date); ex = exit_px_s.get(date)
        if any(pd.isna(x) for x in [e1, en, ex]):
            continue
        mom = (en - e1) / e1
        if abs(mom) < threshold:
            continue
        sig_sign = int(np.sign(mom))
        side = sig_sign if side_dir == "mom" else -sig_sign
        gross_bps = side * (ex - en) / en * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": instrument, "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    return pd.DataFrame(trades)


def family_pair_mr(params):
    """Pair mean reversion: z-score of return divergence.
    params: asset_a, asset_b, lookback_ret, lookback_z, z_threshold,
            holding_days, asset_class_a, asset_class_b.
    """
    a = params["asset_a"]; b = params["asset_b"]
    lookback_r = params["lookback_ret"]
    lookback_z = params["lookback_z"]
    z_thr = params["z_threshold"]
    hold = params["holding_days"]
    cls_a = params["asset_class_a"]; cls_b = params["asset_class_b"]

    da = get_daily(a); db = get_daily(b)
    if da.empty or db.empty:
        return pd.DataFrame()
    common = da.index.intersection(db.index)
    if len(common) < lookback_z + 30:
        return pd.DataFrame()
    da = da.loc[common]; db = db.loc[common]
    ra = (da["close"] / da["close"].shift(lookback_r) - 1.0)
    rb = (db["close"] / db["close"].shift(lookback_r) - 1.0)
    div = ra - rb
    z = (div - div.rolling(lookback_z, min_periods=20).mean()) / div.rolling(lookback_z, min_periods=20).std()
    z = z.shift(1)

    trades = []
    for i, date in enumerate(common):
        zi = z.get(date)
        if pd.isna(zi) or abs(zi) < z_thr:
            continue
        if i + hold >= len(common):
            break
        exit_date = common[i + hold]
        a_side = -1 if zi > 0 else 1  # a over-performed → short a
        b_side = +1 if zi > 0 else -1
        ae = da.loc[date, "open"]; ax = da.loc[exit_date, "close"]
        be = db.loc[date, "open"]; bx = db.loc[exit_date, "close"]
        a_gross = a_side * (ax - ae) / ae * 10000.0
        b_gross = b_side * (bx - be) / be * 10000.0
        gross_bps = (a_gross + b_gross) / 2.0
        cost_bps = FTMO_COST_BPS_RT[cls_a] + FTMO_COST_BPS_RT[cls_b]
        swap_bps = hold * (FTMO_SWAP_BPS_PER_NIGHT.get(cls_a, -3.0)
                            + FTMO_SWAP_BPS_PER_NIGHT.get(cls_b, -3.0))
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": exit_date, "asset": f"{a}-{b}", "side": a_side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": hold * 2})
    return pd.DataFrame(trades)


def family_gap_variant(params):
    """Gap fade/continuation with parametric threshold.
    params: instrument, gap_threshold_sigma, side_dir ('fade'/'cont'),
            exit_mode ('close' or 'fill'), asset_class.
    """
    inst = params["instrument"]
    gap_thr = params["gap_threshold_sigma"]
    side_dir = params["side_dir"]
    exit_mode = params["exit_mode"]
    asset_class = params["asset_class"]

    d = get_daily(inst)
    if d.empty:
        return pd.DataFrame()
    d["close_prev"] = d["close"].shift(1)
    d["gap"] = (d["open"] - d["close_prev"]) / d["close_prev"]
    d["abs_gap_std30"] = d["gap"].abs().rolling(30, min_periods=10).std()
    trades = []
    for date, row in d.iterrows():
        if pd.isna(row["close_prev"]) or pd.isna(row["abs_gap_std30"]):
            continue
        thr = gap_thr * row["abs_gap_std30"]
        if abs(row["gap"]) < thr:
            continue
        sign_gap = 1 if row["gap"] > 0 else -1
        side = sign_gap if side_dir == "cont" else -sign_gap
        entry = row["open"]
        if exit_mode == "fill":
            target = row["close_prev"]
            if side == -1:
                target_hit = row["low"] <= target
                stop = entry + abs(row["gap"]) * entry
                stop_hit = row["high"] >= stop
            else:
                target_hit = row["high"] >= target
                stop = entry - abs(row["gap"]) * entry
                stop_hit = row["low"] <= stop
            if target_hit and stop_hit:
                exit_px = stop
            elif target_hit:
                exit_px = target
            elif stop_hit:
                exit_px = stop
            else:
                exit_px = row["close"]
        else:
            exit_px = row["close"]
        gross_bps = side * (exit_px - entry) / entry * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        net_bps = gross_bps - cost_bps
        trades.append({"exit_date": date, "asset": inst, "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": 0.0, "net_bps": net_bps, "n_nights": 0})
    return pd.DataFrame(trades)


def family_calendar(params):
    """Calendar seasonal: turn-of-month or day-of-week effect.
    params: instrument, kind ('tom'/'eom'/'dow_mon'/'dow_fri'), side, asset_class.
    """
    inst = params["instrument"]
    kind = params["kind"]
    side = params["side"]
    asset_class = params["asset_class"]

    d = get_daily(inst)
    if d.empty:
        return pd.DataFrame()
    d = d.copy()
    d["day_of_month"] = d.index.day
    d["dow"] = d.index.dayofweek

    if kind == "tom":  # last 3 trading days of month + first 3
        # Use 4-day window around month-end
        is_active = (d["day_of_month"] >= 27) | (d["day_of_month"] <= 3)
    elif kind == "eom":  # last 3 trading days only
        is_active = d["day_of_month"] >= 28
    elif kind == "dow_mon":
        is_active = d["dow"] == 0
    elif kind == "dow_fri":
        is_active = d["dow"] == 4
    elif kind == "dow_tue":
        is_active = d["dow"] == 1
    else:
        return pd.DataFrame()

    d["next_close"] = d["close"].shift(-1)
    trades = []
    for date, row in d[is_active].iterrows():
        if pd.isna(row["next_close"]):
            continue
        entry, exit_p = row["open"], row["next_close"]
        gross_bps = side * (exit_p - entry) / entry * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT.get(asset_class, -3.0)
        net_bps = gross_bps - cost_bps + swap_bps
        try:
            idx = d.index.get_loc(date)
            if idx + 1 >= len(d):
                continue
            exit_date = d.index[idx + 1]
        except (KeyError, IndexError):
            continue
        trades.append({"exit_date": exit_date, "asset": inst, "side": side,
                       "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    return pd.DataFrame(trades)


def family_multi_event(params):
    """Stack multiple event types on single asset.
    params: event_types (list), instrument, side, asset_class.
    """
    types = params["event_types"]
    instrument = params["instrument"]
    side = params["side"]
    asset_class = params["asset_class"]

    all_events = []
    for et in types:
        evs = get_events(et)
        if not evs.empty:
            all_events.append(evs)
    if not all_events:
        return pd.DataFrame()
    events = pd.concat(all_events).drop_duplicates(subset=["date"]).sort_values("date")

    daily = get_daily(instrument)
    if daily.empty:
        return pd.DataFrame()
    intraday = get_m1(instrument) if instrument in {"US500", "US100", "US30", "GER40",
        "AUDJPY", "AUDUSD", "EURGBP", "EURJPY", "EURUSD", "GBPUSD", "NZDUSD",
        "USDCAD", "USDCHF", "USDJPY", "XAUUSD", "BTCUSD"} else get_m5_dukas(instrument)

    trades = []
    for _, ev in events.iterrows():
        ev_date = ev["date"]
        prev_dates = daily.index[daily.index < ev_date]
        if len(prev_dates) == 0:
            continue
        t_minus_1 = prev_dates[-1]
        entry_px = daily.loc[t_minus_1, "close"]
        time_str = ev["time_utc"] if pd.notna(ev["time_utc"]) else "13:30"
        try:
            hh, mm = time_str.split(":")
        except (ValueError, AttributeError):
            hh, mm = "13", "30"
        release_dt = pd.Timestamp(ev_date) + pd.Timedelta(hours=int(hh), minutes=int(mm))
        exit_px = _bar_at_time_or_close(intraday, release_dt)
        if exit_px is None or pd.isna(entry_px) or entry_px <= 0:
            continue
        gross_bps = side * (exit_px - entry_px) / entry_px * 10000.0
        cost_bps = FTMO_COST_BPS_RT[asset_class]
        swap_bps = FTMO_SWAP_BPS_PER_NIGHT.get(asset_class, -3.0)
        net_bps = gross_bps - cost_bps + swap_bps
        trades.append({"exit_date": pd.Timestamp(ev_date), "asset": instrument,
                       "side": side, "gross_bps": gross_bps, "cost_bps": cost_bps,
                       "swap_bps": swap_bps, "net_bps": net_bps, "n_nights": 1})
    return pd.DataFrame(trades)


# ===========================================================================
# Strategy spec list (~100)
# ===========================================================================

def build_specs():
    specs = []

    # --- EVENT DRIFT (pre-event) — 35 variants ---
    event_inst_map = [
        # event_type, instrument, asset_class, default_long_side
        ("FOMC", "US500", "Index_CFD_major", 1),
        ("FOMC", "US100", "Index_CFD_major", 1),
        ("FOMC", "US30", "Index_CFD_major", 1),
        ("FOMC", "EURUSD", "FX_major", 1),
        ("FOMC", "USDJPY", "FX_major", -1),
        ("FOMC", "XAUUSD", "Metals_CFD_gold", 1),
        ("FOMC", "GBPUSD", "FX_major", 1),
        ("FOMC", "GER40", "Index_CFD_major", 1),
        ("NFP_US", "US500", "Index_CFD_major", 1),
        ("NFP_US", "EURUSD", "FX_major", -1),
        ("NFP_US", "USDJPY", "FX_major", 1),
        ("NFP_US", "GBPUSD", "FX_major", -1),
        ("NFP_US", "XAUUSD", "Metals_CFD_gold", -1),
        ("CPI_US", "US500", "Index_CFD_major", 1),
        ("CPI_US", "EURUSD", "FX_major", 1),
        ("CPI_US", "USDJPY", "FX_major", -1),
        ("CPI_US", "XAUUSD", "Metals_CFD_gold", 1),
        ("ECB_RATE", "EURUSD", "FX_major", 1),
        ("ECB_RATE", "EURGBP", "FX_cross", 1),
        ("ECB_RATE", "EURJPY", "FX_cross", 1),
        ("BOE_RATE", "GBPUSD", "FX_major", 1),
        ("BOE_RATE", "EURGBP", "FX_cross", -1),
        ("BOJ_RATE", "USDJPY", "FX_major", 1),
        ("BOJ_RATE", "EURJPY", "FX_cross", 1),
    ]
    for et, inst, cls, side_long in event_inst_map:
        # Long side
        specs.append(StratSpec(
            id=f"ed_{et.lower()}_{inst}_LO",
            name=f"Pre-{et} {inst} LO",
            family="event_drift", asset_class=cls,
            params=dict(event_type=et, instrument=inst, side=side_long, asset_class=cls)))
        # Short side
        specs.append(StratSpec(
            id=f"ed_{et.lower()}_{inst}_SS",
            name=f"Pre-{et} {inst} SS",
            family="event_drift", asset_class=cls,
            params=dict(event_type=et, instrument=inst, side=-side_long, asset_class=cls)))

    # --- POST-EVENT REVERSAL — 12 variants ---
    post_event_set = [
        ("FOMC", "US500", "Index_CFD_major"),
        ("FOMC", "EURUSD", "FX_major"),
        ("FOMC", "USDJPY", "FX_major"),
        ("FOMC", "XAUUSD", "Metals_CFD_gold"),
        ("NFP_US", "EURUSD", "FX_major"),
        ("NFP_US", "USDJPY", "FX_major"),
        ("NFP_US", "US500", "Index_CFD_major"),
        ("CPI_US", "US500", "Index_CFD_major"),
        ("CPI_US", "EURUSD", "FX_major"),
        ("ECB_RATE", "EURUSD", "FX_major"),
        ("BOE_RATE", "GBPUSD", "FX_major"),
        ("BOJ_RATE", "USDJPY", "FX_major"),
    ]
    for et, inst, cls in post_event_set:
        for hh in [1, 2, 4]:
            specs.append(StratSpec(
                id=f"per_{et.lower()}_{inst}_{hh}h",
                name=f"Post-{et} {inst} fade {hh}h",
                family="post_event_rev", asset_class=cls,
                params=dict(event_type=et, instrument=inst, hold_hours=hh, asset_class=cls)))

    # --- INTRADAY MOM/FADE — variants ---
    # Use h:m windows. Signal end == entry start (no look-ahead).
    intraday_set = [
        # (asset, sig_start, sig_end, trade_end, threshold, side_dir, asset_class)
        ("US500", (14, 30), (15, 30), (16, 30), 0.003, "mom", "Index_CFD_major"),
        ("US500", (14, 30), (15, 30), (16, 30), 0.003, "fade", "Index_CFD_major"),
        ("US500", (15, 0), (16, 30), (18, 0), 0.003, "mom", "Index_CFD_major"),
        ("US500", (15, 0), (16, 30), (18, 0), 0.003, "fade", "Index_CFD_major"),
        ("US500", (16, 30), (18, 0), (19, 30), 0.003, "fade", "Index_CFD_major"),
        ("US100", (14, 30), (15, 30), (16, 30), 0.004, "mom", "Index_CFD_major"),
        ("US100", (14, 30), (15, 30), (16, 30), 0.004, "fade", "Index_CFD_major"),
        ("US100", (15, 0), (16, 30), (18, 0), 0.004, "mom", "Index_CFD_major"),
        ("US100", (15, 0), (16, 30), (18, 0), 0.004, "fade", "Index_CFD_major"),
        ("GER40", (14, 30), (15, 30), (16, 30), 0.005, "mom", "Index_CFD_major"),
        ("GER40", (14, 30), (15, 30), (16, 30), 0.005, "fade", "Index_CFD_major"),
        ("EURUSD", (13, 0), (14, 0), (15, 0), 0.002, "mom", "FX_major"),
        ("EURUSD", (13, 0), (14, 0), (15, 0), 0.002, "fade", "FX_major"),
        ("USDJPY", (1, 0), (2, 0), (3, 0), 0.002, "mom", "FX_major"),
        ("XAUUSD", (14, 30), (15, 30), (16, 30), 0.003, "mom", "Metals_CFD_gold"),
        ("XAUUSD", (14, 30), (15, 30), (16, 30), 0.003, "fade", "Metals_CFD_gold"),
    ]
    for asset, ss, se, te, thr, sd, cls in intraday_set:
        specs.append(StratSpec(
            id=f"im_{asset}_{ss[0]:02d}{ss[1]:02d}_{se[0]:02d}{se[1]:02d}_{sd}",
            name=f"{asset} intraday {sd} {ss[0]:02d}:{ss[1]:02d}-{se[0]:02d}:{se[1]:02d}",
            family="intraday_mom", asset_class=cls,
            params=dict(instrument=asset, sig_start=ss, sig_end=se, trade_end=te,
                        threshold=thr, side_dir=sd, asset_class=cls)))

    # --- PAIR MR — 12 pairs ---
    pair_set = [
        # asset_a, asset_b, lookback_ret, lookback_z, z_thr, hold_days, class_a, class_b
        ("US100", "US500", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("US500", "GER40", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("US100", "GER40", 5, 60, 1.5, 3, "Index_CFD_major", "Index_CFD_major"),
        ("EURUSD", "USDJPY", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("EURUSD", "GBPUSD", 5, 60, 2.0, 3, "FX_major", "FX_major"),
        ("GBPUSD", "USDJPY", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("AUDUSD", "NZDUSD", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("USDCAD", "USDCHF", 5, 60, 1.5, 3, "FX_major", "FX_major"),
        ("XAUUSD", "XAGUSD", 5, 60, 1.5, 5, "Metals_CFD_gold", "Metals_CFD_gold"),
        ("USOIL", "UKOIL", 3, 60, 1.5, 3, "Commodity_CFD", "Commodity_CFD"),
        ("EURJPY", "GBPJPY", 5, 60, 1.5, 3, "FX_cross", "FX_cross"),
        ("EURUSD", "EURGBP", 5, 60, 1.5, 3, "FX_major", "FX_cross"),
    ]
    for a, b, lr, lz, zt, hd, ca, cb in pair_set:
        specs.append(StratSpec(
            id=f"pr_{a}_{b}_z{zt}_h{hd}",
            name=f"Pair MR {a}-{b} z>{zt} hold={hd}d",
            family="pair_mr", asset_class=ca,
            params=dict(asset_a=a, asset_b=b, lookback_ret=lr, lookback_z=lz,
                        z_threshold=zt, holding_days=hd, asset_class_a=ca, asset_class_b=cb)))

    # --- GAP VARIANTS — 12 ---
    gap_set = [
        # instrument, threshold, side_dir, exit_mode, asset_class
        ("US500", 1.5, "fade", "close", "Index_CFD_major"),
        ("US500", 1.5, "cont", "close", "Index_CFD_major"),
        ("US500", 2.0, "fade", "close", "Index_CFD_major"),
        ("US500", 2.0, "cont", "close", "Index_CFD_major"),
        ("US100", 1.5, "fade", "close", "Index_CFD_major"),
        ("US100", 1.5, "cont", "close", "Index_CFD_major"),
        ("US100", 2.0, "cont", "close", "Index_CFD_major"),
        ("GER40", 1.5, "cont", "close", "Index_CFD_major"),
        ("GER40", 2.0, "cont", "close", "Index_CFD_major"),
        ("XAUUSD", 1.5, "cont", "close", "Metals_CFD_gold"),
        ("XAUUSD", 1.5, "fade", "close", "Metals_CFD_gold"),
        ("USDJPY", 1.5, "cont", "close", "FX_major"),
    ]
    for inst, thr, sd, em, cls in gap_set:
        specs.append(StratSpec(
            id=f"gv_{inst}_t{thr}_{sd}",
            name=f"Gap {sd} {inst} {thr}σ",
            family="gap_variant", asset_class=cls,
            params=dict(instrument=inst, gap_threshold_sigma=thr,
                        side_dir=sd, exit_mode=em, asset_class=cls)))

    # --- CALENDAR — 10 ---
    cal_set = [
        ("US500", "tom", 1, "Index_CFD_major"),
        ("US500", "eom", 1, "Index_CFD_major"),
        ("US500", "dow_mon", -1, "Index_CFD_major"),  # Monday effect (historical negative)
        ("US500", "dow_fri", 1, "Index_CFD_major"),
        ("US500", "dow_tue", 1, "Index_CFD_major"),
        ("EURUSD", "eom", -1, "FX_major"),  # EOM USD rebalance
        ("EURUSD", "tom", 1, "FX_major"),
        ("XAUUSD", "tom", 1, "Metals_CFD_gold"),
        ("US100", "tom", 1, "Index_CFD_major"),
        ("GER40", "tom", 1, "Index_CFD_major"),
    ]
    for inst, kind, side, cls in cal_set:
        specs.append(StratSpec(
            id=f"cal_{inst}_{kind}_{side:+d}",
            name=f"Calendar {kind} {inst} side={side}",
            family="calendar", asset_class=cls,
            params=dict(instrument=inst, kind=kind, side=side, asset_class=cls)))

    # --- MULTI-EVENT STACKING — 8 ---
    multi_set = [
        # event_types, instrument, side, asset_class
        (["FOMC", "NFP_US", "CPI_US"], "US500", 1, "Index_CFD_major"),
        (["FOMC", "NFP_US", "CPI_US"], "US100", 1, "Index_CFD_major"),
        (["FOMC", "NFP_US", "CPI_US"], "XAUUSD", 1, "Metals_CFD_gold"),
        (["FOMC", "NFP_US", "CPI_US"], "EURUSD", 1, "FX_major"),
        (["FOMC", "NFP_US", "CPI_US"], "EURUSD", -1, "FX_major"),
        (["FOMC", "ECB_RATE"], "EURUSD", 1, "FX_major"),
        (["FOMC", "BOE_RATE"], "GBPUSD", 1, "FX_major"),
        (["FOMC", "BOJ_RATE"], "USDJPY", 1, "FX_major"),
    ]
    for ets, inst, side, cls in multi_set:
        ets_str = "_".join(et.replace("_US","").replace("_RATE","")[:3].lower() for et in ets)
        specs.append(StratSpec(
            id=f"me_{ets_str}_{inst}_{side:+d}",
            name=f"Multi-event {'+'.join(ets)} {inst} side={side}",
            family="multi_event", asset_class=cls,
            params=dict(event_types=ets, instrument=inst, side=side, asset_class=cls)))

    return specs


FAMILY_HANDLERS = {
    "event_drift": family_event_drift,
    "post_event_rev": family_post_event_rev,
    "intraday_mom": family_intraday_mom,
    "pair_mr": family_pair_mr,
    "gap_variant": family_gap_variant,
    "calendar": family_calendar,
    "multi_event": family_multi_event,
}
