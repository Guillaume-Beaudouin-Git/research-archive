"""
Strategy 50/109 — Normalized Linear Regression Slope (Entry). Source rating C. (Kaufman)
https://oxfordstrat.com/trading-strategies/normalized-linear-regression/
NLRS = LRS(Look_Back) / ATR(20). Enter long when NLRS>Growth_Index ; exit when NLRS<0 (+ ATR*6). Short symmetric.
-> trend-following (slope/vol) -> expect Gate 2 long-beta. Reuses trend_lab + ftmo_lab + beta_bench.
Point Look_Back=100, Growth_Index=0.025.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

LB_REP, GR_REP = 100, 0.025
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def nlrs_regime(df, lb, growth):
    c = df['close'].values; s = T.lrs(c, lb); atr = lab.atr(df, 20).values
    with np.errstate(invalid='ignore', divide='ignore'):
        nl = s / atr
    n = len(c); reg = np.zeros(n, np.int8); st = 0
    for i in range(n):
        if not np.isfinite(nl[i]):
            reg[i] = st; continue
        if st == 0:
            st = 1 if nl[i] > growth else (-1 if nl[i] < -growth else 0)
        elif st == 1:
            st = 0 if nl[i] < 0 else 1
        else:
            st = 0 if nl[i] > 0 else -1
        reg[i] = st
    return reg

def sig(lb, growth):
    def f(df):
        reg = nlrs_regime(df, lb, growth)
        return pd.Series(reg == 1, index=df.index), pd.Series(reg == -1, index=df.index)
    return f

def run_point(lb, growth, fill='stop'):
    return T.run_state(uni, costs, sig(lb, growth), fill=fill)

if __name__ == "__main__":
    pool = run_point(LB_REP, GR_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, GR_REP, fill='next_open'))
    print(f"=== S050 Normalized LR Slope (Look_Back={LB_REP} Growth={GR_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    LBs = [40, 100, 160]; GRs = [0.0, 0.025, 0.05]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, lb in enumerate(LBs):
        for b_, gr in enumerate(GRs):
            m = lab.trade_metrics(run_point(lb, gr)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"G{x}" for x in GRs]).to_csv("s050_sensitivity_expectancy.csv")
    print("grid expR (LB x Growth):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"G{x}" for x in GRs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, GR_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s050_gates.csv", index=False)
