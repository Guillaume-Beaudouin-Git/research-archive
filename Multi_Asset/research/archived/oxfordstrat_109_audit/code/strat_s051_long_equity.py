"""
Strategy 51/109 — Long Equity Trading System (Filter & Exit). Source rating C. (Bruce Babcock)
https://oxfordstrat.com/trading-strategies/long-equity-trading-system/
LONG-ONLY time-series-momentum breakout on equity indices:
  Setup : Momentum[i-1] > Momentum[i-2] (Momentum=Close-Close[i-LookBack]; LB=11) -> momentum accelerating.
  Filter: Open[i] > (H[i-1]+L[i-1]+C[i-1])/3.
  Entry : buy stop at Close[i-1] + TrueRange[i-1]. Exit: Nth profitable Open (N=1) + ATR*6.
  -> long-only equity momentum = beta long by construction. Run on INDICES (the equity-futures equivalent).
Reuses ftmo_lab + beta_bench. Point Look_Back=11, N=1.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
LB_REP, N_REP = 11, 1
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
INDICES = [t for t in uni if lab.CLASS.get(t) == 'indices']

def simulate_le(df, look_back, N, *, atr_stop=ATR_STOP, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; n = len(df); idx = df.index
    mom = c - np.concatenate([np.full(look_back, np.nan), c[:-look_back]])
    trades = []; i = look_back + 3
    while i < n - 1:
        setup = (mom[i - 1] > mom[i - 2]) if (np.isfinite(mom[i - 1]) and np.isfinite(mom[i - 2])) else False
        filt = o[i] > (h[i - 1] + l[i - 1] + c[i - 1]) / 3.0
        if not (setup and filt) or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        tr_prev = max(c[i - 2], h[i - 1]) - min(c[i - 2], l[i - 1])
        lvl = c[i - 1] + tr_prev
        if h[i] < lvl:                                           # buy stop not hit today
            i += 1; continue
        if fill == 'stop':      entry = max(o[i], lvl); start = i
        elif fill == 'close':   entry = c[i]; start = i
        elif fill == 'next_open': start = i + 1; entry = o[start] if start <= n - 1 else np.nan
        else: raise ValueError(fill)
        if start > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - risk0; prof = 0; exit_p = exit_j = None
        for j in range(start + 1, n):
            if l[j] <= stop: exit_p, exit_j = stop, j; break
            if o[j] > entry:                                     # profitable open
                prof += 1
                if prof >= N: exit_p, exit_j = o[j], j; break
            if j == n - 1: exit_p, exit_j = c[j], j; break
        if exit_p is None: exit_p, exit_j = c[n - 1], n - 1
        trades.append(dict(entry=idx[start], exit=idx[exit_j], dir=1, netR=(exit_p - entry) / risk0 - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

def run_point(look_back, N, fill='stop', instruments=None):
    frames = []
    for t in (instruments or list(uni)):
        tr = simulate_le(uni[t], look_back, N, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    pool = run_point(LB_REP, N_REP, instruments=INDICES); pm = lab.trade_metrics(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, N_REP, fill='next_open', instruments=INDICES))
    print(f"=== S051 Long Equity (indices, Look_Back={LB_REP} N={N_REP}) — LONG-ONLY ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    bb.beta_line(pool)
    LBs = [11, 50, 100]; Ns = [1, 5, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, lb in enumerate(LBs):
        for b_, nn in enumerate(Ns):
            m = lab.trade_metrics(run_point(lb, nn, instruments=INDICES)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"N{x}" for x in Ns]).to_csv("s051_sensitivity_expectancy.csv")
    print("grid expR (Look_Back x N):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"N{x}" for x in Ns]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, N_REP, fill=fill, instruments=INDICES), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES (two-sided N/A: long-only by design):")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    e = pd.to_datetime(pool['entry']); rec = lab.trade_metrics(pool[e > pd.Timestamp('2018-12-31')])
    print(f"RECENT 2019+: expR {rec['expR']:+.4f} Sh {rec['sharpe']:+.2f}")
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s051_gates.csv", index=False)
