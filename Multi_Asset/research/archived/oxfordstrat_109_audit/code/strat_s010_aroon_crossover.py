"""
Strategy 10/109 — Aroon Indicator Crossover (Setup & Exit). Source rating D. (Chande)
https://oxfordstrat.com/trading-strategies/aroon-indicator-crossover/

Cluster clone (trend-following). Setup = AroonUp crosses ABOVE AroonDown (long) / below (short);
entry MARKET-ON-OPEN at i; exits Time + ATR. Sweep Aroon_Index x Time_Index.
Same machinery as S007-S009; only the signal is a crossover instead of a level.
Reuses ftmo_lab v2-gates UNCHANGED. Processed in HERITAGE mode (short report if cluster death).
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
AI_REP, TM_REP = 25, 20

def aroon_updown(df, aroon_index):
    W = aroon_index + 1; hv, lv = df['high'].values, df['low'].values; n = len(hv)
    up = np.full(n, np.nan); dn = np.full(n, np.nan)
    if n >= W:
        swh = np.lib.stride_tricks.sliding_window_view(hv, W)
        swl = np.lib.stride_tricks.sliding_window_view(lv, W)
        up[W-1:] = 100.0 * (aroon_index - swh[:, ::-1].argmax(axis=1)) / aroon_index
        dn[W-1:] = 100.0 * (aroon_index - swl[:, ::-1].argmin(axis=1)) / aroon_index
    return up, dn

def cross_dir(up, dn):
    n = len(up); fin = np.isfinite(up) & np.isfinite(dn)
    valid = fin & np.r_[False, fin[:-1]]
    gt = up > dn                                    # AroonUp above AroonDown (nan -> False)
    prev = np.r_[False, gt[:-1]]
    cu = valid & gt & ~prev                         # cross up  -> long
    cd = valid & ~gt & prev                         # cross down -> short
    return np.where(cu, 1, np.where(cd, -1, 0))

def simulate_aroon(df, dir_sig, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                   cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig; n = len(df); idx = df.index
    trades = []; s = 1
    while s < n - 1:
        d = ds[s]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[s]) or A[s] <= 0:
            s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = o[eb] if eb <= n-1 else np.nan
        elif fill == 'close':     eb = s + 1; entry = c[eb] if eb <= n-1 else np.nan
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; last = min(eb + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last:                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_AR = {}
def _updown(t, df, ai):
    if (t, ai) not in _AR: _AR[(t, ai)] = aroon_updown(df, ai)
    return _AR[(t, ai)]

def run_point(aroon_index, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        up, dn = _updown(t, df, aroon_index)
        tr = simulate_aroon(df, cross_dir(up, dn), time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(AI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    pos_long = (pool[pool.dir==1]['instr'].nunique() if len(pool) else 0)
    print(f"=== S010 Aroon Crossover  Aroon_Index={AI_REP} Time={TM_REP} ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns})")
    AIs = [10, 25, 50, 100, 200]; TMs = [1, 10, 20, 40]
    grid = np.full((len(AIs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ai in enumerate(AIs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ai, tm)); grid[a, b] = m['expR']; sg[a, b] = m['sharpe']
    print("grid expR:\n" + pd.DataFrame(grid, index=[f"AI{x}" for x in AIs], columns=[f"T{x}" for x in TMs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(AI_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s010_gates.csv", index=False)
