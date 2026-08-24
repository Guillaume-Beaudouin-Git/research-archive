"""Mechanism + Q3 + robustness (PRE_REGISTRATION §7, Q3) and verdict-supporting anchors:
 - co-loss decomposition (are worst book days multi-sleeve / risk-off?)
 - per-sleeve announcement tails (J1/BoJ, gold+overnight/FOMC)
 - day-of-week tail profile
 - A2 USD-effect sub-period stability (is the one live signal a single 2022 episode?)
 - worst-N book days + funded bust days, with regime labels (anchors the 'dispersed' claim)
"""
import sys, json, time
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import chi2_contingency
import lib_regime as R
HERE = Path(__file__).resolve().parent; CACHE = HERE/"_cache"; RES = HERE/"results"
MAIN = "<HOME>/Desktop/Algo_claude"; SEED = 20260620
BD = pd.read_parquet(CACHE/"book_daily.parquet"); P = pd.read_parquet(CACHE/"regime_panel.parquet").reindex(BD.index)
EV = pd.read_parquet(CACHE/"challenge_busts.parquet"); FMC = pd.read_parquet(CACHE/"funded_mc.parquet")
r = BD.daily_ret; bd = BD.index

# standalone sleeves (directional proxy) aligned to book dates
SL = pd.read_parquet(f"{MAIN}/data/ftmo_portfolio/cache/phase1c_sleeves.parquet")[["gold","J1","overnight"]].reindex(bd)
def cvar(x, q=0.05):
    x=pd.Series(x).dropna(); k=max(1,int(len(x)*q)); return x.nsmallest(k).mean()

print("############ Q3a — DAY-OF-WEEK tail profile (book) ############")
dows = ["Mon","Tue","Wed","Thu","Fri"]
for w in range(5):
    x = r[bd.dayofweek==w]
    print(f"  {dows[w]}: n={len(x):4d} mean={x.mean()*1e4:+6.2f}bps  worst={x.min()*100:+6.2f}%  "
          f"CVaR5={cvar(x)*100:+6.2f}%  share_of_tail5={(r.nsmallest(int(len(r)*.05)).index.dayofweek==w).mean():.2f}")
# chi2: are worst-5% days uniformly spread across weekdays?
tail5 = r <= r.quantile(.05)
tab = np.array([[((bd.dayofweek==w)&(tail5==v)).sum() for w in range(5)] for v in (0,1)],float)
print(f"  chi2(tail5 x dow) p={chi2_contingency(tab)[1]:.3f}  (Wed triple-swap, Tue overnight-gap checks)")

print("\n############ Q3b — per-SLEEVE announcement tails ############")
fomc = P.A4_fomc.values=="fomc"; boj=(P.A4_boj.values=="boj")&P.post2020.values; non_boj=(P.A4_boj.values=="no")&P.post2020.values
for name, ser, ann, lbl in [("gold",SL.gold,fomc,"FOMC"),("overnight",SL.overnight,fomc,"FOMC"),
                            ("J1",SL.J1,boj,"BoJ(2020+)")]:
    s=ser.copy(); on=s[ann].dropna(); off=s[(~ann)].dropna() if lbl!="BoJ(2020+)" else s[non_boj].dropna()
    print(f"  {name:9s} on {lbl:11s}: n={len(on):3d} mean={on.mean()*1e4:+6.2f}bps worst={on.min()*100:+6.2f}% "
          f"CVaR5={cvar(on)*100:+6.2f}%  | off: mean={off.mean()*1e4:+6.2f}bps worst={off.min()*100:+6.2f}% CVaR5={cvar(off)*100:+6.2f}%")

print("\n############ Q2-mech — CO-LOSS: are worst book days multi-sleeve / risk-off? ############")
wmask = (r <= r.quantile(.05))
sgn = (SL < 0).astype(int)
n_neg_all = sgn.sum(1); n_neg_worst = sgn[wmask.values].sum(1)
print(f"  mean #neg sleeves: all-days={n_neg_all.mean():.2f}  worst5%-days={n_neg_worst.mean():.2f} (of 3)")
print(f"  worst-day breadth: 1-sleeve={ (n_neg_worst==1).mean():.2f}  2-sleeve={(n_neg_worst==2).mean():.2f}  3-sleeve={(n_neg_worst==3).mean():.2f}")
# per-sleeve mean on worst book days (attribution)
print("  sleeve mean on worst5% book days (bps):", {c: round(SL[c][wmask.values].mean()*1e4,1) for c in SL.columns})
# are the broad (>=2 neg) worst days the high-VIX ones?
broad = (n_neg_worst>=2).values; wdf = P.loc[wmask.values]
hi = (wdf.A1_vol.values=="hi")
print(f"  among worst5% days: P(hi-VIX | broad>=2neg)={hi[broad].mean():.2f}  P(hi-VIX | narrow)={hi[~broad].mean():.2f}  base(hi)=0.33")

print("\n############ ROBUSTNESS — A2 USD-up effect sub-period stability ############")
def lift_p(ev, col, sub, B=3000, roff="usd_up"):
    m = P[col].notna().values & sub
    e = ev.values[m].astype(int); g=P[col].values[m]
    if e.sum()<5: return (np.nan,np.nan,int(e.sum()))
    base=e.mean(); lift=e[g==roff].mean()/base if base>0 else np.nan
    bk=sorted(pd.unique(g[~pd.isna(g)]))
    def c2(gg):
        t=np.array([[((gg==b)&(e==v)).sum() for b in bk] for v in (0,1)],float); t=t[:,t.sum(0)>0]
        return chi2_contingency(t,correction=False)[0] if t.shape[1]>1 else 0.0
    obs=c2(g); rng=np.random.default_rng(SEED); cnt=1; n=len(e)
    for _ in range(B):
        if c2(np.roll(g,int(rng.integers(1,n))))>=obs-1e-12: cnt+=1
    return (lift, cnt/(B+1), int(e.sum()))
pre = np.asarray(bd<pd.Timestamp("2020-01-01")); post=np.asarray(bd>=pd.Timestamp("2020-01-01"))
ch_bust = pd.Series(bd.normalize().isin(set(EV.date.dt.normalize())), index=bd)
for tag,ev in [("Q1_ch_bust",ch_bust),("Q1_tail5", r<=r.quantile(.05))]:
    for sname,sub in [("full",np.ones(len(bd),bool)),("2013-2019",pre),("2020-2026",post)]:
        l,p,n = lift_p(ev,"A2_usd",sub)
        print(f"  {tag:11s} {sname:9s}: lift_usd_up={l:.2f}  p_perm={p:.4f}  n_ev={n}")

print("\n############ ANCHORS — worst book days & funded busts with regime ############")
worst = r.nsmallest(12)
print("  worst 12 book days (vm=1 daily_ret):")
for d,v in worst.items():
    row=P.loc[d]
    print(f"    {d.date()}  {v*100:+6.2f}%  VIX={row.vix_lag:5.1f}({row.A1_vol})  USD3m={row.dxy_mom_lag:+.3f}({row.A2_usd})  "
          f"FOMC±1={row.A4_fomc}  dow={['Mon','Tue','Wed','Thu','Fri'][d.dayofweek]}")
fb = pd.to_datetime(FMC.bust_date.dropna()).dt.normalize().unique()
print(f"  funded bust calendar days (distinct={len(fb)}):")
for d in sorted(fb):
    d=pd.Timestamp(d); row=P.reindex([d]).iloc[0] if d in P.index else None
    if row is not None:
        print(f"    {d.date()}  VIX={row.vix_lag:.1f}({row.A1_vol})  USD3m({row.A2_usd})  FOMC±1={row.A4_fomc}")
print("DONE")
