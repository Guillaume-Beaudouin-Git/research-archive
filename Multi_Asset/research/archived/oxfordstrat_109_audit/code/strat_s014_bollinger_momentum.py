"""
Strategy 14/109 — Bollinger Bands Momentum Model (Setup). Source rating C. (J. Bollinger)
https://oxfordstrat.com/trading-strategies/bollinger-band/  -> TREND-FOLLOWING (band breakout).
Setup Long: Close[i-1] > Upper_Band[i-1]; Short: Close[i-1] < Lower_Band[i-1]. Entry market-on-open.
Exit: Trend Exit (Long: sell at open if Close<MA; Short: buy at open if Close>MA) OR ATR(20)*6 stop.
Sweep MA_Length x St_Dev. Site: MA_Length>60 + St_Dev>0 preferred.

Trend-following clone of the S003-S011 cluster -> HERITAGE mode (short report if Gate 2 beta-long).
Reuses ftmo_lab v2-gates UNCHANGED. Fills: 'stop'=open[s+1] native, 'next_open'=open[s+2], 'close'=close[s+1].
"""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
ML_REP, SD_REP = 100, 2.0                              # site-recommended region (slow, vol envelope)

def bands(df, ma_len, st_dev):
    c = df['close']; ma = c.rolling(ma_len).mean(); sd = c.rolling(ma_len).std(ddof=1)
    return (ma + st_dev * sd).values, (ma - st_dev * sd).values, ma.values

def simulate_bandmom(df, upper, lower, ma, *, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                     cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; n = len(df); idx = df.index
    trades = []; s = 1
    while s < n - 1:
        if not (np.isfinite(A[s]) and A[s] > 0 and np.isfinite(upper[s]) and np.isfinite(ma[s])):
            s += 1; continue
        d = 1 if c[s] > upper[s] else (-1 if (c[s] < lower[s] and allow_short) else 0)
        if d == 0: s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = o[eb] if eb <= n-1 else np.nan
        elif fill == 'close':     eb = s + 1; entry = c[eb] if eb <= n-1 else np.nan
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0
        exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            # MA-cross trend exit: condition at close[j] -> exit at next open
            if np.isfinite(ma[j]) and ((d == 1 and c[j] < ma[j]) or (d == -1 and c[j] > ma[j])):
                ej = j + 1
                if ej <= n - 1: exit_p, reason, exit_j = o[ej], 'macross', ej
                else: exit_p, reason, exit_j = c[j], 'macross', j
                break
        if exit_p is None:
            exit_j = n - 1; exit_p, reason = c[n-1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_B = {}
def _bands(t, df, ml, sd):
    if (t, ml, sd) not in _B: _B[(t, ml, sd)] = bands(df, ml, sd)
    return _B[(t, ml, sd)]

def run_point(ma_len, st_dev, fill='stop'):
    frames = []
    for t, df in uni.items():
        up, lo, ma = _bands(t, df, ma_len, st_dev)
        tr = simulate_bandmom(df, up, lo, ma, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(ML_REP, SD_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    pd.DataFrame(per).T.assign(cls=lambda x:[lab.CLASS.get(i) for i in x.index]).sort_values('expR',ascending=False).to_csv("s014_per_instrument.csv")
    print(f"=== S014 Bollinger Momentum  MA_Length={ML_REP} St_Dev={SD_REP} (trend-following) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns})")
    MLs = [20, 50, 100, 150, 200]; SDs = [0.5, 1.0, 2.0, 3.0]
    grid = np.full((len(MLs), len(SDs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ml in enumerate(MLs):
        for bb, sd in enumerate(SDs):
            m = lab.trade_metrics(run_point(ml, sd)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"SD{x}" for x in SDs]).to_csv("s014_sensitivity_expectancy.csv")
    print("grid expR (MA_Length x St_Dev):\n" + pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"SD{x}" for x in SDs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(ML_REP, SD_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k=='dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s014_gates.csv", index=False)
    bp = run_point(MLs[int(np.nanargmax(grid)//grid.shape[1])], SDs[int(np.nanargmax(grid)%grid.shape[1])])
    el2, es2, _, _ = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable] expR {mb['expR']:+.4f} Sharpe {mb['sharpe']:+.2f} | long {el2:+.4f}/short {es2:+.4f}")
