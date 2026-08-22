"""
Deep audit of S012 (Bollinger %b mean-reversion). Treats it as a quasi-candidate.
Decisive questions:
  A) Is the LONG dip-buy a real entry-timing alpha, or just uptrend beta?
     -> compare dip-buy (oversold %b<0.2) vs a NEUTRAL entry in the same uptrend (%b in [0.4,0.6]),
        same exit logic. If dip-buy >> neutral, the oversold timing adds value.
  B) Long-only vs short-only equity (Sharpe / CAGR / MaxDD).
  C) Walk-forward across sequential calendar blocks (stability over time).
  D) By asset class (long vs short).
  E) Cost stress x1.5 / x2.
Reuses strat_s012 (signals, simulate_meanrev, run_point) + ftmo_lab.
"""
import numpy as np, pandas as pd
import strat_s012_bollinger_pctb as s12, ftmo_lab as lab

ML, SD = s12.ML_REP, s12.SD_REP                         # canonical MA5 / SD1
uni, costs = s12.uni, s12.costs

def metrics(r):
    r = np.asarray(r, float)
    if len(r) == 0: return dict(n=0, expR=np.nan, win=np.nan, pf=np.nan, sharpe=np.nan)
    wins, los = r[r > 0], r[r < 0]
    pf = wins.sum()/abs(los.sum()) if los.sum() != 0 else np.inf
    return dict(n=len(r), expR=r.mean(), win=(r > 0).mean(), pf=pf)

def eq_metrics(tr):                                    # Sharpe/CAGR/MaxDD on a trades frame
    m = lab.trade_metrics(tr); return m['sharpe'], m['cagr'], m['maxdd']

# ---------- pooled trades at canonical ----------
pool = s12.run_point(ML, SD); pool['class'] = [lab.CLASS.get(i) for i in pool['instr']]
r, d = pool['netR'].values, pool['dir'].values
print("="*70); print("AUDIT S012 — Bollinger %b mean-reversion (canonical MA5/SD1)"); print("="*70)
print(f"Pooled: n={len(r)} expR {r.mean():+.4f} | long {r[d==1].mean():+.4f}(n{(d==1).sum()}) "
      f"short {r[d==-1].mean():+.4f}(n{(d==-1).sum()})")

# ---------- A) entry-timing alpha: dip-buy vs neutral-in-uptrend ----------
def neutral_signals(df, ma_len, st_dev, lo=0.4, hi=0.6):
    c = df['close']; b = s12.pctb(c, ma_len, st_dev).values
    mat = c.rolling(s12.MA_TREND).mean().values; cv = c.values; n = len(cv)
    ds = np.zeros(n)
    for s in range(3, n):
        if not (np.isfinite(mat[s]) and np.isfinite(b[s])): continue
        if cv[s] > mat[s] and lo <= b[s] <= hi: ds[s] = 1
        elif cv[s] < mat[s] and lo <= b[s] <= hi: ds[s] = -1
    return ds, b

dip_long, neu_long, dip_short, neu_short = [], [], [], []
for t, df in uni.items():
    ds, b = s12._sig(t, df, ML, SD)
    tr = s12.simulate_meanrev(df, ds, b, cost_bps=costs[t])
    if len(tr):
        dip_long += list(tr[tr.dir == 1]['netR']); dip_short += list(tr[tr.dir == -1]['netR'])
    nds, nb = neutral_signals(df, ML, SD)
    ntr = s12.simulate_meanrev(df, nds, nb, cost_bps=costs[t])
    if len(ntr):
        neu_long += list(ntr[ntr.dir == 1]['netR']); neu_short += list(ntr[ntr.dir == -1]['netR'])
print("\n[A] ENTRY-TIMING ALPHA (dip/pop vs neutral entry in same trend, same exit)")
dl, nl = metrics(dip_long), metrics(neu_long); ds_, ns_ = metrics(dip_short), metrics(neu_short)
print(f"  LONG  dip-buy   expR {dl['expR']:+.4f} (n{dl['n']}, win {dl['win']*100:.0f}%) "
      f"vs neutral expR {nl['expR']:+.4f} (n{nl['n']})  -> alpha {dl['expR']-nl['expR']:+.4f}")
print(f"  SHORT rip-sell  expR {ds_['expR']:+.4f} (n{ds_['n']}, win {ds_['win']*100:.0f}%) "
      f"vs neutral expR {ns_['expR']:+.4f} (n{ns_['n']})  -> alpha {ds_['expR']-ns_['expR']:+.4f}")

# ---------- B) long-only vs short-only equity ----------
print("\n[B] LONG-ONLY vs SHORT-ONLY equity (Sharpe / CAGR / MaxDD)")
for name, sub in [('LONG ', pool[pool.dir == 1]), ('SHORT', pool[pool.dir == -1]), ('BOTH ', pool)]:
    sh, cg, dd = eq_metrics(sub)
    print(f"  {name}: n={len(sub)} expR {sub['netR'].mean():+.4f} Sharpe {sh:+.2f} CAGR {cg*100:+.1f}% MaxDD {dd*100:.1f}%")

# ---------- C) walk-forward by calendar blocks ----------
print("\n[C] WALK-FORWARD (entry-date blocks)")
ent = pd.to_datetime(pool['entry'])
blocks = [('2000-07', '2006'), ('2006', '2012'), ('2012', '2018'), ('2018', '2027')]
for lo, hi in blocks:
    sub = pool[(ent >= pd.Timestamp(lo)) & (ent < pd.Timestamp(hi))]
    if len(sub) == 0: continue
    rr, dd2 = sub['netR'].values, sub['dir'].values
    sh, _, mdd = eq_metrics(sub)
    print(f"  {lo[:4]}-{hi[:4]}: n={len(sub):4d} expR {rr.mean():+.4f} Sh {sh:+.2f} "
          f"| long {rr[dd2==1].mean():+.4f} short {rr[dd2==-1].mean():+.4f}")

# ---------- D) by asset class ----------
print("\n[D] BY ASSET CLASS (long / short expR)")
for cls in ['indices', 'forex', 'commodities', 'crypto']:
    sub = pool[pool['class'] == cls]; rr, dd2 = sub['netR'].values, sub['dir'].values
    if len(rr) == 0: continue
    el = rr[dd2 == 1].mean() if (dd2 == 1).any() else np.nan
    es = rr[dd2 == -1].mean() if (dd2 == -1).any() else np.nan
    print(f"  {cls:12s}: n={len(rr):4d} expR {rr.mean():+.4f} | long {el:+.4f}(n{(dd2==1).sum()}) short {es:+.4f}(n{(dd2==-1).sum()})")

# ---------- E) cost stress ----------
print("\n[E] COST STRESS (x1.0 / x1.5 / x2.0)")
base = dict(costs)
for mult in [1.0, 1.5, 2.0]:
    for t in costs: costs[t] = base[t] * mult
    s12._SIG.clear()                                   # signals independent of cost, but clear cache to be safe
    p = s12.run_point(ML, SD); m = lab.trade_metrics(p)
    rr, dd2 = p['netR'].values, p['dir'].values
    print(f"  x{mult}: expR {m['expR']:+.4f} PF {m['pf']:.3f} Sharpe {m['sharpe']:.2f} "
          f"| long {rr[dd2==1].mean():+.4f} short {rr[dd2==-1].mean():+.4f}")
for t in costs: costs[t] = base[t]
print("\n(audit done)")
