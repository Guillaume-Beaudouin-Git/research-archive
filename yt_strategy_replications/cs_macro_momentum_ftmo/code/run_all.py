"""Steps (c) + (d): the four pre-registered variants, the vm sweep, and the four
pre-registered kill rules. Writes results/*.csv + results/kill_rules.json."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import analysis as A
from . import costs as C
from . import panel as P
from . import strategy as St

OUT = Path(__file__).resolve().parent.parent / "results"
VM_GRID = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
N_PATHS = 3000

VARIANTS = {
    "V0": dict(rebalance="2w", vol_overlay=True, intraday_flat=False),
    "V1": dict(rebalance="2w", vol_overlay=False, intraday_flat=False),
    "V2": dict(rebalance="monthly", vol_overlay=True, intraday_flat=False),
    "V3": dict(rebalance="2w", vol_overlay=True, intraday_flat=True),
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pan, _ = P.build()
    idx_ret = P.closes(pan)[["US30", "US100", "US500", "GER40"]].pct_change()

    series: dict[str, pd.Series] = {}
    runs: dict[str, dict] = {}
    rows = []

    for cost_mode, uplift in (("panel", False), ("anchor", True)):
        for v, kw in VARIANTS.items():
            cfg = St.Config(name=v, spread_uplift=uplift, **kw)
            r = St.run(pan, cfg)
            key = f"{v}_{cost_mode}"
            runs[key] = r
            series[key] = r["daily"]["net"]
            m = A.metrics(r["daily"]["net"])
            m.update(variant=v, cost_mode=cost_mode,
                     gross_sharpe=A.S.sharpe_ratio(r["daily"]["gross"], A.ANN),
                     cost_spread_pct_yr=r["daily"]["cost_spread"].mean() * 252 * 100,
                     cost_swap_pct_yr=r["daily"]["cost_swap"].mean() * 252 * 100,
                     turnover_yr=r["daily"]["turnover"].mean() * 252)
            rows.append(m)
            print(f"{key:12s} grossSR={m['gross_sharpe']:+.3f} netSR={m['sharpe']:+.3f} "
                  f"CAGR={m['cagr']:+.2%} MDD={m['max_dd']:+.2%} "
                  f"spread={m['cost_spread_pct_yr']:.2f}%/yr swap={m['cost_swap_pct_yr']:.2f}%/yr",
                  flush=True)

    pd.DataFrame(rows).set_index(["variant", "cost_mode"]).to_csv(OUT / "variant_metrics.csv")
    pd.DataFrame(series).to_parquet(OUT / "variant_series.parquet")

    # ---------------- vm sweep -> the decision metric
    sweep = []
    for key, s in series.items():
        for vm in VM_GRID:
            c = A.campaign(s, n_paths=N_PATHS, scale=vm)
            eq = (1 + s * vm).cumprod()
            mdd, _ = A.S.max_drawdown(eq.to_numpy())
            sweep.append({
                "key": key, "variant": key.split("_")[0], "cost_mode": key.split("_")[1],
                "vm": vm, "vol_ann": float((s * vm).std(ddof=1) * np.sqrt(252)),
                "sharpe": A.S.sharpe_ratio(s, 252), "max_dd": mdd,
                **{k: v for k, v in c.items() if k != "n_paths"},
            })
            print(f"  {key:12s} vm={vm:<4} p={c['p_pass_global']:.3f} "
                  f"p1={c['p_pass_phase1']:.3f} med={c['days_median']:.0f} "
                  f"p90={c['days_p90']:.0f} daily={c['p_fail_daily']:.3f} "
                  f"floor={c['p_fail_floor']:.3f}", flush=True)
    sw = pd.DataFrame(sweep)
    sw.to_csv(OUT / "vm_sweep.csv", index=False)

    # ---------------- kill rules
    kills: dict[str, object] = {}

    # 1. placebo, at each variant's best vm (panel cost = the friendliest setting)
    plac = {}
    for v in VARIANTS:
        key = f"{v}_panel"
        sub = sw[sw.key == key]
        best_vm = float(sub.loc[sub.p_pass_global.idxmax(), "vm"])
        s = series[key]
        real = A.campaign(s, n_paths=N_PATHS, scale=best_vm)
        pl = A.campaign(s - s.mean(), n_paths=N_PATHS, scale=best_vm)
        plac[v] = {"best_vm": best_vm, "p_real": real["p_pass_global"],
                   "p_placebo": pl["p_pass_global"],
                   "days_real": real["days_median"], "days_placebo": pl["days_median"],
                   "beats_placebo": real["p_pass_global"] > pl["p_pass_global"]}
        print(f"[kill1] {v} vm={best_vm} p_real={real['p_pass_global']:.3f} "
              f"p_placebo={pl['p_pass_global']:.3f}", flush=True)
    kills["kill1_placebo"] = plac
    kills["kill1_verdict_family_dead"] = not any(
        plac[v]["beats_placebo"] for v in ("V0", "V2", "V3"))

    # 2. two-sided (L25): short leg only, ZERO cost
    sh = St.run(pan, St.Config(name="V0_short", side="short", zero_cost=True))
    lo = St.run(pan, St.Config(name="V0_long", side="long", zero_cost=True))
    kills["kill2_two_sided"] = {
        "short_leg_zero_cost": A.kill_two_sided(sh["daily"]["net"]),
        "long_leg_zero_cost": A.kill_two_sided(lo["daily"]["net"]),
    }
    print("[kill2]", json.dumps(kills["kill2_two_sided"], indent=1, default=float), flush=True)

    # 3. beta orthogonality (L38)
    kills["kill3_beta_orthogonality"] = {
        v: A.kill_beta_orthogonality(series[f"{v}_panel"], idx_ret) for v in VARIANTS
    }
    print("[kill3]", json.dumps(kills["kill3_beta_orthogonality"], indent=1, default=float),
          flush=True)

    # 4. gross per rebalance vs 1.5x measured p95 cost (L43)
    k4 = {}
    for v in VARIANTS:
        for mode in ("panel", "anchor"):
            r = runs[f"{v}_{mode}"]
            d = r["daily"]
            rb = pd.Series(St.rebalance_mask(d.index, VARIANTS[v]["rebalance"]), index=d.index)
            k4[f"{v}_{mode}"] = A.kill_gross_vs_cost(d, rb)
    kills["kill4_gross_vs_cost"] = k4
    print("[kill4]", json.dumps(k4, indent=1, default=float), flush=True)

    json.dump(kills, open(OUT / "kill_rules.json", "w"), indent=2, default=float)
    print("\nwritten:", OUT)


if __name__ == "__main__":
    main()
