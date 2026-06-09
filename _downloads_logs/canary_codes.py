"""Validate Dukascopy URL codes by fetching 3 liquid hours of a recent trading day.

Codes returning 0 ticks across all hours = WRONG. Codes returning >0 ticks at any
hour = VALID.

Run: /usr/bin/python3 _downloads_logs/canary_codes.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Forex" / "data"))

import requests

from dukascopy_downloader_m5 import _fetch_hour  # noqa: E402

TEST_DAY = date(2026, 6, 2)  # Tuesday 2026-06-02, recent active session
TEST_HOURS = [8, 13, 15]  # London open, NY open, mid-afternoon (UTC)

# Codes flagged as "best-guess" in dukascopy_downloader_m5.py
SUSPECT_CODES: dict[str, str] = {
    # Energies
    "USOIL":  "LIGHTCMDUSD",
    "UKOIL":  "BRENTCMDUSD",
    "NGAS":   "GASCMDUSD",
    # Indices ex-US/GER
    "UK100":  "GBRIDXGBP",
    "FRA40":  "FRAIDXEUR",
    "JP225":  "JPNIDXJPY",
    "AUS200": "AUSIDXAUD",
    "EU50":   "EUSIDXEUR",
    "HK50":   "HKGIDXHKD",
}

# Alternative Dukascopy codes to try when the primary fails (per Dukascopy
# public instrument list — verify with --canary if needed).
ALT_CODES: dict[str, list[str]] = {
    "USOIL":  ["LIGHTCMDUSX", "LIGHT_CMDUSD", "USOIL"],
    "UKOIL":  ["BRENTCMDUSX", "BRENT_CMDUSD", "UKOIL"],
    "NGAS":   ["GASCMDUSX", "GAS_CMDUSD", "NGAS"],
    "UK100":  ["GBRIDXGBP", "UK100GBPIDX", "GBR100GBP", "FTS100", "UK100"],
    "FRA40":  ["FRA40EURIDX", "FRA40EUR", "CAC40", "FRA40"],
    "JP225":  ["JPN225JPYIDX", "JPN225JPY", "JPN225", "NKY225"],
    "AUS200": ["AUS200AUDIDX", "AUS200AUD", "ASX200", "AUS200"],
    "EU50":   ["EUSTX50EURIDX", "EUSTX50EUR", "STOXX50E", "EU50EUR", "EU50"],
    "HK50":   ["HKG33HKDIDX", "HKG33HKD", "HSI", "HK50HKD", "HK50"],
}


def test_code(name: str, code: str) -> tuple[bool, int]:
    sess = requests.Session()
    total_ticks = 0
    for h in TEST_HOURS:
        ticks = _fetch_hour(code, TEST_DAY, h, sess)
        total_ticks += len(ticks)
    return total_ticks > 0, total_ticks


def main() -> None:
    print(f"Canary test day: {TEST_DAY} (UTC hours: {TEST_HOURS})")
    print("=" * 72)

    results: dict[str, tuple[str, bool, int]] = {}
    for name, primary in SUSPECT_CODES.items():
        ok, n = test_code(name, primary)
        status = "OK  " if ok else "FAIL"
        print(f"  [{status}] {name:6}  primary='{primary:20}'  ticks={n}")
        results[name] = (primary, ok, n)

    fails = {n: r for n, r in results.items() if not r[1]}
    if not fails:
        print("\nAll primary codes valid.")
        return

    print("\n" + "=" * 72)
    print(f"FAILED primary codes ({len(fails)}): {sorted(fails.keys())}")
    print("Trying alternatives …\n")

    fixes: dict[str, str] = {}
    for name in fails:
        for alt in ALT_CODES.get(name, []):
            if alt == results[name][0]:  # already tested as primary
                continue
            ok, n = test_code(name, alt)
            mark = "OK  " if ok else "fail"
            print(f"  [{mark}] {name:6}  alt='{alt:20}'  ticks={n}")
            if ok:
                fixes[name] = alt
                break

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for name, (primary, ok, n) in results.items():
        if ok:
            print(f"  KEEP   {name:6} = '{primary}'  ({n} ticks)")
        elif name in fixes:
            print(f"  FIX    {name:6}: '{primary}' -> '{fixes[name]}'")
        else:
            print(f"  ORPHAN {name:6}: '{primary}' fails, NO valid alt found")


if __name__ == "__main__":
    main()
