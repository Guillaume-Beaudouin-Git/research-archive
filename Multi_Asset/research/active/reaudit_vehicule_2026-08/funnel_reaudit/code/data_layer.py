"""Data layer for the funnel re-audit — two CLOCKS, one price feed per symbol.

The funnel's original inputs were deleted by the 2026-06-10 P2 cleanup:
    data/panels/m5_indices/{US500,US100,US30,GER40,...}_M1.csv   (EET, mislabelled UTC)
    data/ftmo_research/EURUSD_m5.parquet
    Forex/data/cache/dukascopy_m5/*.parquet
Surviving supersets of the SAME MT5 feed:
    data/panels/m5_indices/m1_panel.parquet        -> US500, US100, US30 (EET)
    data/panels/m5_indices/{GER40,XAUUSD,EURUSD}_m1_panel.parquet (EET)
    data/deep_history_utc/*_M1.csv                 -> TRUE UTC, repaired

Clock convention (defect #2 of the pre-registration):
  clock="eet"  reproduces the funnel: bar labels are Europe/Athens local time
               but the code treats them as UTC.
  clock="utc"  repairs it: SAME price series, labels moved to true UTC.

Verified empirically (2026-08-13): panel index == UTC + 2h in winter,
+3h in summer, i.e. Europe/Athens. Median |close diff| vs deep_history_utc
at the matching offset = 0.4 pip on EURUSD (different broker feed, same clock).
"""
from __future__ import annotations

import os
from functools import lru_cache

import numpy as np
import pandas as pd

PANEL_DIR = "<HOME>/Desktop/Algo_claude/data/panels/m5_indices"
CACHE_DIR = ("<SCRATCH>"
             "9fd32b98-b3ee-47bf-93c1-b7c5a1ac70a6/scratchpad/cache")
VIX_PATH = "<HOME>/Desktop/Algo_claude/data/panels/vix.csv"
NEWS_EVENTS_PATH = ("<HOME>/Desktop/Algo_claude/Forex/research/archived/"
                    "strategy_f2_asian_breakout/news_events_2020_2025.csv")

PANEL_SYMBOLS = {"US500", "US100", "US30", "US2000", "GER40", "XAUUSD", "EURUSD", "BTCUSD"}
DEEP_SYMBOLS = {"USDJPY", "GBPUSD", "EURGBP", "EURJPY", "AUDUSD", "NZDUSD",
                "USDCAD", "USDCHF", "XAGUSD", "USOIL", "UKOIL"}
UNAVAILABLE = {"GBPJPY", "UK100", "CADJPY", "EURCHF"}

_M1_CACHE: dict = {}


@lru_cache(maxsize=1)
def _us_panel() -> pd.DataFrame:
    return pd.read_parquet(f"{PANEL_DIR}/m1_panel.parquet")


def _load_panel_eet(symbol: str) -> pd.DataFrame:
    """EET-labelled M1 from the surviving MT5 panels (index named timestamp_utc,
    but the clock is Europe/Athens — this is defect #2 at its source)."""
    if symbol in {"US500", "US100", "US30", "US2000"}:
        df = _us_panel()[symbol].dropna(how="all")
    else:
        df = pd.read_parquet(f"{PANEL_DIR}/{symbol}_m1_panel.parquet")
    df = df[["open", "high", "low", "close"]].astype("float64").sort_index()
    return df[~df.index.duplicated(keep="first")]


def _load_deep_utc(symbol: str) -> pd.DataFrame:
    p = f"{CACHE_DIR}/{symbol}_m1_utc.parquet"
    if not os.path.exists(p):
        return pd.DataFrame()
    df = pd.read_parquet(p).astype("float64")
    return df[~df.index.duplicated(keep="first")].sort_index()


def _eet_to_utc(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return (idx.tz_localize("Europe/Athens", ambiguous="NaT", nonexistent="NaT")
               .tz_convert("UTC").tz_localize(None))


def _utc_to_eet(idx: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return idx.tz_localize("UTC").tz_convert("Europe/Athens").tz_localize(None)


def get_m1(symbol: str, clock: str = "eet") -> pd.DataFrame:
    """M1 OHLC. clock='eet' = funnel-as-was; clock='utc' = same prices, true labels."""
    key = (symbol, clock)
    if key in _M1_CACHE:
        return _M1_CACHE[key]
    if symbol in UNAVAILABLE:
        out = pd.DataFrame()
    elif symbol in PANEL_SYMBOLS:
        df = _load_panel_eet(symbol)
        if clock == "utc":
            idx = _eet_to_utc(df.index)
            df = df[idx.notna()].copy()
            df.index = idx[idx.notna()]
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="first")]
        out = df
    elif symbol in DEEP_SYMBOLS:
        df = _load_deep_utc(symbol)
        if not df.empty and clock == "eet":
            df = df.copy()
            df.index = _utc_to_eet(df.index)
            df = df.sort_index()
            df = df[~df.index.duplicated(keep="first")]
        out = df
    else:
        out = pd.DataFrame()
    _M1_CACHE[key] = out
    return out


def get_daily(symbol: str, clock: str = "eet") -> pd.DataFrame:
    key = ("D", symbol, clock)
    if key in _M1_CACHE:
        return _M1_CACHE[key]
    df = get_m1(symbol, clock)
    if df.empty:
        out = pd.DataFrame()
    else:
        out = df.resample("1D").agg({"open": "first", "high": "max",
                                     "low": "min", "close": "last"}).dropna()
    _M1_CACHE[key] = out
    return out


@lru_cache(maxsize=None)
def get_events(event_type: str) -> pd.DataFrame:
    df = pd.read_csv(NEWS_EVENTS_PATH, comment="#")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    return df[df["event_type"] == event_type][["date", "time_utc"]].copy()


@lru_cache(maxsize=1)
def get_vix() -> pd.DataFrame:
    df = pd.read_csv(VIX_PATH)
    df["Date"] = pd.to_datetime(df["Date"])
    return df.set_index("Date").sort_index()


# ---------------------------------------------------------------------------
# Deployed overnight sleeve (reference for the decorrelation test, P1-R2)
# US100 + GER40 LONG, Mondays and Tuesdays.
# GER40 in 17:35 CET -> out 09:00 CET (next session)
# US100 in 22:05 CET -> out 15:30 CET (next session)
# Europe/Athens (panel clock) == Europe/Paris (CET) + 1h, all year.
# ---------------------------------------------------------------------------

SLEEVE_LEGS = [("GER40", (17, 35), (9, 0)), ("US100", (22, 5), (15, 30))]


def _bar_open_at(df: pd.DataFrame, day: pd.Timestamp, hh: int, mm: int,
                 max_lag_min: int = 90):
    t0 = day + pd.Timedelta(hours=hh, minutes=mm)
    sub = df.index[(df.index >= t0) & (df.index <= t0 + pd.Timedelta(minutes=max_lag_min))]
    if len(sub) == 0:
        return None, None
    return float(df.loc[sub[0], "open"]), sub[0]


def overnight_sleeve_daily(cost_bps_rt: float = 0.9) -> pd.Series:
    """Daily (exit-date indexed) fractional return of the deployed sleeve,
    equal-weight across its two legs, net of round-trip cost and measured swap."""
    swap = {"US100": -2.126, "GER40": -1.564}          # long, bps/night (spec_v22)
    frames = {}
    for sym, entry, exit_ in SLEEVE_LEGS:
        m1 = get_m1(sym, "eet")
        if m1.empty:
            continue
        cet = m1.copy()
        cet.index = cet.index - pd.Timedelta(hours=1)   # Athens -> Paris
        days = pd.Index(sorted(set(cet.index.normalize())))
        rows = []
        for d in days:
            if d.dayofweek not in (0, 1):               # Monday, Tuesday entries
                continue
            e_px, e_ts = _bar_open_at(cet, d, *entry)
            if e_px is None:
                continue
            nxt = d + pd.Timedelta(days=1)
            x_px, x_ts = _bar_open_at(cet, nxt, *exit_)
            if x_px is None or e_px <= 0:
                continue
            gross = (x_px - e_px) / e_px * 10000.0
            rows.append((x_ts.normalize(), (gross - cost_bps_rt + swap[sym]) / 10000.0))
        if rows:
            s = pd.DataFrame(rows, columns=["d", "r"]).groupby("d")["r"].sum()
            frames[sym] = s
    if not frames:
        return pd.Series(dtype=float)
    df = pd.DataFrame(frames)
    idx = pd.date_range(df.index.min(), df.index.max(), freq="B")
    return df.reindex(idx).fillna(0.0).mean(axis=1)
