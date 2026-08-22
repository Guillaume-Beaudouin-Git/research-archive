"""S097 — J. Welles Wilder Volatility Breakout (Volatility System). Rating C.
https://oxfordstrat.com/trading-strategies/welles-wilder-1/
2-phase stop-and-reverse: SIC = best close while in trade; SAR = SIC -/+ ARC (ATR*Constant).
Flip long when close > SAR (from short); flip short when close < SAR. = trend-following / beta.
Entry @open on flip + ATR stop. Reuses trend_lab (persistent regime). ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
K_REP, LB_REP = 3.0, 14
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def sig(k, lb):
    def f(df):
        c = df['close'].values; A = lab.atr(df, lb).values; n = len(c)
        st = np.zeros(n, np.int8); sic = c[0]; cur = 1
        for i in range(n):
            a = A[i] if np.isfinite(A[i]) else 0.0
            if cur == 1:
                sic = max(sic, c[i]); sar = sic - a*k
                if a > 0 and c[i] < sar: cur = -1; sic = c[i]
            else:
                sic = min(sic, c[i]); sar = sic + a*k
                if a > 0 and c[i] > sar: cur = 1; sic = c[i]
            st[i] = cur
        s = pd.Series(st, index=df.index); return (s > 0), (s < 0)
    return f
def run_pt(k=K_REP, lb=LB_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(k, lb), fill=fill)
if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S097 Wilder Volatility Breakout (Constant={K_REP} LookBack={LB_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    Ks = [2.0, 3.0, 5.0]; LBs = [7, 14, 28]; sg = np.full((3, 3), np.nan)
    for a, k in enumerate(Ks):
        for b_, lb in enumerate(LBs): sg[a, b_] = lab.trade_metrics(run_pt(k, lb))['sharpe']
    pd.DataFrame(sg, index=[f"K{x}" for x in Ks], columns=[f"lb{x}" for x in LBs]).to_csv("s097_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s097_gates.csv", index=False)
