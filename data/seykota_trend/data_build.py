"""
Build daily OHLC dataset for the Seykota trend-following replication.

Sources (local, pre-audited):
  - deep_history_utc/{US500,US100,XAUUSD,USOIL}_M1.csv  -> resampled to daily UTC bars
  - momentum_universe.csv                                -> BTC, ETH daily OHLCV (UTC)

Output:
  seykota_trend/daily/{SYMBOL}.parquet  with columns [open, high, low, close]

Conventions:
  - Daily bar = UTC calendar day aggregation of M1 (open=first, high=max, low=min, close=last).
  - Days with fewer than MIN_BARS M1 bars are dropped (holiday stubs / bad days).
  - All series validated: OHLC coherence, positivity, monotonic index, max gap report.
"""

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]          # .../data
OUT = Path(__file__).resolve().parent / "daily"
OUT.mkdir(exist_ok=True)

M1_SYMBOLS = ["US500", "US100", "XAUUSD", "USOIL"]
MIN_BARS_PER_DAY = 60  # drop stub days (<1h of quotes)


def resample_m1(symbol: str) -> pd.DataFrame:
    fp = ROOT / "deep_history_utc" / f"{symbol}_M1.csv"
    df = pd.read_csv(
        fp,
        usecols=["timestamp_utc", "open", "high", "low", "close"],
        dtype={c: "float64" for c in ["open", "high", "low", "close"]},
    )
    ts = pd.to_datetime(df.pop("timestamp_utc"), format="%Y.%m.%d %H:%M:%S", utc=True)
    df.index = ts
    daily = df.resample("1D").agg(
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n=("close", "size"),
    )
    daily = daily[daily["n"] >= MIN_BARS_PER_DAY].drop(columns="n").dropna()
    daily.index = daily.index.tz_localize(None)
    return daily


def load_crypto(symbol: str) -> pd.DataFrame:
    df = pd.read_csv(ROOT / "momentum_universe.csv", parse_dates=["date"])
    df = df[df["symbol"] == symbol].set_index("date").sort_index()
    df = df[["open", "high", "low", "close"]].astype(float)
    # Early rows can carry open/high/low == 0 placeholders -> drop until clean
    bad = (df[["open", "high", "low", "close"]] <= 0).any(axis=1)
    df = df[~bad]
    return df


def validate(symbol: str, df: pd.DataFrame) -> dict:
    assert df.index.is_monotonic_increasing and df.index.is_unique, symbol
    assert (df > 0).all().all(), f"{symbol}: non-positive prices"
    ohlc_ok = (
        (df["high"] >= df[["open", "close"]].max(axis=1) - 1e-9)
        & (df["low"] <= df[["open", "close"]].min(axis=1) + 1e-9)
    )
    gaps = df.index.to_series().diff().dt.days.dropna()
    return {
        "symbol": symbol,
        "start": str(df.index[0].date()),
        "end": str(df.index[-1].date()),
        "rows": len(df),
        "ohlc_violations": int((~ohlc_ok).sum()),
        "max_gap_days": int(gaps.max()),
        "gaps_gt_5d": int((gaps > 5).sum()),
    }


def main() -> None:
    summary = []
    for sym in M1_SYMBOLS:
        d = resample_m1(sym)
        summary.append(validate(sym, d))
        d.to_parquet(OUT / f"{sym}.parquet")
        print(f"{sym}: {len(d)} daily bars  {d.index[0].date()} -> {d.index[-1].date()}")
    for sym in ["BTC", "ETH"]:
        d = load_crypto(sym)
        summary.append(validate(sym, d))
        d.to_parquet(OUT / f"{sym}.parquet")
        print(f"{sym}: {len(d)} daily bars  {d.index[0].date()} -> {d.index[-1].date()}")
    pd.DataFrame(summary).to_csv(OUT / "data_quality.csv", index=False)
    print(pd.DataFrame(summary).to_string(index=False))


if __name__ == "__main__":
    main()
