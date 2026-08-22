"""
gate1_decoder_check.py
======================
GATE 1 (mandatory, pre-bulk): verify the repo Dukascopy candle decoder is correct
across every decimalFactor family by comparing it, bar-for-bar, against the
independent `dukascopy-node` CLI ground truth.

Families exercised (decimalFactor): EURUSD 1e5, USDJPY 1e3, XAUUSD 1e3, US500 1e3.
Days are chosen to CONTAIN down-bars (close < high) and bars where O,H,L,C are all
distinct, so a byte-order error (OHLC instead of the true O,C,L,H) WOULD surface.

PASS criterion (per family): the day contains genuine down-bars AND 0 OHLC mismatches
(> half a point) on the minutes present in both sources. Exits non-zero on any failure.
"""
from __future__ import annotations

import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from duka_m1_backfill import URL, HEADERS, _decode, _fetch  # noqa: E402
import requests

BASE = Path(__file__).resolve().parent
DNODE = BASE / "_tool" / "node_modules" / ".bin" / "dukascopy-node"
TMP = Path("/tmp/gate1_dnode"); TMP.mkdir(exist_ok=True)

# (sym, datafeed code, decimalFactor, dukascopy-node id, day)
FAMILIES = [
    ("EURUSD", "EURUSD",        100000, "eurusd",        date(2024, 3, 5)),
    ("USDJPY", "USDJPY",          1000, "usdjpy",        date(2024, 3, 5)),
    ("XAUUSD", "XAUUSD",          1000, "xauusd",        date(2024, 3, 5)),
    ("US500",  "USA500IDXUSD",    1000, "usa500idxusd",  date(2024, 3, 5)),
]


def repo_decode_day(code: str, df: float, day: date) -> pd.DataFrame:
    """Repo decoder -> DataFrame(epoch_min, open, high, low, close) for the BID side."""
    s = requests.Session()
    url = URL.format(code=code, y=day.year, m0=day.month - 1, d=day.day, side="BID")
    rows = _decode(_fetch(s, url), df)  # (sec, o, h, l, c, v) with the OCLH fix applied
    midnight = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
    rec = [{"epoch_min": (midnight + sec) // 60, "open": o, "high": h, "low": l, "close": c}
           for (sec, o, h, l, c, v) in rows]
    return pd.DataFrame(rec)


def dnode_day(dnode_id: str, day: date) -> pd.DataFrame:
    """dukascopy-node ground truth -> DataFrame(epoch_min, open, high, low, close)."""
    fn = f"{dnode_id}_{day.isoformat()}"
    out = TMP / f"{fn}.csv"
    if out.exists():
        out.unlink()
    cmd = [str(DNODE), "-i", dnode_id, "-from", day.isoformat(),
           "-to", (day + timedelta(days=1)).isoformat(), "-t", "m1", "-p", "bid",
           "-v", "-f", "csv", "-dir", str(TMP), "-fn", fn, "-s"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if not out.exists():
        raise RuntimeError(f"dukascopy-node produced no file for {dnode_id} {day}: "
                           f"{r.stdout[-400:]} {r.stderr[-400:]}")
    d = pd.read_csv(out)
    d["epoch_min"] = (d["timestamp"] // 1000 // 60).astype("int64")
    return d[["epoch_min", "open", "high", "low", "close"]]


def check(sym, code, df, dnode_id, day) -> dict:
    repo = repo_decode_day(code, df, day)
    truth = dnode_day(dnode_id, day)
    half_pt = 0.5 / df
    # down-bars / distinctness present in ground truth -> O,C,L,H order is exercised
    down = int((truth["close"] < truth["high"] - half_pt).sum())
    distinct = int(((truth["open"] != truth["close"]) & (truth["high"] != truth["low"])).sum())
    m = repo.merge(truth, on="epoch_min", suffixes=("_repo", "_truth"), how="inner")
    diffs = {col: (m[f"{col}_repo"] - m[f"{col}_truth"]).abs() for col in ("open", "high", "low", "close")}
    mismatch = sum(int((d > half_pt).sum()) for d in diffs.values())
    max_abs = max((float(d.max()) if len(d) else 0.0) for d in diffs.values())
    ok = (mismatch == 0) and (len(m) > 100) and (down > 10) and (distinct > 10)
    return dict(sym=sym, day=str(day), repo_bars=len(repo), truth_bars=len(truth),
                matched=len(m), down_bars=down, distinct_bars=distinct,
                mismatches=mismatch, max_abs_diff=max_abs, half_point=half_pt, PASS=ok)


def main() -> None:
    print("=== GATE 1 — decoder correctness vs dukascopy-node (4 decimalFactor families) ===")
    results, all_ok = [], True
    for fam in FAMILIES:
        try:
            r = check(*fam)
        except Exception as e:  # noqa: BLE001
            r = dict(sym=fam[0], day=str(fam[4]), PASS=False, error=str(e))
        results.append(r)
        all_ok &= bool(r.get("PASS"))
        flag = "PASS" if r.get("PASS") else "FAIL"
        print(f"  [{flag}] {r['sym']:7} {r.get('day')}: matched={r.get('matched')} "
              f"down={r.get('down_bars')} distinct={r.get('distinct_bars')} "
              f"mismatches={r.get('mismatches')} max|Δ|={r.get('max_abs_diff')} "
              f"{r.get('error','')}")
    print(f"\nGATE 1 OVERALL: {'PASS' if all_ok else 'FAIL'}")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
