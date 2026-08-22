"""
Strategy 29/109 — Bullish Engulfing Candlestick Type A (Exits). Source rating D.
https://oxfordstrat.com/trading-strategies/pattern-bullish-engulfing-a/
Type A = stricter bullish engulfing (also engulfs the RANGE: H[t]>H[t-1] & L[t]<L[t-1]). ORB-up long.
Reuses S027 module. HERITAGE of engulfing-ORB / S001 family.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import strat_s027_engulfing as s27

run = lambda fill='stop', ti=s27.TI_REP, tm=s27.TM_REP: s27.run_dir(s27.eng_bull_A, 1, ti, tm, fill)

if __name__ == "__main__":
    pool = run(); pm = lab.trade_metrics(pool); m_no = lab.trade_metrics(run('next_open'))
    print(f"=== S029 Bullish Engulfing TYPE A (ORB-up long, Target={s27.TI_REP} Time={s27.TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    fb, nb = s27.pattern_forward_edge(s27.eng_bull_A, 1)
    print(f"PURE-PATTERN 10d fwd edge (no ORB, net): {fb:+.5f}(n{nb})")
    TIs = [1.0, 3.0, 6.0]; TMs = [5, 10, 20]; sg = np.full((len(TIs), len(TMs)), np.nan)
    for a, ti in enumerate(TIs):
        for bb, tm in enumerate(TMs): sg[a, bb] = lab.trade_metrics(run('stop', ti, tm))['sharpe']
    res = lab.run_gates(lambda fill='stop': run(fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s029_gates.csv", index=False)
