"""
TIER-1 RE-AUDIT SCAN — systematically re-test every DISCARD for a hidden edge (false negative),
applying the lens that flipped S012: disaggregate by side x asset-class, test RECENT OOS (2019+),
measure TIMING-ALPHA vs unconditional drift, and check two-sided symmetry.

For each strategy: full & recent Sharpe; best class-subset recent; long/short recent expR;
timing-alpha (mean H=10d fwd return on signal dates minus instrument unconditional drift, by side);
two-sided-recent flag. Resumable (appends to reaudit_scan.csv; skips done). Reuses each strat module
+ ftmo_lab UNCHANGED. load_universe cached at runtime (no file edit).
"""
import sys, os, importlib, numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab
lab.load_universe = lru_cache(None)(lab.load_universe)   # runtime cache only
UNI = lab.load_universe(); CLS = {t: lab.CLASS.get(t) for t in UNI}
RECENT = pd.Timestamp('2018-12-31'); H = 10
OUT = "reaudit_scan.csv"

# per-instrument H-day forward return + unconditional drift (for timing-alpha)
FWD = {}; UNC = {}
for t, df in UNI.items():
    c = df['close']; fr = (c.shift(-H) / c - 1.0)
    FWD[t] = dict(zip(df.index, fr.values)); UNC[t] = float(np.nanmean(fr.values))

REG = [
    (1, 'strat_s001_crabel_nr_orb', 's001', (3.0, 10), 'orb'),
    (2, 'strat_s002_crabel_nr_setupexit', 'rp', (20, 10), 'orb'),
    (3, 'strat_s003_3bar_momentum', 'rp', (40, 35), 'trend'),
    (4, 'strat_s004_kaufman_ama', 'rp', (10, 0.2), 'trend'),
    (5, 'strat_s005_kaufman_ama_setup', 'rp', (10, 2), 'trend'),
    (6, 'strat_s006_adx_donchian', 'rp', (20, 0), 'trend'),
    (7, 'strat_s007_aroon_breakout', 'rp', (25, 70), 'trend'),
    (8, 'strat_s008_aroon_newhigh', 'rp', (25, 20), 'trend'),
    (9, 'strat_s009_aroon_slow', 'rp', (50, 20), 'trend'),
    (10, 'strat_s010_aroon_crossover', 'rp', (25, 20), 'trend'),
    (11, 'strat_s011_adx_lookback', 'rp', (14, 0), 'trend'),
    (12, 'strat_s012_bollinger_pctb', 'rp', (5, 1.0), 'MR*ctrl'),
    (13, 'strat_s013_bollinger_filter', 'rp', (5, 200), 'MR'),
    (14, 'strat_s014_bollinger_momentum', 'rp', (100, 2.0), 'trend'),
    (15, 'strat_s015_directional_movement', 'rp', (14, 0), 'trend'),
    (16, 'strat_s016_doji_reversal', 'rp', (0.10, 10), 'MR'),
    (17, 'strat_s017_doji_reversal_exit', 'rp', (10, 20), 'MR'),
    (18, 'strat_s018_doji_trend', 'rp', (0.10, 10), 'trend'),
    (19, 'strat_s019_doji_trend_exit', 'rp', (10, 20), 'trend'),
    (20, 'strat_s020_donchian', 'rp', (20, 20), 'trend'),
    (21, 'strat_s021_donchian_atr', 'rp', (20, 3), 'trend'),
    (22, 'strat_s022_combined_donchian', 'rp', (20, 50), 'trend'),
    (23, 'strat_s023_dow_mtf', 'rp', (2, 3), 'trend'),
    (24, 'strat_s024_dow_trend', 'rp', (3, 21), 'trend'),
    (25, 'strat_s025_dual_momentum_roc', 'rp', (100, 51), 'trend'),
    (26, 'strat_s026_dual_momentum_vortex', 'rp', (100, 51), 'trend'),
    (27, 'strat_s027_engulfing', 'combined', None, 'candle'),
    (28, 'strat_s028_engulfing_bull', 'run', None, 'candle'),
    (29, 'strat_s029_engulfing_bull_a', 'run', None, 'candle'),
    (30, 'strat_s030_engulfing_bull_a_filter', 'run', None, 'candle'),
]

def get_pool(modname, kind, args):
    m = importlib.import_module(modname)
    if kind == 'rp':       p = m.run_point(*args, fill='stop')
    elif kind == 's001':   p = m.run(args[0], args[1], m.uni, m.costs)[0]
    elif kind == 'combined': p = m.run_combined(fill='stop')
    elif kind == 'run':    p = m.run('stop')
    if 'cls' not in p.columns and len(p):
        p['cls'] = p['instr'].map(CLS)
    return p

def timing_alpha(pool, side):
    sub = pool[pool['dir'] == side]
    if not len(sub): return np.nan, 0
    a = []
    for _, r in sub.iterrows():
        f = FWD.get(r['instr'], {}).get(r['entry'])
        if f is not None and np.isfinite(f):
            a.append(side * (f - UNC[r['instr']]))   # entry timing vs random-timing drift, by side
    return (float(np.mean(a)) if a else np.nan), len(a)

def m_(pool):
    return lab.trade_metrics(pool)

def scan_one(num, modname, kind, args, typ):
    pool = get_pool(modname, kind, args)
    if not len(pool): return None
    e = pd.to_datetime(pool['entry']); rec = pool[e > RECENT]
    full, recm = m_(pool), m_(rec)
    # best class subset (recent), and recent long/short
    best_cls, best_sh, best_n = '-', -9, 0
    for cl in ['indices', 'forex', 'commodities', 'crypto']:
        s = rec[rec['cls'] == cl]
        if len(s) >= 30:
            mm = m_(s)
            if np.isfinite(mm['sharpe']) and mm['sharpe'] > best_sh:
                best_cls, best_sh, best_n = cl, mm['sharpe'], mm['trades']
    rl = rec[rec['dir'] == 1]; rs = rec[rec['dir'] == -1]
    rl_e = m_(rl)['expR'] if len(rl) else np.nan
    rs_e = m_(rs)['expR'] if len(rs) else np.nan
    al, nal = timing_alpha(pool[e > RECENT], 1); ash, nash = timing_alpha(pool[e > RECENT], -1)
    twosided_rec = bool(np.isfinite(rl_e) and np.isfinite(rs_e) and rl_e > 0 and rs_e > 0 and len(rl) >= 30 and len(rs) >= 30)
    # FLAG for Tier-2 re-exam
    flag = []
    if typ.startswith('MR'): flag.append('MR-lens')
    if twosided_rec: flag.append('2sided-recent+')
    if np.isfinite(best_sh) and best_sh > 0.7 and best_n >= 50 and np.isfinite(al) and al > 0.003:
        flag.append('subset+alpha')
    return dict(num=num, type=typ, n=full['trades'], full_expR=round(full['expR'], 4), full_Sh=round(full['sharpe'], 2),
                rec_n=recm['trades'], rec_expR=round(recm['expR'], 4), rec_Sh=round(recm['sharpe'], 2),
                best_cls=best_cls, best_cls_Sh=round(best_sh, 2), best_cls_n=best_n,
                rec_long_expR=round(rl_e, 4) if np.isfinite(rl_e) else np.nan,
                rec_short_expR=round(rs_e, 4) if np.isfinite(rs_e) else np.nan,
                alpha_long_rec=round(al, 4) if np.isfinite(al) else np.nan,
                alpha_short_rec=round(ash, 4) if np.isfinite(ash) else np.nan,
                flag='|'.join(flag) if flag else '-')

if __name__ == "__main__":
    done = set()
    if os.path.exists(OUT):
        try: done = set(pd.read_csv(OUT)['num'].tolist())
        except Exception: pass
    rows = [] if not done else pd.read_csv(OUT).to_dict('records')
    for num, modname, kind, args, typ in REG:
        if num in done:
            continue
        try:
            r = scan_one(num, modname, kind, args, typ)
            if r: rows.append(r); print(f"S{num:03d} {typ:<8} fullSh {r['full_Sh']:+.2f} recSh {r['rec_Sh']:+.2f} "
                                        f"best={r['best_cls']}{r['best_cls_Sh']:+.2f}(n{r['best_cls_n']}) "
                                        f"recL {r['rec_long_expR']} recS {r['rec_short_expR']} "
                                        f"aL {r['alpha_long_rec']} aS {r['alpha_short_rec']} FLAG[{r['flag']}]")
            pd.DataFrame(rows).sort_values('num').to_csv(OUT, index=False)
        except Exception as ex:
            print(f"S{num:03d} ERROR {type(ex).__name__}: {ex}")
    print(f"\nDONE {len(rows)}/30 -> {OUT}")
