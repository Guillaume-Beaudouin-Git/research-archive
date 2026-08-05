"""Corrected analysis: gradient vs placebo, asymmetric Pace legs with power,
economics on the audited V, the mur-optimal-vs-V curve, and the two-lever matrix.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

import econ2
import pace_lib as P

OUT = Path(__file__).resolve().parent.parent / "outputs"
TAB = Path(__file__).resolve().parent.parent / "tables"
TAB.mkdir(exist_ok=True)
pd.set_option("display.width", 260)

RAW = pd.read_csv(OUT / "grid2_raw.csv")
FL = {k: np.load(OUT / f"grid2_{k}_flags.npy")
      for k in ("funded", "onetry", "floor", "daily")}
WALLS = [65, 91, 130, 182, 270, 360]
N = FL["funded"].shape[1]


def pick(kind, wall, mode, draw=-1, denom=None):
    q = ((RAW.kind == kind) & (RAW.wall == wall) & (RAW["mode"] == mode)
         & (RAW.draw == draw))
    if denom is not None:
        q &= RAW.pace_denom == denom
    i = RAW.index[q]
    assert len(i) == 1, (kind, wall, mode, draw, denom, len(i))
    return int(i[0])


def cycle_days(wall):
    r = RAW.loc[pick("real", wall, "coupled")]
    return r.p_campaign * r.mean_days + (1 - r.p_campaign) * wall


def blocklen(wall):
    return P.cohort_block_len(cycle_days(wall))


def boot(a, b, wall, seed=3):
    d, lo, hi = P.block_boot_delta(a, b, blocklen(wall), seed=seed)
    return d * 100, lo * 100, hi * 100


# ================================================================= 1. GRADIENT
rows = []
for w in WALLS:
    r = RAW.loc[pick("real", w, "coupled")]
    pl = np.array([FL["funded"][pick("placebo", w, "coupled", k)].mean()
                   for k in range(12)]) * 100
    rows.append(dict(wall=w, p_campaign=r.p_campaign * 100, p_1try=r.p_one_try * 100,
                     attempts=r.avg_attempts, median_days=r.median_days,
                     mean_days=r.mean_days,
                     bust_daily=r.d_bust_daily * 100, bust_floor=r.d_bust_floor * 100,
                     timeout=r.d_timeout * 100, abandon=r.d_abandon * 100,
                     placebo_p50=np.median(pl), placebo_p95=np.percentile(pl, 95),
                     edge_pt=r.p_campaign * 100 - np.median(pl)))
G = pd.DataFrame(rows)
base = G[G.wall == 91].iloc[0]
G["gain_vs_91"] = G.p_campaign - base.p_campaign
G["placebo_gain_vs_91"] = G.placebo_p50 - base.placebo_p50
G["edge_attributable"] = G.gain_vs_91 - G.placebo_gain_vs_91
for w in WALLS:
    d, lo, hi = boot(FL["funded"][pick("real", w, "coupled")],
                     FL["funded"][pick("real", 91, "coupled")], max(w, 91))
    G.loc[G.wall == w, ["gain_ci_lo", "gain_ci_hi"]] = lo, hi
G.to_csv(TAB / "gradient2.csv", index=False)
print("=" * 118)
print("1. CORRECTED WALL GRADIENT (deployed MONO book, min-trading-days backstop ARMED)")
print("=" * 118)
print(G.to_string(index=False, float_format=lambda x: f"{x:.2f}"))

# pure horizon channel (Pace denominator pinned at 91)
h = []
for w in WALLS:
    r = RAW.loc[pick("real", w, "frozen", denom=91)]
    o = RAW.loc[pick("real", w, "off", denom=91)]
    c = RAW.loc[pick("real", w, "coupled")]
    d, lo, hi = boot(FL["funded"][pick("real", w, "frozen", denom=91)],
                     FL["funded"][pick("real", 91, "frozen", denom=91)], max(w, 91))
    h.append(dict(wall=w, coupled=c.p_campaign * 100, frozen91=r.p_campaign * 100,
                  pace_off=o.p_campaign * 100,
                  horizon_gain=d, ci_lo=lo, ci_hi=hi,
                  pace_channel=(c.p_campaign - r.p_campaign) * 100))
H = pd.DataFrame(h)
H.to_csv(TAB / "horizon_channel2.csv", index=False)
print("\n1b. HORIZON channel (Pace denominator frozen at 91) vs the deployed coupling")
print(H.to_string(index=False, float_format=lambda x: f"{x:+.2f}"))

# ============================================================== 2. PACE LEGS
rows = []
for wall in (91, 182):
    bl = blocklen(wall)
    for metric, mname in (("funded", "p_campaign"), ("onetry", "p_1try"),
                          ("floor", "p_floor|1try"), ("daily", "p_daily|1try")):
        for leg, a, b, est in (("HIGH", "hi_only", "off", "main"),
                               ("HIGH", "coupled", "lo_only", "interaction"),
                               ("LOW", "lo_only", "off", "main"),
                               ("LOW", "coupled", "hi_only", "interaction"),
                               ("BOTH", "coupled", "off", "aggregate (first pass)")):
            ia = pick("real", wall, a, denom=(91 if a == "off" else None))
            ib = pick("real", wall, b, denom=(91 if b == "off" else None))
            d, lo, hi = boot(FL[metric][ia], FL[metric][ib], wall)
            pv = np.array([(FL[metric][pick("placebo", wall, a, k)].mean()
                            - FL[metric][pick("placebo", wall, b, k)].mean()) * 100
                           for k in range(12)])
            se = (hi - lo) / (2 * 1.96)
            rows.append(dict(wall=wall, metric=mname, leg=leg, estimand=est,
                             arms=f"{a}-{b}", delta_pt=d, ci_lo=lo, ci_hi=hi,
                             placebo_mean=pv.mean(), edge_pt=d - pv.mean(),
                             mde80_pt=2.80 * se,
                             sig="YES" if (lo > 0 or hi < 0) else "ns",
                             block_cohorts=bl, n_eff=round(N / bl, 1)))
L = pd.DataFrame(rows)
L.to_csv(TAB / "pace_legs2.csv", index=False)
print("\n" + "=" * 118)
print("2. ASYMMETRIC PACE DECOMPOSITION (corrected harness)")
print("=" * 118)
for wall in (91, 182):
    print(f"\n### wall {wall}  E[cycle] {cycle_days(wall):.0f} cal d -> block "
          f"{blocklen(wall)} cohorts, n_eff {N/blocklen(wall):.0f} independent windows")
    for m in ("p_campaign", "p_1try", "p_floor|1try", "p_daily|1try"):
        print(f"\n  {m}")
        print(L[(L.wall == wall) & (L.metric == m)][
            ["leg", "estimand", "arms", "delta_pt", "ci_lo", "ci_hi",
             "placebo_mean", "edge_pt", "mde80_pt", "sig"]]
            .to_string(index=False, float_format=lambda x: f"{x:+.2f}"))

print("\n### arm levels")
lv = RAW[RAW.kind == "real"][["wall", "mode", "pace_denom", "p_campaign", "p_one_try",
                              "d_bust_floor", "d_bust_daily", "d_timeout",
                              "median_days", "avg_attempts"]].sort_values(["wall", "mode"])
lv.to_csv(TAB / "pace_levels2.csv", index=False)
print(lv.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

# ============================================== 3. A-WITHOUT-B (saturation risk)
print("\n" + "=" * 118)
print("3. A WITHOUT B — abandon horizon 182 with the Pace denominator still 91")
print("=" * 118)
ab = RAW.loc[pick("AnoB", 182, "frozen", denom=91)]
full = RAW.loc[pick("real", 182, "coupled")]
off = RAW.loc[pick("real", 182, "off", denom=91)]
for lab, r in (("A+B   horizon 182, denominator 182", full),
               ("A only horizon 182, denominator 91 (SATURATING)", ab),
               ("pace OFF horizon 182", off)):
    print(f"  {lab:50s} p_camp {r.p_campaign:.4f} p1 {r.p_one_try:.4f} "
          f"floor {r.d_bust_floor:.4f} daily {r.d_bust_daily:.4f} to {r.d_timeout:.4f}")
for met, lab in (("funded", "p(campaign)"), ("floor", "p(floor|1try)")):
    d, lo, hi = boot(FL[met][pick("real", 182, "coupled")],
                     FL[met][pick("AnoB", 182, "frozen", denom=91)], 182)
    print(f"  (A+B) - (A only)  {lab:14s} {d:+.2f} pt  CI95 [{lo:+.2f}, {hi:+.2f}]")

prof = pd.read_csv(TAB / "pace_profile2.csv")
g = prof.groupby(["wall", "mode"]).agg(
    n=("out", "size"), f_hi=("f_hi", "mean"), f_lo=("f_lo", "mean"),
    mean_x=("mean_x", "mean"), max_x=("max_x", "mean"),
    ever_hi=("f_hi", lambda s: (s > 0).mean()), ever_lo=("f_lo", lambda s: (s > 0).mean()),
    ever_sat=("max_x", lambda s: (s >= 1.999).mean()),
    p95_max_x=("max_x", lambda s: s.quantile(0.95)),
    med_used=("used", "median"))
g.to_csv(TAB / "pace_exposure2.csv")
print("\n  exposure (first attempt, per cohort)")
print(g.to_string(float_format=lambda x: f"{x:.4f}"))
for wall, mode, cal in ((91, "coupled", 91), (182, "AnoB_denom91", 91)):
    s = prof[(prof.wall == wall) & (prof["mode"] == mode)]
    print(f"  wall {wall} {mode:14s} P(attempt open at cal day {cal}) = "
          f"{(s.used > cal*252/365).mean():.4f}")

# ==================================================== 4. ECONOMICS ON AUDITED V
econ_in = G[["wall", "p_campaign", "avg_attempts", "mean_days"]].copy() \
    if "avg_attempts" in G else None
econ_in = pd.DataFrame(dict(wall=G.wall, p_campaign=G.p_campaign / 100,
                            avg_attempts=G.attempts, mean_days=G.mean_days))
print("\n" + "=" * 118)
print("4. ECONOMICS — renewal-reward, audited V (trader share of ONE funded account)")
print("=" * 118)
be = pd.DataFrame([dict(wall=int(r.wall), p_campaign=r.p_campaign,
                        attempts=r.avg_attempts,
                        breakeven_V=econ2.breakeven_V(r))
                   for r in econ_in.itertuples()])
print("\nbreak-even V by wall (V at which $/day = 0):")
print(be.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
be.to_csv(TAB / "breakeven_V.csv", index=False)

sens = []
for lab, v in econ2.V_GRID.items():
    t = econ2.table(econ_in, v=v)
    row = dict(scenario=lab, V=v)
    for r in t.itertuples():
        row[f"w{int(r.wall)}"] = r.usd_per_day
    row["argmax"] = int(t.loc[t.usd_per_day.idxmax(), "wall"])
    row["any_positive"] = bool((t.usd_per_day > 0).any())
    sens.append(row)
S = pd.DataFrame(sens)
S.to_csv(TAB / "econ_sensitivity2.csv", index=False)
print("\n$/day by (V, wall):")
print(S.to_string(index=False, float_format=lambda x: f"{x:+.3f}"))

vs = np.arange(100, 4001, 25.0)
C = econ2.optimal_wall_curve(econ_in, vs)
C.to_csv(TAB / "wall_optimal_by_V.csv", index=False)
pos = C[C.best_usd_per_day > 0]
print(f"\nEV-negative at EVERY wall for V < ${pos.V.min():,.0f}" if len(pos)
      else "\nEV-negative at EVERY wall over the whole V grid tested")
if len(pos):
    print("optimal wall as V rises:")
    print(C[C.V.isin([250, 500, 782, 1000, 1200, 1500, 2000, 2500, 3000, 4000])]
          .to_string(index=False, float_format=lambda x: f"{x:,.3f}"))
print("\nsaved tables/")
