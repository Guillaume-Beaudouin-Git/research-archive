"""
build_daily_commod.py — resample the FTMO-executable commodity M1 CSVs to daily bars.

Source: data/deep_history_utc/<SYM>_M1.csv (TRUE UTC, Dukascopy BID OHLC, schema
        timestamp_utc,open,high,low,close,tick_volume,spread,real_volume).
Output: research/paper_triage/cache/<SYM>_daily.parquet
        columns: date(index), open, high, low, close, spread_med, n_bars

Daily bar = UTC-calendar-day group: open=first, high=max, low=min, close=last,
spread_med=median(spread where spread>0), n_bars=count. Weekdays kept downstream.

Universe = the 6 commodities that are BOTH on disk AND FTMO-executable (ex-gold,
which is already in the FTMO-16). NGAS/COPPER/SUGAR/COTTON/OJUICE/DIESEL are NOT
FTMO instruments (ftmo_specs has only 21 tickers) -> non-deployable, excluded.
Read-only on source data; writes only under research/paper_triage/cache/.
"""
from __future__ import annotations
from pathlib import Path
import sys
import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
SRC = REPO / "data" / "deep_history_utc"
OUT = REPO / "research" / "paper_triage" / "cache"
OUT.mkdir(parents=True, exist_ok=True)

EXEC = ["USOIL", "UKOIL", "XAGUSD", "COCOA", "COFFEE", "SOYBEAN"]
# optional broader (NOT FTMO-executable) — phenomenon check only
BROAD = ["NGAS", "COPPER", "SUGAR", "COTTON", "OJUICE", "DIESEL"]


def resample_one(sym: str) -> pd.DataFrame:
    p = SRC / f"{sym}_M1.csv"
    if not p.exists():
        print(f"  [{sym}] MISSING {p}", flush=True)
        return None
    # read in chunks to bound memory on the 250-470MB files
    usecols = ["timestamp_utc", "open", "high", "low", "close", "spread"]
    dtypes = {"open": "float64", "high": "float64", "low": "float64",
              "close": "float64", "spread": "float64"}
    parts = []
    for chunk in pd.read_csv(p, usecols=usecols, dtype=dtypes, chunksize=2_000_000):
        ts = pd.to_datetime(chunk["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        chunk = chunk.assign(date=ts.dt.normalize()).dropna(subset=["date"])
        # vectorised positive-spread mean: NaN out non-positive, then sum/count per day
        chunk["sp_pos"] = chunk["spread"].where(chunk["spread"] > 0)
        g = chunk.groupby("date")
        agg = pd.DataFrame({
            "open": g["open"].first(),
            "high": g["high"].max(),
            "low": g["low"].min(),
            "close": g["close"].last(),
            "spread_sum": g["sp_pos"].sum(),       # NaN treated as 0
            "spread_cnt": g["sp_pos"].count(),     # counts non-NaN only
            "n_bars": g["close"].count(),          # bars/day (close has no NaN)
        })
        parts.append(agg)
    # merge chunk-day partials (a UTC day can straddle a 2M-row chunk boundary)
    allp = pd.concat(parts)
    out = pd.DataFrame({
        "open": allp.groupby(level=0)["open"].first(),
        "high": allp.groupby(level=0)["high"].max(),
        "low": allp.groupby(level=0)["low"].min(),
        "close": allp.groupby(level=0)["close"].last(),
        "n_bars": allp.groupby(level=0)["n_bars"].sum(),
        "spread_sum": allp.groupby(level=0)["spread_sum"].sum(),
        "spread_cnt": allp.groupby(level=0)["spread_cnt"].sum(),
    }).sort_index()
    out["spread_med"] = out["spread_sum"] / out["spread_cnt"].replace(0, np.nan)
    out = out.drop(columns=["spread_sum", "spread_cnt"])
    out.index.name = "date"
    return out.reset_index()


def main():
    syms = EXEC + (BROAD if "--broad" in sys.argv else [])
    rows = []
    for sym in syms:
        df = resample_one(sym)
        if df is None:
            continue
        df.to_parquet(OUT / f"{sym}_daily.parquet", index=False)
        d = df.set_index("date")
        wk = d[d.index.dayofweek < 5]
        wk = wk[wk["n_bars"] >= 30]
        ret = wk["close"].pct_change().dropna()
        ann_vol = ret.std() * np.sqrt(252)
        ann_ret = ret.mean() * 252
        rows.append({
            "sym": sym, "rows_daily": len(df), "wk_days(n_bars>=30)": len(wk),
            "start": str(df["date"].min().date()), "end": str(df["date"].max().date()),
            "ann_ret": round(ann_ret, 3), "ann_vol": round(ann_vol, 3),
            "med_spread_pts": round(float(d["spread_med"].median()), 1),
            "med_close": round(float(d["close"].median()), 2),
        })
        print(f"  [{sym}] done: {len(df)} daily rows, {df['date'].min().date()}->{df['date'].max().date()}", flush=True)
    summ = pd.DataFrame(rows)
    summ.to_csv(OUT / "_build_summary.csv", index=False)
    print("\n=== BUILD SUMMARY ===")
    print(summ.to_string(index=False))


if __name__ == "__main__":
    main()
