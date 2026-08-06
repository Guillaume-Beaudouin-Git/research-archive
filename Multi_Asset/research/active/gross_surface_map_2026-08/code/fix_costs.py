"""Recompute the cost floor properly and patch the cost columns of the sweep.

Why this file exists: the MT5 `spread` column is in POINTS, not price units, so
`spread / price * 1e4` is off by the instrument's point size (10^-digits). The
first pass produced 5370 bps for XAGUSD, which is how the error was caught.

Point size is inferred from the data (smallest observed non-zero price increment,
snapped to the nearest power of ten). Validation: the resulting XAUUSD and US500
spreads must reproduce COST_AUDIT.md S3/S2 (0.699 and 0.824 bps) -- they do.

For FX and the indices the fixed table from COST_AUDIT.md is kept, because that
column is zero-inflated there (EURUSD: 48.6% of post-2021 bars carry spread 0)
and any median taken over it is biased LOW.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from build_map import CACHE, CLASS, COST_RT, INSTRUMENTS, OUT, SPLIT

SLIPPAGE_RT_BPS = 1.0  # 2 x 0.5 bps, the provision used by the live sim


def infer_point(px: pd.Series) -> float:
    d = np.abs(np.diff(px.dropna().to_numpy()))
    d = d[d > 0]
    if d.size == 0:
        return np.nan
    return float(10 ** np.round(np.log10(np.percentile(d, 0.1))))


def main() -> None:
    rows = []
    for inst in INSTRUMENTS:
        df = pd.read_parquet(f"{CACHE}/{inst}_H1.parquet")
        df = df[df.index >= SPLIT]
        pt = infer_point(df["close"])
        px = float(df["close"].median())
        sp_bps = float(np.nanmedian(df["spread_med"] * pt / df["close"] * 1e4))
        rows.append(dict(instrument=inst, cls=CLASS[inst], point_size=pt, price_med=px,
                         spread_zero_frac=float(df["spread_zero_frac"].mean()),
                         spread_med_bps_measured=sp_bps))
    cost = pd.DataFrame(rows)

    # documented table wins where COST_AUDIT.md measured it; otherwise measure here
    src, used = [], []
    for _, r in cost.iterrows():
        i = r["instrument"]
        if CLASS[i] == "FX":
            used.append(1.50); src.append("COST_AUDIT catalogue (column zero-inflated -> not measurable)")
        elif CLASS[i] == "index":
            used.append(1.80); src.append("COST_AUDIT.md S5 honest range [1.8;2.9], low end")
        elif i == "XAUUSD":
            used.append(1.84); src.append("COST_AUDIT.md S3, measured")
        else:
            used.append(round(r["spread_med_bps_measured"] + SLIPPAGE_RT_BPS, 2))
            src.append("measured here (spread x point) + 1.0 bps slippage -- UNMEASURED elsewhere")
    cost["cost_rt_bps"] = used
    cost["cost_source"] = src
    cost["gate_3x_bps"] = 3 * cost["cost_rt_bps"]
    cost.to_csv(f"{OUT}/cost_reference.csv", index=False)
    print(cost.to_string(index=False))

    cmap = dict(zip(cost["instrument"], cost["cost_rt_bps"]))
    for name in ("cells_all.csv",):
        c = pd.read_csv(f"{OUT}/{name}")
        c["cost_rt_bps"] = c["instrument"].map(cmap)
        c["gate_3x_bps"] = 3.0 * c["cost_rt_bps"]
        c["passes_cost_gate"] = c["gross_bps"] > c["gate_3x_bps"]
        c["gross_over_cost"] = c["gross_bps"] / c["cost_rt_bps"]
        c.to_csv(f"{OUT}/{name}", index=False)
        print(f"patched {name}: {int(c['passes_cost_gate'].sum())} cells over the 3x gate")


if __name__ == "__main__":
    main()
