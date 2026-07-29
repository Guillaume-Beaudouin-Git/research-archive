"""Step (b): V0 alone, full cost stack, plus the cost-attribution audit."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as A
from . import panel as P
from . import strategy as St

OUT = Path(__file__).resolve().parent.parent / "results"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pan, _ = P.build()

    runs = {
        "V0_gross_only": St.Config(name="V0", zero_cost=True),
        "V0_spread_only": St.Config(name="V0", swap_mult=0.0),
        "V0": St.Config(name="V0"),
        "V0_anchor_cost": St.Config(name="V0", spread_uplift=True),
        "V0_swap_x1.5": St.Config(name="V0", swap_mult=1.5, spread_uplift=True),
    }
    rows, series = [], {}
    for key, cfg in runs.items():
        r = St.run(pan, cfg)
        d = r["daily"]
        series[key] = d["net"]
        m = A.metrics(d["net"])
        m["key"] = key
        m["gross_sharpe"] = A.S.sharpe_ratio(d["gross"], A.ANN)
        m["cost_spread_bps_yr"] = d["cost_spread"].mean() * 252 * 1e4
        m["cost_swap_bps_yr"] = d["cost_swap"].mean() * 252 * 1e4
        m["turnover_yr"] = d["turnover"].mean() * 252
        rows.append(m)
        print(f"{key:18s} SR={m['sharpe']:+.3f} CAGR={m['cagr']:+.2%} "
              f"vol={m['vol_ann']:.2%} MDD={m['max_dd']:+.2%} "
              f"swapcost={m['cost_swap_bps_yr']/100:.2f}%/yr "
              f"spreadcost={m['cost_spread_bps_yr']/100:.2f}%/yr", flush=True)

    df = pd.DataFrame(rows).set_index("key")
    df.to_csv(OUT / "v0_cost_ladder.csv")
    pd.DataFrame(series).to_parquet(OUT / "v0_series.parquet")

    base = St.run(pan, runs["V0"])
    camp = A.campaign(base["daily"]["net"], n_paths=4000)
    print("\nV0 campaign:", json.dumps({k: round(v, 4) for k, v in camp.items()
                                        if isinstance(v, float)}, indent=1))
    # per-leg swap bill at the realised book weights
    w = base["weights"].abs()
    sw = A.pd.Series((base["daily"]["cost_swap"].sum()), index=["total"])
    print("mean gross exposure (sum |w|):", round(float(w.sum(axis=1).mean()), 3))
    print("V0 total swap bill over the sample: "
          f"{base['daily']['cost_swap'].sum():.2%} of equity")
    print("V0 total spread bill over the sample: "
          f"{base['daily']['cost_spread'].sum():.2%} of equity")
    json.dump({"campaign_V0": camp}, open(OUT / "v0_campaign.json", "w"), indent=2)


if __name__ == "__main__":
    main()
