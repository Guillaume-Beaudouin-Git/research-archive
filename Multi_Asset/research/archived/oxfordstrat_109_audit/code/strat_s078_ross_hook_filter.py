"""
Strategy 78/109 — Ross Hook with Filter (Filter & Exit 1). Joe Ross. Rating B.
https://oxfordstrat.com/trading-strategies/ross-hook-filter-2/

= #76 Ross Hook + DEPTH FILTER: hook depth <= Max_Hook(ratio) * leg drawdown. Min_Setup=10.
Sweep Max_Hook(ratio) x Time_Index. Reuses rosshook.simulate_rosshook(depth_ratio=...).
Rating B (rare). Full gates + beta_line + (MTM audit handled separately). ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import rosshook as rh

MIN_SETUP, RATIO_REP, TIME_REP = 10, 1.0, 10
MAX_HOOK_BARS = 40                       # generous window; the binding constraint is depth_ratio
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def run_point(ratio=RATIO_REP, time_index=TIME_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = rh.simulate_rosshook(df, MIN_SETUP, MAX_HOOK_BARS, time_index, depth_ratio=ratio,
                                  cost_bps=costs[t], fill=fill, side='both')
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = rh.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S078 Ross Hook + depth filter (ratio={RATIO_REP} Time={TIME_REP}, Min_Setup={MIN_SETUP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    RTs = [0.5, 1.0, 1.5, 2.0]; TMs = [5, 10, 20, 40]
    grid = np.full((len(RTs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, rt in enumerate(RTs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(rt, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"r{x}" for x in RTs], columns=[f"T{x}" for x in TMs]).to_csv("s078_sensitivity_expectancy.csv")
    print("grid expR (depth_ratio x Time):\n" + pd.DataFrame(grid, index=[f"r{x}" for x in RTs], columns=[f"T{x}" for x in TMs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s078_gates.csv", index=False)
