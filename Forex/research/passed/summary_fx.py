"""
summary_fx.py
=============
Reads results.json from the 3 FX feasibility scripts and prints
a unified comparison table.

Run AFTER the 3 feasibility.py have completed and saved their JSON.
    python -m Forex.research.passed.fx_carry_fred.feasibility
    python -m Forex.research.passed.fx_momentum_monthly.feasibility
    python -m Forex.research.passed.fx_carry_em.feasibility
    python Forex/research/passed/summary_fx.py
"""

from __future__ import annotations

import json
from pathlib import Path

BASE = Path(__file__).parent

SOURCES = [
    ("fx_carry_fred/results.json",        "single"),   # single signal
    ("fx_momentum_monthly/results.json",  "dual"),     # has momentum_cs + tsmom
    ("fx_carry_em/results.json",          "single_em"),
]


def _row(name: str, freq: str, sharpe, max_dd, ic, t, gate) -> str:
    def f(x, w, prec):
        if x is None or (isinstance(x, float) and (x != x)):
            return " " * w
        if isinstance(x, float):
            return f"{x:>{w}.{prec}f}"
        return f"{str(x):>{w}s}"
    return (
        f"│ {name:<28s} │ {freq:<7s} │ {f(sharpe, 6, 2)} │ "
        f"{f(max_dd, 7, 3)} │ {f(ic, 6, 4)} │ {f(t, 6, 2)} │ {gate:<4s} │"
    )


def _load(rel: str):
    p = BASE / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def collect() -> list[tuple]:
    rows = []
    for rel, kind in SOURCES:
        r = _load(rel)
        if r is None:
            rows.append((rel, None))
            continue
        if kind == "dual":
            rows.append(("Momentum CS 12M-1M (G10)", "monthly",
                         r["momentum_cs"]["sharpe"], r["momentum_cs"]["max_dd"],
                         r["momentum_cs"]["ic_mean"], r["momentum_cs"]["ic_tstat"],
                         r["momentum_cs"]["gate"]))
            rows.append(("TSMOM tanh 12M (G10)", "monthly",
                         r["tsmom"]["sharpe"], r["tsmom"]["max_dd"],
                         r["tsmom"]["ic_mean"], r["tsmom"]["ic_tstat"],
                         r["tsmom"]["gate"]))
        elif kind == "single":
            rows.append(("Carry FRED 3M (G10)", r["freq"],
                         r["sharpe"], r["max_dd"],
                         r["ic_mean"], r["ic_tstat"], r["gate"]))
        elif kind == "single_em":
            # Primary table uses 4W IC for EM (matches monthly Menkhoff style)
            rows.append(("Carry G10 + EM", r["freq"],
                         r["sharpe"], r["max_dd"],
                         r["h4w_ic_mean"], r["h4w_ic_tstat"], r["gate"]))
    return rows


def main():
    rows = collect()

    print()
    print("┌──────────────────────────────┬─────────┬────────┬─────────┬────────┬────────┬──────┐")
    print("│ Signal                       │ Freq    │ Sharpe │ MaxDD   │ IC     │ t-stat │ Gate │")
    print("├──────────────────────────────┼─────────┼────────┼─────────┼────────┼────────┼──────┤")
    for r in rows:
        if isinstance(r, tuple) and len(r) == 2 and r[1] is None:
            print(f"│ MISSING: {r[0]:<69s} │")
            continue
        print(_row(*r))
    print("└──────────────────────────────┴─────────┴────────┴─────────┴────────┴────────┴──────┘")
    print()
    print("Gate: PASS (t>2.5)  WEAK (1.5<t<=2.5)  SKIP (t<=1.5)")
    print()

    # EM-specific crash report
    em = _load("fx_carry_em/results.json")
    if em and "crashes" in em:
        print("EM CARRY — CRASH PERIOD ANALYSIS")
        print("─" * 72)
        for cn, cv in em["crashes"].items():
            if "max_dd" not in cv:
                print(f"  {cn:<14s} {cv.get('note', 'n/a')}")
                continue
            print(f"  {cn:<14s} period {cv['period']}  "
                  f"Sharpe={cv['sharpe']:+.2f}  MaxDD={cv['max_dd']:+.3f}  "
                  f"CumRet={cv['cum_ret']:+.3f}")
        propfirm = em.get("propfirm_compatible", False)
        print()
        print(f"  Propfirm-compatible (COVID MaxDD > -25%): {propfirm}")
        print("─" * 72)


if __name__ == "__main__":
    main()
