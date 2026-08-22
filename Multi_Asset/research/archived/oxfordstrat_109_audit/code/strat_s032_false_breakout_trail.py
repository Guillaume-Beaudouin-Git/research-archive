"""
Strategy 32/109 — False Breakout (Setup & Exit 2). Source rating C.
https://oxfordstrat.com/trading-strategies/false-breakout-2/
SAME fade setup+entry as #31, but exit = Quick + TRAILING Channel_#2 + ATR*6 (no time exit).
Sweep Channel_#1 x Channel_#2. HERITAGE of #31: the entry (stop) fill-artefact and the broken
short side can't be fixed by a different exit. Reuses ftmo_lab + beta_bench; same setup detection.
"""
import bisect, numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
C1_REP, C2_REP = 20, 10
MAXWAIT = 5

def simulate_fbo_trail(df, c1, c2, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    prior_min = pd.Series(l, index=df.index).rolling(c1).min().shift(1).values
    prior_max = pd.Series(h, index=df.index).rolling(c1).max().shift(1).values
    lowexit = pd.Series(l, index=df.index).rolling(c2).min().shift(1).values   # LowerChannelExit[i-1]
    upexit = pd.Series(h, index=df.index).rolling(c2).max().shift(1).values    # UpperChannelExit[i-1]
    new_low = l <= prior_min; new_high = h >= prior_max
    nl_bars = list(np.where(new_low)[0]); nh_bars = list(np.where(new_high)[0])
    n = len(df); idx = df.index; trades = []; i = c1 + 1
    while i < n - 1:
        sig = 0
        if new_low[i] and np.isfinite(prior_min[i]):
            j = bisect.bisect_right(nl_bars, i - 5) - 1
            if j >= 0 and c[i] <= l[nl_bars[j]]: sig = 1
        if sig == 0 and allow_short and new_high[i] and np.isfinite(prior_max[i]):
            j = bisect.bisect_right(nh_bars, i - 5) - 1
            if j >= 0 and c[i] >= h[nh_bars[j]]: sig = -1
        if sig == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        k = i; lvl = h[k] if sig == 1 else l[k]; entry = None; eb = None
        for j in range(k + 1, min(k + MAXWAIT, n)):
            trig = (h[j] >= lvl) if sig == 1 else (l[j] <= lvl)
            if trig:
                if fill == 'stop': entry = (max(o[j], lvl) if sig == 1 else min(o[j], lvl)); eb = j
                elif fill == 'close': entry = c[j]; eb = j
                elif fill == 'next_open': eb = j + 1; entry = o[eb] if eb <= n - 1 else None
                break
        if entry is None or eb is None or eb > n - 1 or not np.isfinite(entry):
            i = k + 1; continue
        d = sig; risk0 = A[k] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        washout = np.min(l[k:eb + 1]) if d == 1 else np.max(h[k:eb + 1])
        atr_lvl = entry - d * risk0
        exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1:
                stop_lvl = max(washout, atr_lvl, lowexit[j] if np.isfinite(lowexit[j]) else -np.inf)
                if l[j] <= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'trail', j; break
            else:
                stop_lvl = min(washout, atr_lvl, upexit[j] if np.isfinite(upexit[j]) else np.inf)
                if h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'trail', j; break
            if j == n - 1: exit_p, reason, exit_j = c[j], 'eod', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(c1, c2, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_fbo_trail(df, c1, c2, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(C1_REP, C2_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(C1_REP, C2_REP, fill='next_open'))
    print(f"=== S032 False Breakout fade + trailing channel exit (C1={C1_REP} C2={C2_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[j+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    C1s = [10, 20, 40]; C2s = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, c1 in enumerate(C1s):
        for b_, c2 in enumerate(C2s):
            m = lab.trade_metrics(run_point(c1, c2)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"C1={x}" for x in C1s], columns=[f"C2={x}" for x in C2s]).to_csv("s032_sensitivity_expectancy.csv")
    print("grid expR:\n" + pd.DataFrame(grid, index=[f"C1={x}" for x in C1s], columns=[f"C2={x}" for x in C2s]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(C1_REP, C2_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    e = pd.to_datetime(pool['entry']); rec = lab.trade_metrics(pool[e > pd.Timestamp('2018-12-31')])
    print(f"RECENT 2019+: expR {rec['expR']:+.4f} Sh {rec['sharpe']:+.2f}")
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s032_gates.csv", index=False)
