"""S091 — Volatility Squeeze (Bollinger). Rating C.
https://oxfordstrat.com/trading-strategies/volatility-squeeze/
Source conclusion: the squeeze filter does NOT improve the base Bollinger trend model
(Squeeze_LookBack=0/Memory=1000 => all trades = base). So we test the BASE Bollinger-band
breakout TREND: long regime from Close>UpperBand until Close<MA ; short mirror ; entry@open
+ ATR stop. Archetype = trend/beta (cf #14 Bollinger Momentum). Reuses trend_lab. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
MA_REP, SD_REP = 80, 2.0
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(ma_len, sd):
    def f(df):
        c = df['close']; ma = c.rolling(ma_len).mean(); s = c.rolling(ma_len).std()
        up = (ma + sd*s).values; lo = (ma - sd*s).values; m = ma.values; cl = c.values
        n = len(c); wl = np.zeros(n, bool); ws = np.zeros(n, bool); st = 0
        for i in range(n):
            if not np.isfinite(m[i]): continue
            if st == 1 and cl[i] < m[i]: st = 0
            elif st == -1 and cl[i] > m[i]: st = 0
            if st == 0:
                if cl[i] > up[i]: st = 1
                elif cl[i] < lo[i]: st = -1
            wl[i] = st == 1; ws[i] = st == -1
        return pd.Series(wl, index=c.index), pd.Series(ws, index=c.index)
    return f
def run_pt(ma_len=MA_REP, sd=SD_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(ma_len, sd), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S091 Volatility Squeeze / Bollinger trend (MA={MA_REP} SD={SD_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    MAs = [40, 80, 160]; SDs = [1.5, 2.0, 2.5]; sg = np.full((3, 3), np.nan)
    for a, ml in enumerate(MAs):
        for b_, sd in enumerate(SDs): sg[a, b_] = lab.trade_metrics(run_pt(ml, sd))['sharpe']
    pd.DataFrame(sg, index=[f"MA{x}" for x in MAs], columns=[f"sd{x}" for x in SDs]).to_csv("s091_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s091_gates.csv", index=False)
