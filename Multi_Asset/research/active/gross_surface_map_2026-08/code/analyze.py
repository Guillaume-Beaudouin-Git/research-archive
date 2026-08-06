"""Read the sweep, produce the map, the t-distribution vs H0, and the shortlist."""
from __future__ import annotations

import numpy as np
import pandas as pd

from build_map import OUT

pd.set_option("display.width", 200)


def main() -> None:
    c = pd.read_csv(f"{OUT}/cells_all.csv")
    nulls = pd.read_csv(f"{OUT}/null_placebo_t.csv")

    post = c[(c["era"] == "post2021") & (c["predictor"] != "S0_LONG")].copy()
    pre = c[(c["era"] == "pre2021") & (c["predictor"] != "S0_LONG")].copy()
    key = ["instrument", "lhour", "horizon_h", "predictor"]
    m = post.merge(pre[key + ["gross_bps", "t_hac6", "n"]], on=key,
                   how="left", suffixes=("", "_pre"))

    # ---------------- 1. t distribution vs H0 -------------------------------
    tt = post["t_hac6"].dropna().to_numpy()
    tn = nulls["t_hac6"].dropna().to_numpy()
    rows = []
    for thr in (1.96, 2.5, 3.0, 3.5, 4.0):
        rows.append(dict(
            threshold=thr,
            real_frac=float((np.abs(tt) > thr).mean()),
            placebo_frac=float((np.abs(tn) > thr).mean()),
            iid_normal_frac=float(2 * (1 - _ncdf(thr))),
            real_count=int((np.abs(tt) > thr).sum()),
            placebo_count_scaled=float((np.abs(tn) > thr).mean() * len(tt)),
        ))
    tdist = pd.DataFrame(rows)
    tdist["excess_over_placebo"] = tdist["real_count"] - tdist["placebo_count_scaled"]
    tdist.to_csv(f"{OUT}/t_distribution_vs_H0.csv", index=False)
    print("=== t-distribution: real sweep vs matched placebo vs iid N(0,1) ===")
    print(tdist.to_string(index=False))
    print(f"\nreal cells={len(tt)}  placebo draws={len(tn)}")
    print(f"sd(t) real={tt.std():.3f}  placebo={tn.std():.3f}  (iid H0 = 1.000)")
    print(f"max|t| real={np.abs(tt).max():.2f}  placebo={np.abs(tn).max():.2f}")

    # ---------------- 2. the map: per instrument x horizon ------------------
    agg = post.groupby(["cls", "instrument", "horizon_h"]).agg(
        cells=("t_hac6", "size"),
        best_gross=("gross_bps", "max"),
        best_t=("t_hac6", lambda s: s.loc[s.abs().idxmax()] if len(s) else np.nan),
        n_gate=("passes_cost_gate", "sum"),
        med_freq=("freq_per_yr", "median"),
        cost=("cost_rt_bps", "first"),
    ).reset_index()
    agg.to_csv(f"{OUT}/map_by_instrument_horizon.csv", index=False)

    hr = post.groupby(["cls", "lhour"]).agg(
        cells=("t_hac6", "size"),
        frac_gate=("passes_cost_gate", "mean"),
        frac_t2=("t_hac6", lambda s: float((s.abs() > 2).mean())),
        med_gross=("gross_bps", "median"),
    ).reset_index()
    hr.to_csv(f"{OUT}/map_by_class_hour.csv", index=False)

    # ---------------- 3. shortlist -----------------------------------------
    sl = m[(m["passes_cost_gate"]) & (m["t_hac6"].abs() > 2.5)].copy()
    sl["pre2021_same_sign"] = np.sign(sl["gross_bps"]) == np.sign(sl["gross_bps_pre"])
    sl["placebo_beat"] = np.nan
    # per-cell placebo p-value: |t_real| vs its own 10 rotations
    nk = nulls.set_index(["instrument", "lhour", "horizon_h", "predictor"])
    for i, r in sl.iterrows():
        try:
            g = nk.loc[(r["instrument"], r["lhour"], r["horizon_h"], r["predictor"]), "t_hac6"]
            sl.at[i, "placebo_beat"] = float((np.abs(np.asarray(g)) >= abs(r["t_hac6"])).mean())
        except KeyError:
            pass
    sl = sl.sort_values("t_hac6", key=lambda s: s.abs(), ascending=False)
    cols = ["instrument", "cls", "lhour", "horizon_h", "predictor", "n", "freq_per_yr",
            "gross_bps", "t_hac6", "cost_rt_bps", "gate_3x_bps", "side_mean",
            "uncond_pool_bps", "excess_bps", "holds_through_break",
            "gross_bps_pre", "t_hac6_pre", "n_pre", "pre2021_same_sign", "placebo_beat"]
    sl[cols].to_csv(f"{OUT}/shortlist.csv", index=False)
    print(f"\n=== shortlist: cost gate (gross > 3x RT) AND |t_HAC6| > 2.5 : {len(sl)} cells ===")
    if len(sl):
        print(sl[cols].head(40).to_string(index=False))

    # survivors of the pre-2021 out-of-sample control too
    surv = sl[(sl["pre2021_same_sign"]) & (sl["placebo_beat"] <= 0.10)]
    surv[cols].to_csv(f"{OUT}/shortlist_survivors.csv", index=False)
    print(f"\n=== + pre-2021 same sign AND placebo p<=0.10 : {len(surv)} cells ===")
    if len(surv):
        print(surv[cols].to_string(index=False))

    # ---------------- 3b. unconditional drift surface (S0) ------------------
    # No predictor at all: is there raw directional drift in some hour x horizon?
    # Its own placebo is meaningless (a constant side rotates into itself), so it
    # is reported with the pre-2021 control only, and it is NOT in the t-histogram.
    s0p = c[(c["era"] == "post2021") & (c["predictor"] == "S0_LONG")]
    s0q = c[(c["era"] == "pre2021") & (c["predictor"] == "S0_LONG")]
    k0 = ["instrument", "lhour", "horizon_h"]
    s0 = s0p.merge(s0q[k0 + ["gross_bps", "t_hac6"]], on=k0, how="left", suffixes=("", "_pre"))
    s0["pre2021_same_sign"] = np.sign(s0["gross_bps"]) == np.sign(s0["gross_bps_pre"])
    s0 = s0.sort_values("t_hac6", key=lambda s: s.abs(), ascending=False)
    c0 = ["instrument", "cls", "lhour", "horizon_h", "n", "freq_per_yr", "gross_bps",
          "t_hac6", "gate_3x_bps", "holds_through_break", "gross_bps_pre", "t_hac6_pre",
          "pre2021_same_sign"]
    s0[c0].to_csv(f"{OUT}/unconditional_drift_surface.csv", index=False)
    t0 = s0["t_hac6"].dropna().to_numpy()
    print(f"\n=== unconditional drift (S0_LONG): {len(s0)} cells, "
          f"frac|t|>2 = {(np.abs(t0) > 2).mean():.3f} (iid H0 0.046), sd(t)={t0.std():.2f} ===")
    print(s0[c0].head(20).to_string(index=False))

    # ---------------- 4. power / frequency trade-off ------------------------
    post["freq_bucket"] = pd.cut(post["freq_per_yr"], [0, 60, 150, 260, 1e9],
                                 labels=["<60/yr", "60-150", "150-260", ">260"])
    pf = post.groupby(["freq_bucket", "predictor"], observed=True).agg(
        cells=("gross_bps", "size"), med_gross=("gross_bps", "median"),
        med_abs_gross=("gross_bps", lambda s: s.abs().median()),
        med_abs_t=("t_hac6", lambda s: s.abs().median()),
        frac_gate=("passes_cost_gate", "mean"),
    ).reset_index()
    pf.to_csv(f"{OUT}/power_frequency_tradeoff.csv", index=False)
    print("\n=== power vs frequency ===")
    print(pf.to_string(index=False))


def _ncdf(x: float) -> float:
    from math import erf, sqrt
    return 0.5 * (1 + erf(x / sqrt(2)))


if __name__ == "__main__":
    main()
