"""S101 — Zero Lag Moving Average Filter (Ehlers/Way). Rating C.
https://oxfordstrat.com/trading-strategies/zero-lag-moving-average/
2-phase reversal trend: ZLMA crosses over/under EMA. ZLEMA de-lag: EMA(2*Close - Close[lag]).
Long regime ZLMA>EMA, short ZLMA<EMA. Entry@open + ATR stop. = trend/beta (source: 'not better
than Hull MA'). Reuses trend_lab. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
LB_REP = 250
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(lb):
    def f(df):
        c = df['close']; a = 2.0/(lb+1); lag = max(1, (lb-1)//2)
        ema = c.ewm(alpha=a, adjust=False).mean()
        zl = (2*c - c.shift(lag)).ewm(alpha=a, adjust=False).mean()
        return (zl > ema).fillna(False), (zl < ema).fillna(False)
    return f
def run_pt(lb=LB_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(lb), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S101 Zero Lag MA (Look_Back={LB_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    LBs = [100, 250, 500]; sg = np.full((1, 3), np.nan)
    for b_, lb in enumerate(LBs): sg[0, b_] = lab.trade_metrics(run_pt(lb))['sharpe']
    pd.DataFrame(sg, columns=[f"L{x}" for x in LBs]).to_csv("s101_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s101_gates.csv", index=False)
