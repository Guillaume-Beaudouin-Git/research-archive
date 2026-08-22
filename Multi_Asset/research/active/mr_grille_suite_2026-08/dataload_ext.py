"""
Thin extension layer for mr_grille_suite_2026-08. Reuses (read-only import, no
duplication) the prior grid's dataload/engine_lib and the shared tracked engine.
Adds: raw-M1-with-index-map loader (for Axis A/B M1 resolution), and nothing else.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]                      # .../Algo_claude
PRIOR = REPO / "Multi_Asset" / "research" / "active" / "mr_intraday_grille_2026-08"
sys.path.insert(0, str(PRIOR))
sys.path.insert(0, str(REPO / "yt_strategy_replications"))

import dataload as DL0          # prior grid's loader (session filter, costs, caches)
import engine_lib as E0         # prior grid's conditioner/entry/vol-target primitives
from engine import indicators as ind
from engine import backtest as BT
from engine import stats as S

CACHE = HERE / "_cache"
CACHE.mkdir(exist_ok=True)

INSTRUMENTS = DL0.ALL
INDICES = DL0.INDICES
COST_RT_BPS = DL0.COST_RT_BPS


def load15(sym: str) -> pd.DataFrame:
    return DL0.load(sym, bar="15min")


def load_native(sym: str, bar: str) -> pd.DataFrame:
    """bar in {'1min','3min','15min','60min'} — reuses the prior grid's session-filtered,
    gitignored parquet cache (built fresh here if the frequency wasn't cached before)."""
    return DL0.build(sym, bar=bar)


def bars_per_year(df: pd.DataFrame) -> float:
    return float(df.groupby("session_date").size().median()) * 252.0


def m1_arrays(sym: str):
    """Session-filtered 1-min OHLC as numpy arrays + timestamp index (int64-ns for
    searchsorted mapping, and the DatetimeIndex itself for building exit_time), cached."""
    df = load_native(sym, "1min")
    ts_dt = df.index
    ts = ts_dt.values.astype("datetime64[ns]").astype(np.int64)
    o = df["open"].to_numpy(float); h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float); c = df["close"].to_numpy(float)
    return ts, ts_dt, o, h, l, c


def map_15to1(ts15: np.ndarray, ts1: np.ndarray) -> np.ndarray:
    """For each 15-min bar timestamp, the exact matching row index in the 1-min array
    (searchsorted exact match; -1 if the minute is missing from the 1-min series)."""
    idx = np.searchsorted(ts1, ts15)
    idx = np.clip(idx, 0, len(ts1) - 1)
    ok = ts1[idx] == ts15
    out = np.where(ok, idx, -1)
    return out
