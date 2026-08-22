"""
Registry #7 / file S011 — ADX Filter on Donchian breakout (Test 2: Filter Threshold & Look Back).
Source: https://oxfordstrat.com/trading-strategies/average-directional-index/  (rating D)
SAME strategy as #6 (S006) — Donchian breakout + ADX filter — but Entry_Channel is FIXED at 50
(Exit_Channel=25) and the swept axes are ADX_Look_Back x ADX_Threshold (vs #6 swept Entry_Channel
x ADX_Threshold with ADX_Look_Back fixed=14). Site summary again: "ADX does not add value".

ARCHETYPE: STOP-entry (Donchian breakout) held long -> fill artefact diluted (cf. S006 passed Gate 1).
Reuses ftmo_lab v2-gates UNCHANGED. Sibling of S006; concise report.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

ENTRY_CHANNEL, EXIT_CHANNEL, ATR_LEN, ATR_STOP = 50, 25, 20, 6.0
ALB_REP, ADX_REP = 14, 0                          # base case: Donchian-50, ADX off (site: ADX adds nothing)

def compute_adx(df, period):
    h, l, c = df['high'], df['low'], df['close']
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def channels(df):
    u1 = df['high'].rolling(ENTRY_CHANNEL).max().shift(1); l1 = df['low'].rolling(ENTRY_CHANNEL).min().shift(1)
    u2 = df['high'].rolling(EXIT_CHANNEL).max().shift(1);  l2 = df['low'].rolling(EXIT_CHANNEL).min().shift(1)
    return u1.values, l1.values, u2.values, l2.values

def simulate_donchian(df, ch, adx_prev, *, adx_threshold, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; u1, l1, u2, l2 = ch; ax = adx_prev
    n = len(df); idx = df.index; trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(ax[i]) and ax[i] >= adx_threshold and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        long_brk = np.isfinite(u1[i]) and h[i] >= u1[i]
        short_brk = allow_short and np.isfinite(l1[i]) and l[i] <= l1[i]
        if not (long_brk or short_brk): i += 1; continue
        d = 1 if long_brk else -1; risk0 = A[i] * atr_stop
        if fill == 'stop':        entry = max(o[i], u1[i]) if d == 1 else min(o[i], l1[i]); eb = i
        elif fill == 'close':     entry = c[i]; eb = i
        elif fill == 'next_open':
            if i + 1 > n - 1: i += 1; continue
            entry = o[i + 1]; eb = i + 1
        else: raise ValueError(fill)
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0; atr_lvl = entry - d * risk0
        exit_p = exit_j = reason = None; j = eb + 1
        while j <= n - 1:
            chl = l2[j] if d == 1 else u2[j]
            ex = (max(atr_lvl, chl) if np.isfinite(chl) else atr_lvl) if d == 1 else \
                 (min(atr_lvl, chl) if np.isfinite(chl) else atr_lvl)
            if d == 1 and l[j] <= ex:  exit_p, reason, exit_j = ex, 'chan/atr', j; break
            if d == -1 and h[j] >= ex: exit_p, reason, exit_j = ex, 'chan/atr', j; break
            j += 1
        if exit_p is None: exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=d,
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_CH = {t: channels(df) for t, df in uni.items()}                 # Entry_Channel fixed -> once
_ADX = {}
def _adx(t, df, alb):
    if (t, alb) not in _ADX: _ADX[(t, alb)] = compute_adx(df, alb).shift(1).values
    return _ADX[(t, alb)]

def run_point(adx_look_back, adx_threshold, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_donchian(df, _CH[t], _adx(t, df, adx_look_back),
                               adx_threshold=adx_threshold, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(ALB_REP, ADX_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    pd.DataFrame(per).T.assign(cls=lambda x: [lab.CLASS.get(i) for i in x.index]).sort_values('expR', ascending=False).to_csv("s011_per_instrument.csv")
    print(f"=== S011 (registry #7) ADX/Donchian-50 LookBack  ADX_LB={ALB_REP} ADX_Thr={ADX_REP} ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} CAGR={pm['cagr']*100:+.1f}% MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns})")
    ALBs = [10, 14, 20, 30, 60]; ADXs = [0, 10, 20, 30]
    grid = np.full((len(ALBs), len(ADXs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, alb in enumerate(ALBs):
        for b, ad in enumerate(ADXs):
            m = lab.trade_metrics(run_point(alb, ad)); grid[a, b] = m['expR']; sg[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in ALBs], columns=[f"A{x}" for x in ADXs]).to_csv("s011_sensitivity_expectancy.csv")
    print("grid expR (ADX_LB x ADX_Threshold):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in ALBs], columns=[f"A{x}" for x in ADXs]).round(4).to_string())
    print(f"ADX value-add: col ADX0 mean {np.nanmean(grid[:,0]):+.4f} vs best ADX>0 mean {np.nanmean(np.nanmax(grid[:,1:],axis=1)):+.4f}")
    res = lab.run_gates(lambda fill='stop': run_point(ALB_REP, ADX_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"opt {x.get('opt_sharpe',0):+.2f}->real {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k=='dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s011_gates.csv", index=False)
    bp = run_point(ALBs[int(np.nanargmax(grid)//grid.shape[1])], ADXs[int(np.nanargmax(grid)%grid.shape[1])])
    el2, es2, nl2, ns2 = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable] expR={mb['expR']:+.4f} Sharpe={mb['sharpe']:+.2f} | two-sided long {el2:+.4f}/short {es2:+.4f}")
