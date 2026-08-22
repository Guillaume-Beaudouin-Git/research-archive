"""
Strategy 58/109 — Oops Pattern (Exits). Source rating D. (Larry Williams)
https://oxfordstrat.com/trading-strategies/oops-pattern/
Gap-failure FADE (two-sided contrarian):
  Long : Open[i] < Low[i-1] (gap down) ; buy stop at Low[i-1] (reclaim the prior low) -> fade up.
  Short: Open[i] > High[i-1] (gap up)  ; sell stop at High[i-1] -> fade down.
  Exit : Time_Index + ATR exit (ATR*ATR_Index, the binding stop) + ATR*6 catastrophe.
Reclaim-stop entry -> Gate 1 fill check. Shared sim (#58 both / #59 short / #60 long).
Reuses ftmo_lab v2-gates + beta_bench. Point ATR_Index=3, Time=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
AIX_REP, TM_REP = 3.0, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def simulate_oops(df, atr_index, time_index, *, atr_stop=ATR_STOP, cost_bps=2.0, side='both', fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; n = len(df); idx = df.index; trades = []; i = 2
    while i < n - 1:
        d = 0
        if side in ('both', 'long') and o[i] < l[i - 1] and h[i] >= l[i - 1]:
            d = 1; lvl = l[i - 1]
        elif side in ('both', 'short') and o[i] > h[i - 1] and l[i] <= h[i - 1]:
            d = -1; lvl = h[i - 1]
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        if fill == 'stop':      entry = (max(o[i], lvl) if d == 1 else min(o[i], lvl)); eb = i
        elif fill == 'close':   entry = c[i]; eb = i
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        exit_stop = entry - d * A[i] * atr_index; last = min(eb + time_index, n - 1)
        exit_p = exit_j = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= exit_stop:  exit_p, exit_j = exit_stop, j; break
            if d == -1 and h[j] >= exit_stop: exit_p, exit_j = exit_stop, j; break
            if j == last: exit_p, exit_j = c[j], j; break
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=d * (exit_p - entry) / risk0 - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

def run_point(atr_index, time_index, fill='stop', side='both'):
    frames = []
    for t, df in uni.items():
        tr = simulate_oops(df, atr_index, time_index, cost_bps=costs[t], side=side, fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(AIX_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(AIX_REP, TM_REP, fill='next_open'))
    print(f"=== S058 Oops Pattern (gap fade, ATR_Index={AIX_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    AIs = [1.5, 3.0, 5.0]; TMs = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, ai in enumerate(AIs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ai, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"A{x}" for x in AIs], columns=[f"T{x}" for x in TMs]).to_csv("s058_sensitivity_expectancy.csv")
    print("grid expR (ATR_Index x Time):\n" + pd.DataFrame(grid, index=[f"A{x}" for x in AIs], columns=[f"T{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(AIX_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s058_gates.csv", index=False)
