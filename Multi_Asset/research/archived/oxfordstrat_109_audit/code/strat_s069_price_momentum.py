"""
Strategy 69/109 — Price Momentum Model (Benchmark). Perry Kaufman. Rating C.
https://oxfordstrat.com/trading-strategies/price-momentum-model/

Pure dual price-momentum TREND benchmark:
  M1[i] = Close[i] - Close[i-M1_LB+1]  (fast)   M2[i] = Close[i] - Close[i-M2_LB+1] (slow)
  Long  if M1[i-1]>0 AND M2[i-1]>0 ; Short if both <0. Entry @open.
  Exit: momentum exit (M1 flips) @open + ATR stop. Default M2_LB>80 (we use 100), M1=0.5*M2.
Archetype = trend/momentum = directional beta. The decisive test is two-sided + beta-matched.
Reuses trend_lab (entry@open state machine, exit on state flip). 42-futures benchmark, rating C.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import trend_lab as tl

M2_REP, IDX_REP = 100, 0.5
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def sig(m2_lb, m1_idx):
    m1_lb = max(2, round(m1_idx * m2_lb))
    def f(df):
        c = df['close']
        m1 = c - c.shift(m1_lb - 1); m2 = c - c.shift(m2_lb - 1)
        wl = (m1 > 0) & (m2 > 0); ws = (m1 < 0) & (m2 < 0)
        return wl.fillna(False), ws.fillna(False)
    return f


def run_pt(m2_lb=M2_REP, m1_idx=IDX_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(m2_lb, m1_idx), fill=fill)


if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S069 Price Momentum (dual momentum trend, M2={M2_REP} M1={int(IDX_REP*M2_REP)}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    M2s = [40, 80, 120, 200]; IDXs = [0.25, 0.5, 1.0]
    sg = np.full((len(M2s), len(IDXs)), np.nan)
    for a, m2 in enumerate(M2s):
        for b_, ix in enumerate(IDXs):
            sg[a, b_] = lab.trade_metrics(run_pt(m2, ix))['sharpe']
    pd.DataFrame(sg, index=[f"M{x}" for x in M2s], columns=[f"i{x}" for x in IDXs]).to_csv("s069_sensitivity_expectancy.csv")
    print("grid Sharpe (M2_LB x M1_idx):\n" + pd.DataFrame(sg, index=[f"M{x}" for x in M2s], columns=[f"i{x}" for x in IDXs]).round(2).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s069_gates.csv", index=False)
