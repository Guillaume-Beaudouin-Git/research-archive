"""
Strategy 73/109 — RSI(2) Model, NEW EXITS (Connors). Rating C.
https://oxfordstrat.com/trading-strategies/relative-strength-index-2/

Same entry as #72 (Close>SMA200 & RSI2<Entry_Threshold, buy next open) but the EXIT
is RSI-based instead of MA-based: sell at OPEN if RSI(2)[i-1] > RSI_Exit_Threshold
(default 95) ; + ATR stop (6*ATR). Sweep Entry_Threshold x Exit_Threshold.
Fiche conclusion: "the RSI exit is NOT significantly better or worse than the MA exit
(base case #72)." -> same archetype, same verdict expected (long-only equity dip-buy = beta).
Reuses s072.rsi + beta_bench. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
from strat_s072_rsi2 import rsi, INDICES, costs, uni_all, SETUP_LB, ATR_LEN, ATR_STOP

ENTRY_REP, EXITTHR_REP = 10, 75      # preferred (Case#3: entry10/exit75 -> best in fiche)


def simulate(df, entry_thr, exit_thr, *, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    cs = pd.Series(c, index=df.index)
    maS = cs.rolling(SETUP_LB).mean().values
    R = rsi(cs, 2).values
    n = len(df); idx = df.index; trades = []; i = SETUP_LB + 1
    while i < n - 1:
        if not (np.isfinite(maS[i]) and c[i] > maS[i] and R[i] < entry_thr and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        eb = i + 1 if fill == 'stop' else i + 2
        if eb > n - 1: break
        entry = o[eb]; risk0 = A[i]*ATR_STOP; cost_R = (cost_bps/1e4)*abs(entry)/risk0
        stop = entry - risk0; exit_p = exit_j = None
        for j in range(eb, n):
            if l[j] <= stop: exit_p, exit_j = stop, j; break
            if R[j-1] > exit_thr: exit_p, exit_j = o[j], j; break       # RSI exit -> sell open[j]
            if j == n-1: exit_p, exit_j = c[j], j; break
        trades.append(lab._trade(idx[eb], idx[exit_j], 'x', 1, (exit_p-entry)/risk0 - cost_R, exit_j-eb))
        i = exit_j + 1
    return pd.DataFrame(trades)


def run_point(entry_thr=ENTRY_REP, exit_thr=EXITTHR_REP, fill='stop'):
    frames = []
    for t in INDICES:
        tr = simulate(uni_all[t], entry_thr, exit_thr, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S073 RSI(2) NEW EXITS (entry_thr={ENTRY_REP} exit_thr={EXITTHR_REP}, indices, LONG-only) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: open[+1] {pm['sharpe']:+.2f} -> open[+2] {m_no['sharpe']:+.2f}")
    bb.beta_line(pool)
    ETs = [5, 10, 15]; XTs = [75, 85, 95]
    sg = np.full((3, 3), np.nan)
    for a, et in enumerate(ETs):
        for b_, xt in enumerate(XTs): sg[a, b_] = lab.trade_metrics(run_point(et, xt))['sharpe']
    pd.DataFrame(sg, index=[f"e{x}" for x in ETs], columns=[f"x{x}" for x in XTs]).to_csv("s073_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s073_gates.csv", index=False)
