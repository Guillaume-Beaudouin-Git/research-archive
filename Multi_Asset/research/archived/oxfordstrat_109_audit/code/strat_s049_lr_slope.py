"""
Strategy 49/109 — Linear Regression Slope (Filter & Entry). Source rating C. (Kaufman)
https://oxfordstrat.com/trading-strategies/linear-regression/
TREND-FOLLOWING dual-slope: LRS_1 = slope over Look_Back (filter), LRS_2 = slope over Look_Back*Index (signal).
  Long when LRS_1>0 & LRS_2>0 ; Short when both <0. Entry @open ; exit when condition off or ATR*6.
  -> expect Gate 2 long-beta (two positive slopes = uptrend). Reuses trend_lab + ftmo_lab + beta_bench.
Point Look_Back=100, Index=0.5 (LRS_2 over 50).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

LB_REP, IX_REP = 100, 0.5
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def sig(look_back, idx):
    lb2 = max(5, int(round(look_back * idx)))
    def f(df):
        s1 = T.lrs(df['close'].values, look_back); s2 = T.lrs(df['close'].values, lb2)
        wl = pd.Series((s1 > 0) & (s2 > 0), index=df.index)
        ws = pd.Series((s1 < 0) & (s2 < 0), index=df.index)
        return wl, ws
    return f

def run_point(look_back, idx, fill='stop'):
    return T.run_state(uni, costs, sig(look_back, idx), fill=fill)

if __name__ == "__main__":
    pool = run_point(LB_REP, IX_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, IX_REP, fill='next_open'))
    print(f"=== S049 LR Slope (Look_Back={LB_REP} Index={IX_REP} -> LRS2 over {max(5,round(LB_REP*IX_REP))}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    LBs = [40, 100, 160]; IXs = [0.3, 0.5, 0.8]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, lb in enumerate(LBs):
        for b_, ix in enumerate(IXs):
            m = lab.trade_metrics(run_point(lb, ix)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"IX{x}" for x in IXs]).to_csv("s049_sensitivity_expectancy.csv")
    print("grid expR (LB x Index):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"IX{x}" for x in IXs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, IX_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s049_gates.csv", index=False)
