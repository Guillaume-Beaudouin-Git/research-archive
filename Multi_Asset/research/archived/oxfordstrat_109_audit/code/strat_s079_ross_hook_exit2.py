"""
Strategy 79/109 — Ross Hook with Filter (Filter & Exit 2). Joe Ross. Rating B.
https://oxfordstrat.com/trading-strategies/ross-hook-filter-3/
= #78 (depth filter) second exit study; reuses s078.run_point with a longer time reference.
Same Ross-Hook archetype (KEEP-class) -> short report; confirms robustness across exits.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import rosshook as rh
from strat_s078_ross_hook_filter import run_point

RATIO_REP, TIME_REP = 1.0, 20      # Exit 2: longer holding reference


if __name__ == "__main__":
    pool = run_point(RATIO_REP, TIME_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = rh.two_sided(pool)
    m_no = lab.trade_metrics(run_point(RATIO_REP, TIME_REP, fill='next_open'))
    print(f"=== S079 Ross Hook Filter & Exit 2 (ratio={RATIO_REP} Time={TIME_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    RTs = [0.5, 1.0, 2.0]; TMs = [10, 20, 40]
    sg = np.full((3, 3), np.nan)
    for a, rt in enumerate(RTs):
        for b_, tm in enumerate(TMs): sg[a, b_] = lab.trade_metrics(run_point(rt, tm))['sharpe']
    pd.DataFrame(sg, index=[f"r{x}" for x in RTs], columns=[f"T{x}" for x in TMs]).to_csv("s079_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(RATIO_REP, TIME_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s079_gates.csv", index=False)
