"""
Strategy 54/109 — Multiple Time Frames - Bruce Babcock (Entry). Source rating C.
https://oxfordstrat.com/trading-strategies/multiple-time-frames-1/
3-timeframe trend alignment: long if (Close>MA) AND (MA>MA[-MA_Length]) AND (Close>Close[-4*MA_Length]).
Short symmetric. Entry@open ; exit when alignment breaks / ATR*6. -> trend = beta long.
Reuses trend_lab + ftmo_lab + beta_bench. Point MA_Length=10 (Trend_Index=40).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

MA_REP = 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def sig(ma_len):
    ti = 4 * ma_len
    def f(df):
        c = df['close']; ma = c.rolling(ma_len).mean()
        wl = (c > ma) & (ma > ma.shift(ma_len)) & (c > c.shift(ti))
        ws = (c < ma) & (ma < ma.shift(ma_len)) & (c < c.shift(ti))
        return wl, ws
    return f

def run_point(ma_len, fill='stop'):
    return T.run_state(uni, costs, sig(ma_len), fill=fill)

if __name__ == "__main__":
    pool = run_point(MA_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(MA_REP, fill='next_open'))
    print(f"=== S054 Multiple Time Frames (MA_Length={MA_REP} Trend_Index={4*MA_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    MAs = [10, 20, 30, 50]; grid = np.full(len(MAs), np.nan); sg = np.full(len(MAs), np.nan)
    for a, ma in enumerate(MAs):
        m = lab.trade_metrics(run_point(ma)); grid[a] = m['expR']; sg[a] = m['sharpe']
    pd.DataFrame({'MA': MAs, 'expR': grid, 'sharpe': sg}).to_csv("s054_sensitivity_expectancy.csv", index=False)
    print("grid expR (MA_Length): " + " ".join(f"MA{m}:{grid[a]:+.4f}" for a, m in enumerate(MAs)))
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(MA_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s054_gates.csv", index=False)
