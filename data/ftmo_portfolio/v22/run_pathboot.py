"""v2.2 path bootstrap — 78 synthetic histories (weekly blocks, mean 13 weeks),
challenge funnel p per history. Mirrors the v2.0 CB-A design on the v2.2 spec."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine_v22 as V
import config_v22 as C22
E = V.E

TAB = HERE / "tables"
t0 = time.time()
PATH_WEEKS, MEAN_BLOCK = 120, 13

M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)

iso = M["dates_idx"].isocalendar()
keys = list(zip(iso.year, iso.week))
weeks, cur, ck = [], [], keys[0]
for i, k in enumerate(keys):
    if k != ck:
        weeks.append(cur); cur = []; ck = k
    cur.append(i)
weeks.append(cur)
weeks = [w for w in weeks if len(w) >= 3]
print(f"{len(weeks)} weeks [{time.time()-t0:.0f}s]", flush=True)


def synth(rng):
    out = []
    while len(out) < PATH_WEEKS:
        s = rng.integers(0, len(weeks))
        L = 1 + rng.geometric(1.0 / MEAN_BLOCK)
        for k in range(s, min(s + L, len(weeks))):
            out.append(weeks[k])
            if len(out) >= PATH_WEEKS:
                break
    return [i for w in out for i in w]


def synth_M(idx):
    S = dict(days=[M["days"][i] for i in idx],
             swL=M["swL"][idx], swS=M["swS"][idx], mult=M["mult"][idx],
             rt=M["rt"], orb_R=M["orb_R"][idx], mR=M["mR"][idx],
             m_risk=M["m_risk"][idx], n=len(idx))
    base = pd.Timestamp("2030-01-07")
    dates, w, last_wd = [], -1, 9
    for i in idx:
        wd = M["dates"][i].dayofweek
        if wd < last_wd:
            w += 1
        last_wd = wd
        dates.append(base + pd.Timedelta(weeks=w, days=wd))
    S["dates"] = dates
    return S


rows = []
n_per_seed = {1: 20, 2: 20, 3: 20, 4: 18}
for seed, n_paths in n_per_seed.items():
    rng = np.random.default_rng(seed)
    for p_ in range(n_paths):
        idx = synth(rng)
        S = synth_M(idx)
        wt = WT[idx]; on = ON[idx]
        st = np.arange(5, S["n"] - 70, 15)
        res = [V.run_funnel(S, int(i0), wt, on, C22.CFG_CHALLENGE, wall=91)
               for i0 in st]
        d = pd.DataFrame(res)
        rows.append(dict(seed=seed, path=p_, p=d.funded.mean(), n=len(d)))
        print(f"seed{seed} path{p_}: p={d.funded.mean():.3f} [{time.time()-t0:.0f}s]",
              flush=True)
pb = pd.DataFrame(rows)
pb.to_csv(TAB / "v22_pathboot.csv", index=False)
print(f"pathboot n={len(pb)}: mean {pb.p.mean()*100:.1f} p5 "
      f"{pb.p.quantile(.05)*100:.1f} min {pb.p.min()*100:.1f} "
      f"P(p>50%)={np.mean(pb.p > 0.5)*100:.0f}%")
