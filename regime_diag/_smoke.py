"""Engine smoke test: import cleanroom from main dir, time load_market, exercise
the diag bust hook + funded loop, cache M to _cache for reuse. Read-only on main."""
import sys, time, pickle
from pathlib import Path
import numpy as np, pandas as pd

CLEAN = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CLEAN)
import engine as E

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_cache"; CACHE.mkdir(exist_ok=True)

t0 = time.time()
M = E.load_market()
print(f"load_market: {time.time()-t0:.1f}s  n={M['n']}  dates {M['dates'][0].date()}..{M['dates'][-1].date()}")
print("E.CACHE ->", E.CACHE)   # confirm points at main dir

t0 = time.time()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)
print(f"build_signals: {time.time()-t0:.1f}s  WT shape {WT.shape}  ON mean {ON.mean():.3f}")

# cache M (+signals) so downstream scripts skip the M5 parse
with open(CACHE / "M.pkl", "wb") as f:
    pickle.dump({"M": M, "WT": WT, "ON": ON}, f)
print("cached M.pkl", f"{(CACHE/'M.pkl').stat().st_size/1e6:.1f}MB")

# --- exercise challenge funnel diag (real bust dates) on a few cohort starts
idx = M["dates"]
starts = E.cohort_starts(M, pd.Timestamp("2015-01-01"), pd.Timestamp("2016-06-30"), step=10)
t0 = time.time(); nb = 0; sample = []
for i0 in starts:
    diag = []
    r = E.run_funnel(M, int(i0), WT, ON, E.CFG_V2, diag=diag)
    if not r["funded"]:
        busts = [d for d in diag if d["kind"] == "bust"]
        if busts:
            nb += 1
            if len(sample) < 4:
                sample.append((idx[i0].date(), [(b["date"].date(), 1) for b in busts]))
print(f"funnel x{len(starts)} cohorts: {time.time()-t0:.1f}s  not-funded-with-bust={nb}")
for s in sample: print("  start", s[0], "busts", s[1])

# timing extrapolation for full-sample dense sweep
per = (time.time()-t0)/max(len(starts),1)
full = E.cohort_starts(M, idx[0], idx[-1], step=2)
print(f"~{per*1000:.0f} ms/cohort -> full step=2 ({len(full)} cohorts) ~ {per*len(full)/60:.1f} min")

# --- original funded run sanity (one cohort)
import importlib.util
spec = importlib.util.spec_from_file_location("p5", CLEAN + "/run_phase5.py")
print("\nfunded one-cohort sanity:")
r = None
# replicate minimal funded call without importing the script's side effects
def run_funded(Mx, i0, wt, on, cfg, horizon=504, wd_every=14):
    bal=E.INIT; pos=np.zeros(4); avg=np.full(4,np.nan); total_wd=0.0; n_pay=0; days=0; i=i0
    while i < Mx["n"] and days < horizon:
        limit=bal-E.DAILY_BUDGET; lim_eff=max(limit,E.FLOOR); brk_line=lim_eff+cfg["breaker"]*E.DAILY_BUDGET
        px_day,bounds=Mx["days"][i]; cuts=[0]+bounds+[len(px_day)]
        taper0=float(np.clip((bal-E.FLOOR)/E.INIT/cfg["taper"],0.0,1.0))
        orb_risk=cfg.get("orb_risk",0.0)*E.INIT*taper0; orb_live=orb_risk>0 and Mx["orb_R"][i]!=0.0
        flat=False
        for s in range(5):
            a,b=cuts[s],cuts[s+1]
            if a>=b: continue
            seg=px_day[a:b]
            if s==4 and orb_live: bal+=orb_risk*Mx["orb_R"][i]; orb_live=False
            dip=1.31*orb_risk if (orb_live and s in (2,3)) else 0.0
            if not flat:
                tgt,_=E._target_for_segment(s,i,Mx,wt,on,cfg,bal,pos,avg,seg[0],i0,cfg["vm"])
                if tgt is not None: bal=E._trade_to(pos,avg,bal,tgt,seg[0],Mx["rt"])
            pl=np.zeros(len(seg))
            for k in range(4):
                if pos[k]!=0.0 and np.isfinite(avg[k]):
                    col=seg[:,k]; pl+=np.where(np.isfinite(col),(col/avg[k]-1.0)*pos[k],0.0)
            eq=bal+pl-dip; bad=eq<lim_eff; brk=eq<brk_line
            tb=int(np.argmax(bad)) if bad.any() else len(seg)
            tk=int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb,tk)<len(seg):
                if tb<=tk: return dict(busted=True, life=days)
                bal=E._flat(pos,avg,bal,seg[tk],Mx["rt"]); flat=True
        if np.any(pos):
            for k in range(4):
                if pos[k]!=0.0:
                    side=Mx["swL"][i,k] if pos[k]>0 else Mx["swS"][i,k]
                    bal+=abs(pos[k])*side/1e4*Mx["mult"][i,k]
        days+=1; i+=1
        if days%wd_every==0 and bal>E.INIT: total_wd+=bal-E.INIT; n_pay+=1; bal=E.INIT
    return dict(busted=False, life=days, wd=total_wd, payouts=n_pay)
FUNDED_CFG=dict(vm=1.0,on_w=0.35,orb_risk=0.0025,breaker=0.30,taper=0.02,glide=1.0,pace=0,margin_cap=0.60,quantize=True,target=10.0)
i2020=int(np.where(idx>=pd.Timestamp("2020-01-02"))[0][0])
print("  funded@2020:", run_funded(M, i2020, WT, ON, FUNDED_CFG))
print("DONE", f"{time.time()-t0:.0f}s")
