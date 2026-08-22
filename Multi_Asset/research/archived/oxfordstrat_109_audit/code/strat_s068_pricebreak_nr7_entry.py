"""
Strategy 68/109 — Price Breakout with NR7 (Setup & Entry). Crabel + Connors/Raschke. Rating C.
https://oxfordstrat.com/trading-strategies/price-breakout-nr7-entry/

Twin of #67: same NR7 setup + channel-breakout entry, but the STUDY varies the entry
threshold Channel_Length (buy stop at UpperChannel(CL)[yesterday]). N=10 fixed, sweep
Channel_Length x NR_Length. Fiche: "better when Channel_Length>=10; not tradeable once
cost applied." -> wider channel = slower trend breakout = same intrabar-stop fill family.
Reuses pricebreak engine + s067.run_pt(cl=...) machinery. Reference Channel_Length=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import pricebreak as pbk
from strat_s067_pricebreak_nr7 import run_pt

CL_REP, NR_REP, N_REP = 10, 6, 10


if __name__ == "__main__":
    pool = run_pt(NR_REP, N_REP, CL_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = pbk.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(NR_REP, N_REP, CL_REP, fill='next_open'))
    print(f"=== S068 Price Breakout NR7 — ENTRY study (Channel_Length={CL_REP} NR={NR_REP} N={N_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    CLs = [1, 5, 10, 20, 30]; NRs = [4, 6, 10]
    sg = np.full((len(CLs), len(NRs)), np.nan); gg = np.full_like(sg, np.nan)
    for a, cl in enumerate(CLs):
        for b_, nr in enumerate(NRs):
            m = lab.trade_metrics(run_pt(nr, N_REP, cl)); sg[a, b_] = m['sharpe']; gg[a, b_] = m['expR']
    pd.DataFrame(gg, index=[f"CL{x}" for x in CLs], columns=[f"NR{x}" for x in NRs]).to_csv("s068_sensitivity_expectancy.csv")
    print("grid expR (Channel_Length x NR_Length):\n" + pd.DataFrame(gg, index=[f"CL{x}" for x in CLs], columns=[f"NR{x}" for x in NRs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_pt(NR_REP, N_REP, CL_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s068_gates.csv", index=False)
