"""
Strategy 83/109 — Smash Day Pattern Type B (Filter & Exit). Larry Williams. Rating B.
https://oxfordstrat.com/trading-strategies/smash-day-pattern-b1/
Failed-pattern reversal: a day CLOSES BELOW the prior day's LOW (the 'smash'), then BUY stop
above its high (reversal of the smash) + trend filter. Reuses smashday + setup_typeB.
Rating B -> gates + beta_line; MTM audit if it survives. Sweep Trend_Index x Time.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, beta_bench as bb, smashday as sm

TR_REP, TM_REP = 20, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def run_point(trend_index=TR_REP, time_index=TM_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = sm.simulate_smash(df, sm.setup_typeB(df, trend_index), time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = sm.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S083 Smash Day Type B (Trend_Index={TR_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    TRs = [4, 10, 20, 40]; TMs = [5, 10, 20, 40]
    grid = np.full((len(TRs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, tr_ in enumerate(TRs):
        for b_, tm in enumerate(TMs):
            mm = lab.trade_metrics(run_point(tr_, tm)); grid[a, b_] = mm['expR']; sg[a, b_] = mm['sharpe']
    pd.DataFrame(grid, index=[f"T{x}" for x in TRs], columns=[f"{x}d" for x in TMs]).to_csv("s083_sensitivity_expectancy.csv")
    print("grid expR (Trend x Time):\n" + pd.DataFrame(grid, index=[f"T{x}" for x in TRs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s083_gates.csv", index=False)
