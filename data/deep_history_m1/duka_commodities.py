"""
duka_commodities.py — TRACK B: download the commodity complex via the PROVEN Track-A pipeline.
REUSES duka_m1_backfill.py (decode/_fetch/fetch_day/download_year: OCLH fix, per-instr decimalFactor,
v<=0 AND h<=l flat-drop, fail-loud-on-dropped-day, nw<=8 rate-limit-safe). Net-new instruments
(no FTMO splice). Does NOT modify the Track-A INSTR on disk — it monkey-patches at runtime.

Datafeed code = UPPERCASE (verified); dukascopy-node id = lowercase. point=1/df, dp=log10(df)
(Dukascopy-native units; ftmo_specs has no spread column). TARGET_START lowered to 2003 so silver
reaches its true floor; per-instrument istart still clamps each.

Usage: /usr/bin/python3 duka_commodities.py [--threads 8] [SYM ...]
"""
from __future__ import annotations
import argparse, json
from datetime import date
import duka_m1_backfill as D

# output_sym -> dict(datafeed code UPPERCASE, decimalFactor, point=1/df, dp=log10(df), istart depth, grp)
COMM = {
    # --- CORE (liquid) ---
    "XAGUSD":  dict(code="XAGUSD",        df=1000,  point=1e-3, dp=3, istart="2003-05-04"),  # silver
    "USOIL":   dict(code="LIGHTCMDUSD",   df=1000,  point=1e-3, dp=3, istart="2013-01-01"),  # WTI
    "UKOIL":   dict(code="BRENTCMDUSD",   df=1000,  point=1e-3, dp=3, istart="2010-12-02"),  # Brent
    "NGAS":    dict(code="GASCMDUSD",     df=10000, point=1e-4, dp=4, istart="2012-09-02"),  # natgas
    "COPPER":  dict(code="COPPERCMDUSD",  df=10000, point=1e-4, dp=4, istart="2012-03-02"),
    # --- AGS / softs (present on Dukascopy) ---
    "SUGAR":   dict(code="SUGARCMDUSD",   df=1000,  point=1e-3, dp=3, istart="2017-10-02"),
    "COCOA":   dict(code="COCOACMDUSD",   df=1000,  point=1e-3, dp=3, istart="2017-10-20"),
    "COFFEE":  dict(code="COFFEECMDUSX",  df=1000,  point=1e-3, dp=3, istart="2017-12-04"),
    "SOYBEAN": dict(code="SOYBEANCMDUSX", df=1000,  point=1e-3, dp=3, istart="2017-12-01"),
    "COTTON":  dict(code="COTTONCMDUSX",  df=1000,  point=1e-3, dp=3, istart="2017-10-20"),
    "OJUICE":  dict(code="OJUICECMDUSX",  df=1000,  point=1e-3, dp=3, istart="2017-10-20"),
    "DIESEL":  dict(code="DIESELCMDUSD",  df=1000,  point=1e-3, dp=3, istart="2017-12-26"),
}
# NOTE: WHEAT & CORN are ABSENT from Dukascopy instrumentMetaData (no code) -> reported, not invented.
for c in COMM.values():
    c.update(es="2026-06-08", ee="2026-06-08", grp="COMM")  # es=ee=today => plan_years not used; we drive years directly


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, default=8)
    ap.add_argument("syms", nargs="*")
    a = ap.parse_args()
    D.INSTR.update(COMM)                 # runtime extension (Track-A file unchanged on disk)
    D.TARGET_START = date(2003, 1, 1)    # let silver reach its 2003 floor; istart clamps the rest
    syms = a.syms or list(COMM)
    (D.BASE / "reports").mkdir(exist_ok=True)
    results = []
    for sym in syms:
        y0 = int(COMM[sym]["istart"][:4])
        print(f"=== {sym} ({COMM[sym]['code']}) {y0}-{D.TODAY.year} ===", flush=True)
        for y in range(y0, D.TODAY.year + 1):
            r = D.download_year(sym, y, threads=a.threads)
            results.append(r)
            print(f"   -> {r}", flush=True)
    json.dump(results, open(D.BASE / "reports" / "download_status_COMM.json", "w"), indent=2, default=str)
    bad = [r for r in results if r.get("status") in ("fetch_err", "ohlc_fail")]
    print(f"\nDONE. {len([r for r in results if r.get('status')=='ok'])} ok, "
          f"{len([r for r in results if r.get('status')=='empty'])} empty, {len(bad)} FAILED "
          f"{[(r['sym'],r['year'],r['status']) for r in bad]}")


if __name__ == "__main__":
    main()
