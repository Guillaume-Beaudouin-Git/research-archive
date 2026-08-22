"""
Strategy 48/109 — Keltner Channels 3-Phase Model (Setup). Source rating C. (Chester Keltner)
https://oxfordstrat.com/trading-strategies/keltner-channels-2/
= #47 but 3-PHASE (long/flat/short): enter long when Close>Buy_Line, EXIT TO NEUTRAL when Close<midline MA
(not a full reversal); short symmetric. Entry @open ; ATR*6 stop. -> trend breakout = beta long.
Reuses trend_lab + ftmo_lab + beta_bench. Point Look_Back=10, Range_Multiple=1.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

LB_REP, RM_REP = 10, 1.0
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def regime3(df, lb, rm):
    h, l, c = df['high'].values, df['low'].values, df['close'].values
    tp = (h + l + c) / 3.0; rng = h - l
    matp = pd.Series(tp).rolling(lb).mean().values; marng = pd.Series(rng).rolling(lb).mean().values
    buy = matp + marng * rm; sell = matp - marng * rm
    n = len(c); reg = np.zeros(n, np.int8); st = 0
    for i in range(n):
        if not np.isfinite(matp[i]):
            reg[i] = 0; continue
        if st == 0:
            st = 1 if c[i] > buy[i] else (-1 if c[i] < sell[i] else 0)
        elif st == 1:
            st = -1 if c[i] < sell[i] else (0 if c[i] < matp[i] else 1)
        else:
            st = 1 if c[i] > buy[i] else (0 if c[i] > matp[i] else -1)
        reg[i] = st
    return reg

def sig(lb, rm):
    def f(df):
        reg = regime3(df, lb, rm)
        return pd.Series(reg == 1, index=df.index), pd.Series(reg == -1, index=df.index)
    return f

def run_point(lb, rm, fill='stop'):
    return T.run_state(uni, costs, sig(lb, rm), fill=fill)

if __name__ == "__main__":
    pool = run_point(LB_REP, RM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, RM_REP, fill='next_open'))
    print(f"=== S048 Keltner 3-Phase (Look_Back={LB_REP} Range_Mult={RM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    LBs = [10, 50, 100]; RMs = [0.5, 1.0, 2.0]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, lb in enumerate(LBs):
        for b_, rm in enumerate(RMs):
            m = lab.trade_metrics(run_point(lb, rm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"RM{x}" for x in RMs]).to_csv("s048_sensitivity_expectancy.csv")
    print("grid expR (LB x RM):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"RM{x}" for x in RMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, RM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s048_gates.csv", index=False)
