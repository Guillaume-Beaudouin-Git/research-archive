"""
Strategy 45/109 — Hook Pattern Bullish (Exits). Source rating D. (Toby Crabel)
https://oxfordstrat.com/trading-strategies/pattern-bull-hook/
Long-only leg of the Hook (#43): long hook setup + Crabel ORB buy-stop. Reuses s043. Heritage ORB-stop.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import strat_s043_hook as s43

run = lambda fill='stop', ti=s43.TI_REP, tm=s43.TM_REP: s43.run_point(ti, tm, fill, side='long')

if __name__ == "__main__":
    pool = run(); pm = lab.trade_metrics(pool); m_no = lab.trade_metrics(run('next_open'))
    print(f"=== S045 Hook Bullish (long, Target={s43.TI_REP} Time={s43.TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    bb.beta_line(pool)
    TIs = [1.0, 3.0, 6.0]; TMs = [5, 10, 20]; sg = np.full((3, 3), np.nan)
    for a, ti in enumerate(TIs):
        for b_, tm in enumerate(TMs): sg[a, b_] = lab.trade_metrics(run('stop', ti, tm))['sharpe']
    res = lab.run_gates(lambda fill='stop': run(fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s045_gates.csv", index=False)
