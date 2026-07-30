"""Fetch OHLC data needed for the month-end intraday/overnight decomposition.

Read-only w.r.t. the rest of the repo: everything lands in ../data/.
"""
from __future__ import annotations

import pathlib
import sys

import pandas as pd
import yfinance as yf

OUT = pathlib.Path(__file__).resolve().parent.parent / "data"
OUT.mkdir(parents=True, exist_ok=True)


def fetch_daily(ticker: str, start: str, end: str) -> pd.DataFrame:
    df = yf.download(ticker, start=start, end=end, interval="1d",
                     auto_adjust=False, progress=False, actions=True)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def main() -> None:
    daily = {
        "TLT": ("2002-07-01", "2026-07-25"),
        "IEF": ("2002-07-01", "2026-07-25"),
        "ZN=F": ("2000-01-01", "2026-07-25"),
        "ZB=F": ("2000-01-01", "2026-07-25"),
        "ZF=F": ("2000-01-01", "2026-07-25"),
        "SPY": ("2002-07-01", "2026-07-25"),
    }
    for tk, (s, e) in daily.items():
        df = fetch_daily(tk, s, e)
        name = tk.replace("=", "").replace(".", "")
        p = OUT / f"daily_{name}.parquet"
        df.to_parquet(p)
        print(f"{tk:6s} daily rows={len(df):5d} {df.index[0].date()} -> {df.index[-1].date()} cols={list(df.columns)}")

    # hourly (yfinance caps 60m history at ~730 days)
    for tk in ["ZN=F", "TLT"]:
        try:
            df = yf.download(tk, period="730d", interval="60m",
                             auto_adjust=False, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            name = tk.replace("=", "")
            df.to_parquet(OUT / f"h1_{name}.parquet")
            print(f"{tk:6s} 60m   rows={len(df):5d} {df.index[0]} -> {df.index[-1]}")
        except Exception as exc:  # pragma: no cover
            print(f"{tk} 60m FAILED: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
