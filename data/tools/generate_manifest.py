"""generate_manifest.py — machine-generates data/deep_history_utc/MANIFEST.md.

Coverage claims are NEVER hand-written: they are rendered from
  - data/tools/audit_report.json          (bar-density audit: coverage, gaps, classes)
  - data/deep_history_m1/reports/assembly_report.json   (splice provenance, optional)
  - data/tools/seam_validation_report.json (T4 seam gate, optional)

Regenerate with:
    /usr/bin/python3 data/tools/audit_bar_density.py
    /usr/bin/python3 data/tools/generate_manifest.py

The pre-repair narrative manifest is archived as MANIFEST_pre_repair_2026-06-07.md.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "data/tools/audit_report.json"
ASSEMBLY = REPO / "data/deep_history_m1/reports/assembly_report.json"
SEAMS = REPO / "data/tools/seam_validation_report.json"
OUT = REPO / "data/deep_history_utc/MANIFEST.md"

REPAIR_LOG = [
    "2026-06-10 — stray-masked splice holes repaired: US500 & US100 2018-01-01→2021-09-13, "
    "GER40 2019-12-30→2021-12-28 (+ degraded 2018-2019 weekly windows). Root cause: MT5 "
    "exports carry 1-23 stray bars/day before their true M1 depth; the splice existence "
    "check treated them as coverage and blocked Dukascopy backfill. Fix: density-based "
    "coverage (assemble.py::_dense_start, ≥50% of max(63d rolling, global) median). "
    "Pre-repair files archived as *_M1.csv.pre_repair_backup; before-state audit: "
    "data/tools/audit_report_pre_repair_2026-06-10.{md,json}. Seam gate: "
    "data/tools/seam_validation_report.md.",
]


def main() -> None:
    audit = json.loads(AUDIT.read_text())
    assembly = {}
    if ASSEMBLY.exists():
        assembly = {r["symbol"]: r for r in json.loads(ASSEMBLY.read_text())}
    seams = {}
    if SEAMS.exists():
        seams = {r["symbol"]: r for r in json.loads(SEAMS.read_text())}

    L = [
        "# Deep-history M1 estate — MANIFEST (TRUE UTC) — machine-generated",
        "",
        "> **Do not edit coverage claims by hand.** Regenerate with:",
        "> ```",
        "> /usr/bin/python3 data/tools/audit_bar_density.py",
        "> /usr/bin/python3 data/tools/generate_manifest.py",
        "> ```",
        f"> Generated {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')} from "
        f"`audit_report.json` (audit run: {audit['generated'][:16]}). "
        "Narrative provenance & method history: `MANIFEST_pre_repair_2026-06-07.md` (archived; "
        "its US500/US100/GER40 'no outages' coverage claims were FALSE — see repair log).",
        "",
        "**Timestamps:** `timestamp_utc` holds TRUE UTC (MT5 EET/EEST localized "
        "Europe/Bucharest→UTC at assembly; Dukascopy native UTC).",
        "",
        "## Repair log",
        "",
    ]
    L += [f"- {x}" for x in REPAIR_LOG]
    L += [
        "",
        "## Coverage & integrity (bar-density audit)",
        "",
        "Day flagged if bars < 50% of the instrument's median (weekdays with ≥1 bar). "
        "Window classes: (a) holiday, (b) source floor/ramp, (d) structural source segment "
        "(lower bar count by design, e.g. session-filtered Dukascopy vs 24h MT5), "
        "(c) ANOMALY (genuine hole / unexplained).",
        "",
        "| instrument | coverage | rows | median b/d | flagged d | (c) windows | dense MT5 start | stray dropped | overlap corr | seam gate |",
        "|---|---|--:|--:|--:|--:|---|--:|--:|---|",
    ]
    for r in sorted(audit["results"], key=lambda x: x["instrument"]):
        sym = r["instrument"]
        asm = assembly.get(sym, {})
        sv = seams.get(sym, {})
        L.append(
            f"| {sym} | {r['coverage'][0]}→{r['coverage'][1]} | {r['rows']:,} | "
            f"{r['median_bars_per_day']} | {r['flagged_days']} | {r['n_anomaly_windows']} | "
            f"{str(asm.get('exist_dense_start_utc', '—'))[:10]} | "
            f"{asm.get('stray_rows_dropped', '—')} | {asm.get('overlap_corr', '—')} | "
            f"{sv.get('status', '—')} |")
    L += ["", "## Known gaps & low-density windows (≥2 weekdays, or any anomaly)", ""]
    for r in sorted(audit["results"], key=lambda x: x["instrument"]):
        wins = [w for w in r["windows"]
                if w["weekdays"] >= 2 or w["klass"].startswith("(c)")]
        if not wins:
            continue
        L.append(f"**{r['instrument']}** — " + "; ".join(
            f"{w['start']}→{w['end']} ({w['weekdays']}wd, {w['mean_bars']}b/d, {w['klass']})"
            for w in wins))
        L.append("")
    L += [
        "## Estate notes (static)",
        "",
        "- US2000 absent by design: Dukascopy USSC2000IDXUSD floor 2018-08-08 > MT5 start "
        "2018-01-23 → backfill impossible (class (b)).",
        "- Index Dukascopy segments are session-filtered (≈390-900 bars/day) vs 24h MT5 "
        "(≈1300-1400) → class (d), not holes.",
        "- Commodities are pure-Dukascopy assemblies; their (c) windows are source-side "
        "thin sessions/holidays — no second source exists to repair against.",
        "- Sources: MT5/FTMO-Demo exports (`data/panels/m5_indices/`, raw, read-only) + "
        "Dukascopy M1 candles (`data/deep_history_m1/_cache_duka/`). Pipeline: "
        "`data/deep_history_m1/{duka_m1_backfill,assemble}.py`.",
    ]
    OUT.write_text("\n".join(L) + "\n")
    print(f"manifest -> {OUT}")


if __name__ == "__main__":
    main()
