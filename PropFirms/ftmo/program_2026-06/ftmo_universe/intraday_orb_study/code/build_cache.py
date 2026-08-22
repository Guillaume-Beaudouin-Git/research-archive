"""Clean M1 CSV -> parquet cache. Clock is broker EET (UTC+2/+3) despite 'timestamp_utc' label.
Adds session-date, EET hour/min, intraday minute index, and masks cross-gap returns."""
import pandas as pd, numpy as np, sys, os
SRC="/sessions/stoic-vigilant-meitner/mnt/data/panels/m5_indices/"
OUT="/sessions/stoic-vigilant-meitner/mnt/outputs/ftmo_intraday/cache/"

def build(sym):
    f=f"{SRC}{sym}_M1.csv"
    df=pd.read_csv(f, usecols=["timestamp_utc","open","high","low","close","spread"],
                   dtype={"open":"float64","high":"float64","low":"float64","close":"float64","spread":"float64"})
    dt=pd.to_datetime(df["timestamp_utc"], format="%Y.%m.%d %H:%M:%S")
    df=df.drop(columns=["timestamp_utc"]); df.insert(0,"dt",dt)
    df=df.sort_values("dt").reset_index(drop=True)
    # drop exact dup timestamps
    df=df[~df["dt"].duplicated(keep="first")].reset_index(drop=True)
    df["date"]=df["dt"].dt.date
    df["hour"]=df["dt"].dt.hour
    df["minute"]=df["dt"].dt.minute
    df["tod"]=df["hour"]*60+df["minute"]          # minutes since EET midnight
    # gap in minutes vs prior bar; returns across >5min gaps are flagged (overnight/maintenance)
    gap=df["dt"].diff().dt.total_seconds().div(60.0)
    df["new_seg"]=(gap>5).fillna(True)
    os.makedirs(OUT,exist_ok=True)
    df.to_parquet(f"{OUT}{sym}.parquet", index=False)
    yrs=df["dt"].dt.year
    print(f"{sym}: {len(df):,} bars  {df.dt.min()} -> {df.dt.max()}  spread med={df.spread.median():.1f}  yrs={yrs.min()}-{yrs.max()}")
    return df

for s in sys.argv[1:]:
    build(s)
