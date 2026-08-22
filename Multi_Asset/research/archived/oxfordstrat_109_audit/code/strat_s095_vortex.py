"""S095 — Vortex Indicator (Entry). Rating C.
https://oxfordstrat.com/trading-strategies/vortex-indicator-1/
VI+ = sum|High-Low_prev|/sum TR ; VI- = sum|Low-High_prev|/sum TR. Long when VI+>VI-,
short when VI-<VI+ -> trend/momentum = beta. Entry@open, exit on flip + ATR. Reuses trend_lab.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
N_REP = 14
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(n):
    def f(df):
        h, l, c = df['high'], df['low'], df['close']
        tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
        vmp = (h - l.shift(1)).abs(); vmm = (l - h.shift(1)).abs()
        vip = vmp.rolling(n).sum() / tr.rolling(n).sum()
        vim = vmm.rolling(n).sum() / tr.rolling(n).sum()
        return (vip > vim).fillna(False), (vip < vim).fillna(False)
    return f
def run_pt(n=N_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(n), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S095 Vortex Indicator (N={N_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    Ns = [7, 14, 28, 50]; sg = np.full((1, 4), np.nan)
    for b_, nn in enumerate(Ns): sg[0, b_] = lab.trade_metrics(run_pt(nn))['sharpe']
    pd.DataFrame(sg, columns=[f"N{x}" for x in Ns]).to_csv("s095_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_pt(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s095_gates.csv", index=False)
