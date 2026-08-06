"""Final readable tables for RESULTS.md.

Adds the decisive read-off the raw sweep does not carry: the QUOTED SPREAD AT THE
CELL'S OWN ENTRY AND EXIT HOUR. COST_AUDIT.md S7 asks for exactly this -- a
daily-median spread is the wrong denominator for a family that trades at one
precise hour. It turns out to be what explains the top of the map.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import build_map as B
from build_map import CLASS, INSTRUMENTS, OUT, SPLIT

pd.set_option("display.width", 250)


def hourly_spread_bps() -> pd.DataFrame:
    """Median quoted spread in bps, per instrument x local hour, post-2021."""
    pt = pd.read_csv(f"{OUT}/cost_reference.csv").set_index("instrument")["point_size"]
    rows = []
    for inst in INSTRUMENTS:
        df = B.load(inst)
        d = df[df.index >= SPLIT]
        sp = (d["spread_med"] * pt[inst] / d["close"] * 1e4).groupby(d["lhour"]).median()
        for h, v in sp.items():
            rows.append(dict(instrument=inst, lhour=int(h), spread_bps_at_hour=float(v)))
    out = pd.DataFrame(rows)
    out.to_csv(f"{OUT}/spread_by_hour.csv", index=False)
    return out


def main() -> None:
    sp = hourly_spread_bps()
    spd = sp.set_index(["instrument", "lhour"])["spread_bps_at_hour"]
    c = pd.read_csv(f"{OUT}/cells_all.csv")
    nulls = pd.read_csv(f"{OUT}/null_placebo_t.csv")

    post = c[c["era"] == "post2021"].copy()
    pre = c[c["era"] == "pre2021"].copy()
    key = ["instrument", "lhour", "horizon_h", "predictor"]
    m = post.merge(pre[key + ["gross_bps", "t_hac6", "n"]], on=key, how="left",
                   suffixes=("", "_pre"))

    # spread paid at the two prints the cell depends on
    m["exit_lhour"] = (m["lhour"] + m["horizon_h"]) % 24
    m["spread_entry_bps"] = [spd.get((i, h), np.nan) for i, h in zip(m["instrument"], m["lhour"])]
    m["spread_exit_bps"] = [spd.get((i, h), np.nan) for i, h in zip(m["instrument"], m["exit_lhour"])]
    m["cost_at_hour_bps"] = m[["spread_entry_bps", "spread_exit_bps"]].sum(axis=1) + 1.0
    m["quote_contaminated"] = m[["spread_entry_bps", "spread_exit_bps"]].max(axis=1) > \
        3.0 * m.groupby("instrument")["spread_entry_bps"].transform("median")
    m.to_csv(f"{OUT}/cells_post2021_annotated.csv", index=False)

    cond = m[m["predictor"] != "S0_LONG"]
    s0 = m[m["predictor"] == "S0_LONG"]

    # ---- 1. THE MAP: per class, how far the best gross is from the cost floor
    rows = []
    for cls, g in m.groupby("cls"):
        gc = g[g["predictor"] != "S0_LONG"]
        clean = gc[~gc["quote_contaminated"]]
        rows.append(dict(
            cls=cls, instruments=g["instrument"].nunique(),
            cond_cells=len(gc), cost_rt_bps=g["cost_rt_bps"].median(),
            gate_3x_bps=3 * g["cost_rt_bps"].median(),
            best_gross_bps=gc["gross_bps"].max(),
            best_gross_clean_bps=clean["gross_bps"].max(),
            best_gross_over_gate=clean["gross_bps"].max() / (3 * g["cost_rt_bps"].median()),
            cells_over_gate=int(gc["passes_cost_gate"].sum()),
            frac_t_over_2=float((gc["t_hac6"].abs() > 2).mean()),
        ))
    mp = pd.DataFrame(rows).sort_values("best_gross_over_gate", ascending=False)
    mp.to_csv(f"{OUT}/map_headline.csv", index=False)
    print("=== THE MAP (conditional cells, post-2021, zero cost applied) ===")
    print(mp.to_string(index=False))

    # ---- 2. per instrument
    rows = []
    for inst, g in cond.groupby("instrument"):
        clean = g[~g["quote_contaminated"]]
        flat = clean[~clean["holds_through_break"]]
        rows.append(dict(
            instrument=inst, cls=CLASS[inst], cells=len(g),
            cost_rt=g["cost_rt_bps"].iloc[0], gate=3 * g["cost_rt_bps"].iloc[0],
            best_gross=clean["gross_bps"].max(),
            best_gross_intraday_flat=flat["gross_bps"].max() if len(flat) else np.nan,
            max_abs_t=g["t_hac6"].abs().max(),
            frac_t2=float((g["t_hac6"].abs() > 2).mean()),
            over_gate=int(g["passes_cost_gate"].sum()),
        ))
    pi = pd.DataFrame(rows)
    pi["shortfall_x"] = pi["gate"] / pi["best_gross"].clip(lower=1e-9)
    pi = pi.sort_values("best_gross", ascending=False)
    pi.to_csv(f"{OUT}/map_by_instrument.csv", index=False)
    print("\n=== per instrument: best conditional gross vs its cost gate ===")
    print(pi.to_string(index=False))

    # ---- 3. hot spots by |t| regardless of the gate, WITH the pre-2021 control
    nk = nulls.set_index(key)
    hot = cond[cond["t_hac6"].abs() > 3.5].copy()
    pb = []
    for _, r in hot.iterrows():
        try:
            g = np.asarray(nk.loc[(r["instrument"], r["lhour"], r["horizon_h"], r["predictor"]),
                                  "t_hac6"])
            pb.append(float((np.abs(g) >= abs(r["t_hac6"])).mean()))
        except KeyError:
            pb.append(np.nan)
    hot["placebo_p"] = pb
    hot["pre2021_same_sign"] = np.sign(hot["gross_bps"]) == np.sign(hot["gross_bps_pre"])
    hot["survives_all"] = (hot["placebo_p"] <= 0.10) & hot["pre2021_same_sign"] & \
                          hot["passes_cost_gate"] & ~hot["quote_contaminated"]
    hot = hot.sort_values("t_hac6", key=lambda s: s.abs(), ascending=False)
    hc = ["instrument", "cls", "lhour", "horizon_h", "predictor", "n", "freq_per_yr",
          "gross_bps", "t_hac6", "cost_rt_bps", "gate_3x_bps", "cost_at_hour_bps",
          "quote_contaminated", "holds_through_break", "side_mean", "uncond_pool_bps",
          "excess_bps", "gross_bps_pre", "t_hac6_pre", "pre2021_same_sign",
          "placebo_p", "survives_all"]
    hot[hc].to_csv(f"{OUT}/hotspots_conditional.csv", index=False)
    print(f"\n=== conditional hot spots |t|>3.5 : {len(hot)} cells "
          f"({int(hot['passes_cost_gate'].sum())} over the cost gate, "
          f"{int(hot['survives_all'].sum())} survive everything) ===")
    print(hot[hc].head(25).to_string(index=False))

    # ---- 4. the rollover artifact, quantified
    s0h = s0.copy()
    s0h["is_rollover"] = s0h["quote_contaminated"]
    tab = s0h.groupby(["cls", "is_rollover"]).agg(
        cells=("t_hac6", "size"), med_abs_t=("t_hac6", lambda s: s.abs().median()),
        max_abs_t=("t_hac6", lambda s: s.abs().max()),
        med_abs_gross=("gross_bps", lambda s: s.abs().median()),
    ).reset_index()
    tab.to_csv(f"{OUT}/rollover_artifact.csv", index=False)
    print("\n=== unconditional drift: cells touching a blown-out quote hour vs the rest ===")
    print(tab.to_string(index=False))

    top20 = s0.reindex(s0["t_hac6"].abs().sort_values(ascending=False).index).head(20)
    print(f"\ntop-20 unconditional |t| cells: {int(top20['quote_contaminated'].sum())}/20 "
          f"sit on a blown-out quote hour")


if __name__ == "__main__":
    main()
