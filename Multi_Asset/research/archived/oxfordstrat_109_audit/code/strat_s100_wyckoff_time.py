"""S100 — Wyckoff MR (Time Exits). Variant of #98 (reward disabled -> time/ATR exit dominates).
Reuses #98 engine with a large reward_index so the time cap / risk stop govern the exit."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, wyckoff as wy
from strat_s098_wyckoff import run_point
if __name__ == "__main__":
    pool = run_point(0.5, 1.0, 1.0, 99.0); pm = lab.trade_metrics(pool); el, es, nl, ns = wy.two_sided(pool)
    m_no = lab.trade_metrics(run_point(0.5, 1.0, 1.0, 99.0, fill='next_open'))
    print(f"=== S100 Wyckoff MR Time Exits (reward disabled, time/ATR governs) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    Eis = [0.2, 0.5, 1.0]; sg = np.full((1, 3), np.nan)
    for b_, ei in enumerate(Eis): sg[0, b_] = lab.trade_metrics(run_point(ei, 1.0, 1.0, 99.0))['sharpe']
    pd.DataFrame(sg).to_csv("s100_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(0.5, 1.0, 1.0, 99.0, fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s100_gates.csv", index=False)
