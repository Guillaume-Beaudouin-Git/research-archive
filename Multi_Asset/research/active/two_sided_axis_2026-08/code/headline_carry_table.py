"""The headline: carry bill as a function of the short fraction — with FLAT
treated as the third sign, which is what the book actually uses.

A sleeve holds a position on a fraction `d` of nights (duty cycle) and, among
those, is short a fraction `f`. Its carry bill is

    carry(d, f) = d * [ (1-f) * swap_long + f * swap_short ]

Flat nights cost exactly zero. The book's long-only sleeves are long-OR-FLAT,
so the real alternative to the expensive long side is not the cheap short side
— it is no side at all.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
PCACHE = MAIN / "data/ftmo_portfolio/cache"
OUT = Path(__file__).resolve().parent.parent

BOOK = ["US100", "GER40", "XAUUSD", "USDJPY"]
NIGHTS = 365.0


def main():
    sL = pd.read_parquet(PCACHE / "panel_swapL.parquet")
    sS = pd.read_parquet(PCACHE / "panel_swapS.parquet")

    eras = {"full 2013-2026": slice("2013-01-01", None),
            "ZIRP 2013-2021": slice("2013-01-01", "2021-12-31"),
            "high-rate 2023-2026": slice("2023-01-01", None)}

    rows = []
    for sym in BOOK:
        for ename, esl in eras.items():
            a, b = float(sL[sym].loc[esl].mean()), float(sS[sym].loc[esl].mean())
            rec = {"symbol": sym, "era": ename,
                   "swap_long_bps_night": round(a, 4),
                   "swap_short_bps_night": round(b, 4)}
            for f in (0.0, 0.25, 0.50, 0.75, 1.0):
                rec[f"carry_pct_yr_f={f:.2f}"] = round(((1 - f) * a + f * b) * NIGHTS / 100, 2)
            rec["carry_pct_yr_FLAT"] = 0.0
            f_star = (-a / (b - a)) if b > 0 else np.nan
            rec["breakeven_short_fraction"] = round(f_star, 4) if (
                b > 0 and f_star <= 1) else "unreachable"
            rows.append(rec)
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "headline_carry_by_short_fraction.csv", index=False)

    # duty-cycle view: what the book actually pays vs its alternatives
    duty = []
    for sym in BOOK:
        a = float(sL[sym].loc["2023":].mean())
        b = float(sS[sym].loc["2023":].mean())
        for d in (1.00, 0.60, 0.40):
            for f, lbl in ((0.0, "long-only"), (0.5, "50/50 two-sided"), (1.0, "short-only")):
                duty.append({"symbol": sym, "duty_cycle": d, "policy": lbl,
                             "carry_pct_yr": round(d * ((1 - f) * a + f * b) * NIGHTS / 100, 2)})
    pd.DataFrame(duty).to_csv(OUT / "carry_by_duty_cycle.csv", index=False)

    print(df.to_string(index=False))
    print("\n=== carry bill by duty cycle x sign policy, high-rate era ===")
    print(pd.DataFrame(duty).pivot_table(index=["symbol", "duty_cycle"],
                                         columns="policy", values="carry_pct_yr").to_string())


if __name__ == "__main__":
    main()
