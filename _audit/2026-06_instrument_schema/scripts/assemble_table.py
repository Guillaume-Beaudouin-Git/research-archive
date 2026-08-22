#!/usr/bin/env python
"""Assemble audit/instrument_table.csv from the fingerprint JSON (exact, measured)
plus inventory rows for instruments not deep-fingerprinted (from download logs /
cache inventory — NOT fabricated). Writes only under audit/. Modifies no data."""
from __future__ import annotations
import csv, json
from pathlib import Path

ROOT = Path("<HOME>/Desktop/Algo_claude")
INT = ROOT / "audit" / "_intermediate"
OUTCSV = ROOT / "audit" / "instrument_table.csv"

J = json.load(open(INT / "mt5_fingerprint.json"))
FX = {"EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","NZDUSD","EURGBP","EURJPY","AUDJPY"}

FIELDS = ["instrument", "group", "source_guess", "first", "last", "rows",
          "completeness_pct", "resolution", "timestamp_basis", "spread_units",
          "spread_min", "spread_median", "spread_median_pips", "spread_round_mult5_frac",
          "spread_floor_detected", "realvol_all_zero", "digits", "dup_count",
          "intraweek_gap_count", "fingerprinted", "notes"]

def reso(r):
    s = r.get("modal_step_sec")
    return "M1" if s == 60 else ("M5" if s == 300 else f"{s}s")

rows = []
for label, r in J.items():
    if "error" in r:
        continue
    grp = r["group"]
    is_mt5 = grp == "mt5_ftmo"
    src = "MT5_FTMO-Demo (live broker export)" if is_mt5 else "Binance_spot"
    basis = "EET/EEST server-time (UTC+2 winter/+3 summer) — col 'timestamp_utc' is a MISNOMER" if is_mt5 else "true UTC"
    floor = (r.get("spread_min_liquidhrs") is not None and r.get("spread_min_liquidhrs") > 0) if is_mt5 else "N/A"
    note = []
    if label == "BTCUSD_mt5":
        note.append("first bar 2018-11-20 anomalous (tick_vol 10.8M, range 4298-5044); Sat weekend halt")
    if label == "XAUUSD":
        note.append("ONLY instrument with populated real_volume (max 467462)")
    if grp == "mt5_ftmo" and r.get("completeness_pct_24x5", 0) and r["completeness_pct_24x5"] < 70:
        note.append("low completeness = cash-index session hours, not 24x5 (expected)")
    if not is_mt5:
        note.append("spread hardcoded 0; no real_volume col; tick_volume=n_trades; 24/7 no weekend gap")
    rows.append({
        "instrument": label, "group": grp, "source_guess": src,
        "first": r.get("first_ts"), "last": r.get("last_ts"), "rows": r.get("rows"),
        "completeness_pct": r.get("completeness_pct_24x5"), "resolution": reso(r),
        "timestamp_basis": basis,
        "spread_units": "MT5 integer points" if is_mt5 else "N/A (const 0)",
        "spread_min": r.get("spread_min"), "spread_median": r.get("spread_p50"),
        "spread_median_pips": (r.get("spread_p50_pips") if label in FX else None),
        "spread_round_mult5_frac": (round(r["spread_mult5_frac"], 2) if r.get("spread_mult5_frac") is not None else None),
        "spread_floor_detected": floor,
        "realvol_all_zero": r.get("realvol_all_zero", "N/A (no col)"),
        "digits": r.get("digits"), "dup_count": r.get("dup_count"),
        "intraweek_gap_count": r.get("intraweek_gap_count"),
        "fingerprinted": "yes", "notes": "; ".join(note),
    })

# Additional Binance instruments (exact bars+range from _downloads_logs/binance_p2.log)
BINANCE = {
    "ADAUSD": (4267215, "2018-04-17", "2026-06-01"), "DOTUSD": (3040808, "2020-08-18", "2026-06-01"),
    "DOGEUSD": (3630247, "2019-07-05", "2026-06-01"), "AVAXUSD": (2991464, "2020-09-22", "2026-06-01"),
    "LINKUSD": (3874223, "2019-01-16", "2026-06-01"), "BNBUSD": (4418085, "2018-01-01", "2026-06-01"),
    "XLMUSD": (4203737, "2018-05-31", "2026-06-01"), "AAVEUSD": (2958698, "2020-10-15", "2026-06-01"),
    "LTCUSD": (4418204, "2018-01-01", "2026-06-01"), "BCHUSD": (3421148, "2019-11-28", "2026-06-01"),
    "XRPUSD": (4242849, "2018-05-04", "2026-06-01"), "DASHUSD": (3772965, "2019-03-28", "2026-06-01"),
    "NEOUSD": (4418338, "2018-01-01", "2026-06-01"), "XMRUSD": (2592510, "2019-03-15", "2024-02-20"),
}
for sym, (n, a, b) in BINANCE.items():
    rows.append({"instrument": sym + "_binance", "group": "binance", "source_guess": "Binance_spot",
                 "first": a, "last": b, "rows": n, "completeness_pct": None, "resolution": "M1",
                 "timestamp_basis": "true UTC", "spread_units": "N/A (const 0)", "spread_min": 0,
                 "spread_median": 0, "spread_median_pips": None, "spread_round_mult5_frac": None,
                 "spread_floor_detected": "N/A", "realvol_all_zero": "N/A (no col)", "digits": None,
                 "dup_count": None, "intraweek_gap_count": None, "fingerprinted": "no (log-inventory)",
                 "notes": "spread hardcoded 0; XMR delisted 2024-02" if sym == "XMRUSD" else "spread hardcoded 0"})

# Dukascopy M5 cache (Forex/data/cache/dukascopy_m5) — separate source, true UTC, NO spread
DUKA_M5 = ["AUDJPY","AUDUSD","CADJPY","EURCHF","EURGBP","EURJPY","GBPJPY","NGAS","NZDUSD",
           "UK100","UKOIL","USDCAD","USDCHF","USDJPY","USOIL","XAGUSD"]
for sym in DUKA_M5:
    last = "2024" if sym == "UK100" else "2026"
    rows.append({"instrument": sym + "_dukascopyM5", "group": "dukascopy_m5_cache",
                 "source_guess": "Dukascopy (bi5 ticks->M5)", "first": "2018", "last": last,
                 "rows": None, "completeness_pct": None, "resolution": "M5", "timestamp_basis": "true UTC",
                 "spread_units": "none (no spread col; cols=OHLC+tick_count)", "spread_min": None,
                 "spread_median": None, "spread_median_pips": None, "spread_round_mult5_frac": None,
                 "spread_floor_detected": "N/A", "realvol_all_zero": "N/A (no col)", "digits": None,
                 "dup_count": None, "intraweek_gap_count": None, "fingerprinted": "no (inventory)",
                 "notes": "P2 pull; overlaps MT5 FX crosses -> spread-calibration window"})
# stray Dukascopy EURUSD 2016 canary
rows.append({"instrument": "EURUSD_dukascopyM5", "group": "dukascopy_m5_cache",
             "source_guess": "Dukascopy (bi5->M5)", "first": "2016", "last": "2016", "rows": None,
             "completeness_pct": None, "resolution": "M5", "timestamp_basis": "true UTC",
             "spread_units": "none", "spread_min": None, "spread_median": None, "spread_median_pips": None,
             "spread_round_mult5_frac": None, "spread_floor_detected": "N/A", "realvol_all_zero": "N/A",
             "digits": None, "dup_count": None, "intraweek_gap_count": None, "fingerprinted": "no",
             "notes": "1-year canary only (2016)"})

# Dukascopy M1 raw (data/raw/dukascopy_*) — EURUSD/GBPUSD, M1, true UTC, vol col, NO spread
for sym, n in [("EURUSD", 1821026), ("GBPUSD", None)]:
    rows.append({"instrument": sym + "_dukascopyM1_raw", "group": "data_raw_dukascopy",
                 "source_guess": "Dukascopy (M1)", "first": "2020", "last": "2024", "rows": n,
                 "completeness_pct": None, "resolution": "M1", "timestamp_basis": "true UTC",
                 "spread_units": "none (cols=OHLC+volume)", "spread_min": None, "spread_median": None,
                 "spread_median_pips": None, "spread_round_mult5_frac": None, "spread_floor_detected": "N/A",
                 "realvol_all_zero": "N/A (no col)", "digits": 5, "dup_count": None,
                 "intraweek_gap_count": None, "fingerprinted": "no (schema-only)",
                 "notes": "distinct from M5 cache; 2020-2024 only"})

with open(OUTCSV, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    for r in rows:
        w.writerow(r)
print(f"WROTE {OUTCSV}  ({len(rows)} instrument rows)")
print(f"  fingerprinted(full): {sum(1 for r in rows if r['fingerprinted']=='yes')}")
print(f"  inventory rows: {sum(1 for r in rows if r['fingerprinted']!='yes')}")
