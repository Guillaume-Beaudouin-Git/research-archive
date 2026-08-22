"""
Strategy 53/109 — MACD Part 2 (Entry). Source rating D. (Gerald Appel)
https://oxfordstrat.com/trading-strategies/macd-part-2/
= #52 + signal line: long when MACD>0 AND MACD>Signal(9-EMA of MACD); exit when MACD<Signal. -> trend/beta.
Fiche: "worse than Part 1." Reuses trend_lab + ftmo_lab + beta_bench. Point EMA1=40, EMA2=80, Signal=9.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

E1_REP, E2IDX_REP, SIG = 40, 2.0, 9
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def sig(e1, e2idx):
    e2 = max(e1 + 1, int(round(e1 * e2idx)))
    def f(df):
        c = df['close']; macd = c.ewm(span=e1, adjust=False).mean() - c.ewm(span=e2, adjust=False).mean()
        sg = macd.ewm(span=SIG, adjust=False).mean()
        return (macd > 0) & (macd > sg), (macd < 0) & (macd < sg)
    return f

def run_point(e1, e2idx, fill='stop'):
    return T.run_state(uni, costs, sig(e1, e2idx), fill=fill)

if __name__ == "__main__":
    pool = run_point(E1_REP, E2IDX_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(E1_REP, E2IDX_REP, fill='next_open'))
    print(f"=== S053 MACD Part 2 (EMA1={E1_REP} EMA2={max(E1_REP+1,round(E1_REP*E2IDX_REP))} Signal=9) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    E1s = [12, 40, 80]; IXs = [2.0, 3.0]; sg = np.full((3, 2), np.nan); grid = np.full((3, 2), np.nan)
    for a, e1 in enumerate(E1s):
        for b_, ix in enumerate(IXs):
            m = lab.trade_metrics(run_point(e1, ix)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"E{x}" for x in E1s], columns=[f"x{x}" for x in IXs]).to_csv("s053_sensitivity_expectancy.csv")
    print("grid expR:\n" + pd.DataFrame(grid, index=[f"E{x}" for x in E1s], columns=[f"x{x}" for x in IXs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(E1_REP, E2IDX_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s053_gates.csv", index=False)
