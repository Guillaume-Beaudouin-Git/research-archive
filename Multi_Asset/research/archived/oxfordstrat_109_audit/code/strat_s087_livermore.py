"""S087 — The Livermore System Part 1 (Filters). Jesse Livermore swing/pivot system. Rating C.
https://oxfordstrat.com/trading-strategies/livermore-system-1/
Source verdict: "an average momentum model". Pivot-penetration entry = swing breakout -> we
proxy it with a persistent Donchian swing-breakout regime (buy after new N-bar high = penetration
of recent supply pivots; sell after new N-bar low), entry @open, exit on regime flip + ATR stop.
Archetype = trend/momentum = beta -> beta_line decisive. Reuses trend_lab. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
N_REP = 40
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(n):
    def f(df):
        hh = df['high'].rolling(n).max(); ll = df['low'].rolling(n).min()
        up = df['close'] >= hh.shift(1); dn = df['close'] <= ll.shift(1)
        reg = pd.Series(np.where(up, 1, np.where(dn, -1, np.nan)), index=df.index).ffill().fillna(0)
        return (reg > 0), (reg < 0)
    return f
def run_pt(n=N_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(n), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S087 Livermore System (Donchian swing regime N={N_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    Ns = [20, 40, 60, 100]; sg = np.full((1, 4), np.nan)
    for b_, nn in enumerate(Ns): sg[0, b_] = lab.trade_metrics(run_pt(nn))['sharpe']
    pd.DataFrame(sg, columns=[f"N{x}" for x in Ns]).to_csv("s087_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s087_gates.csv", index=False)
