"""S085 — Smash Day Type C (Exits). Larry Williams, rating D.
https://oxfordstrat.com/trading-strategies/smash-day-pattern-c/
= Type B setup (Close<Low[i-2] long / Close>High[i-2] short) but NO trend filter.
Reuses smashday + setup_typeB(filt=False). (Source adds a %target exit; here we keep the
standard quick/ATR/time engine — minor; Type C is the un-filtered, rating-D variant.)
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, smashday as sm
TM_REP = 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def run_point(time_index=TM_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = sm.simulate_smash(df, sm.setup_typeB(df, 0, filt=False), time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = sm.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S085 Smash Day Type C (no filter, Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: {pm['sharpe']:+.2f} -> {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}/short {es:+.4f}"); bb.beta_line(pool)
    TMs=[5,10,20,40]; sg=np.full((1,4),np.nan)
    for b_,tm in enumerate(TMs): sg[0,b_]=lab.trade_metrics(run_point(tm))['sharpe']
    pd.DataFrame(sg, columns=[f"{x}d" for x in TMs]).to_csv("s085_sensitivity_expectancy.csv")
    res=lab.run_gates(lambda fill='stop': run_point(fill=fill), sg, split='2015-12-31')
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate':x['gate'],'pass':x['pass'],'tag':x.get('tag') or ''} for x in res['gates']]).to_csv("s085_gates.csv", index=False)
