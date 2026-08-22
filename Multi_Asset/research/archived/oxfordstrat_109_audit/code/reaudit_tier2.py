"""
TIER-2 RE-AUDIT — decisive discriminators on the flagged/representative DISCARDs.
(1) BUY&HOLD class benchmark (full, 2019+) -> contextualises every 'high recent subset Sharpe':
    a strategy subset that doesn't beat buy&hold of that class is just (worse) beta.
(2) REGIME-MATCHED timing-alpha (the S012 test, generalised): long-alpha = mean 10d-fwd-ret on the
    strategy's long-entry dates  -  mean 10d-fwd-ret over ALL same-instrument bars in the same trend
    regime (close>MA200). MR (buy dips) => alpha>0 ; trend (buy breakouts) => alpha~0 (pure beta).
(3) ORB delay+1 (S001/S002): does the recent two-sided edge survive a realistic fill?
Indices-focused (crypto=2 assets handled by the buy&hold benchmark). Reuses strat modules + ftmo_lab.
"""
import importlib, numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab
lab.load_universe = lru_cache(None)(lab.load_universe)
UNI = lab.load_universe(); CLS = {t: lab.CLASS.get(t) for t in UNI}
INDICES = [t for t in UNI if CLS[t] == 'indices']
RECENT = pd.Timestamp('2018-12-31'); H = 10

# per-instrument: 10d fwd return, MA200 up-regime, regime-conditional neutral baselines
FWD, UP, NEU_UP, NEU_DN = {}, {}, {}, {}
for t, df in UNI.items():
    c = df['close']; fr = (c.shift(-H) / c - 1.0)
    up = (c > c.rolling(200).mean())
    FWD[t] = pd.Series(fr.values, index=df.index)
    UP[t] = pd.Series(up.values, index=df.index)
    NEU_UP[t] = float(np.nanmean(fr.values[up.values & np.isfinite(fr.values)]))
    NEU_DN[t] = float(np.nanmean(fr.values[(~up.values) & np.isfinite(fr.values)]))

def bh_sharpe(instruments, since=None):
    rs = []
    for t in instruments:
        r = UNI[t]['close'].pct_change()
        if since is not None: r = r[r.index > since]
        rs.append(r)
    R = pd.concat(rs, axis=1).mean(axis=1).dropna()           # equal-weight daily basket
    return float(R.mean() / R.std() * np.sqrt(252)) if R.std() > 0 else np.nan

def regime_alpha(pool, instruments):
    p = pool[pool['instr'].isin(instruments)].copy(); e = pd.to_datetime(p['entry'])
    def side_alpha(sub, side):
        vals = []
        for _, r in sub.iterrows():
            f = FWD[r['instr']].get(r['entry'])
            if f is not None and np.isfinite(f):
                base = NEU_UP[r['instr']] if side == 1 else NEU_DN[r['instr']]
                vals.append(side * (f - base))
        return (float(np.mean(vals)) if vals else np.nan, len(vals))
    out = {}
    for tag, mask in [('full', np.ones(len(p), bool)), ('rec', (e > RECENT).values)]:
        pp = p[mask]
        la, ln = side_alpha(pp[pp['dir'] == 1], 1); sa, sn = side_alpha(pp[pp['dir'] == -1], -1)
        out[tag] = (la, ln, sa, sn)
    return out

REG = {  # num -> (module, kind, args)
    1: ('strat_s001_crabel_nr_orb', 's001', (3.0, 10)), 2: ('strat_s002_crabel_nr_setupexit', 'rp', (20, 10)),
    6: ('strat_s006_adx_donchian', 'rp', (20, 0)), 11: ('strat_s011_adx_lookback', 'rp', (14, 0)),
    12: ('strat_s012_bollinger_pctb', 'rp', (5, 1.0)), 13: ('strat_s013_bollinger_filter', 'rp', (5, 200)),
    16: ('strat_s016_doji_reversal', 'rp', (0.10, 10)), 17: ('strat_s017_doji_reversal_exit', 'rp', (10, 20)),
    22: ('strat_s022_combined_donchian', 'rp', (20, 50)), 23: ('strat_s023_dow_mtf', 'rp', (2, 3)),
    25: ('strat_s025_dual_momentum_roc', 'rp', (100, 51)), 26: ('strat_s026_dual_momentum_vortex', 'rp', (100, 51)),
}
def pool_of(num, fill='stop'):
    mod, kind, args = REG[num]; m = importlib.import_module(mod)
    if kind == 'rp':   p = m.run_point(*args, fill=fill)
    else:              p = m.run(args[0], args[1], UNI, {t: lab.round_turn_cost_bps(t, UNI[t]) for t in UNI}, )[0] if kind == 's001' else None
    if 'cls' not in p.columns: p['cls'] = p['instr'].map(CLS)
    return p

if __name__ == "__main__":
    print("===== 1) BUY & HOLD benchmark (Sharpe) — context for 'recent subset' beta =====")
    for cl, inst in [('indices', INDICES), ('crypto', [t for t in UNI if CLS[t] == 'crypto']),
                     ('commodities', [t for t in UNI if CLS[t] == 'commodities']),
                     ('forex', [t for t in UNI if CLS[t] == 'forex'])]:
        print(f"  {cl:<12} buy&hold full Sh {bh_sharpe(inst):+.2f} | 2019+ Sh {bh_sharpe(inst, RECENT):+.2f}  ({len(inst)} instr)")

    print("\n===== 2) INDICES-LONG recent vs buy&hold + REGIME-MATCHED timing-alpha =====")
    print("  (alpha>0 = real timing edge beyond regime/beta ; ~0 = beta)")
    bh_idx_rec = bh_sharpe(INDICES, RECENT)
    for num in [12, 13, 16, 17, 2, 6, 11, 22, 23, 25, 26]:
        try:
            p = pool_of(num)
        except Exception as ex:
            print(f"  S{num:03d} ERR {ex}"); continue
        idx = p[p['instr'].isin(INDICES)]; e = pd.to_datetime(idx['entry'])
        il = idx[(idx['dir'] == 1)]; ilr = il[pd.to_datetime(il['entry']) > RECENT]
        mlr = lab.trade_metrics(ilr)
        a = regime_alpha(p, INDICES)
        laf, lnf, saf, snf = a['full']; lar, lnr, sar, snr = a['rec']
        print(f"  S{num:03d}: idx-LONG recent Sh {mlr['sharpe']:+.2f} (n{mlr['trades']}, expR {mlr['expR']:+.4f}) "
              f"| regime-alpha LONG full {laf:+.4f}/rec {lar:+.4f}  SHORT full {saf:+.4f}/rec {sar:+.4f}")

    print("\n===== 3) ORB delay+1 (recent two-sided) — real edge or fill artefact? =====")
    for num in [1, 2]:
        try:
            ps, pn = pool_of(num, 'stop'), pool_of(num, 'next_open')
        except Exception as ex:
            print(f"  S{num:03d} ERR {ex}"); continue
        for tag, p in [('stop', ps), ('next_open', pn)]:
            r = p[pd.to_datetime(p['entry']) > RECENT]; m = lab.trade_metrics(r)
            rl = r[r['dir'] == 1]; rs = r[r['dir'] == -1]
            print(f"  S{num:03d} [{tag:<9}] recent expR {m['expR']:+.4f} Sh {m['sharpe']:+.2f} | "
                  f"L {lab.trade_metrics(rl)['expR']:+.4f} S {lab.trade_metrics(rs)['expR']:+.4f}")
    print("\nDONE tier2.")
