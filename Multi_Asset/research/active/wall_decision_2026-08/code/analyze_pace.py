"""GAP 1 analysis — asymmetric leg contrasts, their placebo, the conditional surface,
and the POWER available on each leg.

Design. The multiplier is x = clip(1 + K(frac_t - max(prog,0)), 0.8, 2.0). Four arms
run on the SAME cohorts:
    off      x := 1
    hi_only  x := max(x, 1)     (amplification leg only)
    lo_only  x := min(x, 1)     (protection leg only)
    coupled  x                  (deployed)
Each leg gets TWO estimates:
    main effect  = leg_only - off        (the leg against no pacing)
    interaction  = coupled - other_only  (the leg added on top of the other)
Reporting both is the point: a single averaged number is what the first pass produced
and it cannot distinguish "no effect" from "two effects that cancel".
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
TAB = Path(__file__).resolve().parent.parent / "tables"

RAW = pd.read_csv(OUT / "pace_raw.csv")
FL = {k: np.load(OUT / f"pace_{k}_flags.npy")
      for k in ("funded", "onetry", "floor", "daily")}


def pick(kind, wall, mode, denom=None, draw=-1):
    q = (RAW.kind == kind) & (RAW.wall == wall) & (RAW["mode"] == mode) & (RAW.draw == draw)
    if denom is not None:
        q &= RAW.pace_denom == denom
    idx = RAW.index[q]
    assert len(idx) == 1, (kind, wall, mode, denom, draw, len(idx))
    return int(idx[0])


def blocklen(wall):
    r = RAW.loc[pick("real", wall, "coupled")]
    cycle = r.p_campaign * r.mean_days + (1 - r.p_campaign) * wall
    return P.cohort_block_len(cycle), cycle


def contrast(wall, a_mode, b_mode, metric, kind="real", kind_b=None):
    ia = pick(kind, wall, a_mode)
    ib = pick(kind_b or kind, wall, b_mode)
    a, b = FL[metric][ia], FL[metric][ib]
    bl, _ = blocklen(wall)
    d, lo, hi = P.block_boot_delta(a, b, bl)
    return d * 100, lo * 100, hi * 100


def placebo_contrast(wall, a_mode, b_mode, metric):
    """Same contrast on the zero-edge null, one value per draw (12 draws)."""
    vals = []
    for k in range(12):
        ia, ib = pick("placebo", wall, a_mode, draw=k), pick("placebo", wall, b_mode, draw=k)
        vals.append((FL[metric][ia].mean() - FL[metric][ib].mean()) * 100)
    v = np.array(vals)
    return v.mean(), np.percentile(v, 5), np.percentile(v, 95), v


rows = []
for wall in (91, 182):
    bl, cyc = blocklen(wall)
    n_eff = len(FL["funded"][0]) / bl
    for metric, mname in (("funded", "p_campaign"), ("onetry", "p_1try"),
                          ("floor", "p_floor(1try)"), ("daily", "p_daily(1try)")):
        for leg, (a, b), est in (
            ("HIGH", ("hi_only", "off"), "main"),
            ("HIGH", ("coupled", "lo_only"), "interaction"),
            ("LOW", ("lo_only", "off"), "main"),
            ("LOW", ("coupled", "hi_only"), "interaction"),
            ("BOTH", ("coupled", "off"), "aggregate (first pass)"),
        ):
            d, lo, hi = contrast(wall, a, b, metric)
            pm, plo, phi, pv = placebo_contrast(wall, a, b, metric)
            se = (hi - lo) / (2 * 1.96)
            rows.append(dict(wall=wall, metric=mname, leg=leg, estimand=est,
                             arms=f"{a}-{b}", delta_pt=d, ci_lo=lo, ci_hi=hi,
                             placebo_mean_pt=pm, placebo_p5=plo, placebo_p95=phi,
                             edge_pt=d - pm,
                             sig=("YES" if (lo > 0 or hi < 0) else "ns"),
                             se_pt=se, mde80_pt=2.80 * se,
                             block_cohorts=bl, n_eff_windows=round(n_eff, 1)))
T = pd.DataFrame(rows)
T.to_csv(TAB / "pace_legs.csv", index=False)
pd.set_option("display.width", 260)

print("=" * 110)
print("ASYMMETRIC DECOMPOSITION OF THE PACE CHANNEL — deployed MONO book")
print("=" * 110)
for wall in (91, 182):
    bl, cyc = blocklen(wall)
    print(f"\n### wall {wall}  (E[cycle] {cyc:.0f} cal d -> block {bl} cohorts, "
          f"n_eff {len(FL['funded'][0])/bl:.0f} independent windows)")
    for m in ("p_campaign", "p_1try", "p_floor(1try)", "p_daily(1try)"):
        s = T[(T.wall == wall) & (T.metric == m)]
        print(f"\n  {m}")
        print(s[["leg", "estimand", "arms", "delta_pt", "ci_lo", "ci_hi",
                 "placebo_mean_pt", "edge_pt", "mde80_pt", "sig"]]
              .to_string(index=False, float_format=lambda x: f"{x:+.2f}"))

# ---- raw levels for the report ----
lv = RAW[(RAW.kind == "real")][["wall", "mode", "p_campaign", "p_one_try",
                                "d_bust_floor", "d_bust_daily", "d_timeout",
                                "median_days", "avg_attempts"]]
lv.to_csv(TAB / "pace_levels.csv", index=False)
print("\n\n### arm levels (real)")
print(lv.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

# ---- A-without-B: the saturation configuration ----
print("\n\n### A-WITHOUT-B  (abandon horizon 182, Pace denominator still 91)")
a = RAW.loc[pick("AnoB", 182, "frozen", denom=91)]
b = RAW.loc[pick("real", 182, "coupled")]
c = RAW.loc[pick("real", 182, "off")]
for lab, r in (("A+B  (horizon 182, denominator 182)", b),
               ("A only (horizon 182, denominator 91 = SATURATING)", a),
               ("pace OFF (horizon 182)", c)):
    print(f"  {lab:52s} p_camp {r.p_campaign:.4f}  p1 {r.p_one_try:.4f}  "
          f"floor {r.d_bust_floor:.4f}  daily {r.d_bust_daily:.4f}  med {r.median_days:.0f}")
for met, lab in (("funded", "p(campaign)"), ("floor", "p(floor|1try)"),
                 ("onetry", "p(1-try)")):
    d, lo, hi = contrast(182, "coupled", "frozen", met, kind="real", kind_b="AnoB")
    print(f"  Delta {lab:14s} (A+B) - (A only) = {d:+.2f} pt  CI95 [{lo:+.2f}, {hi:+.2f}]")

# ---- profiles: duty cycle + how often the wall is actually reached ----
prof = pd.read_csv(TAB / "pace_profile.csv")
print("\n\n### EXPOSURE — per-cohort duty cycle of each leg (first attempt)")
g = prof.groupby(["wall", "mode"]).agg(
    n=("out", "size"), f_hi=("f_hi", "mean"), f_lo=("f_lo", "mean"),
    mean_x=("mean_x", "mean"), max_x_mean=("max_x", "mean"),
    ever_hi=("f_hi", lambda s: (s > 0).mean()), ever_lo=("f_lo", lambda s: (s > 0).mean()),
    ever_sat=("max_x", lambda s: (s >= 1.999).mean()),
    p95_max_x=("max_x", lambda s: s.quantile(0.95)),
    med_used=("used", "median"), p95_used=("used", lambda s: s.quantile(0.95)),
)
print(g.to_string(float_format=lambda x: f"{x:.4f}"))
g.to_csv(TAB / "pace_exposure.csv")

# survival past the wall: `used` is in TRADING days; 91 cal d ~ 63 td, 182 ~ 126 td
for wall, mode, cal in ((91, "coupled", 91), (182, "coupled", 182),
                        (182, "AnoB_denom91", 91)):
    s = prof[(prof.wall == wall) & (prof["mode"] == mode)]
    td = cal * 252 / 365
    print(f"  wall {wall:3d} {mode:14s}: P(first attempt still open at cal day {cal}) = "
          f"{(s.used > td).mean():.4f}   (n={len(s)})")

print("\nsaved", TAB / "pace_legs.csv")
