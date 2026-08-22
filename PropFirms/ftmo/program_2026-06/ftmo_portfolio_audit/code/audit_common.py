"""
audit_common.py — shared primitives for the INDEPENDENT FTMO portfolio audit.

Clean-room reimplementation. Does NOT import the author's engine
(PropFirms/ftmo_alpha_program/...) or trust cached sleeve series.
READ-ONLY on all source data.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
DAILY = ROOT / "research/s076_replication/daily"          # EET & UTC daily parquets (built read-only by prior task)
DEEP = ROOT / "data/deep_history_utc"                      # TRUE UTC M1 (verified Gate 1)
PANEL = ROOT / "data/panels/m5_indices"                   # EET/EEST M1 (verified Gate 1)
BINANCE = PANEL / "binance"                               # genuinely-UTC crypto M1
FMT = "%Y.%m.%d %H:%M:%S"

# price decimals -> point size = 10^-decimals (from cfd_costs.py DECIMALS, extended)
DECIMALS = {"EURUSD": 5, "GBPUSD": 5, "AUDUSD": 5, "NZDUSD": 5, "USDCHF": 5,
            "USDJPY": 3, "US100": 2, "US500": 2, "US30": 2, "GER40": 2,
            "XAUUSD": 2, "BTCUSD": 2}
FX = {"EURUSD", "GBPUSD", "AUDUSD", "NZDUSD", "USDCHF", "USDJPY"}


def point_size(sym: str) -> float:
    return 10.0 ** (-DECIMALS[sym])


# ── data loaders ──────────────────────────────────────────────────────────────
def load_daily(sym: str, tz: str = "EET") -> pd.DataFrame:
    """Daily OHLC + spread (MT5 points) from the prior task's parquets. tz in {EET,UTC}."""
    df = pd.read_parquet(DAILY / f"{sym}_{tz}.parquet")
    df = df[df.index.dayofweek < 5]                        # drop weekend sliver-days (UTC build artifact)
    return df.sort_index()


def load_m1(sym: str, source: str) -> pd.DataFrame:
    """
    1-min OHLC(+spread) with a DatetimeIndex in TRUE UTC.
      source='deep'    : data/deep_history_utc (already true UTC)
      source='panel'   : data/panels/m5_indices (EET/EEST -> converted to true UTC)
      source='binance' : data/panels/m5_indices/binance (already UTC, ISO stamps)
    """
    if source == "deep":
        p = DEEP / f"{sym}_M1.csv"
        df = pd.read_csv(p, usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
        ts = pd.to_datetime(df["timestamp_utc"], format=FMT, errors="coerce")
        df = df.drop(columns="timestamp_utc").assign(ts=ts).dropna(subset=["ts"]).set_index("ts")
    elif source == "panel":
        p = PANEL / f"{sym}_M1.csv"
        df = pd.read_csv(p, usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
        ts = pd.to_datetime(df["timestamp_utc"], format=FMT, errors="coerce")
        df = df.drop(columns="timestamp_utc").assign(ts=ts).dropna(subset=["ts"]).set_index("ts")
        # EET/EEST naive -> localize Europe/Bucharest -> true UTC -> naive UTC
        idx = df.index.tz_localize("Europe/Bucharest", ambiguous="NaT", nonexistent="shift_forward")
        df = df[idx.notna()]
        df.index = idx[idx.notna()].tz_convert("UTC").tz_localize(None)
    elif source == "binance":
        p = BINANCE / f"{sym}_M1.csv"
        df = pd.read_csv(p, usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
        df = df.assign(ts=pd.to_datetime(df["timestamp_utc"], errors="coerce")).drop(columns="timestamp_utc")
        df = df.dropna(subset=["ts"]).set_index("ts")
    else:
        raise ValueError(source)
    return df[~df.index.duplicated(keep="first")].sort_index()


# ── RSI(2) Wilder ─────────────────────────────────────────────────────────────
def rsi(close: pd.Series, n: int = 2) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0.0)
    dn = (-d).clip(lower=0.0)
    au = up.ewm(alpha=1.0 / n, adjust=False).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50)


# ── metrics ───────────────────────────────────────────────────────────────────
def metrics(ret: pd.Series, periods: int = 252) -> dict:
    r = ret.dropna().values
    if len(r) < 2:
        return {"n_days": int(len(r))}
    mu, sd = r.mean(), r.std(ddof=1)
    pos, neg = r[r > 0], r[r < 0]
    from scipy import stats
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return {
        "n_days": int(len(r)),
        "mean_daily": float(mu),
        "sigma_daily": float(sd),
        "daily_sharpe": float(mu / sd) if sd > 0 else 0.0,
        "ann_sharpe": float(mu / sd * np.sqrt(periods)) if sd > 0 else 0.0,
        "ann_return": float(mu * periods),
        "win_rate": float((r > 0).mean()),
        "win_loss_ratio": float(abs(pos.mean() / neg.mean())) if len(pos) and len(neg) and neg.mean() != 0 else np.nan,
        "excess_kurtosis": float(stats.kurtosis(r, fisher=True, bias=False)),
        "skew": float(stats.skew(r, bias=False)),
        "max_dd": float((peak - eq).max()),
        "worst_day": float(r.min()),
        "best_day": float(r.max()),
    }


def vol_target(gross: pd.Series, sigma_target: float = 0.01, lookback: int = 63,
               cap: float = 4.0) -> pd.Series:
    """Causal daily vol-targeting: scale by sigma_target / lagged rolling std, capped."""
    trail = gross.rolling(lookback).std().shift(1)
    scale = (sigma_target / trail).clip(upper=cap).fillna(0.0)
    return gross * scale


def per_year_sharpe(ret: pd.Series) -> dict:
    out = {}
    for y, g in ret.groupby(ret.index.year):
        r = g.values
        out[int(y)] = float(r.mean() / r.std(ddof=1) * np.sqrt(252)) if r.std(ddof=1) > 0 else 0.0
    return out
