"""
DEEP-DIVE part 2 — corrected audit of the CHAMPION (indices LONG dip-buy) + low-vol thesis.
Iteration findings from part 1: (1) edge lives in LOW vol (vol-filter>=0.5 was wrong);
(2) champion = indices LONG-only (recent Sharpe ~1.0, not decayed). Here we audit it rigorously:
alpha-vs-neutral (full+recent), walk-forward, US-concentrate, low-vol filter, delay1/DSR/OOS/strict-OOS.
Reuses s012_deepdive (run_variant, simulate_ex) + ftmo_lab gates.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import strat_s012_bollinger_pctb as s12
import s012_deepdive as dd

uni, costs, INDICES = dd.uni, dd.costs, dd.INDICES
US = ['US30', 'US500', 'US100', 'US2000']
RECENT = pd.Timestamp('2018-12-31')

def wf(pool, label):
    e = pd.to_datetime(pool['entry']); row = []
    for y0 in (2000, 2006, 2012, 2018, 2024):
        sub = pool[(e >= pd.Timestamp(f"{y0}-01-01")) & (e < pd.Timestamp(f"{y0+6}-01-01"))]
        m = lab.trade_metrics(sub); row.append(f"{y0}-{str(y0+5)[2:]}:Sh{m['sharpe']:+.2f}(n{m['trades']})")
    print(f"  {label:<26} " + " ".join(row))

def sc(pool):
    m = lab.trade_metrics(pool); rec = lab.trade_metrics(pool[pd.to_datetime(pool['entry']) > RECENT])
    return m, rec

# neutral entry (same uptrend, %b in [0.4,0.6]) — to isolate timing alpha vs beta
def neutral_run(instruments, ml=5, sd=1.0, vol_max=None):
    frames = []
    for t in instruments:
        df = uni[t]; c = df['close']; b = s12.pctb(c, ml, sd).values
        mat = c.rolling(200).mean().values; cv = c.values; n = len(cv); ds = np.zeros(n, np.int8)
        for s in range(3, n):
            if np.isfinite(mat[s]) and np.isfinite(b[s]) and cv[s] > mat[s] and 0.4 <= b[s] <= 0.6:
                ds[s] = 1
        tr = dd.simulate_ex(t, df, ds, b, side='long', vol_max=vol_max, cost_bps=costs[t])
        if len(tr): frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    print("DEEP-DIVE 2 — CHAMPION (indices LONG dip-buy) corrected audit\n")
    print("===== A) CORRECTED BATTERY (full | 2019+) =====")
    cands = {
        "C0 indices/LONG":              dict(instruments=INDICES, side='long'),
        "C1 indices/LONG/vol<=0.5":     dict(instruments=INDICES, side='long', vol_max=0.5),
        "C2 indices/LONG/vol<=0.66":    dict(instruments=INDICES, side='long', vol_max=0.66),
        "C3 US-indices/LONG":           dict(instruments=US, side='long'),
        "C4 US-indices/LONG/vol<=0.5":  dict(instruments=US, side='long', vol_max=0.5),
        "C5 indices/BOTH/vol<=0.5":     dict(instruments=INDICES, vol_max=0.5),
    }
    pools = {}
    for lbl, kw in cands.items():
        p = dd.run_variant(**kw); pools[lbl] = p; m, rec = sc(p)
        print(f"{lbl:<28} n={m['trades']:>5} expR={m['expR']:+.4f} Sh={m['sharpe']:+.2f} DD={m['maxdd']*100:>5.0f}% "
              f"PF={m['pf']:.2f} | 2019+ n={rec['trades']:>4} expR={rec['expR']:+.4f} Sh={rec['sharpe']:+.2f}")

    print("\n===== B) WALK-FORWARD =====")
    for lbl in ["C0 indices/LONG", "C1 indices/LONG/vol<=0.5", "C3 US-indices/LONG", "C5 indices/BOTH/vol<=0.5"]:
        wf(pools[lbl], lbl)

    print("\n===== C) ALPHA vs NEUTRAL (timing alpha, not beta) =====")
    for lbl, instr, vmax in [("indices/LONG", INDICES, None), ("US-indices/LONG", US, None)]:
        champ = pools["C0 indices/LONG"] if instr is INDICES else pools["C3 US-indices/LONG"]
        neu = neutral_run(instr, vol_max=vmax)
        cm, cr = sc(champ); nm, nr = sc(neu)
        print(f"  {lbl:<16} dip-buy expR full {cm['expR']:+.4f} / 2019+ {cr['expR']:+.4f}  |  "
              f"neutral full {nm['expR']:+.4f} / 2019+ {nr['expR']:+.4f}  |  "
              f"ALPHA full {cm['expR']-nm['expR']:+.4f} / 2019+ {cr['expR']-nr['expR']:+.4f}")

    print("\n===== D) PER-INDEX recent 2019+ (champion C0) =====")
    champ = pools["C0 indices/LONG"]; rec = champ[pd.to_datetime(champ['entry']) > RECENT]
    perp = {t: lab.trade_metrics(rec[rec['instr'] == t]) for t in INDICES if len(rec[rec['instr'] == t]) >= 5}
    perdf = pd.DataFrame(perp).T.sort_values('expR', ascending=False)
    print(perdf[['trades', 'expR', 'sharpe', 'win']].round(3).to_string())

    print("\n===== E) AUDIT champion C0 (indices LONG) — gates adapted =====")
    runC = lambda fill='stop': dd.run_variant(INDICES, side='long', fill=fill)
    opt = lab.trade_metrics(runC('stop')); rea = lab.trade_metrics(runC('next_open')); cl = lab.trade_metrics(runC('close'))
    print(f"  [delay1] natif open[s+1] Sh {opt['sharpe']:+.2f} (expR {opt['expR']:+.4f}) -> open[s+2] Sh {rea['sharpe']:+.2f} (expR {rea['expR']:+.4f}) ; close[s+1] Sh {cl['sharpe']:+.2f}")
    MLs = [3, 5, 10, 20]; SDs = [1.0, 1.5, 2.0]; sgr = []
    for ml in MLs:
        for sd in SDs:
            sgr.append(lab.trade_metrics(dd.run_variant(INDICES, ml=ml, sd=sd, side='long'))['sharpe'])
    sgr = np.array(sgr); base = runC('stop')
    dsr = lab.gate_dsr(sgr, float(np.nanmax(sgr)), base['netR'].values)
    print(f"  [DSR] N={dsr['N_trials']} SR_obs={dsr['SR_obs']:.3f} vs E[max]={dsr['E_max_SR']:.3f} z={dsr['DSR_z']:.2f} -> {'PASS' if dsr['pass'] else 'FAIL'}")
    oos = lab.gate_oos(base, '2015-12-31')
    print(f"  [OOS 2015] train {oos['train_expR']:+.4f}(Sh{oos['train_sharpe']:+.2f}) -> test {oos['test_expR']:+.4f}(Sh{oos['test_sharpe']:+.2f}) -> {'PASS' if oos['pass'] else 'FAIL'}")
    ent = pd.to_datetime(base['entry']); tr_, te_ = base[ent <= RECENT], base[ent > RECENT]
    mtr, mte = lab.trade_metrics(tr_), lab.trade_metrics(te_)
    print(f"  [STRICT OOS <=2018/2019+] train {mtr['expR']:+.4f}(Sh{mtr['sharpe']:+.2f}) -> test {mte['expR']:+.4f}(Sh{mte['sharpe']:+.2f})")
    # alpha-vs-neutral recent already in C; long-only => two-sided gate replaced by that.
    print(f"\n  CHAMPION C0 summary: full Sh {opt['sharpe']:+.2f}, recent Sh {mte['sharpe']:+.2f}, "
          f"delay1 {'OK' if rea['sharpe']>0 and rea['expR']>0 else 'FAIL'}, DSR {'OK' if dsr['pass'] else 'FAIL'}, "
          f"recent-OOS {'OK' if mte['expR']>0 else 'FAIL'}")
    pd.DataFrame({k: lab.trade_metrics(v) for k, v in pools.items()}).T.to_csv("s012_deepdive2_candidates.csv")
    print("\nSaved: s012_deepdive2_candidates.csv")
