"""S082 — Smash Day Type A (Exits). Variant of #81 (exit study, Time ref=20). Reuses #81 engine."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, smashday as sm
from strat_s081_smashday_a import run_point
TR_REP, TM_REP = 20, 20
if __name__ == "__main__":
    pool = run_point(TR_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = sm.two_sided(pool)
    m_no = lab.trade_metrics(run_point(TR_REP, TM_REP, fill='next_open'))
    print(f"=== S082 Smash Day Type A Exits (Trend={TR_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f}")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    TRs=[10,20,40]; TMs=[10,20,40]; sg=np.full((3,3),np.nan)
    for a,tr_ in enumerate(TRs):
        for b_,tm in enumerate(TMs): sg[a,b_]=lab.trade_metrics(run_point(tr_,tm))['sharpe']
    pd.DataFrame(sg).to_csv("s082_sensitivity_expectancy.csv")
    res=lab.run_gates(lambda fill='stop': run_point(TR_REP,TM_REP,fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate':x['gate'],'pass':x['pass'],'tag':x.get('tag') or ''} for x in res['gates']]).to_csv("s082_gates.csv", index=False)
