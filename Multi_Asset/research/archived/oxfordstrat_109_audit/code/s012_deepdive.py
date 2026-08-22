"""
DEEP-DIVE / ITERATION — S012 Bollinger %b mean-reversion (the lone watchlist).
Goal: locate the edge precisely (vol regime, %b depth, per-instrument recency, exit), then ITERATE
improvements (indices-only, vol-filter, exit redesign, deeper threshold) and AUDIT each through the
4 constitutional gates + a STRICT recent OOS (train<=2018 / test 2019+). Honest verdict, no flattery.

Reuses strat_s012 (pctb) + ftmo_lab v2-gates (atr, costs, trade_metrics, run_gates) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
import strat_s012_bollinger_pctb as s12

uni, costs = s12.uni, s12.costs
CLS = {t: lab.CLASS.get(t) for t in uni}
INDICES = [t for t in uni if CLS[t] == 'indices']
MA_TREND, ATR_LEN, ATR_STOP = 200, 20, 6.0
RECENT = pd.Timestamp('2018-12-31')

# ---------- per-instrument precompute (vol regime) ----------
def realized_vol(df, w=20):
    return df['close'].pct_change().rolling(w).std()
_VOLP = {t: realized_vol(df).rolling(252).rank(pct=True).values for t, df in uni.items()}  # current-vol percentile

# ---------- parameterised signals & simulator ----------
_SIGC = {}
def signals_ex(t, df, ma_len, st_dev, thr=0.2, nconsec=3):
    key = (t, ma_len, st_dev, thr, nconsec)
    if key in _SIGC: return _SIGC[key]
    c = df['close']; b = s12.pctb(c, ma_len, st_dev).values
    mat = c.rolling(MA_TREND).mean().values; cv = c.values; n = len(cv)
    ds = np.zeros(n, np.int8); ok = np.isfinite(b); lo, hi = thr, 1 - thr
    for s in range(nconsec, n):
        if not (np.isfinite(mat[s]) and ok[s] and ok[s-1] and ok[s-2]):
            continue
        if cv[s] > mat[s] and b[s] < lo and b[s-1] < lo and b[s-2] < lo:
            ds[s] = 1
        elif cv[s] < mat[s] and b[s] > hi and b[s-1] > hi and b[s-2] > hi:
            ds[s] = -1
    _SIGC[key] = (ds, b); return _SIGC[key]

def simulate_ex(t, df, ds, b, *, exit_type='pctb', time_n=10, atr_stop=ATR_STOP, cost_bps=2.0,
                side='both', vol_min=None, vol_max=None, fill='stop', revL=0.8, revS=0.2):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; vp = _VOLP[t]; n = len(df); idx = df.index
    trades = []; s = 3
    while s < n - 1:
        d = ds[s]
        if d == 0 or not np.isfinite(A[s]) or A[s] <= 0:
            s += 1; continue
        if (side == 'long' and d != 1) or (side == 'short' and d != -1):
            s += 1; continue
        if vol_min is not None and (not np.isfinite(vp[s]) or vp[s] < vol_min):
            s += 1; continue
        if vol_max is not None and (not np.isfinite(vp[s]) or vp[s] > vol_max):
            s += 1; continue
        eb = s + 2 if fill == 'next_open' else s + 1
        if eb > n - 1:
            s += 1; continue
        entry = c[eb] if fill == 'close' else o[eb]
        if not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if exit_type in ('pctb', 'pctb_or_time'):
                if d == 1 and np.isfinite(b[j]) and b[j] > revL:  exit_p, reason, exit_j = c[j], 'trend', j; break
                if d == -1 and np.isfinite(b[j]) and b[j] < revS: exit_p, reason, exit_j = c[j], 'trend', j; break
            if exit_type in ('time', 'pctb_or_time') and j >= eb + time_n - 1:
                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = n - 1; exit_p, reason = c[n-1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, volp=vp[s], instr=t, cls=CLS[t]))
        s = exit_j
    return pd.DataFrame(trades)

def run_variant(instruments, ml=5, sd=1.0, thr=0.2, exit_type='pctb', time_n=10,
                side='both', vol_min=None, vol_max=None, cost_bps=None, fill='stop'):
    frames = []
    for t in instruments:
        df = uni[t]; ds, b = signals_ex(t, df, ml, sd, thr)
        tr = simulate_ex(t, df, ds, b, exit_type=exit_type, time_n=time_n, side=side,
                         vol_min=vol_min, vol_max=vol_max, fill=fill, cost_bps=costs[t] if cost_bps is None else cost_bps)
        if len(tr): frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def score(pool):
    m = lab.trade_metrics(pool)
    rec = lab.trade_metrics(pool[pd.to_datetime(pool['entry']) > RECENT]) if len(pool) else m
    r = pool['netR'].values; d = pool['dir'].values if len(pool) else np.array([])
    el = r[d == 1].mean() if (d == 1).any() else np.nan
    es = r[d == -1].mean() if (d == -1).any() else np.nan
    return dict(n=m['trades'], expR=m['expR'], sharpe=m['sharpe'], maxdd=m['maxdd'],
                rec_n=rec['trades'], rec_expR=rec['expR'], rec_sharpe=rec['sharpe'],
                long=el, short=es)

def line(label, sc):
    print(f"{label:<42} n={sc['n']:>5} expR={sc['expR']:+.4f} Sh={sc['sharpe']:+.2f} DD={sc['maxdd']*100:>5.0f}% "
          f"| 2019+ n={sc['rec_n']:>4} expR={sc['rec_expR']:+.4f} Sh={sc['rec_sharpe']:+.2f} "
          f"| L={sc['long']:+.4f} S={sc['short']:+.4f}")

if __name__ == "__main__":
    print(f"DEEP-DIVE S012 | {lab.PIPELINE_VERSION} | indices={len(INDICES)} | recent split >{RECENT.date()}\n")
    ALL = list(uni)
    # ============ A) VARIANT BATTERY ============
    print("===== A) BATTERY (full-sample + 2019+ recent) =====")
    variants = {
        "B0 baseline all/both/pctb":        dict(instruments=ALL),
        "B1 indices/both/pctb":             dict(instruments=INDICES),
        "B2 indices/LONG/pctb":             dict(instruments=INDICES, side='long'),
        "B3 indices/both/vol>=0.5":         dict(instruments=INDICES, vol_min=0.5),
        "B4 indices/both/vol>=0.7":         dict(instruments=INDICES, vol_min=0.7),
        "B5 indices/LONG/vol>=0.5":         dict(instruments=INDICES, side='long', vol_min=0.5),
        "B6 indices/both/exit=time5":       dict(instruments=INDICES, exit_type='time', time_n=5),
        "B7 indices/both/pctb_or_time10":   dict(instruments=INDICES, exit_type='pctb_or_time', time_n=10),
        "B8 indices/both/thr=0.1":          dict(instruments=INDICES, thr=0.1),
        "B9 indices/both/vol>=0.5/por_t10": dict(instruments=INDICES, vol_min=0.5, exit_type='pctb_or_time', time_n=10),
        "B10 indices/LONG/vol>=0.5/thr0.1": dict(instruments=INDICES, side='long', vol_min=0.5, thr=0.1),
    }
    scores = {}
    for lbl, kw in variants.items():
        scores[lbl] = score(run_variant(**kw)); line(lbl, scores[lbl])

    # ============ B) WHERE THE EDGE LIVES: VOL REGIME ============
    print("\n===== B) EDGE BY VOLATILITY REGIME (baseline indices, both) =====")
    base = run_variant(INDICES)
    for name, lo, hi in [("low vol (<0.33)", 0, .33), ("mid (0.33-0.66)", .33, .66), ("high vol (>0.66)", .66, 1.01)]:
        sub = base[(base['volp'] >= lo) & (base['volp'] < hi)]
        ml = lab.trade_metrics(sub); r = sub['netR'].values; d = sub['dir'].values
        el = r[d == 1].mean() if (d == 1).any() else np.nan; es = r[d == -1].mean() if (d == -1).any() else np.nan
        print(f"  {name:<18} n={ml['trades']:>5} expR={ml['expR']:+.4f} Sh={ml['sharpe']:+.2f} | L={el:+.4f} S={es:+.4f}")

    # ============ C) WALK-FORWARD: baseline vs engineered ============
    print("\n===== C) WALK-FORWARD (4-yr blocks): baseline-all vs engineered(B9) =====")
    b0 = run_variant(ALL); b9 = run_variant(INDICES, vol_min=0.5, exit_type='pctb_or_time', time_n=10)
    for lab_, pool in [("baseline-all", b0), ("engineered B9", b9)]:
        e = pd.to_datetime(pool['entry'])
        row = []
        for y0 in (2000, 2006, 2012, 2018, 2024):
            sub = pool[(e >= pd.Timestamp(f"{y0}-01-01")) & (e < pd.Timestamp(f"{y0+6}-01-01"))]
            m = lab.trade_metrics(sub); row.append(f"{y0}-{y0+5}:Sh{m['sharpe']:+.2f}(n{m['trades']})")
        print(f"  {lab_:<14} " + "  ".join(row))

    # ============ D) PER-INDEX RECENT (2019+) ============
    print("\n===== D) PER-INDEX recent 2019+ (engineered B9) =====")
    rec = b9[pd.to_datetime(b9['entry']) > RECENT]
    perp = {t: lab.trade_metrics(rec[rec['instr'] == t]) for t in INDICES if len(rec[rec['instr'] == t]) >= 5}
    perdf = pd.DataFrame(perp).T.sort_values('expR', ascending=False)
    print(perdf[['trades', 'expR', 'sharpe', 'win']].round(3).to_string())

    # ============ E) AUDIT the engineered sleeve through the gates ============
    print("\n===== E) GATES on ENGINEERED B9 (indices, vol>=0.5, pctb_or_time10) =====")
    runE = lambda fill='stop': run_variant(INDICES, vol_min=0.5, exit_type='pctb_or_time', time_n=10, fill=fill)
    MLs = [3, 5, 10]; SDs = [1.0, 1.5, 2.0]; sg = np.full((3, 3), np.nan)
    for a, ml in enumerate(MLs):
        for bb, sd in enumerate(SDs):
            sg[a, bb] = lab.trade_metrics(run_variant(INDICES, ml=ml, sd=sd, vol_min=0.5,
                                                      exit_type='pctb_or_time', time_n=10))['sharpe']
    res = lab.run_gates(runE, sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                        (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                         f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                         f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                         f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                        (f"  << {x['tag']}" if x.get('tag') else ""))
    # STRICT recent OOS: train<=2018 / test 2019+
    pe = run_variant(INDICES, vol_min=0.5, exit_type='pctb_or_time', time_n=10)
    ent = pd.to_datetime(pe['entry']); tr_, te_ = pe[ent <= RECENT], pe[ent > RECENT]
    mtr, mte = lab.trade_metrics(tr_), lab.trade_metrics(te_)
    print(f"  STRICT OOS (<=2018 / 2019+): train expR {mtr['expR']:+.4f} Sh {mtr['sharpe']:+.2f}  ->  "
          f"test expR {mte['expR']:+.4f} Sh {mte['sharpe']:+.2f}")
    print(f"  >>> B9 verdict: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")

    # save battery
    pd.DataFrame(scores).T.to_csv("s012_deepdive_battery.csv")

    # ============ FIGURE (4 panels) ============
    fig, ax = plt.subplots(2, 2, figsize=(14, 9))
    # 1) equity curves (cum net R by exit date)
    def eq(pool):
        p = pool.sort_values('exit'); return pd.to_datetime(p['exit']), p['netR'].cumsum().values
    for lbl, pool, c_ in [("baseline all/both", b0, '#888'),
                          ("indices/both", run_variant(INDICES), '#1f77b4'),
                          ("indices/LONG", run_variant(INDICES, side='long'), '#2ca02c'),
                          ("engineered B9", b9, '#d62728')]:
        if len(pool): x, y = eq(pool); ax[0, 0].plot(x, y, label=lbl, color=c_, lw=1.5)
    ax[0, 0].set_title("A) Cumulative net R (after costs)"); ax[0, 0].legend(fontsize=8); ax[0, 0].grid(alpha=.3)
    # 2) annual Sharpe baseline vs engineered
    def annual_sharpe(pool):
        p = pool.copy(); p['yr'] = pd.to_datetime(p['entry']).dt.year
        out = {}
        for y, gp in p.groupby('yr'):
            r = gp['netR'].values
            out[y] = (r.mean()/r.std()*np.sqrt(len(r)/((pd.to_datetime(gp['exit']).max()-pd.to_datetime(gp['entry']).min()).days/365+1e-9))) if r.std()>0 and len(r)>3 else np.nan
        return out
    a0, a9 = annual_sharpe(b0), annual_sharpe(b9)
    yrs = sorted(set(a0) | set(a9)); w = .4
    ax[0, 1].bar([y-w/2 for y in yrs], [a0.get(y, np.nan) for y in yrs], w, label='baseline', color='#888')
    ax[0, 1].bar([y+w/2 for y in yrs], [a9.get(y, np.nan) for y in yrs], w, label='engineered B9', color='#d62728')
    ax[0, 1].axhline(0, color='k', lw=.8); ax[0, 1].axhline(0.5, color='g', ls='--', lw=.8, label='Sh=0.5')
    ax[0, 1].set_title("B) Annual Sharpe (decay)"); ax[0, 1].legend(fontsize=8); ax[0, 1].grid(alpha=.3)
    # 3) edge by vol regime
    buckets = [("low", 0, .33), ("mid", .33, .66), ("high", .66, 1.01)]
    bl = run_variant(INDICES)
    eLs, eSs = [], []
    for _, lo, hi in buckets:
        sub = bl[(bl['volp'] >= lo) & (bl['volp'] < hi)]; r = sub['netR'].values; d = sub['dir'].values
        eLs.append(r[d == 1].mean() if (d == 1).any() else 0); eSs.append(r[d == -1].mean() if (d == -1).any() else 0)
    xb = np.arange(3)
    ax[1, 0].bar(xb-.2, eLs, .4, label='long', color='#2ca02c'); ax[1, 0].bar(xb+.2, eSs, .4, label='short', color='#d62728')
    ax[1, 0].set_xticks(xb); ax[1, 0].set_xticklabels([b[0] for b in buckets]); ax[1, 0].axhline(0, color='k', lw=.8)
    ax[1, 0].set_title("C) Edge (expR) by vol regime — indices"); ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=.3)
    # 4) expR by class x side (baseline all)
    cls_order = ['indices', 'forex', 'commodities', 'crypto']; eL, eS = [], []
    for cl in cls_order:
        sub = b0[b0['cls'] == cl]; r = sub['netR'].values; d = sub['dir'].values
        eL.append(r[d == 1].mean() if (d == 1).any() else 0); eS.append(r[d == -1].mean() if (d == -1).any() else 0)
    xc = np.arange(4)
    ax[1, 1].bar(xc-.2, eL, .4, label='long', color='#2ca02c'); ax[1, 1].bar(xc+.2, eS, .4, label='short', color='#d62728')
    ax[1, 1].set_xticks(xc); ax[1, 1].set_xticklabels(cls_order, fontsize=8); ax[1, 1].axhline(0, color='k', lw=.8)
    ax[1, 1].set_title("D) Edge (expR) by class x side"); ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=.3)
    fig.suptitle("S012 Bollinger %b mean-reversion — deep dive (FTMO universe, net of costs)", fontweight='bold')
    fig.tight_layout(); fig.savefig("s012_deepdive.png", dpi=120)
    print("\nSaved: s012_deepdive.png, s012_deepdive_battery.csv")
