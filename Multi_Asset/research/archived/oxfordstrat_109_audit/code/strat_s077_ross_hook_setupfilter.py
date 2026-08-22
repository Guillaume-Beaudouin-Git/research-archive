"""
Strategy 77/109 — Ross Hook with Filter (Setup & Filter). Joe Ross. Rating C.
https://oxfordstrat.com/trading-strategies/ross-hook-filter-1/
= #76 + depth filter; the "Setup & Filter" study sweeps Min_Setup x depth_ratio (Max_Hook).
Reuses rosshook.simulate_rosshook. Same Ross-Hook archetype as #76 (KEEP-class) -> short report.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import rosshook as rh

MIN_REP, RATIO_REP, TIME = 10, 1.0, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def run_point(min_setup=MIN_REP, ratio=RATIO_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = rh.simulate_rosshook(df, min_setup, 40, TIME, depth_ratio=ratio, cost_bps=costs[t], fill=fill, side='both')
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = rh.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S077 Ross Hook Setup&Filter (Min_Setup={MIN_REP} ratio={RATIO_REP} Time={TIME}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    MNs = [4, 10, 20]; RTs = [0.5, 1.0, 2.0]
    sg = np.full((3, 3), np.nan)
    for a, mn in enumerate(MNs):
        for b_, rt in enumerate(RTs): sg[a, b_] = lab.trade_metrics(run_point(mn, rt))['sharpe']
    pd.DataFrame(sg, index=[f"MS{x}" for x in MNs], columns=[f"r{x}" for x in RTs]).to_csv("s077_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s077_gates.csv", index=False)
