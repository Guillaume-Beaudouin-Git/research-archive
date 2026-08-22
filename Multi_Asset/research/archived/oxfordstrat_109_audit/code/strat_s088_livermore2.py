"""S088 — Livermore System Part 2 (Filters). Variant of #87 (2nd filter study, same momentum
model). https://oxfordstrat.com/trading-strategies/livermore-system-2/ Reuses #87 proxy (N=60)."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, trend_lab as tl
from strat_s087_livermore import run_pt
N_REP = 60
if __name__ == "__main__":
    pool = run_pt(N_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(N_REP, fill='next_open'))
    print(f"=== S088 Livermore Part 2 (momentum proxy N={N_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    Ns = [40, 60, 100]; sg = np.full((1, 3), np.nan)
    for b_, nn in enumerate(Ns): sg[0, b_] = lab.trade_metrics(run_pt(nn))['sharpe']
    pd.DataFrame(sg, columns=[f"N{x}" for x in Ns]).to_csv("s088_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_pt(N_REP, fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s088_gates.csv", index=False)
