"""S096 — Wide Range N-Day Pattern (Crabel). Rating D.
https://oxfordstrat.com/trading-strategies/wide-range-pattern/
Reverse of Narrow Range: setup = widest N-day range over Look_Back, then Crabel ORB-stop entry
(Open +/- Stretch). Same ORB-stop fill-artefact family as NR(#55)/NR7(#56)/GSV(#37)/ORB(#61).
Source's OWN benchmark: NET LOSING (Sharpe -1.45, MaxDD -88%), worse than Narrow Range.
Reuses ftmo_lab.simulate_bracket + orb_filtered.crabel_stretch. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb
from orb_filtered import crabel_stretch
N_REP, LB_REP, TM, AIX = 2, 20, 10, 3.0
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_ST = {t: crabel_stretch(df, 10, 2.0) for t, df in uni.items()}
def wide_setup(df, n, lb):
    rng = df['high'].rolling(n).max() - df['low'].rolling(n).min()
    return (rng >= rng.rolling(lb).max())          # widest N-day range over Look_Back
def run_point(n=N_REP, lb=LB_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = lab.simulate_bracket(df, wide_setup(df, n, lb), _ST[t], target_index=AIX, time_index=TM,
                                  atr_len=20, atr_stop=6.0, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))
if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S096 Wide Range N-Day (N={N_REP} LookBack={LB_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    Ns = [2, 5, 10]; LBs = [20, 35, 50]; sg = np.full((3, 3), np.nan)
    for a, n in enumerate(Ns):
        for b_, lb in enumerate(LBs): sg[a, b_] = lab.trade_metrics(run_point(n, lb))['sharpe']
    pd.DataFrame(sg, index=[f"N{x}" for x in Ns], columns=[f"L{x}" for x in LBs]).to_csv("s096_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s096_gates.csv", index=False)
