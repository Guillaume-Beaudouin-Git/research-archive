"""Q5-bis — J1 ablation ON THE AUDITED FUNNEL ITSELF (not a proxy).

The historical claim under audit is "J1 OFF cost Delta p -7.6 pt". Re-measure it on
the same cleanroom funnel (405 paired cohorts, wall 91d, v2.8 leg cap, Swing margin
rates), and run the SAME ablation against circular-shift placebos of the J1 weight —
identical marginal, identical autocorrelation, wrong alignment. If J1 ON only matches
its own placebos, what the book gains is "a second uncorrelated vol source", which any
persistent series supplies, not J1's signal.
"""
import sys
import numpy as np
import pandas as pd

CR = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CR)
import engine as E  # noqa: E402

CFG = dict(vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0, micro_orb=True, breaker=0.3,
           taper=0.02, glide=0.5, pace=1, pace_k=1.0, ab_buf=0.02, ab_days=5,
           margin_cap=0.6, quantize=True, fix_deadlock=True,
           mrate=E.MRATE_SWING, leg_lev_cap=[0.0, 12.0, 0.0, 0.0])

M = E.load_market()
WT, ON = E.build_signals()
starts = E.cohort_starts(M, pd.Timestamp("2014-10-01"), M["dates"][-200], step=7)
ONa = ON.reindex(M["dates"]).fillna(0.0).to_numpy(float)


def campaign(wt_df, tag):
    WTa = wt_df.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    ok, ts, att = [], [], []
    for i0 in starts:
        r = E.run_funnel(M, i0, WTa, ONa, CFG)
        ok.append(r["funded"])
        att.append(r["attempts"])
        if r["funded"]:
            ts.append(r["t"])
    ok = np.asarray(ok, float)
    return dict(tag=tag, p=ok.mean(), n=len(ok), med=float(np.median(ts)) if ts else np.nan,
                att=float(np.mean(att)), ok=ok)


base = campaign(WT, "J1 ON (deployed)")
off = campaign(WT.assign(USDJPY=0.0), "J1 OFF")
print(f"### paired cohorts N = {base['n']} (weekly starts 2014-10 -> 2025-08, wall 91d)")
for r in (base, off):
    print(f"  {r['tag']:<22} p(campaign) {r['p']*100:6.2f} %   median {r['med']:.0f} d   "
          f"attempts {r['att']:.2f}")
d = base["p"] - off["p"]
diff = base["ok"] - off["ok"]
se = diff.std(ddof=1) / np.sqrt(len(diff))
print(f"  -> J1 contribution = {d*100:+.2f} pt   paired SE {se*100:.2f}  "
      f"CI95 [{(d-1.96*se)*100:+.2f}, {(d+1.96*se)*100:+.2f}]")
print(f"     cohorts flipped by J1: +{int(((base['ok']==1)&(off['ok']==0)).sum())} / "
      f"-{int(((base['ok']==0)&(off['ok']==1)).sum())}")

print("\n### PLACEBO: circular shifts of the J1 weight column (N=25)")
rng = np.random.default_rng(3)
n = len(WT)
ps = []
for k in rng.choice(np.arange(120, n - 120), size=25, replace=False):
    wt = WT.copy()
    wt["USDJPY"] = np.roll(WT["USDJPY"].values, int(k))
    r = campaign(wt, f"shift{k}")
    ps.append(r["p"] - off["p"])
ps = np.asarray(ps)
print(f"  placebo J1 contribution: mean {ps.mean()*100:+.2f} pt  "
      f"p5 {np.percentile(ps,5)*100:+.2f}  p50 {np.percentile(ps,50)*100:+.2f}  "
      f"p95 {np.percentile(ps,95)*100:+.2f}")
print(f"  REAL J1 = {d*100:+.2f} pt -> percentile "
      f"{(ps < d).mean()*100:.0f} of the placebo distribution")
print(f"  VERDICT: {'signal-specific' if (ps < d).mean() >= 0.95 else 'NOT signal-specific — any persistent USDJPY-vol series does the same job'}")
