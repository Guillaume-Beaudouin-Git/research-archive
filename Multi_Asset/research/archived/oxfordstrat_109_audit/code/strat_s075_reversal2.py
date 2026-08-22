"""
Strategy 75/109 — Reversal Patterns Part 2 (Wyckoff/Crabel + Appel). Rating C.
https://oxfordstrat.com/trading-strategies/reversal-patterns-part-2/

= #74 pivot reversal + a PRICE-MOMENTUM DIVERGENCE filter: the pivot break must be
UNCONFIRMED by MACD(12,26,9) (bullish/bearish divergence). Fiche: the MACD divergence
"adds value" vs Part 1, but the family stays very cost-sensitive (Case#1 RR=2 Sharpe -0.11).
Reuses strat_s074_reversal.simulate_rev(macd_div=True). ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
from strat_s074_reversal import simulate_rev, uni, costs, two_sided

RR_REP, TD_REP = 4.0, 20


def run_point(reward_ratio=RR_REP, trade_dur=TD_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_rev(df, reward_ratio, trade_dur, cost_bps=costs[t], fill=fill, macd_div=True)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S075 Reversal Patterns Part 2 (pivots + MACD divergence, RR={RR_REP} TD={TD_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: open[+1] {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[+2] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    RRs = [2.0, 4.0, 8.0]; TDs = [10, 20, 40]
    grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, rr in enumerate(RRs):
        for b_, td in enumerate(TDs):
            m = lab.trade_metrics(run_point(rr, td)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"RR{x}" for x in RRs], columns=[f"TD{x}" for x in TDs]).to_csv("s075_sensitivity_expectancy.csv")
    print("grid expR (Reward_Ratio x Trade_Dur):\n" + pd.DataFrame(grid, index=[f"RR{x}" for x in RRs], columns=[f"TD{x}" for x in TDs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s075_gates.csv", index=False)
