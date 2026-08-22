"""
Strategy 67/109 — Price Breakout with NR7 (Setup & Exit). Crabel + Connors/Raschke. Rating C.
https://oxfordstrat.com/trading-strategies/price-breakout-nr7/

NR7 setup (range < each of prior 6 ranges) -> next day buy stop at prevDay HIGH
(UpperChannel, Channel_Length=1) / sell stop at prevDay LOW. 1st touched = position.
Exit: Time N at close + ATR stop(6). Swept: NR_Length x N. Channel_Length=1 fixed.
Fiche: "not tradeable once cost applied; similar performance to NR7-ORB" (which was DISCARD 3/4).
-> intrabar STOP breakout = fill-artefact family. Reuses pricebreak engine + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import pricebreak as pbk

CL_REP, NR_REP, N_REP = 1, 6, 10
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SET = {}                                            # cache NR setups by nr_len


def setup(t, nr_len):
    _SET.setdefault((t, nr_len), pbk.nr_setup(uni[t], nr_len))
    return _SET[(t, nr_len)]


def run_pt(nr_len=NR_REP, n=N_REP, cl=CL_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = pbk.simulate_pricebreak(df, setup(t, nr_len), cl, n, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = pbk.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print(f"=== S067 Price Breakout NR7 (NR_Length={NR_REP} N={N_REP} Channel=1) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    NRs = [2, 4, 6, 10]; Ns = [1, 5, 10, 40]
    sg = np.full((len(NRs), len(Ns)), np.nan); gg = np.full_like(sg, np.nan)
    for a, nr in enumerate(NRs):
        for b_, n in enumerate(Ns):
            m = lab.trade_metrics(run_pt(nr, n)); sg[a, b_] = m['sharpe']; gg[a, b_] = m['expR']
    pd.DataFrame(gg, index=[f"NR{x}" for x in NRs], columns=[f"N{x}" for x in Ns]).to_csv("s067_sensitivity_expectancy.csv")
    print("grid expR (NR_Length x N):\n" + pd.DataFrame(gg, index=[f"NR{x}" for x in NRs], columns=[f"N{x}" for x in Ns]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_pt(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s067_gates.csv", index=False)
