"""S086 — TD Sequential (DeMark). Exhaustion mean-reversion. Rating N/A.
https://oxfordstrat.com/trading-strategies/td-sequential-1/  Reuses td_seq.simulate_tdseq + beta_bench."""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb, td_seq as td
SL_REP, CD_REP = 9, 13
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def run_point(sl=SL_REP, cd=CD_REP, fill='stop'):
    fr = []
    for t, df in uni.items():
        tr = td.simulate_tdseq(df, sl, cd, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; fr.append(tr)
    return pd.concat(fr, ignore_index=True) if fr else pd.DataFrame()
if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = td.two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S086 TD Sequential (Setup={SL_REP} Countdown={CD_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(close) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    SLs = [7, 9, 13]; CDs = [9, 13, 17]; sg = np.full((3, 3), np.nan); gg = np.full((3, 3), np.nan)
    for a, sl in enumerate(SLs):
        for b_, cd in enumerate(CDs):
            mm = lab.trade_metrics(run_point(sl, cd)); sg[a, b_] = mm['sharpe']; gg[a, b_] = mm['expR']
    pd.DataFrame(gg, index=[f"S{x}" for x in SLs], columns=[f"C{x}" for x in CDs]).to_csv("s086_sensitivity_expectancy.csv")
    print("grid expR (Setup x Countdown):\n" + pd.DataFrame(gg, index=[f"S{x}" for x in SLs], columns=[f"C{x}" for x in CDs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s086_gates.csv", index=False)
