#!/usr/bin/env python
"""READ-ONLY characterization of FRED macro parquet + economic calendars.
Writes audit/_intermediate/macro_calendar.json. Modifies no data."""
from __future__ import annotations
import glob, json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path("<HOME>/Desktop/Algo_claude")
OUT = ROOT / "audit" / "_intermediate"
OUT.mkdir(parents=True, exist_ok=True)

def date_index(df):
    if pd.api.types.is_datetime64_any_dtype(df.index):
        return pd.DatetimeIndex(df.index)
    for c in df.columns:
        if "date" in c.lower() or "time" in c.lower():
            return pd.DatetimeIndex(pd.to_datetime(df[c], errors="coerce"))
    return None

def fred():
    out = {}
    for f in sorted(glob.glob(str(ROOT / "data/raw/fred_*.parquet"))):
        p = Path(f)
        try:
            df = pd.read_parquet(p)
            di = date_index(df)
            datacols = [c for c in df.columns if not ("date" in c.lower() or "time" in c.lower())]
            rec = {"rows": int(len(df)), "columns": list(map(str, df.columns)),
                   "data_cols": datacols}
            if di is not None and di.notna().any():
                di2 = di[di.notna()]
                rec["first"] = str(di2.min().date()); rec["last"] = str(di2.max().date())
                dd = pd.Series(di2.sort_values()).diff().dropna().dt.days
                rec["modal_step_days"] = int(dd.mode().iloc[0]) if len(dd) else None
            rec["nan_frac"] = {str(c): round(float(pd.to_numeric(df[c], errors="coerce").isna().mean()), 3)
                               for c in datacols}
            out[p.name] = rec
        except Exception as e:
            out[p.name] = {"error": f"{type(e).__name__}: {e}"}
    # series-level summary: widest range per series token
    series = {}
    for name, rec in out.items():
        if "error" in rec: continue
        for tok in ["VIXCLS","T10Y2Y","DTB3","DGS3MO","DTWEXBGS","BAMLH0A0"]:
            if tok in name or tok in rec.get("data_cols", []):
                cur = series.get(tok)
                span = (rec.get("first"), rec.get("last"), rec.get("rows", 0))
                if cur is None or span[2] > cur[2]:
                    series[tok] = span
    summary = {k: {"first": v[0], "last": v[1], "rows": v[2]} for k, v in series.items()}
    return {"files": out, "series_widest": summary}

def calendar(relpath, comment=None):
    p = ROOT / relpath
    if not p.exists():
        return {"exists": False}
    df = pd.read_csv(p, comment=comment)
    df.columns = [c.strip() for c in df.columns]
    rec = {"exists": True, "rows": int(len(df)), "columns": list(df.columns)}
    di = None
    for c in df.columns:
        if c.lower() in ("date", "datetime_utc") or "date" in c.lower():
            di = pd.to_datetime(df[c], errors="coerce"); break
    if di is not None:
        rec["first"] = str(di.min()); rec["last"] = str(di.max())
        rec["by_year"] = {str(k): int(v) for k, v in di.dt.year.value_counts().sort_index().items()}
        years = max(1, (di.max() - di.min()).days / 365.25)
        rec["events_per_year"] = round(len(df) / years, 1)
    for cand in ["currency", "currencies_affected", "ccy"]:
        if cand in df.columns:
            rec["by_currency"] = {str(k): int(v) for k, v in df[cand].value_counts().head(15).items()}
            break
    for cand in ["impact", "importance"]:
        if cand in df.columns:
            rec["by_impact"] = {str(k): int(v) for k, v in df[cand].value_counts().items()}
            break
    for cand in ["event", "event_type", "name"]:
        if cand in df.columns:
            rec["by_event"] = {str(k): int(v) for k, v in df[cand].value_counts().head(15).items()}
            break
    return rec

def main():
    res = {"fred": fred(),
           "calendar_economic": calendar("data/panels/economic_calendar.csv"),
           "calendar_economic_dup_ftmo_universe": calendar("data/ftmo_universe/news/economic_calendar.csv"),
           "calendar_news_events_f2": calendar("Forex/data/news_events_2020_2025.csv", comment="#")}
    (OUT / "macro_calendar.json").write_text(json.dumps(res, indent=2, default=str))
    # print summary
    print("=== FRED series (widest range available) ===")
    for k, v in res["fred"]["series_widest"].items():
        print(f"  {k:9} {v['first']} -> {v['last']}  ({v['rows']} rows)")
    print(f"  ({len(res['fred']['files'])} cached fred_*.parquet files total)")
    for key in ["calendar_economic", "calendar_news_events_f2"]:
        c = res[key]
        print(f"\n=== {key} ===")
        print(f"  rows={c.get('rows')} cols={c.get('columns')}")
        print(f"  range {c.get('first')} -> {c.get('last')}  events/yr={c.get('events_per_year')}")
        print(f"  by_impact={c.get('by_impact')}")
        print(f"  by_currency={c.get('by_currency')}")
        print(f"  by_event={c.get('by_event')}")
        print(f"  by_year={c.get('by_year')}")
    print(f"\nWROTE {OUT/'macro_calendar.json'}")

if __name__ == "__main__":
    main()
