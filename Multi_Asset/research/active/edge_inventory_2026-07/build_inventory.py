#!/usr/bin/env python3
"""Consolidate the pipe-delimited collection files into INVENTORY.csv.

Pure I/O: reads rows_0*.psv, writes INVENTORY.csv. No backtest, no data access,
no contribution to n_tests. Run with /usr/bin/python3 from this directory.
"""
from __future__ import annotations

import csv
import pathlib

HERE = pathlib.Path(__file__).resolve().parent

COLUMNS = [
    "id", "name", "family", "instruments", "window", "N", "sharpe", "t_stat",
    "maxdd", "cost_assumed", "origin_verdict", "kill_reason", "kill_class",
    "reopenable", "source",
]

# Futures-vehicle mapping for the entries whose kill was FTMO-specific (L51/L53).
# Notional anchors marked (M) are measured in-repo (growth_engine survival-core,
# 2026-07-18, real prices); the others are NOT scraped this session -> verify.
VEHICLE = {
    "E001": "ZN 10y (~$119k notional, margin ~$1.8k = 14% of EUR13k) -- FITS, deployed",
    "E002": "MGC micro gold ~$40k/lot (M). Margin fits EUR13k; notional forces ~3x gross -> granularity, not margin, binds",
    "E003": "SIL micro silver (1000oz). Notional NOT scraped -- verify; SI full (5000oz) does NOT fit EUR13k",
    "E004": "MCL micro WTI ~$8-14k/lot (M) -- FITS cleanly, best granularity of the family",
    "E005": "MZS micro soybean (500bu, 1/10 of ZS) -- likely fits; ZS full does NOT. Report already recommends ZS/MZS at ~1.5bps",
    "E006": "SIL micro silver -- same caveat as E003",
    "E007": "Platinum PL (50oz) -- no micro contract; notional likely > EUR13k -> MATERIALLY DEAD at this capital",
    "E008": "MGC micro gold ~$40k/lot (M) -- fits on margin, chunky on notional",
    "E009": "basket needs >=3 legs incl. Pt -> blocked by E007; degrade to MGC+SIL only",
    "E012": "MNQ/MGC/M6E/MCL micros (multi-instrument by construction) -- granularity is the open question",
    "E013": "idem E012",
    "E014": "MNQ ~$40k/lot (M, MES $38k) -- 1 lot on EUR13k = ~3x gross; ETF QQQ is the alternative but that is the cost that killed it",
    "E015": "VX / VXM (mini VIX future) -- VIXY ETF also available on IBKR; margin fits",
    "E016": "MES micro S&P ~$38k/lot (M) -- fits on margin",
    "E017": "VX / VXM future or VIXY ETF -- fits",
    "E018": "MNQ ~$40k/lot (M) -- fits on margin",
    "E020": "ZN/ZF/ZB or micro-yield 10Y (~$320 margin) -- FITS (same family as E001)",
    "M005": "MGC + SIL two-leg -- both micro; margin fits, 2-leg notional ~$75k = 5.8x on EUR13k -> tight",
    "M053": "FULL-size futures required (CL/BZ, ZC/ZW, RB/HO) -- does NOT fit EUR13k (measured: ~EUR247k notional for the 5-spread book)",
}


def read_rows(path: pathlib.Path, expect_header: bool) -> list[dict[str, str]]:
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if expect_header:
        lines = lines[1:]
    out = []
    for ln in lines:
        parts = ln.split("|")
        if len(parts) != len(COLUMNS):
            raise ValueError(f"{path.name}: expected {len(COLUMNS)} fields, got {len(parts)}: {parts[0]}")
        out.append(dict(zip(COLUMNS, parts)))
    return out


def main() -> None:
    rows: list[dict[str, str]] = []
    rows += read_rows(HERE / "rows_01_strong.psv", expect_header=True)
    rows += read_rows(HERE / "rows_02_mecanique.psv", expect_header=False)
    rows += read_rows(HERE / "rows_03_reste.psv", expect_header=False)

    for r in rows:
        r["futures_vehicle_fits_13k"] = VEHICLE.get(r["id"], "n/a")

    out = HERE / "INVENTORY.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS + ["futures_vehicle_fits_13k"])
        w.writeheader()
        w.writerows(rows)

    print(f"{len(rows)} entries -> {out}")
    from collections import Counter
    c = Counter(r["kill_class"].split("(")[0].split("+")[0].strip() for r in rows)
    for k, v in c.most_common():
        print(f"  {v:3d}  {k}")


if __name__ == "__main__":
    main()
