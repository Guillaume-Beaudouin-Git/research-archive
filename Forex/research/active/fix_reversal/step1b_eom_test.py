"""
step1b_eom_test.py — Month/Quarter-end up-sizing test for fix-reversal.

Practitioner brief asks for month/quarter-end up-sizing (E postmortem noted ~15 bp
gross on EOM days vs 1-4 bp intra-month). Quick due-diligence: does the EOM
subset produce a gross/trade large enough to amortise FTMO MT5 cost (~2.23 bps RT
at London fix)?

If EOM gross >> cost → reconsider verdict.
If EOM gross still in same ~bps range → confirm NO-GO.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

OUTDIR = Path(__file__).resolve().parent
import sys
sys.path.insert(0, str(OUTDIR))
from step1_backtest import (load_panel, load_costs, backtest_fix,
                            t_hac, sharpe)


def filter_eom(trades: pd.DataFrame, mode: str) -> pd.DataFrame:
    """
    mode='eom'        : last 3 business days of each calendar month
    mode='qom_quarter': last 3 b-days of Mar/Jun/Sep/Dec
    """
    dates = pd.DatetimeIndex(trades["date"])
    out_mask = np.zeros(len(trades), dtype=bool)
    for period, period_dates in [(p, dates[dates.to_period("M") == p])
                                  for p in dates.to_period("M").unique()]:
        last_3 = period_dates[-3:]
        if mode == "qom_quarter":
            if period.month not in (3, 6, 9, 12):
                continue
        for d in last_3:
            out_mask |= (dates == d)
    return trades.loc[out_mask].copy()


def main() -> None:
    prices = load_panel()["close"]
    costs = load_costs()
    cs = costs["cost_stack_RT_bps"]
    cost_london = cs["London_fix_p95"]["total_markup1"]
    cost_ecb    = cs["ECB_fix_p95_winter"]["total_markup1"]
    cost_tokyo  = cs["Tokyo_fix_p95"]["total_markup1"]

    print(f"[load] {len(prices):,} M1 bars\n")

    rows_all = []
    for fix, cost in [("london", cost_london), ("ecb", cost_ecb),
                      ("tokyo", cost_tokyo)]:
        full = backtest_fix(prices, fix, cost, delay_minutes=0)
        for mode_label, subset in [
            ("ALL",       full),
            ("EOM (last 3 b-days)",   filter_eom(full, "eom")),
            ("QoQ-EOM (Mar/Jun/Sep/Dec last 3)", filter_eom(full, "qom_quarter")),
        ]:
            g = subset["gross"].values
            n = subset["net"].values
            row = {"fix": fix, "subset": mode_label, "N": int(len(subset)),
                   "gross_bps": round(float(np.nanmean(g)) * 1e4, 2)
                                  if len(g) else float("nan"),
                   "net_bps":   round(float(np.nanmean(n)) * 1e4, 2)
                                  if len(n) else float("nan"),
                   "gross_t":   round(t_hac(g), 2) if len(g) else float("nan"),
                   "net_t":     round(t_hac(n), 2) if len(n) else float("nan"),
                   "gross_SR":  round(sharpe(g, 252), 2) if len(g) else float("nan"),
                   "net_SR":    round(sharpe(n, 252), 2) if len(n) else float("nan")}
            rows_all.append(row)

    df = pd.DataFrame(rows_all)
    print(df.to_string(index=False))
    df.to_csv(OUTDIR / "step1b_eom_results.csv", index=False)
    print(f"\nsaved → {OUTDIR / 'step1b_eom_results.csv'}")


if __name__ == "__main__":
    main()
