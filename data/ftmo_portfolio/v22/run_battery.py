"""v2.2 contractual battery — one load, acceptance gate, then the full suite."""
import sys, time, copy
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine_v22 as V
import config_v22 as C22
E = V.E

TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
t0 = time.time()
FEE = C22.FEE
rng = np.random.default_rng(42)

M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
print(f"stack loaded [{time.time()-t0:.0f}s]", flush=True)


def sweep(tag, Mx=None, wt=None, on=None, cfg=None, wall=None, save=True):
    Mx = Mx or M; wt = WT if wt is None else wt; on = ON if on is None else on
    cfg = cfg or C22.CFG_CHALLENGE; wall = wall or C22.WALL
    rows = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V.starts(Mx, lo, hi, C22.COHORT_STEP):
            r = V.run_funnel(Mx, int(i0), wt, on, cfg, wall=wall)
            rows.append(dict(win=win, start=Mx["dates"][int(i0)], funded=r["funded"],
                             attempts=r["attempts"], t=r["t"], micro=r["micro"]))
    d = pd.DataFrame(rows)
    p = d.funded.mean()
    print(f"{tag:24s} IS {d[d.win=='IS'].funded.mean()*100:5.1f} "
          f"OOS {d[d.win=='OOS'].funded.mean()*100:5.1f} pooled {p*100:5.2f} "
          f"att {d.attempts.mean():.2f} [{time.time()-t0:.0f}s]", flush=True)
    if save:
        d.to_csv(TAB / f"v22_{tag}.csv", index=False)
    return d


def block_ci(y, B=10, nb=4000):
    y = np.asarray(y, float); n = len(y); out = []
    for _ in range(nb):
        ix = []
        while len(ix) < n:
            s = rng.integers(0, n)
            ix.extend(((s + np.arange(B)) % n).tolist())
        out.append(y[np.array(ix[:n])].mean())
    return np.percentile(out, [2.5, 97.5]), np.std(out)


def neff(d):
    y = d.sort_values("start").funded.to_numpy(float)
    ac = [pd.Series(y).autocorr(k) for k in range(1, 14)]
    return len(y) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))


# ---------- A. challenge + acceptance gate ----------
V.COUNTERS.update(micro_fires=0, backstop_fires=0)
base = sweep("challenge_91")
pooled = base.funded.mean()
(ci_lo, ci_hi), _ = block_ci(base.sort_values("start").funded)
print(f"  pooled CI95 block [{ci_lo*100:.1f};{ci_hi*100:.1f}]  "
      f"N={len(base)} N_eff={neff(base):.0f}")
print(f"  med_t IS {base[base.win=='IS'].loc[lambda x: x.funded,'t'].median():.0f}j "
      f"OOS {base[base.win=='OOS'].loc[lambda x: x.funded,'t'].median():.0f}j")
print(f"  micro fires {V.COUNTERS['micro_fires']} | cohorts>=1 micro "
      f"{(base.micro>0).mean()*100:.1f}% | backstop {V.COUNTERS['backstop_fires']}")
if not (0.86 <= pooled <= 0.91):
    print(f"*** ACCEPTANCE FAIL {pooled*100:.2f} outside [86,91] — STOP ***")
    sys.exit(1)
print("  ACCEPTANCE PASS", flush=True)

# ---------- B. CDF ----------
cdf_rows = [dict(wall=91, p=pooled, lo=ci_lo, hi=ci_hi)]
for wall in (30, 61, 182, 270):
    dw = sweep(f"wall_{wall}", wall=wall)
    (lo_, hi_), _ = block_ci(dw.sort_values("start").funded)
    cdf_rows.append(dict(wall=wall, p=dw.funded.mean(), lo=lo_, hi=hi_))
cdf = pd.DataFrame(cdf_rows).sort_values("wall")
cdf.to_csv(TAB / "v22_cdf.csv", index=False)
mono = bool(cdf.p.is_monotonic_increasing)
print(f"CDF: {[f'{w}:{p*100:.1f}' for w, p in zip(cdf.wall, cdf.p)]} monotone={mono}",
      flush=True)

# ---------- C. funded (config unchanged; orb_rt_bps={}) ----------
print(f"funded (ORB_RT_BPS={C22.ORB_RT_BPS}):", flush=True)
fr = {}
for win, lo, hi in C22.FUNDED_WINDOWS:
    rows = [V.run_funded(M, int(i0), WT, ON, C22.CFG_FUNDED,
                         horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
            for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP)]
    d = pd.DataFrame(rows); d["extr"] = d.wd + d.residual
    d.to_csv(TAB / f"v22_funded_{win}.csv", index=False)
    fr[win] = d
    print(f"  {win}: n={len(d)} E[extr]=${d.extr.mean():,.0f} med=${d.extr.median():,.0f} "
          f"bust={d.busted.mean()*100:.1f}% payouts={d.payouts.mean():.1f} "
          f"[{time.time()-t0:.0f}s]", flush=True)
extr_pooled = (fr["IS"].extr.mean() + fr["OOS"].extr.mean()) / 2
VAL = FEE + 0.8 * extr_pooled
att = base.attempts.mean()
ev = pooled * VAL - att * FEE
print(f"  VAL re-derived = $96 + 0.8 x ${extr_pooled:,.0f} = ${VAL:,.0f}")
print(f"  EV chain = {pooled:.3f} x ${VAL:,.0f} - {att:.2f} x $96 = ${ev:+,.0f}",
      flush=True)

# ---------- D. placebo (cost-symmetric, pre-cost flip) ----------
M_pl = dict(M); M_pl["mR"] = M["orb_R_anti"]
pl = sweep("placebo", Mx=M_pl, wt=-WT, cfg=dict(C22.CFG_CHALLENGE, on_w=-0.6))
print(f"  edge = {pooled*100:.1f} - {pl.funded.mean()*100:.1f} = "
      f"{(pooled-pl.funded.mean())*100:+.1f} pts", flush=True)

# ---------- E. anticausal -1j (must NOT improve) ----------
WT_ac = np.vstack([WT[1:], WT[-1:]])
ON_ac = np.concatenate([ON[1:], ON[-1:]])
M_ac = dict(M)
for k in ("orb_R", "mR", "m_risk"):
    M_ac[k] = np.concatenate([M[k][1:], M[k][-1:]])
ac = sweep("anticausal", Mx=M_ac, wt=WT_ac, on=ON_ac)
print(f"  anticausal {ac.funded.mean()*100:.1f} vs base {pooled*100:.1f} -> "
      f"{'OK (no improvement)' if ac.funded.mean() <= pooled + 0.01 else '*** LEAK ***'}",
      flush=True)

# ---------- F. swap x1.5 / spread x2 (array-scaled) ----------
M_sw = dict(M); M_sw["swL"] = M["swL"] * 1.5; M_sw["swS"] = M["swS"] * 1.5
sweep("swap_x1.5", Mx=M_sw)
M_sp = dict(M); M_sp["rt"] = M["rt"] * 2.0
sweep("spread_x2", Mx=M_sp)

# ---------- G. margin ----------
E.MARGIN_LOG.clear()
sweep("margin_log", cfg=dict(C22.CFG_CHALLENGE, margin_log=True), save=False)
ml = np.array(E.MARGIN_LOG)
print(f"margin pre-cap: p50 {np.percentile(ml,50)*100:.0f}% p99 "
      f"{np.percentile(ml,99)*100:.0f}% max {ml.max()*100:.0f}% "
      f"bind {(ml>0.60).mean()*100:.1f}%", flush=True)
pd.DataFrame([dict(p50=np.percentile(ml,50), p99=np.percentile(ml,99),
                   mx=ml.max(), bind=(ml>0.60).mean())]
             ).to_csv(TAB / "v22_margin.csv", index=False)

# ---------- H. weekend-gap stress ----------
for k in (1.5, 2.0):
    sweep(f"wgap_x{k}", cfg=dict(C22.CFG_CHALLENGE, wgap_stress=k))

# ---------- I. vm sweep sanity ----------
for vmx in (10, 12, 16, 18):
    sweep(f"vm{vmx}", cfg=dict(C22.CFG_CHALLENGE, vm=float(vmx)))

print(f"battery done [{time.time()-t0:.0f}s]")
