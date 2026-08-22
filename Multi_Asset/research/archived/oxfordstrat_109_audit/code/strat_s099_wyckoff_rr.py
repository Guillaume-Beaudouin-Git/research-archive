"""S099 — Wyckoff MR (Risk-Reward). Variant of #98 (sweep Risk/Reward exit). Reuses #98 engine."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, wyckoff as wy
from strat_s098_wyckoff import run_point
RISK_REP, REWARD_REP = 1.0, 3.0
if __name__ == "__main__":
    pool = run_point(0.5, 1.0, RISK_REP, REWARD_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = wy.two_sided(pool)
    m_no = lab.trade_metrics(run_point(0.5, 1.0, RISK_REP, REWARD_REP, fill='next_open'))
    print(f"=== S099 Wyckoff MR Risk-Reward (Risk={RISK_REP} Reward={REWARD_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    Rk = [0.5, 1.0, 2.0]; Rw = [1.0, 2.0, 4.0]; sg = np.full((3, 3), np.nan)
    for a, rk in enumerate(Rk):
        for b_, rw in enumerate(Rw): sg[a, b_] = lab.trade_metrics(run_point(0.5, 1.0, rk, rw))['sharpe']
    pd.DataFrame(sg).to_csv("s099_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(0.5, 1.0, RISK_REP, REWARD_REP, fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s099_gates.csv", index=False)
