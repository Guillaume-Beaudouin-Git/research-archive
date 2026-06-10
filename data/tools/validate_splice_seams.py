"""validate_splice_seams.py — T4 gate for the deep_history_utc splice repair.

For each repaired instrument, compares MT5 (dense range, EET->UTC per repo convention)
against the Dukascopy cache on their timestamp overlap:
  1. daily |close diff| in bps at the last COMMON minute of each day
     GATE: median daily |diff| <= 5 bps, else STOP (do not ship the merge)
  2. timezone-shift signature: re-joins with Dukascopy shifted ±60 min; if a nonzero
     shift reduces the median |diff| by >50%, a silent tz mismatch exists -> STOP
  3. structural checks on the assembled output: monotonic timestamps, zero duplicates,
     seam price step at the dense-start boundary, bars/day on both sides of the seam

Outputs data/tools/seam_validation_report.{md,json}. Read-only on all inputs.

Usage: /usr/bin/python3 data/tools/validate_splice_seams.py --symbols US500,US100,GER40,EURGBP
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "data" / "deep_history_m1"))
from assemble import _dense_start, load_duka, load_existing  # noqa: E402

OUT_DIR = REPO / "data" / "deep_history_utc"
GATE_MEDIAN_BPS = 5.0
SHIFTS_MIN = (-60, 0, 60)


def daily_close_diff(mt5: pd.DataFrame, duka: pd.DataFrame, shift_min: int) -> pd.Series:
    """Per-day |close diff| in bps at the last common minute (MT5 bid vs Duka bid)."""
    d = duka[["ts_utc", "close"]].copy()
    d["ts_utc"] = d["ts_utc"] + pd.Timedelta(minutes=shift_min)
    m = mt5.merge(d, left_on="_ts", right_on="ts_utc", how="inner",
                  suffixes=("_mt5", "_duka"))
    if m.empty:
        return pd.Series(dtype=float)
    m = m.sort_values("_ts")
    last = m.groupby(m["_ts"].dt.normalize()).last()
    return (1e4 * (last["close_mt5"] - last["close_duka"]).abs() / last["close_duka"])


def validate(sym: str) -> dict:
    exist = load_existing(sym)
    exist["close"] = pd.to_numeric(exist["close"], errors="coerce")
    ds = _dense_start(exist["_ts"])
    dense = exist.loc[exist["_ts"] >= ds, ["_ts", "close"]]
    duka = load_duka(sym)
    res: dict = {"symbol": sym, "dense_mt5_start": str(ds)}
    if duka is None or duka.empty:
        res["status"] = "NO_DUKA_CACHE"
        return res

    # --- 1+2: overlap close diffs at shifts ---
    by_shift = {}
    for s in SHIFTS_MIN:
        diffs = daily_close_diff(dense, duka, s)
        by_shift[s] = {"n_days": int(len(diffs)),
                       "median_bps": round(float(diffs.median()), 3) if len(diffs) else None,
                       "mean_bps": round(float(diffs.mean()), 3) if len(diffs) else None,
                       "max_bps": round(float(diffs.max()), 3) if len(diffs) else None}
    res["overlap_by_shift_min"] = by_shift
    med0 = by_shift[0]["median_bps"]
    res["gate_median_bps"] = med0
    gate_diff = med0 is not None and med0 <= GATE_MEDIAN_BPS
    tz_flag = False
    for s in SHIFTS_MIN:
        if s != 0 and by_shift[s]["median_bps"] is not None and med0 is not None \
                and by_shift[s]["median_bps"] < 0.5 * med0:
            tz_flag = True
    res["tz_shift_signature"] = tz_flag

    # --- 3: structural checks on the assembled output file ---
    out = OUT_DIR / f"{sym}_M1.csv"
    ts = pd.to_datetime(
        pd.read_csv(out, usecols=["timestamp_utc"], dtype=str)["timestamp_utc"],
        format="%Y.%m.%d %H:%M:%S")
    res["assembled_rows"] = int(len(ts))
    res["monotonic"] = bool(ts.is_monotonic_increasing)
    res["duplicate_timestamps"] = int(ts.duplicated().sum())

    closes = pd.read_csv(out, usecols=["timestamp_utc", "close"])
    closes["ts"] = ts
    i = int(np.searchsorted(ts.values, np.datetime64(ds)))
    if 0 < i < len(closes):
        c_prev, c_at = float(closes["close"].iloc[i - 1]), float(closes["close"].iloc[i])
        res["seam"] = {
            "boundary": str(ds),
            "step_bps": round(1e4 * abs(c_at - c_prev) / c_prev, 2),
            "gap_minutes": round(float((ts.iloc[i] - ts.iloc[i - 1]).total_seconds() / 60), 1),
        }
    day = ts.dt.normalize()
    seam_day = pd.Timestamp(ds).normalize()
    around = day.value_counts().sort_index()
    mask = (around.index >= seam_day - pd.Timedelta(days=7)) & \
           (around.index <= seam_day + pd.Timedelta(days=7))
    res["bars_per_day_around_seam"] = {str(k.date()): int(v)
                                       for k, v in around[mask].items()}

    res["status"] = "PASS" if (gate_diff and not tz_flag and res["monotonic"]
                               and res["duplicate_timestamps"] == 0) else "STOP"
    return res


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", required=True)
    a = ap.parse_args()
    syms = [s.strip() for s in a.symbols.split(",") if s.strip()]
    results = [validate(s) for s in syms]

    md = ["# Splice seam validation (T4)", "",
          f"**Generated:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} by "
          "`/usr/bin/python3 data/tools/validate_splice_seams.py`",
          f"**Gate:** median daily |MT5−Duka| close diff ≤ {GATE_MEDIAN_BPS} bps on the "
          "overlap, no ±60min tz-shift signature, monotonic, zero duplicate timestamps.", ""]
    md += ["| symbol | status | overlap days | median bps | mean bps | max bps | tz-shift | dups | mono | seam step bps |",
           "|---|---|--:|--:|--:|--:|---|--:|---|--:|"]
    for r in results:
        o = r.get("overlap_by_shift_min", {}).get(0, {})
        md.append(f"| {r['symbol']} | **{r['status']}** | {o.get('n_days','—')} | "
                  f"{o.get('median_bps','—')} | {o.get('mean_bps','—')} | {o.get('max_bps','—')} | "
                  f"{'YES' if r.get('tz_shift_signature') else 'no'} | "
                  f"{r.get('duplicate_timestamps','—')} | {r.get('monotonic','—')} | "
                  f"{r.get('seam',{}).get('step_bps','—')} |")
    md.append("")
    for r in results:
        md += [f"## {r['symbol']}", "",
               f"dense MT5 start: {r['dense_mt5_start']} · seam: {json.dumps(r.get('seam', {}))}",
               "", "shift sensitivity (median bps): " + ", ".join(
                   f"{s:+d}min: {r['overlap_by_shift_min'][s]['median_bps']}"
                   for s in SHIFTS_MIN if "overlap_by_shift_min" in r),
               "", "bars/day around seam: " + json.dumps(r.get("bars_per_day_around_seam", {})), ""]

    (REPO / "data/tools/seam_validation_report.md").write_text("\n".join(md))
    (REPO / "data/tools/seam_validation_report.json").write_text(json.dumps(results, indent=2))
    for r in results:
        print(f"{r['symbol']}: {r['status']} median={r.get('gate_median_bps')}bps "
              f"tz_flag={r.get('tz_shift_signature')} dups={r.get('duplicate_timestamps')}")
    return 0 if all(r["status"] == "PASS" for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
