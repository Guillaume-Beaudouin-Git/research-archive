"""Download futures + FRED + AQR for A1 (frozen pre-reg).

Run: /usr/bin/python3 code/mtf/_download_a1_data.py
Writes:
  data/mtf_survey/raw/prices_{TICKER}.parquet (yfinance daily)
  data/mtf_survey/raw/dtb3.parquet (FRED)
  data/mtf_survey/raw/aqr_tsmom_monthly.parquet (if downloadable)
"""
from __future__ import annotations

import io
import json
import sys
import time
import warnings
from pathlib import Path

import pandas as pd
import requests

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "mtf_survey" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

UNIVERSE = {
    "equity": ["ES=F", "NQ=F", "YM=F", "RTY=F"],
    "bonds":  ["ZT=F", "ZF=F", "ZN=F", "ZB=F"],
    "fx":     ["6E=F", "6J=F", "6B=F", "6A=F", "6C=F", "6S=F"],
    "commod": ["CL=F", "NG=F", "GC=F", "SI=F", "HG=F",
               "ZC=F", "ZW=F", "ZS=F", "KC=F", "SB=F"],
}

ALL_TICKERS = [t for v in UNIVERSE.values() for t in v]


def dl_yf(ticker: str) -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(ticker, period="max", auto_adjust=False, progress=False, threads=False)
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.index = pd.to_datetime(df.index).tz_localize(None)
    return df


def dl_fred_dtb3() -> pd.DataFrame:
    """FRED DTB3 — 3M T-Bill secondary market rate, daily, annualized %."""
    from pandas_datareader import data as web
    df = web.DataReader("DTB3", "fred", start="1980-01-01")
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.rename(columns={"DTB3": "dtb3_pct"})
    return df


def dl_aqr_tsmom() -> pd.DataFrame:
    """AQR 'Time Series Momentum' monthly factor.

    URL changes occasionally; we try a few canonical paths.
    """
    candidates = [
        # Direct xlsx (canonical AQR data library — current path used 2020+).
        "https://images.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factor-Monthly.xlsx",
        "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Factor-Monthly.xlsx",
    ]
    last_err = None
    for url in candidates:
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code != 200:
                last_err = f"HTTP {r.status_code} on {url}"
                continue
            xl = pd.ExcelFile(io.BytesIO(r.content))
            # AQR sheets typically: 'TSMOM Factor' or similar; pick the largest data sheet.
            best_sheet, best_df = None, None
            for sh in xl.sheet_names:
                try:
                    candidate = pd.read_excel(xl, sheet_name=sh, header=None)
                except Exception:
                    continue
                if candidate.shape[0] > 50 and candidate.shape[1] >= 2:
                    if best_df is None or candidate.shape[0] > best_df.shape[0]:
                        best_sheet, best_df = sh, candidate
            if best_df is None:
                last_err = "no usable sheet"
                continue
            # Find the first row where col 0 is a date and col 1 is numeric.
            df = best_df.copy()
            df.columns = [f"c{i}" for i in range(df.shape[1])]
            start = None
            for i in range(df.shape[0]):
                v = df.iloc[i, 0]
                try:
                    pd.to_datetime(v)
                    float(df.iloc[i, 1])
                    start = i
                    break
                except Exception:
                    continue
            if start is None:
                last_err = "no date row found"
                continue
            df = df.iloc[start:].copy()
            df["date"] = pd.to_datetime(df.iloc[:, 0], errors="coerce")
            df = df.dropna(subset=["date"]).set_index("date").sort_index()
            # Identify TSMOM factor column. Use the second column by default.
            df_factor = pd.to_numeric(df.iloc[:, 1], errors="coerce").to_frame("aqr_tsmom_monthly")
            df_factor = df_factor.dropna()
            df_factor.attrs = {"source_url": url, "sheet": best_sheet}
            return df_factor
        except Exception as e:
            last_err = f"{url}: {e}"
            continue
    raise RuntimeError(f"AQR TSMOM download failed: {last_err}")


def main() -> None:
    meta = {"downloaded_at": pd.Timestamp.utcnow().isoformat(), "tickers": {}}

    for tkr in ALL_TICKERS:
        path = OUT / f"prices_{tkr.replace('=', '_').replace('/', '_')}.parquet"
        if path.exists():
            print(f"[skip exists] {tkr}")
            continue
        print(f"[yf] {tkr}", flush=True)
        for attempt in range(3):
            try:
                df = dl_yf(tkr)
                if df.empty:
                    print(f"  empty on attempt {attempt+1}")
                    time.sleep(2)
                    continue
                df.to_parquet(path)
                meta["tickers"][tkr] = {
                    "rows": int(df.shape[0]),
                    "start": str(df.index.min().date()) if df.shape[0] else None,
                    "end": str(df.index.max().date()) if df.shape[0] else None,
                }
                break
            except Exception as e:
                print(f"  err attempt {attempt+1}: {e}")
                time.sleep(3)

    # FRED DTB3
    dtb3_path = OUT / "dtb3.parquet"
    if not dtb3_path.exists():
        print("[fred] DTB3", flush=True)
        try:
            df = dl_fred_dtb3()
            df.to_parquet(dtb3_path)
            meta["dtb3"] = {"rows": int(df.shape[0]),
                            "start": str(df.index.min().date()),
                            "end": str(df.index.max().date())}
        except Exception as e:
            print(f"  FRED err: {e}")
            meta["dtb3_error"] = str(e)
    else:
        print("[skip] DTB3 exists")

    # AQR TSMOM
    aqr_path = OUT / "aqr_tsmom_monthly.parquet"
    if not aqr_path.exists():
        print("[aqr] TSMOM monthly", flush=True)
        try:
            df = dl_aqr_tsmom()
            df.to_parquet(aqr_path)
            meta["aqr"] = {"rows": int(df.shape[0]),
                           "start": str(df.index.min().date()),
                           "end": str(df.index.max().date()),
                           "source": df.attrs.get("source_url"),
                           "sheet": df.attrs.get("sheet")}
        except Exception as e:
            print(f"  AQR err: {e}")
            meta["aqr_error"] = str(e)
    else:
        print("[skip] AQR exists")

    with open(OUT / "_download_meta.json", "w") as f:
        json.dump(meta, f, indent=2, default=str)
    print("Done. meta in", OUT / "_download_meta.json")


if __name__ == "__main__":
    main()
