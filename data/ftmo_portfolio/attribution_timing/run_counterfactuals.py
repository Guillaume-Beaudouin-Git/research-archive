"""Phase 2.2/2.3/2.4-sensitivity — LOO iso-vol, flag-only, vm sweep.
All arms on the cleanroom engine runner (fix_deadlock ON), paired vs its own
baseline arm (same starts), block-bootstrap CIs on paired deltas.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import attr_engine as AE
E = AE.E

TAB = HERE / "tables"
t0 = time.time()
VAL, FEE = 1453.0, 96.0
WINDOWS = (("IS", "2013-10-01", "2019-12-31"), ("OOS", "2020-01-02", "2026-02-25"))

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)

# iso-vol factors from baseline attributed day records
df = pd.read_parquet(HERE / "baseline_day_records.parquet")
df["total"] = df[["gold", "jpy", "on_us", "on_ger", "orb", "fix"]].sum(axis=1)
book = df.total
FACT = {}
for sleeve, cols in AE.SLEEVES.items():
    pnl = df[cols].sum(axis=1) if len(cols) > 1 else df[cols[0]]
    FACT[sleeve] = float(book.std() / (book - pnl).std())
print("iso-vol vm factors:", {k: round(v, 3) for k, v in FACT.items()})

def arm(tag, wt=WT, cfg_over=None):
    cfg = dict(E.CFG_V2, fix_deadlock=True)
    if cfg_over:
        cfg.update(cfg_over)
    rows = []
    for win, lo, hi in WINDOWS:
        st = E.cohort_starts(M, lo, hi, 7)
        for i0 in st:
            r = E.run_funnel(M, int(i0), wt, ON, cfg, wall=91)
            rows.append(dict(win=win, start=M["dates"][int(i0)],
                             funded=r["funded"], attempts=r["attempts"], t=r["t"]))
    d = pd.DataFrame(rows)
    p = d.funded.mean()
    ev = p * VAL - d.attempts.mean() * FEE
    print(f"{tag:28s} IS {d[d.win=='IS'].funded.mean()*100:5.1f} "
          f"OOS {d[d.win=='OOS'].funded.mean()*100:5.1f} pooled {p*100:5.1f} "
          f"att {d.attempts.mean():.2f} EV ${ev:+5.0f} "
          f"med_t {d.loc[d.funded,'t'].median():3.0f} [{time.time()-t0:.0f}s]",
          flush=True)
    d.to_csv(TAB / f"cf_{tag}.csv", index=False)
    return d

def wt_zero(col):
    w = WT.copy(); w[:, col] = 0.0; return w

def wt_flag(col):
    w = WT.copy(); w[:, col] = np.where(w[:, col] != 0, 1e-12, 0.0); return w

base = arm("baseline")

ARMS = {}
ARMS["loo_gold_isovol"] = arm("loo_gold_isovol", wt=wt_zero(0),
                              cfg_over=dict(vm=14 * FACT["gold"]))
ARMS["loo_gold_noresc"] = arm("loo_gold_noresc", wt=wt_zero(0))
ARMS["loo_jpy_isovol"] = arm("loo_jpy_isovol", wt=wt_zero(1),
                             cfg_over=dict(vm=14 * FACT["jpy"]))
ARMS["loo_jpy_noresc"] = arm("loo_jpy_noresc", wt=wt_zero(1))
ARMS["loo_on_isovol"] = arm("loo_on_isovol",
                            cfg_over=dict(on_w=0.0, vm=14 * FACT["overnight"]))
ARMS["loo_on_noresc"] = arm("loo_on_noresc", cfg_over=dict(on_w=0.0))
ARMS["loo_orb_isovol"] = arm("loo_orb_isovol",
                             cfg_over=dict(orb_risk=0.0, vm=14 * FACT["orb"]))
ARMS["loo_orb_noresc"] = arm("loo_orb_noresc", cfg_over=dict(orb_risk=0.0))

ARMS["flag_gold"] = arm("flag_gold", wt=wt_flag(0))
ARMS["flag_jpy"] = arm("flag_jpy", wt=wt_flag(1))
ARMS["flag_on"] = arm("flag_on", cfg_over=dict(on_w=1e-12))
ARMS["flag_orb"] = arm("flag_orb", cfg_over=dict(orb_risk=1e-9))

for vmx in (10, 12, 16, 18):
    ARMS[f"vm{vmx}"] = arm(f"vm{vmx}", cfg_over=dict(vm=float(vmx)))

# paired block-bootstrap CIs on delta p vs baseline
rng = np.random.default_rng(23)
B = 10
y0 = base.funded.to_numpy(float)
rows = []
for tag, d in ARMS.items():
    y1 = d.funded.to_numpy(float)
    delta = y1 - y0
    n = len(delta)
    boots = []
    for _ in range(3000):
        ix = []
        while len(ix) < n:
            s = rng.integers(0, n)
            ix.extend(((s + np.arange(B)) % n).tolist())
        boots.append(delta[np.array(ix[:n])].mean())
    lo_, hi_ = np.percentile(boots, [2.5, 97.5])
    ev = d.funded.mean() * VAL - d.attempts.mean() * FEE
    ev0 = base.funded.mean() * VAL - base.attempts.mean() * FEE
    rows.append(dict(arm=tag, p=d.funded.mean(), dp=delta.mean(),
                     dp_lo=lo_, dp_hi=hi_,
                     dp_IS=(d[d.win == 'IS'].funded.mean()
                            - base[base.win == 'IS'].funded.mean()),
                     dp_OOS=(d[d.win == 'OOS'].funded.mean()
                             - base[base.win == 'OOS'].funded.mean()),
                     dEV=ev - ev0,
                     d_med_t=(d.loc[d.funded, 't'].median()
                              - base.loc[base.funded, 't'].median()),
                     d_att=d.attempts.mean() - base.attempts.mean()))
res = pd.DataFrame(rows)
res.to_csv(TAB / "p2_counterfactuals.csv", index=False)
print(res.round(3).to_string(index=False))
print(f"done {time.time()-t0:.0f}s")
