"""
Strategy 80/109 — Simple Moving Average Filter (Entry & Exit). Kaufman. Rating C.
https://oxfordstrat.com/trading-strategies/simple-moving-average/

Canonical dual-SMA trend (2-phase always-in): Fast_SMA>Slow_SMA -> long ; < -> short.
Entry @open, exit on flip + ATR stop. Fast_SMA_Length = Fast_Index * Slow_Length.
Reference Slow=250, Fast_Index=0.25 (=Fast 62). Pure trend = beta -> beta_line decisive.
Reuses trend_lab (entry@open state machine). ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import trend_lab as tl

SLOW_REP, FIDX_REP = 250, 0.25
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def sig(slow, fidx):
    fast = max(2, int(round(fidx * slow)))
    def f(df):
        c = df['close']; fs = c.rolling(fast).mean(); ss = c.rolling(slow).mean()
        return (fs > ss).fillna(False), (fs < ss).fillna(False)
    return f


def run_pt(slow=SLOW_REP, fidx=FIDX_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(slow, fidx), fill=fill)


if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S080 SMA dual-trend (Slow={SLOW_REP} Fast={int(FIDX_REP*SLOW_REP)}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    SLs = [100, 250, 500]; FIs = [0.2, 0.35, 0.5]
    sg = np.full((3, 3), np.nan)
    for a, sl in enumerate(SLs):
        for b_, fi in enumerate(FIs): sg[a, b_] = lab.trade_metrics(run_pt(sl, fi))['sharpe']
    pd.DataFrame(sg, index=[f"S{x}" for x in SLs], columns=[f"f{x}" for x in FIs]).to_csv("s080_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s080_gates.csv", index=False)
