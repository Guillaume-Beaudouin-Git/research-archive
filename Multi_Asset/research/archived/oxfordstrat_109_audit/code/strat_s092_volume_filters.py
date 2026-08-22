"""S092 — Volume Filters Part 1 (Edwards/Magee + Donchian). Rating C.
https://oxfordstrat.com/trading-strategies/volume-filters-1/
Price breakout (Donchian channel) CONFIRMED by a volume breakout filter.
** Volume NOT available **: FTMO CFDs have no centralized volume; the daily store is OHLC+spread
(M1 tick_volume exists for only ~6 instruments). The source's OWN benchmark shows the volume
filter does NOT help (Sharpe 0.95 off -> 0.81 on). So we test the FTMO-tradable BASE = the
Donchian price-breakout (volume OFF), which is a trend/beta system (cf #20-22 DISCARD).
Reuses trend_lab (Donchian breakout regime). ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
LB_REP = 100
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(lb):
    def f(df):
        hh = df['high'].rolling(lb).max(); ll = df['low'].rolling(lb).min()
        up = df['high'] > hh.shift(1); dn = df['low'] < ll.shift(1)
        reg = pd.Series(np.where(up, 1, np.where(dn, -1, np.nan)), index=df.index).ffill().fillna(0)
        return (reg > 0), (reg < 0)
    return f
def run_pt(lb=LB_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(lb), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S092 Volume Filters P1 — BASE price breakout (volume OFF, non-repro), LB={LB_REP} ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    LBs = [50, 100, 150, 200]; sg = np.full((1, 4), np.nan)
    for b_, lb in enumerate(LBs): sg[0, b_] = lab.trade_metrics(run_pt(lb))['sharpe']
    pd.DataFrame(sg, columns=[f"LB{x}" for x in LBs]).to_csv("s092_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s092_gates.csv", index=False)
