#!/usr/bin/env python3
"""Standalone verifier for the overnight equity-drift seasonality.
Reproduces the report's numbers and lets you falsify independently.

Usage:
  python verify_overnight.py nq [PATH_TO_NQ_PARQUET]      # reproduce the NQ 2010-2026 result
  python verify_overnight.py daily PATH.csv [DateCol Open Close]   # any daily OHLC (e.g. QQQ from yfinance)

Core definitions (see report §1.1):
  overnight[t] = open[t]/close[t-1] - 1     (HOLD the prior night; weekday shown = weekday of OPEN day t)
  intraday[t]  = close[t]/open[t]   - 1
No future data is used (close[t-1] via shift(1)). Weekday: 0=Mon..4=Fri.
"""
import sys, numpy as np, pandas as pd
WD = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]

def report(df, label, split_year=2019):
    """df must have DatetimeIndex and columns o (open), c (close)."""
    df = df.sort_index().copy()
    df["pc"] = df["c"].shift(1)
    df["overnight"] = (df["o"]/df["pc"] - 1)*1e4
    df["intraday"]  = (df["c"]/df["o"] - 1)*1e4
    df["wd"] = df.index.weekday; df["yr"] = df.index.year
    df = df.dropna(subset=["overnight"])
    for col in ["overnight","intraday"]:
        print(f"\n=== {label}: {col} (bps) | weekday=OPEN day (Tue=Mon-night hold) ===")
        print(f"{'wd':4s}{'n':>6s}{'mean':>9s}{'t':>7s}{'IN<%d'%split_year:>9s}{'OOS>=%d'%split_year:>9s}")
        for wd in range(5):
            s = df[df.wd==wd][col]
            if len(s) < 30: continue
            t = s.mean()/(s.std()/np.sqrt(len(s)))
            ins = df[(df.wd==wd)&(df.yr<split_year)][col].mean()
            oos = df[(df.wd==wd)&(df.yr>=split_year)][col].mean()
            print(f"{WD[wd]:4s}{len(s):6d}{s.mean():9.2f}{t:7.2f}{ins:9.2f}{oos:9.2f}")
        s = df[col]; t = s.mean()/(s.std()/np.sqrt(len(s)))
        ins = df[df.yr<split_year][col].mean(); oos = df[df.yr>=split_year][col].mean()
        print(f"{'ALL':4s}{len(s):6d}{s.mean():9.2f}{t:7.2f}{ins:9.2f}{oos:9.2f}")
    yr = df.groupby("yr")["overnight"].mean()
    print(f"\novernight positive years: {(yr>0).sum()}/{len(yr)}  (worst {yr.min():.1f}, best {yr.max():.1f} bps)")

def from_nq(path):
    d = pd.read_parquet(path).reset_index()
    tcol = [c for c in d.columns if "time" in c.lower() or "date" in c.lower()][0]
    d["dt"] = pd.to_datetime(d[tcol])
    if "is_rth" in d.columns: d = d[d["is_rth"]==True]
    d["date"] = d["dt"].dt.normalize()
    g = d.groupby("date"); out = pd.DataFrame({"o":g["open"].first(),"c":g["close"].last()})
    out.index = pd.to_datetime(out.index); return out

def from_daily(path, dcol="Date", ocol="Open", ccol="Close"):
    d = pd.read_csv(path)
    d[dcol] = pd.to_datetime(d[dcol]); d = d.set_index(dcol).sort_index()
    return pd.DataFrame({"o":d[ocol].astype(float),"c":d[ccol].astype(float)})

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv)>1 else "nq"
    if mode == "nq":
        path = sys.argv[2] if len(sys.argv)>2 else "data/raw/NQ_1min_databento_2010-2026.parquet"
        report(from_nq(path), f"NQ ({path})")
    else:
        path = sys.argv[2]; cols = sys.argv[3:6] if len(sys.argv)>=6 else ["Date","Open","Close"]
        report(from_daily(path, *cols), f"DAILY ({path})")
