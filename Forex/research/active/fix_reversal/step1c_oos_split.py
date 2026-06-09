"""
step1c_oos_split.py — Diagnostic: pre/post 2022 gross split (alpha decay vs uniform low edge).

If gross stays low uniformly: L23/L23b — institutional ≠ retail edge, no decay angle.
If gross was high pre-2022 and collapses post: L31 alpha-decay (post-publication).
"""
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

OUTDIR = Path(__file__).resolve().parent
sys.path.insert(0, str(OUTDIR))
from step1_backtest import load_panel, load_costs, backtest_fix, t_hac, sharpe


def main() -> None:
    prices = load_panel()["close"]
    costs = load_costs()
    cs = costs["cost_stack_RT_bps"]
    fix_costs = {"london": cs["London_fix_p95"]["total_markup1"],
                 "ecb":    cs["ECB_fix_p95_winter"]["total_markup1"],
                 "tokyo":  cs["Tokyo_fix_p95"]["total_markup1"]}

    rows = []
    for fix, cost in fix_costs.items():
        full = backtest_fix(prices, fix, cost, delay_minutes=0)
        full["date"] = pd.to_datetime(full["date"])
        for label, start, end in [
            ("2018-2020", "2018-01-01", "2020-12-31"),
            ("2021-2022", "2021-01-01", "2022-12-31"),
            ("2023-2024", "2023-01-01", "2024-12-31"),
            ("2025-2026", "2025-01-01", "2026-12-31"),
        ]:
            sub = full[(full["date"] >= start) & (full["date"] <= end)]
            g = sub["gross"].values
            rows.append({"fix": fix, "period": label, "N": int(len(sub)),
                         "gross_bps": round(float(np.nanmean(g)) * 1e4, 2)
                                        if len(g) else float("nan"),
                         "gross_t":   round(t_hac(g), 2) if len(g) else float("nan"),
                         "gross_SR":  round(sharpe(g, 252), 2)
                                        if len(g) else float("nan")})
    df = pd.DataFrame(rows)
    print(df.to_string(index=False))
    df.to_csv(OUTDIR / "step1c_oos_split.csv", index=False)


if __name__ == "__main__":
    main()
