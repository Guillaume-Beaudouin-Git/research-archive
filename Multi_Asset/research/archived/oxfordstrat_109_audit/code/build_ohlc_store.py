"""
build_ohlc_store.py — Reconstruct the consolidated daily OHLC store used to
backtest the oxfordstrat strategies on the FTMO universe.

Sources (relative to DATA_DIR = your .../Algo_claude/data folder):
  - Indices (10) : panels/ftmo_open.csv, ftmo_high.csv, ftmo_low.csv, ftmo_close.csv
                   (wide panels, Date index, one column per index, 2000-2026)
  - FX (9) + BTCUSD + XAUUSD : panels/m5_indices/{TICKER}_M1.csv
                   (MetaTrader/FTMO M1 export: timestamp_utc, open, high, low,
                    close, tick_volume, spread, real_volume) -> resampled to
                    daily OHLC. The real `spread` column (broker points) is
                    aggregated (median/day) and reused by the cost model.
  - Commodities (8) + ETHUSD : raw/yf_{YFTICKER}_1d*.parquet  (yfinance daily OHLC)

Output: {OUT_DIR}/{INSTR}.parquet  (columns: open, high, low, close[, spread])
        {OUT_DIR}/_coverage.csv

Daily-bar convention for 24h markets (FX/crypto/metals from M1): bars are cut on
the UTC calendar day (00:00 UTC). This is an explicit assumption — FTMO server
time is typically EET; shifting the cutoff changes the 'open' used by ORB-type
entries. Documented as an audit point.
"""
import os, re, glob, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

DATA_DIR = os.environ.get("ALGO_DATA_DIR", "<HOME>/Desktop/Algo_claude/data")
OUT_DIR  = os.environ.get("OHLC_OUT_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ohlc"))

M1_RESAMPLE = {  # FTMO ticker -> M1 filename stem, asset class
    "EURUSD": ("EURUSD", "forex"), "GBPUSD": ("GBPUSD", "forex"), "USDJPY": ("USDJPY", "forex"),
    "USDCHF": ("USDCHF", "forex"), "USDCAD": ("USDCAD", "forex"), "AUDUSD": ("AUDUSD", "forex"),
    "NZDUSD": ("NZDUSD", "forex"), "EURGBP": ("EURGBP", "forex"), "AUDJPY": ("AUDJPY", "forex"),
    "BTCUSD": ("BTCUSD", "crypto"), "XAUUSD": ("XAUUSD", "commodities"),
}
YF = {  # FTMO ticker -> yfinance ticker (daily OHLC parquet in raw/)
    "XAGUSD": ("SI=F", "commodities"), "XPTUSD": ("PL=F", "commodities"),
    "XPDUSD": ("PA=F", "commodities"), "UKOIL": ("BZ=F", "commodities"),
    "WHEAT": ("ZW=F", "commodities"), "SOYBEAN": ("ZS=F", "commodities"),
    "COFFEE": ("KC=F", "commodities"), "COCOA": ("CC=F", "commodities"),
    "ETHUSD": ("ETH-USD", "crypto"),
}
# NOTE: USOIL (CL=F) and the 8 close-only cryptos (LTC/XRP/XMR/NEO/ADA/DASH/DOT/DOGE)
# and GBPJPY are intentionally skipped — no reliable local daily OHLC. See report.

def _clean(df):
    df = df[["open", "high", "low", "close"] + (["spread"] if "spread" in df else [])].copy()
    df = df.dropna(subset=["open", "high", "low", "close"])
    df = df[(df[["open", "high", "low", "close"]] > 0).all(axis=1)]
    df.index = pd.to_datetime(df.index); df.index.name = "Date"
    return df.sort_index()

def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    rep = []
    P = os.path.join(DATA_DIR, "panels")

    # 1) Indices
    o = pd.read_csv(f"{P}/ftmo_open.csv",  index_col=0, parse_dates=True)
    h = pd.read_csv(f"{P}/ftmo_high.csv",  index_col=0, parse_dates=True)
    l = pd.read_csv(f"{P}/ftmo_low.csv",   index_col=0, parse_dates=True)
    c = pd.read_csv(f"{P}/ftmo_close.csv", index_col=0, parse_dates=True)
    for t in c.columns:
        df = _clean(pd.DataFrame({"open": o[t], "high": h[t], "low": l[t], "close": c[t]}))
        df.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, "indices", "ftmo_panel", len(df), df.index.min().date(), df.index.max().date(), ""))

    # 2) M1 -> daily OHLC (+ median daily spread in broker points)
    for t, (fn, cls) in M1_RESAMPLE.items():
        d = pd.read_csv(f"{P}/m5_indices/{fn}_M1.csv",
                        usecols=["timestamp_utc", "open", "high", "low", "close", "spread"])
        d["dt"] = pd.to_datetime(d["timestamp_utc"], format="%Y.%m.%d %H:%M:%S", errors="coerce")
        d = d.dropna(subset=["dt"]); d["date"] = d["dt"].dt.normalize()
        g = d.groupby("date").agg(open=("open", "first"), high=("high", "max"),
                                  low=("low", "min"), close=("close", "last"),
                                  spread=("spread", "median"))
        g = _clean(g)
        g.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, cls, "M1_resample", len(g), g.index.min().date(), g.index.max().date(),
                    f"spread~{g['spread'].median():.0f}pt"))

    # 3) yfinance daily OHLC
    for t, (yt, cls) in YF.items():
        cands = sorted(glob.glob(f"{DATA_DIR}/raw/yf_{yt}_1d*.parquet"), key=os.path.getsize)
        if not cands:
            rep.append((t, cls, "MISSING", 0, "", "", "")); continue
        df = pd.read_parquet(cands[-1]); df.columns = [str(x).lower() for x in df.columns]
        df = _clean(df)
        df.to_parquet(f"{OUT_DIR}/{t}.parquet")
        rep.append((t, cls, f"yf:{yt}", len(df), df.index.min().date(), df.index.max().date(), ""))

    R = pd.DataFrame(rep, columns=["instr", "class", "source", "days", "start", "end", "note"])
    R = R.sort_values(["class", "instr"]).reset_index(drop=True)
    R.to_csv(f"{OUT_DIR}/_coverage.csv", index=False)
    print(R.to_string(index=False))
    print(f"\n{(R.days > 0).sum()}/40 instruments with real OHLC -> {OUT_DIR}")
    return R

if __name__ == "__main__":
    build()
