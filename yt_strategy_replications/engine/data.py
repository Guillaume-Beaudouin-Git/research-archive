"""
Data loaders and cache builders.

Crypto: Binance spot 5m klines (downloaded from data.binance.vision) -> per-pair
parquet. Gold: the repo's canonical true-UTC XAUUSD M1 series resampled to H1
(and optionally 1m kept for intrabar fill resolution in Module 3).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJ = Path(__file__).resolve().parents[1]
REPO = PROJ.parent  # .../Algo_claude
CRYPTO_ZIPS = PROJ / "data_cache" / "crypto_5m" / "_zips"
CRYPTO_PARQUET = PROJ / "data_cache" / "crypto_5m"
GOLD_CACHE = PROJ / "data_cache" / "gold"
RAW_GOLD_CSV = REPO / "data" / "deep_history_utc" / "XAUUSD_M1.csv"

UNIVERSE = [
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT", "SOLUSDT",
    "DOGEUSDT", "LTCUSDT", "LINKUSDT", "UNIUSDT", "DOTUSDT", "AVAXUSDT",
    "TRXUSDT", "ATOMUSDT", "ETCUSDT", "BCHUSDT", "XLMUSDT", "FILUSDT",
]

_KLINE_COLS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
               "quote_volume", "count", "taker_base", "taker_quote", "ignore"]


# --------------------------------------------------------------------------- crypto
def build_crypto_parquet(pair: str) -> pd.DataFrame | None:
    """Concatenate a pair's monthly kline zips into a clean OHLCV parquet."""
    zips = sorted(CRYPTO_ZIPS.glob(f"{pair}-5m-*.zip"))
    frames = []
    for z in zips:
        try:
            with zipfile.ZipFile(z) as zf:
                raw = zf.read(zf.namelist()[0])
        except (zipfile.BadZipFile, OSError):
            continue
        d = pd.read_csv(io.BytesIO(raw), header=None, names=_KLINE_COLS,
                        usecols=[0, 1, 2, 3, 4, 5])
        frames.append(d)
    if not frames:
        return None
    df = pd.concat(frames, ignore_index=True)
    # 2025+ monthly files carry a header row -> coerce non-numeric open_time away
    ot = pd.to_numeric(df["open_time"], errors="coerce")
    df = df[ot.notna()].copy()
    ot = ot[ot.notna()].astype("int64").to_numpy()
    # Binance monthly dumps mix epoch units across months (ms / microseconds / ns).
    # Normalise everything to milliseconds before parsing.
    ot = np.where(ot >= 10 ** 17, ot // 10 ** 6,
                  np.where(ot >= 10 ** 14, ot // 10 ** 3, ot))
    df["open_time"] = ot
    df["ts"] = pd.to_datetime(df["open_time"], unit="ms", utc=True).dt.tz_localize(None)
    df = (df.drop_duplicates("ts").sort_values("ts").set_index("ts")
          [["open", "high", "low", "close", "volume"]].astype("float64"))
    CRYPTO_PARQUET.mkdir(parents=True, exist_ok=True)
    df.to_parquet(CRYPTO_PARQUET / f"{pair}.parquet")
    return df


def load_crypto(pair: str, start=None, end=None) -> pd.DataFrame:
    df = pd.read_parquet(CRYPTO_PARQUET / f"{pair}.parquet")
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


def available_pairs() -> list[str]:
    return sorted(p.stem for p in CRYPTO_PARQUET.glob("*.parquet"))


# --------------------------------------------------------------------------- gold
def build_gold_cache(timeframe: str = "1h", keep_1m: bool = False) -> pd.DataFrame:
    """Resample the canonical XAUUSD M1 (true UTC) to the requested timeframe."""
    GOLD_CACHE.mkdir(parents=True, exist_ok=True)
    usecols = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"]
    df = pd.read_csv(RAW_GOLD_CSV, usecols=usecols)
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    df = df.astype({"open": "float64", "high": "float64", "low": "float64",
                    "close": "float64", "tick_volume": "float64", "spread": "float64"})
    if keep_1m:
        df.to_parquet(GOLD_CACHE / "gold_1m.parquet")
    agg = (df.resample(timeframe)
           .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                 "tick_volume": "sum", "spread": "mean"})
           .dropna(subset=["open", "high", "low", "close"]))
    agg.to_parquet(GOLD_CACHE / f"gold_{timeframe}.parquet")
    return agg


def load_gold(timeframe: str = "1h", start=None, end=None) -> pd.DataFrame:
    df = pd.read_parquet(GOLD_CACHE / f"gold_{timeframe}.parquet")
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


DEEPHIST = REPO / "data" / "deep_history_utc"


def build_deephist_h1(symbol: str, timeframe: str = "1h") -> pd.DataFrame:
    """Resample any repo deep_history_utc M1 series (true UTC) to a timeframe.
    Used for the cross-instrument generalisation test in Module 2."""
    GOLD_CACHE.mkdir(parents=True, exist_ok=True)
    usecols = ["timestamp_utc", "open", "high", "low", "close", "tick_volume", "spread"]
    df = pd.read_csv(DEEPHIST / f"{symbol}_M1.csv", usecols=usecols)
    ts = pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df = df.drop(columns=["timestamp_utc"])
    df.index = ts
    df = df.astype({c: "float64" for c in ["open", "high", "low", "close", "tick_volume", "spread"]})
    agg = (df.resample(timeframe)
           .agg({"open": "first", "high": "max", "low": "min", "close": "last",
                 "tick_volume": "sum", "spread": "mean"})
           .dropna(subset=["open", "high", "low", "close"]))
    agg.to_parquet(GOLD_CACHE / f"{symbol}_{timeframe}.parquet")
    return agg


def load_h1(symbol: str, timeframe: str = "1h", start=None, end=None) -> pd.DataFrame:
    df = pd.read_parquet(GOLD_CACHE / f"{symbol}_{timeframe}.parquet")
    if start is not None:
        df = df[df.index >= pd.Timestamp(start)]
    if end is not None:
        df = df[df.index <= pd.Timestamp(end)]
    return df


def resample_ohlc(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    agg = {"open": "first", "high": "max", "low": "min", "close": "last"}
    if "volume" in df.columns:
        agg["volume"] = "sum"
    return df.resample(timeframe).agg(agg).dropna(subset=["open", "high", "low", "close"])
