"""
certify_all.py — assemble puis certifie chaque paire acquise, écrit un JSON par
paire dans Forex/research/active/dedale_data_2026-08/certification/<PAIR>.json.

Ne re-télécharge rien : lit ce qui est déjà dans scratchpad/duka_raw (par symbole x
année) et scratchpad/m1_cache (legs majeures déjà présentes : EURUSD, GBPUSD,
USDJPY, USDCAD, USDCHF, AUDUSD, NZDUSD, EURGBP, AUDJPY).

Usage: /usr/bin/python3 certify_all.py [--symbol GBPJPY ...]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import download_pairs as dp
import quality_checks as qc

OUT_DIR = Path(__file__).parent.parent / "certification"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR = dp.CACHE_DIR

# formule de cohérence croisée: (jambe1, op, jambe2)
CROSS_FORMULA: dict[str, tuple[str, str, str]] = {
    "GBPJPY": ("GBPUSD", "mul", "USDJPY"),
    "CADJPY": ("USDJPY", "div", "USDCAD"),
    "NZDJPY": ("NZDUSD", "mul", "USDJPY"),
    "CHFJPY": ("USDJPY", "div", "USDCHF"),
    "EURAUD": ("EURUSD", "div", "AUDUSD"),
    "EURCAD": ("EURUSD", "mul", "USDCAD"),
    "EURCHF": ("EURUSD", "mul", "USDCHF"),
    "GBPAUD": ("GBPUSD", "div", "AUDUSD"),
    "GBPCAD": ("GBPUSD", "mul", "USDCAD"),
    "GBPCHF": ("GBPUSD", "mul", "USDCHF"),
    "AUDCAD": ("AUDUSD", "mul", "USDCAD"),
    "AUDCHF": ("AUDUSD", "mul", "USDCHF"),
    "AUDNZD": ("AUDUSD", "div", "NZDUSD"),
    "NZDCAD": ("NZDUSD", "mul", "USDCAD"),
}


def load_leg(name: str) -> pd.DataFrame | None:
    p = CACHE_DIR / f"{name}_M1.parquet"
    if not p.exists():
        return None
    return pd.read_parquet(p)


def certify(sym: str) -> dict:
    out_pq = dp.assemble(sym)
    if out_pq is None:
        return dict(sym=sym, status="NO_RAW_DATA")
    df = pd.read_parquet(out_pq)

    result: dict = dict(sym=sym, rows=len(df),
                         start=str(df.index.min()), end=str(df.index.max()))

    result["flat_pct_by_year"] = qc.flat_pct_by_year(df).to_dict()
    result["max_flat_pct_year"] = max(result["flat_pct_by_year"].values()) if result["flat_pct_by_year"] else None

    result["gaps"] = qc.gap_report(df)

    start_s, end_s = df.index.min().strftime("%Y-%m-%d"), df.index.max().strftime("%Y-%m-%d")
    result["weekday_coverage"] = qc.weekday_coverage(df, start_s, end_s)

    if sym in CROSS_FORMULA:
        leg1_name, op, leg2_name = CROSS_FORMULA[sym]
        leg1, leg2 = load_leg(leg1_name), load_leg(leg2_name)
        if leg1 is not None and leg2 is not None:
            result["cross_check"] = dict(formula=f"{leg1_name} {op} {leg2_name}",
                                          **qc.cross_check(df, leg1, leg2, op))
        else:
            result["cross_check"] = dict(note=f"missing leg(s): "
                                          f"{leg1_name if leg1 is None else ''} "
                                          f"{leg2_name if leg2 is None else ''}")

    with open(OUT_DIR / f"{sym}.json", "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"  {sym}: {result['rows']:,} rows, max flat% {result['max_flat_pct_year']}, "
          f"illegit gaps {result['gaps']['n_illegit_gaps']}, "
          f"weekday missing {result['weekday_coverage']['pct_missing']}%")
    if "cross_check" in result:
        print(f"    cross-check: {result['cross_check']}")
    return result


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", nargs="*", default=None)
    a = ap.parse_args()
    syms = a.symbol or sorted(dp.NEW_INSTR)
    for s in syms:
        try:
            certify(s)
        except Exception as e:
            print(f"  {s}: ERROR {e}")


if __name__ == "__main__":
    main()
