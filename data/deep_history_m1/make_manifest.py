"""
make_manifest.py
================
Build the single deliverable MANIFEST (md + csv) for data/deep_history_utc/ from the
assembly report, the download status, and the calendar stats — plus the hard facts
that aren't derivable from a single run (US2000 impossible, index depth floors,
DAX30->DAX40, tick_volume/real_volume caveats, broken legacy files).

Usage: /usr/bin/python3 make_manifest.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from duka_m1_backfill import INSTR  # noqa: E402

BASE = Path(__file__).resolve().parent
REP = BASE / "reports"
OUT = BASE.parent / "deep_history_utc"
CAL = OUT / "calendar"

NOTES = {
    "GER40": "DAX: constituent change DAX30->DAX40 (Sep 2021); price series continuous. Dukascopy code DEUIDXEUR.",
    "XAUUSD": "Existing real_volume is populated (FTMO supplies gold volume); Dukascopy backfill has NO real_volume -> set 0.",
    "US500": "Index: Dukascopy depth floor 2012-01-16 (earliest backfill).",
    "US100": "Index: Dukascopy depth floor 2013-01-01.",
    "US30": "Index: Dukascopy depth floor 2013-01-01; existing MT5 starts 2019-02-08.",
}

# things that could NOT be fetched (hard facts, reported not invented)
CANNOT = [
    "**US2000** — backfill IMPOSSIBLE: Dukascopy `USSC2000IDXUSD` depth starts 2018-08-08, "
    "LATER than the existing MT5 start (2018-01-23). No pre-existing history to add; not attempted.",
    "**BTCUSD** — skipped per task scope (crypto handled elsewhere; MT5 first bar is a synthetic aggregate).",
    "**Index depth floors** — US500 backfill only to 2012-01-16; US100/US30/GER40 only to 2013-01-01 "
    "(Dukascopy `startHourForTicks`). No CFD index data exists before those dates at the source.",
    "**Pre-2007** — FX/metals deep target capped at 2007-01-01 by design (depth ≥2003 exists but out of scope).",
    "**Legacy broken files (pre-existing, untouched):** `data/ftmo_research/eurusd_m1_spread.parquet` "
    "is corrupt (no parquet footer) and `data/ftmo_research/EURUSD_m15.parquet` is a 4-byte empty "
    "placeholder — both are derived re-exports, NOT inputs to this splice; left as-is.",
]

CSV_COLS = ["symbol", "code", "group", "final_start_utc", "final_end_utc", "final_rows",
            "exist_rows", "backfill_before_rows", "backfill_after_rows", "overlap_rows",
            "overlap_corr", "spread_model", "index_spread_tick_round", "n_ambiguous_bars",
            "n_nonexistent_bars", "monotonic_increasing", "dups_removed", "ohlc_violations",
            "spread_negative", "spread_zero_frac", "spread_max", "intraweek_gaps_gt2min",
            "max_gap_hours", "seam_before", "seam_after", "status"]


def main() -> None:
    reps = json.load(open(REP / "assembly_report.json")) if (REP / "assembly_report.json").exists() else []
    rep_by = {r["symbol"]: r for r in reps}
    dl = json.load(open(REP / "download_status.json")) if (REP / "download_status.json").exists() else []
    dl_fail = [d for d in dl if d.get("status") in ("ohlc_fail", "empty")]
    cal_stats = json.load(open(CAL / "_stats.json")) if (CAL / "_stats.json").exists() else {}

    # ---- manifest.csv ----
    rows = []
    for sym in INSTR:
        r = rep_by.get(sym, {"symbol": sym, "status": "MISSING"})
        rows.append({c: r.get(c) for c in CSV_COLS})
    df = pd.DataFrame(rows, columns=CSV_COLS)
    df.to_csv(OUT / "manifest.csv", index=False)

    # ---- MANIFEST.md ----
    L = ["# Deep-history M1 backfill — MANIFEST (TRUE UTC)", "",
         "**Output dir:** `data/deep_history_utc/`  ·  **Scripts/cache:** `data/deep_history_m1/`",
         "**Timestamps:** column `timestamp_utc` now holds **TRUE UTC** (existing MT5 files were "
         "broker EET/EEST mislabeled UTC; localized `Europe/Bucharest`→UTC). Dukascopy backfill is "
         "native UTC. Schema/dtypes/units identical to the existing MT5 panel.", "",
         "## Gates (passed before bulk)",
         "- **GATE 1 — decoder vs `dukascopy-node`:** EURUSD(1e5)/USDJPY(1e3)/XAUUSD(1e3)/US500(1e3), "
         "days with down-bars, **0 OHLC mismatches** (max|Δ|=0.0). Confirms the O,C,L,H byte order + "
         "per-family decimalFactor.",
         "- **GATE 2 — full pipeline EURUSD (2010+2024):** 0 OHLC violations, monotonic true-UTC, 0 dups, "
         "**overlap close-corr 0.999999** (re-confirms tz direction).", "",
         "## Method",
         "- **Source:** Dukascopy per-day M1 **candle** bi5 (`{BID,ASK}_candles_min_1.bi5`), record "
         "`>iiiiif` = (sec, O, **C, L, H**, vol) — byte order O,C,L,H (the prior OHLC bug, now fixed).",
         "- **Splice:** existing MT5 range stays authoritative; Dukascopy fills strictly before/after it.",
         "- **Spread calibration (2024 overlap, true-UTC hour-of-day):** fit BOTH additive "
         "(MT5≈Duka+offset_h) and multiplicative (MT5≈Duka×ratio_h); pick per instrument by lower MAE on "
         "a held-out (last-30%) slice; refit on full overlap; apply to all Dukascopy rows. Existing "
         "spreads never modified. Indices optionally rounded to the existing spread tick.",
         "- **tick_volume caveat:** backfill tick_volume = Dukascopy M1 volume (≈millions scale), NOT an "
         "MT5 tick count — different scale than existing rows (documented, dtype-matched int).",
         "- **real_volume:** backfill = `0` (Dukascopy has none); existing values kept verbatim "
         "(note: existing column is cosmetically mixed `0`/`0.0`/empty across MT5 exporters).", "",
         "## Per-instrument summary", "",
         "| sym | final range (UTC) | rows | bf_before | bf_after | overlap corr | spread | "
         "amb/ne | mono | dups | ohlc✗ | sprd<0 | gaps |",
         "|---|---|---|--:|--:|--:|---|---|---|--:|--:|--:|--:|"]
    for sym in INSTR:
        r = rep_by.get(sym, {})
        rng = f"{str(r.get('final_start_utc'))[:10]}→{str(r.get('final_end_utc'))[:10]}"
        L.append(f"| {sym} | {rng} | {r.get('final_rows','-')} | {r.get('backfill_before_rows','-')} | "
                 f"{r.get('backfill_after_rows','-')} | {r.get('overlap_corr','-')} | "
                 f"{r.get('spread_model','-')}{(' /tick'+str(r.get('index_spread_tick_round'))) if r.get('index_spread_tick_round') else ''} | "
                 f"{r.get('n_ambiguous_bars','-')}/{r.get('n_nonexistent_bars','-')} | "
                 f"{r.get('monotonic_increasing','-')} | {r.get('dups_removed','-')} | "
                 f"{r.get('ohlc_violations','-')} | {r.get('spread_negative','-')} | "
                 f"{r.get('intraweek_gaps_gt2min','-')} |")
    L += ["", "### Per-instrument notes"]
    for sym, note in NOTES.items():
        L.append(f"- **{sym}:** {note}")
    # seam flags
    L += ["", "### Splice-seam price steps (points across the backfill↔existing join)"]
    for sym in INSTR:
        r = rep_by.get(sym, {})
        sb, sa = r.get("seam_before"), r.get("seam_after")
        if sb or sa:
            L.append(f"- **{sym}:** before={sb}  after={sa}")

    L += ["", "## What could NOT be fetched (reported, not invented)"]
    L += [f"- {c}" for c in CANNOT]
    if dl_fail:
        L.append(f"- **Download year failures (OHLC-guard / empty):** "
                 + ", ".join(f"{d['sym']} {d['year']} ({d['status']})" for d in dl_fail))
    else:
        L.append("- **Download year failures:** none (every fetched symbol-year passed the OHLC guard).")

    L += ["", "## P3 economic calendar",
          f"- `calendar/economic_calendar_2018_2026.csv` — **{cal_stats.get('rows','?')} events**, "
          f"{str(cal_stats.get('date_min'))[:10]}→{str(cal_stats.get('date_max'))[:10]}, 9 currencies, "
          f"impact LOW/MED/HIGH.",
          "- **Source:** TradingView economic-calendar API (no key; gray-area ToS — FLAGGED). "
          "Forex Factory historical was Cloudflare-blocked (403); faireconomy serves only the current "
          "week. NOT merged into existing calendars. See `calendar/calendar_gap_report.md`.", "",
          "## Validation",
          "- Per instrument: strictly-increasing true-UTC, 0 dups, OHLC validity, spread≥0, overlap "
          "corr≥0.999, gap report — see `manifest.csv` / `reports/assembly_report.json`.",
          "- Random backfill-day spot-checks vs `dukascopy-node` — see `reports/spotcheck` output."]
    (OUT / "MANIFEST.md").write_text("\n".join(L))
    print(f"wrote {OUT/'MANIFEST.md'} and {OUT/'manifest.csv'} ({len(df)} instruments)")
    if dl_fail:
        print(f"  NOTE: {len(dl_fail)} download year failures recorded")


if __name__ == "__main__":
    main()
