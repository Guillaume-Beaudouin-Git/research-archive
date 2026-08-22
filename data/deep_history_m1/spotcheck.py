"""
spotcheck.py
============
Post-bulk validation: for each instrument, pick a few RANDOM *backfilled* days
(Dukascopy-sourced, i.e. before the existing MT5 start) and compare the FINAL
assembled CSV (data/deep_history_utc/<SYM>_M1.csv, true UTC) bar-for-bar against an
independent `dukascopy-node` pull for the same day. Catches data-dependent decode
errors a single pre-bulk gate day could miss, and confirms the splice/format/tz.

Both sides are true UTC -> direct minute match (no tz shift). Prices compared at the
instrument's dp precision (the CSV is dp-rounded). Seeded for reproducibility.

Usage: /usr/bin/python3 spotcheck.py [--per 3]
"""
from __future__ import annotations

import argparse
import random
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from duka_m1_backfill import INSTR, TARGET_START  # noqa: E402

BASE = Path(__file__).resolve().parent
DNODE = BASE / "_tool" / "node_modules" / ".bin" / "dukascopy-node"
FINAL = BASE.parent / "deep_history_utc"
TMP = Path("/tmp/spotcheck_dnode"); TMP.mkdir(exist_ok=True)
random.seed(42)


def dnode_day(dnode_id: str, day: date) -> pd.DataFrame:
    fn = f"{dnode_id}_{day.isoformat()}"
    out = TMP / f"{fn}.csv"
    if out.exists():
        out.unlink()
    cmd = [str(DNODE), "-i", dnode_id, "-from", day.isoformat(),
           "-to", (day + timedelta(days=1)).isoformat(), "-t", "m1", "-p", "bid",
           "-f", "csv", "-dir", str(TMP), "-fn", fn, "-s"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        return pd.DataFrame(columns=["hm", "open", "high", "low", "close"])
    d = pd.read_csv(out)
    ts = pd.to_datetime(d["timestamp"], unit="ms", utc=True)
    d["hm"] = ts.dt.strftime("%H:%M")
    return d[["hm", "open", "high", "low", "close"]]


def csv_day(sym: str, day: date) -> pd.DataFrame:
    """Extract one day's rows from the final CSV via grep (avoids loading the huge file)."""
    f = FINAL / f"{sym}_M1.csv"
    if not f.exists():
        return pd.DataFrame(columns=["hm", "open", "high", "low", "close"])
    pref = day.strftime("%Y.%m.%d ")
    r = subprocess.run(["grep", f"^{pref}", str(f)], capture_output=True, text=True)
    rows = []
    for ln in r.stdout.splitlines():
        p = ln.split(",")
        if len(p) >= 5:
            rows.append({"hm": p[0][11:16], "open": float(p[1]), "high": float(p[2]),
                         "low": float(p[3]), "close": float(p[4])})
    return pd.DataFrame(rows)


def pick_backfill_days(cfg: dict, n: int) -> list[date]:
    es = datetime.strptime(cfg["es"], "%Y-%m-%d").date()
    istart = datetime.strptime(cfg["istart"], "%Y-%m-%d").date()
    lo = max(TARGET_START, istart)
    span = (es - lo).days - 2
    if span <= 1:
        return []
    days, tries = [], 0
    while len(days) < n and tries < 200:
        tries += 1
        d = lo + timedelta(days=random.randint(0, span))
        if d.weekday() < 5 and d not in days:
            days.append(d)
    return sorted(days)


def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--per", type=int, default=3)
    a = ap.parse_args()
    print("=== SPOT-CHECK: final CSV (true UTC) vs dukascopy-node, random backfill days ===")
    all_ok = True
    for sym, cfg in INSTR.items():
        dp = cfg["dp"]
        tol = 1.5 * (10 ** -dp)
        for day in pick_backfill_days(cfg, a.per):
            truth = dnode_day(cfg["code"].lower(), day)
            mine = csv_day(sym, day)
            if mine.empty and truth.empty:
                print(f"  [skip] {sym} {day}: both empty")
                continue
            m = mine.merge(truth, on="hm", suffixes=("_me", "_tv"), how="inner")
            if len(m) == 0:
                print(f"  [WARN] {sym} {day}: no overlapping minutes (mine={len(mine)} tv={len(truth)})")
                all_ok = False
                continue
            mm = 0
            mx = 0.0
            for c in ("open", "high", "low", "close"):
                dd = (m[f"{c}_me"] - m[f"{c}_tv"].round(dp)).abs()
                mm += int((dd > tol).sum())
                mx = max(mx, float(dd.max()))
            ok = mm == 0
            all_ok &= ok
            print(f"  [{'OK' if ok else 'FAIL'}] {sym} {day}: matched={len(m)} "
                  f"mismatch={mm} max|Δ|={mx:.{dp}f} (mine={len(mine)} tv={len(truth)})")
    print(f"\nSPOT-CHECK OVERALL: {'PASS' if all_ok else 'REVIEW NEEDED'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
