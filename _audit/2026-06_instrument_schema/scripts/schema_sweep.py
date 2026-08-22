#!/usr/bin/env python
"""READ-ONLY schema sweep of representative parquet files across all data groups.
Writes audit/_intermediate/schema_sweep.json and prints a human summary.
No data file is modified; only audit/_intermediate/*.json is written."""
from __future__ import annotations
import json, os, sys
from pathlib import Path
import pyarrow.parquet as pq
import pandas as pd
import numpy as np

ROOT = Path("<HOME>/Desktop/Algo_claude")
OUT = ROOT / "audit" / "_intermediate"
OUT.mkdir(parents=True, exist_ok=True)

# Representative files per group (relative to ROOT)
TARGETS = {
    "data/ftmo_research/EURUSD_m1.parquet": "ftmo_research",
    "data/ftmo_research/EURUSD_m5.parquet": "ftmo_research",
    "data/ftmo_research/EURUSD_m15.parquet": "ftmo_research",
    "data/ftmo_research/eurusd_m1_spread.parquet": "ftmo_research",
    "data/ftmo_research/audit/_nq_5min_rth_cached.parquet": "ftmo_research",
    "data/raw/dukascopy_EURUSD_2020.parquet": "data_raw_dukascopy",
    "data/raw/dukascopy_EURUSD_2020_2024.parquet": "data_raw_dukascopy",
    "data/raw/dukascopy_GBPUSD_2022.parquet": "data_raw_dukascopy",
    "Forex/data/cache/dukascopy_m5/USDJPY_2024_M5.parquet": "dukascopy_m5_cache",
    "Forex/data/cache/dukascopy_m5/USOIL_2024_M5.parquet": "dukascopy_m5_cache",
    "Forex/data/cache/dukascopy_m5/UK100_2024_M5.parquet": "dukascopy_m5_cache",
    "data/oxfordstrat_109/ohlc/EURUSD.parquet": "oxfordstrat_daily",
    "data/oxfordstrat_109/ohlc/XAUUSD.parquet": "oxfordstrat_daily",
    "data/oxfordstrat_109/ohlc/GER40.parquet": "oxfordstrat_daily",
    "data/oxfordstrat_109/ohlc/US100.parquet": "oxfordstrat_daily",
    "data/mtf_survey/raw/prices_NQ_F.parquet": "mtf_survey_yf_futures",
    "data/mtf_survey/raw/prices_ES_F.parquet": "mtf_survey_yf_futures",
    "data/raw/NQ_1min_databento_2010-2026.parquet": "nq_intraday",
    "data/raw/NQ_1min_2022-12-26_2025-12-11.parquet": "nq_intraday",
    "data/panels/m5_indices/m1_panel.parquet": "panel_parquet",
    "data/panels/m5_indices/m5_panel.parquet": "panel_parquet",
    "data/panels/m5_indices/EURUSD_m1_panel.parquet": "panel_parquet",
    "data/overnight_research/nq_rth_daily.parquet": "overnight",
}

def find_ts_col(df):
    for c in df.columns:
        if "time" in c.lower() or "date" in c.lower() or c.lower() in ("ts","t","dt"):
            return c
    return None

def describe(path: Path):
    info = {"exists": path.exists(), "size_bytes": path.stat().st_size if path.exists() else 0}
    if not path.exists() or info["size_bytes"] < 100:
        info["note"] = "missing/empty(<100B)"
        return info
    try:
        pf = pq.ParquetFile(str(path))
        info["num_rows"] = pf.metadata.num_rows
        sch = pf.schema_arrow
        info["columns"] = [f"{sch.field(i).name}:{sch.field(i).type}" for i in range(len(sch))]
        # read a tiny head + figure index/timestamp
        df = pd.read_parquet(path)
        info["pandas_shape"] = list(df.shape)
        info["index_name"] = df.index.name
        info["index_dtype"] = str(df.index.dtype)
        # determine timestamp source: index if datetime, else a ts column
        tser = None
        tuple_cols = any(isinstance(c, tuple) for c in df.columns)
        if pd.api.types.is_datetime64_any_dtype(df.index):
            tser = pd.Series(pd.to_datetime(df.index, errors="coerce", utc=False))
            info["ts_source"] = "index"
        elif not tuple_cols:
            tc = find_ts_col(df)
            if tc is not None:
                tser = pd.to_datetime(df[tc], errors="coerce", utc=False)
                info["ts_source"] = tc
        if tser is not None and tser.notna().any():
            tser = pd.Series(tser).dropna().sort_values()
            info["first_ts"] = str(tser.iloc[0]); info["last_ts"] = str(tser.iloc[-1])
            if len(tser) > 5:
                d = tser.diff().dropna()
                md = d.mode()
                info["modal_step_sec"] = float(md.iloc[0].total_seconds()) if len(md) else None
                info["median_step_sec"] = float(d.median().total_seconds())
            info["tz_aware"] = tser.iloc[0].tzinfo is not None
        # head sample (stringified — avoids tuple-key json issues)
        info["head2"] = df.head(2).to_string()
        if tuple_cols:
            return info
        # if a spread column exists, summarize
        low = {str(c).lower(): c for c in df.columns}
        for key in ("spread","real_volume","tick_volume","tick_count","volume"):
            if key in low:
                col = pd.to_numeric(df[low[key]], errors="coerce")
                info[f"{key}_min"] = float(np.nanmin(col)) if col.notna().any() else None
                info[f"{key}_median"] = float(np.nanmedian(col)) if col.notna().any() else None
                info[f"{key}_max"] = float(np.nanmax(col)) if col.notna().any() else None
                info[f"{key}_allzero"] = bool((col.fillna(0) == 0).all())
        # digits on close
        if "close" in low:
            c = df[low["close"]].dropna().astype(str).head(5000)
            decs = c.str.split(".").str[-1].str.len().where(c.str.contains(".", regex=False), 0)
            info["close_decimals_mode"] = int(decs.mode().iloc[0]) if len(decs) else None
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"
    return info

def main():
    results = {}
    for rel, grp in TARGETS.items():
        p = ROOT / rel
        print(f"\n=== [{grp}] {rel} ===", flush=True)
        info = describe(p)
        info["group"] = grp; info["rel"] = rel
        results[rel] = info
        for k in ("size_bytes","num_rows","columns","ts_source","first_ts","last_ts",
                  "modal_step_sec","tz_aware","spread_min","spread_median","spread_max",
                  "spread_allzero","real_volume_allzero","tick_volume_median","tick_count_median",
                  "close_decimals_mode","error","note"):
            if k in info:
                print(f"  {k}: {info[k]}")
    (OUT / "schema_sweep.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"\nWROTE {OUT/'schema_sweep.json'}")

if __name__ == "__main__":
    main()
