"""S059 — Oops Pattern Bearish (Exits). Rating D. https://oxfordstrat.com/trading-strategies/bear-oops-pattern/
Short leg of #58 (gap-up fade). Reuses s058. Heritage."""
import numpy as np, pandas as pd
import ftmo_lab as lab, beta_bench as bb, strat_s058_oops as s58
run = lambda fill='stop', ai=s58.AIX_REP, tm=s58.TM_REP: s58.run_point(ai, tm, fill, side='short')
if __name__ == "__main__":
    pool = run(); pm = lab.trade_metrics(pool); m_no = lab.trade_metrics(run('next_open'))
    print(f"=== S059 Oops Bearish (short) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    bb.beta_line(pool)
    AIs = [1.5, 3.0, 5.0]; TMs = [5, 10, 20]; sg = np.full((3, 3), np.nan)
    for a, ai in enumerate(AIs):
        for b_, tm in enumerate(TMs): sg[a, b_] = lab.trade_metrics(run('stop', ai, tm))['sharpe']
    res = lab.run_gates(lambda fill='stop': run(fill), sg, split='2015-12-31'); g = {x['gate']: x for x in res['gates']}
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s059_gates.csv", index=False)
