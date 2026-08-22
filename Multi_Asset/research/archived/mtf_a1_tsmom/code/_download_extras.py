"""Round-2 download: AQR original-paper xlsx + FRED DTB3 via CSV direct."""
from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "mtf_survey" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

meta: dict = {}

# --- AQR original paper data (Moskowitz-Ooi-Pedersen 2012 JFE) ---
aqr_url = "https://www.aqr.com/-/media/AQR/Documents/Insights/Data-Sets/Time-Series-Momentum-Original-Paper-Data.xlsx"
print(f"[aqr] GET {aqr_url}")
r = requests.get(aqr_url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
print(f"  HTTP {r.status_code} | size {len(r.content)} | ct {r.headers.get('content-type')}")
if r.status_code == 200 and "officedocument" in (r.headers.get("content-type") or ""):
    blob_path = OUT / "aqr_tsmom_original_paper.xlsx"
    blob_path.write_bytes(r.content)
    meta["aqr_blob"] = str(blob_path)
    xl = pd.ExcelFile(io.BytesIO(r.content), engine="openpyxl")
    meta["aqr_sheets"] = xl.sheet_names
    print("  sheets:", xl.sheet_names)
    # Dump each sheet as a parquet for inspection.
    for sh in xl.sheet_names:
        try:
            df = pd.read_excel(xl, sheet_name=sh, header=None)
        except Exception as e:
            print(f"  err reading {sh}: {e}")
            continue
        p = OUT / f"aqr_tsmom_sheet_{sh.replace(' ', '_')}.csv"
        df.to_csv(p, index=False)
        print(f"  saved {p.name}: shape {df.shape}")
else:
    raise RuntimeError(f"AQR download failed: {r.status_code} {r.headers.get('content-type')}")

# --- FRED DTB3 via direct CSV ---
fred_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"
print(f"\n[fred] GET {fred_url}")
try:
    r = requests.get(fred_url, timeout=120, headers={"User-Agent": "Mozilla/5.0"})
    print(f"  HTTP {r.status_code} | size {len(r.content)}")
    if r.status_code == 200:
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = [c.strip().lower() for c in df.columns]
        date_col = "observation_date" if "observation_date" in df.columns else "date"
        df = df.rename(columns={date_col: "date", "dtb3": "dtb3_pct"})
        df["date"] = pd.to_datetime(df["date"])
        df["dtb3_pct"] = pd.to_numeric(df["dtb3_pct"], errors="coerce")
        df = df.dropna(subset=["dtb3_pct"]).set_index("date").sort_index()
        p = OUT / "dtb3.parquet"
        df.to_parquet(p)
        meta["dtb3_rows"] = int(df.shape[0])
        meta["dtb3_range"] = f"{df.index.min().date()} → {df.index.max().date()}"
        print(f"  saved {p.name}: {meta['dtb3_range']}, rows={meta['dtb3_rows']}")
    else:
        meta["dtb3_error"] = f"HTTP {r.status_code}"
except Exception as e:
    meta["dtb3_error"] = str(e)
    print(f"  err: {e}")

with open(OUT / "_extras_meta.json", "w") as f:
    json.dump(meta, f, indent=2, default=str)
print("\nmeta:", meta)
