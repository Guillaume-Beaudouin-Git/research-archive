"""
Strategy 76/109 — Ross Hook Pattern (Setup). Joe Ross. Rating C.
https://oxfordstrat.com/trading-strategies/ross-hook-1/

Trend-continuation: first correction after a 1-2-3 breakout; buy stop above the hook high.
Reuses rosshook.simulate_rosshook (no depth filter). Sweep Min_Setup x Max_Hook (bars), Time=10.
-> intrabar STOP entry (fill-artefact test) + continuation = directional beta. Reuses ftmo_lab+beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import rosshook as rh

MIN_REP, HOOK_REP, TIME = 10, 20, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def run_point(min_setup=MIN_REP, max_hook=HOOK_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = rh.simulate_rosshook(df, min_setup, max_hook, TIME, cost_bps=costs[t], fill=fill, side='both')
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = rh.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S076 Ross Hook (Min_Setup={MIN_REP} Max_Hook={HOOK_REP} Time={TIME}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    MNs = [4, 10, 20, 40]; HKs = [5, 10, 20, 40]
    grid = np.full((len(MNs), len(HKs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, mn in enumerate(MNs):
        for b_, hk in enumerate(HKs):
            m = lab.trade_metrics(run_point(mn, hk)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"MS{x}" for x in MNs], columns=[f"H{x}" for x in HKs]).to_csv("s076_sensitivity_expectancy.csv")
    print("grid expR (Min_Setup x Max_Hook):\n" + pd.DataFrame(grid, index=[f"MS{x}" for x in MNs], columns=[f"H{x}" for x in HKs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s076_gates.csv", index=False)
