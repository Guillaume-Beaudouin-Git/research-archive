"""Step 1 (H1) — session mapping: is the drift anchored to UTC or to the exchange clock?

Two competing mechanisms make OPPOSITE predictions across US DST:
  H_asia   (UTC anchor)      : Tokyo/Shanghai are DST-free -> no DST dependence.
  H_reopen (exchange anchor) : Globex reopen 17:00/19:00 CT -> legacy UTC window is
                               aligned in winter, 1h late in summer.
Spec A = legacy UTC-fixed window. Spec B = same window on the exchange clock
(-1 UTC hour during US DST). Winter: A == B by construction.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from common import (OUT, SLEEVES, block_bootstrap_diff, hac_t, load_h1, obs_per_year,
                    sharpe, us_dst, window_returns)

rows, profiles = [], []

for name, sp in SLEEVES.items():
    h1 = load_h1(sp["cfd"])
    h1 = h1[h1.index >= pd.Timestamp(sp["sample_start"])]

    winA = window_returns(h1, sp["start_utc_winter"], sp["hours"], anchor="utc")
    winB = window_returns(h1, sp["start_utc_winter"], sp["hours"], anchor="exchange")

    for spec, w in (("A_utc", winA), ("B_exchange", winB)):
        d = us_dst(w.index)
        for regime, mask in (("winter", ~d), ("summer", d), ("all", np.ones(len(w), bool))):
            s = w[mask]
            if len(s) < 60:
                continue
            mu, t = hac_t(s)
            rows.append(dict(sleeve=name, spec=spec, dst=regime, N=len(s),
                             drift_bps=round(1e4 * s.mean(), 3),
                             sharpe_gross=round(sharpe(s), 3),
                             t_hac=round(t, 2),
                             obs_per_yr=round(obs_per_year(s), 1)))

    # pre-registered contrast: summer only (winter is identical by construction)
    dA, dB = us_dst(winA.index), us_dst(winB.index)
    bs = block_bootstrap_diff(winB[dB], winA[dA])
    rows.append(dict(sleeve=name, spec="B_minus_A", dst="summer",
                     N=bs["n"], drift_bps=np.nan,
                     sharpe_gross=round(bs["obs"], 3) if bs["obs"] == bs["obs"] else np.nan,
                     t_hac=np.nan, obs_per_yr=np.nan))
    print(f'{name:8s} bootstrap Sharpe(B)-Sharpe(A) summer = {bs["obs"]:+.3f}  '
          f'p={bs["p"]:.3f}  n={bs["n"]}  ci90={[round(c,3) for c in bs["ci"]]}')

    # hourly profile in both clocks
    lr = np.log(h1["close"] / h1["close"].shift(1)).dropna()
    d = us_dst(lr.index)
    et_hour = (lr.index.hour - np.where(d, 4, 5)) % 24        # UTC -> US Eastern
    prof = pd.DataFrame({"lr": lr.to_numpy(), "utc_h": lr.index.hour,
                         "et_h": et_hour, "dst": d})
    for clock, col in (("utc", "utc_h"), ("exchange_ET", "et_h")):
        g = prof.groupby([col, "dst"])["lr"].mean().unstack() * 1e4
        g.columns = ["winter_bps", "summer_bps"]
        g = g.reset_index().rename(columns={col: "hour"})
        g.insert(0, "clock", clock)
        g.insert(0, "sleeve", name)
        profiles.append(g)

res = pd.DataFrame(rows)
prof = pd.concat(profiles, ignore_index=True)
pd.set_option("display.width", 220, "display.max_rows", 200)
print("\n=== H1 spec x DST regime ===")
print(res.to_string(index=False))

# how well do the two DST sub-profiles superpose, per clock?
print("\n=== profile superposition (corr of winter vs summer hourly means) ===")
sup = []
for (sl, clock), g in prof.groupby(["sleeve", "clock"]):
    c = g[["winter_bps", "summer_bps"]].dropna().corr().iloc[0, 1]
    sup.append(dict(sleeve=sl, clock=clock, corr_winter_summer=round(float(c), 3)))
sup = pd.DataFrame(sup).pivot(index="sleeve", columns="clock", values="corr_winter_summer")
print(sup.to_string())

res.to_csv(OUT / "step1_session_map.csv", index=False)
prof.to_csv(OUT / "step1_hourly_profiles.csv", index=False)
sup.to_csv(OUT / "step1_profile_superposition.csv")
