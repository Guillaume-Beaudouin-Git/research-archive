"""
ORB production-ledger placement inside this grid's own empirical t-distribution
(PREREGISTRATION.md §8). Not a grid cell -- an external comparator, computed with this study's
own `engine.stats.hac_tstat` for a same-yardstick comparison against `grille_resultats.csv`.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "yt_strategy_replications"))
from engine import stats as S

LEDGER = Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/program_2026-06/"
              "ftmo_research/audit/nq_v2_trades.parquet")


def main():
    df = pd.read_parquet(LEDGER)
    rows = {}
    for name, sub in [("both", df), ("long", df[df.direction == 1]), ("short", df[df.direction == -1])]:
        arr = sub["r_gross"].to_numpy(float)
        m, t = S.hac_tstat(arr, lags=6)
        rows[name] = dict(n=len(sub), mean_R=float(arr.mean()), hac_mean_R=float(m), hac_t=float(t))
        print(name, rows[name])

    grid = pd.read_csv(HERE / "grille_resultats.csv")
    for leg, col in [("both", "gross_t"), ("long", "long_t"), ("short", "short_t")]:
        vals = grid[col].dropna().to_numpy()
        t_orb = rows[leg]["hac_t"]
        pct = float((vals <= t_orb).mean()) * 100
        print(f"ORB {leg} t={t_orb:+.3f} -> percentile {pct:.1f} of this grid's {col} "
              f"(n={len(vals)}, grid mean={vals.mean():+.3f}, grid max={vals.max():+.3f})")

    # same-family comparison: construction B only (closest mechanism analogue)
    b = grid[grid["construction"] == "B"]
    for leg, col in [("both", "gross_t"), ("long", "long_t"), ("short", "short_t")]:
        vals = b[col].dropna().to_numpy()
        t_orb = rows[leg]["hac_t"]
        pct = float((vals <= t_orb).mean()) * 100
        print(f"[construction B only] ORB {leg} t={t_orb:+.3f} -> percentile {pct:.1f} "
              f"of construction-B's {col} (n={len(vals)}, mean={vals.mean():+.3f}, max={vals.max():+.3f})")

    out = pd.DataFrame(rows).T
    out.to_csv(HERE / "orb_reference.csv")


if __name__ == "__main__":
    main()
