"""Assemble the gradient, the horizon/Pace decomposition, the placebo bands and the
economics. Reads outputs/grid_raw.csv + funded_flags.npy; writes the report tables."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"          # raw + regenerable (gitignored)
TAB = HERE.parent / "tables"           # small cited summaries (tracked)
TAB.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parents[4]))
sys.path.insert(0, str(HERE))

from Portfolio.admission.marginal import stationary_bootstrap_indices  # noqa: E402
import econ  # noqa: E402

WALLS = [65, 91, 130, 182, 270, 360]
TD_PER_CAL = 252.0 / 365.0
NB = 4000


def ci(flags: np.ndarray, wall: int, seed: int = 3) -> tuple[float, float]:
    """Block bootstrap over COHORTS. Block length = number of cohorts spanned by one
    wall (cohorts are 7 trading days apart), because two cohorts closer than a wall
    share most of their market path."""
    rng = np.random.default_rng(seed)
    mb = max(2.0, wall * TD_PER_CAL / 7.0)
    n = flags.size
    draws = np.empty(NB)
    for b in range(NB):
        draws[b] = flags[stationary_bootstrap_indices(n, mb, rng)[:n]].mean()
    return float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def main():
    df = pd.read_csv(OUT / "grid_raw.csv")
    flags = np.load(OUT / "funded_flags.npy")
    df["row"] = np.arange(len(df))

    real = df[df.kind == "real"].copy()
    piv = real.pivot(index="wall", columns="pace_mode", values="p_campaign")
    med = real.pivot(index="wall", columns="pace_mode", values="median_days")
    p90 = real.pivot(index="wall", columns="pace_mode", values="p90_days")

    # ---- gradient (deployed semantics = coupled) + CI
    g = real[real.pace_mode == "coupled"].set_index("wall").loc[WALLS]
    lo, hi = zip(*[ci(flags[int(g.loc[w, "row"])], w) for w in WALLS])
    g["ci_lo"], g["ci_hi"] = lo, hi

    # ---- placebo bands (zero-edge null, matched 10-day persistence)
    for kind, tag in (("placebo", "coupled"), ("placebo_off", "off")):
        p = df[df.kind == kind]
        for w in WALLS:
            v = p[p.wall == w]["p_campaign"].to_numpy()
            g.loc[w, f"plac_{tag}_p50"] = np.median(v)
            g.loc[w, f"plac_{tag}_p95"] = np.percentile(v, 95)
            g.loc[w, f"plac_{tag}_max"] = v.max()
            g.loc[w, f"plac_{tag}_n"] = len(v)
        o = real[real.pace_mode == "off"].set_index("wall")
        g[f"real_{tag}"] = (g["p_campaign"] if tag == "coupled" else o["p_campaign"])
        g[f"edge_{tag}"] = g[f"real_{tag}"] - g[f"plac_{tag}_p50"]
        for w in WALLS:
            v = p[p.wall == w]["p_campaign"].to_numpy()
            g.loc[w, f"rank_{tag}"] = float((v < g.loc[w, f"real_{tag}"]).mean())

    # ---- decomposition
    dec = pd.DataFrame(index=WALLS)
    dec["off"] = piv["off"]
    dec["frozen91"] = piv["frozen"]
    dec["coupled"] = piv["coupled"]
    b = 91
    dec["horizon_pt"] = (piv["frozen"] - piv["frozen"].loc[b]) * 100
    dec["pace_pt"] = (piv["coupled"] - piv["frozen"]) * 100
    dec["total_pt"] = (piv["coupled"] - piv["coupled"].loc[b]) * 100
    dec["pace_feature_pt"] = (piv["frozen"] - piv["off"]) * 100
    dec["median_days_coupled"] = med["coupled"]
    dec["median_days_off"] = med["off"]
    dec["p90_days_coupled"] = p90["coupled"]

    # ---- pace-denominator sweep at FIXED horizon 91
    d91 = df[df.kind == "denom91"].set_index("pace_denom")[
        ["p_campaign", "p_one_try", "median_days", "d_bust_daily", "d_bust_floor", "d_timeout"]]
    d91.loc["OFF"] = real[(real.wall == 91) & (real.pace_mode == "off")][
        ["p_campaign", "p_one_try", "median_days", "d_bust_daily", "d_bust_floor",
         "d_timeout"]].iloc[0]

    # ---- economics
    e = g.reset_index()[["wall", "p_campaign", "avg_attempts", "mean_days", "median_days"]]
    econ_tabs = {}
    for name, v in econ.V_SCENARIOS.items():
        t = econ.table(e, v=v)
        econ_tabs[name] = t
    base = econ_tabs["BASELINE (v2.2.1 OOS 2y, measured costs)"]

    g.to_csv(TAB / "gradient.csv")
    dec.to_csv(TAB / "decomposition.csv")
    d91.to_csv(TAB / "pace_denominator_at_wall91.csv")
    base.to_csv(TAB / "econ_baseline.csv", index=False)
    pd.concat([t.assign(scenario=k, V=econ.V_SCENARIOS[k]) for k, t in econ_tabs.items()]
              ).to_csv(TAB / "econ_sensitivity.csv", index=False)

    f = lambda x: f"{x:.4f}"
    print("=== GRADIENT (deployed semantics: wall drives horizon AND Pace) ===")
    print(g[["p_campaign", "ci_lo", "ci_hi", "p_one_try", "median_days", "p90_days",
             "avg_attempts", "d_bust_daily", "d_bust_floor", "d_timeout", "d_abandon"]
            ].to_string(float_format=f))
    print("\n=== PLACEBO (zero-edge, 10d-block sign flips, 20 draws) ===")
    print(g[["real_coupled", "plac_coupled_p50", "plac_coupled_max", "edge_coupled",
             "rank_coupled", "real_off", "plac_off_p50", "plac_off_max", "edge_off",
             "rank_off", "plac_coupled_n"]].to_string(float_format=f))
    print("\n  gain over the 91 baseline, real vs placebo (points of p(campaign)):")
    for w in WALLS:
        dr = (g.loc[w, "real_coupled"] - g.loc[91, "real_coupled"]) * 100
        dp = (g.loc[w, "plac_coupled_p50"] - g.loc[91, "plac_coupled_p50"]) * 100
        print(f"    wall {w:3d}: real {dr:+6.2f}pt | placebo {dp:+6.2f}pt | "
              f"edge-attributable {dr - dp:+6.2f}pt")
    print("\n=== DECOMPOSITION vs wall=91 (points of p(campaign)) ===")
    print(dec.to_string(float_format=f))
    print("\n=== PACE DENOMINATOR SWEEP at FIXED horizon 91 ===")
    print(d91.to_string(float_format=f))
    print("\n=== ECONOMICS, V=$2,529 (baseline) ===")
    print(base.to_string(float_format=f, index=False))
    print("\n=== OPTIMAL WALL BY REVENUE SCENARIO ===")
    for k, v in econ.V_SCENARIOS.items():
        w, rate = econ.optimal_wall(e, v)
        t = econ.table(e, v=v).set_index("wall")
        print(f"{k:45s} V=${v:7.0f} -> wall {w:3d}  ${rate:6.2f}/day  "
              f"(${rate*30.44:7.2f}/mo)   at91=${t.loc[91,'usd_per_day']:6.2f}/day")


if __name__ == "__main__":
    main()
