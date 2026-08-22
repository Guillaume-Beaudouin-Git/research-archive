"""S090 — Turtle Soup (Setup & Exit 2). Variant of #89 (2nd exit study, faster Channel_#2=5).
https://oxfordstrat.com/trading-strategies/turtle-soup-plus-2/ Reuses #89 engine."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, turtlesoup as ts
from strat_s089_turtle_soup import run_point
C1_REP, C2_REP = 20, 5
if __name__ == "__main__":
    pool = run_point(C1_REP, C2_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = ts.two_sided(pool)
    m_no = lab.trade_metrics(run_point(C1_REP, C2_REP, fill='next_open'))
    print(f"=== S090 Turtle Soup Exit 2 (Channel1={C1_REP} Channel2={C2_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    C1s = [10, 20, 40]; C2s = [3, 5, 10]; sg = np.full((3, 3), np.nan)
    for a, c1 in enumerate(C1s):
        for b_, c2 in enumerate(C2s): sg[a, b_] = lab.trade_metrics(run_point(c1, c2))['sharpe']
    pd.DataFrame(sg).to_csv("s090_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(C1_REP, C2_REP, fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s090_gates.csv", index=False)
