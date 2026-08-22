"""
Strategy 56/109 — NR7 Pattern (Setup & Exit). Source rating C. (Toby Crabel)
https://oxfordstrat.com/trading-strategies/nr7/
NR7 setup (today's range < each of prior NR_Length=6 days) + Crabel ORB-stop entry (Open +/- Stretch).
-> SAME ORB-stop archetype as S001/S055 -> Gate 1 fill-artefact. Fiche: "not tradeable once costs applied."
Reuses ftmo_lab.simulate_bracket + s027.crabel_stretch + beta_bench. Point NR_Length=6, N(time)=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import strat_s027_engulfing as s27

ATR_LEN, ATR_STOP, BIG = 20, 6.0, 999.0
NR_REP, N_REP = 6, 10
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_STR = {t: s27.crabel_stretch(df) for t, df in uni.items()}

def nr_setup(df, nrlen):
    rng = df['high'] - df['low']
    return rng < rng.shift(1).rolling(nrlen).min()             # narrower than each of prior nrlen days

def run_point(nrlen, n_time, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = lab.simulate_bracket(df, nr_setup(df, nrlen), _STR[t], target_index=BIG, time_index=n_time,
                                  atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(NR_REP, N_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(NR_REP, N_REP, fill='next_open'))
    print(f"=== S056 NR7 (NR_Length={NR_REP} N={N_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    NRs = [4, 6, 10]; Ns = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, nr in enumerate(NRs):
        for b_, nn in enumerate(Ns):
            m = lab.trade_metrics(run_point(nr, nn)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"NR{x}" for x in NRs], columns=[f"N{x}" for x in Ns]).to_csv("s056_sensitivity_expectancy.csv")
    print("grid expR (NR_Length x N):\n" + pd.DataFrame(grid, index=[f"NR{x}" for x in NRs], columns=[f"N{x}" for x in Ns]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(NR_REP, N_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    e = pd.to_datetime(pool['entry']); rec = lab.trade_metrics(pool[e > pd.Timestamp('2018-12-31')])
    print(f"RECENT 2019+: expR {rec['expR']:+.4f} Sh {rec['sharpe']:+.2f}")
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s056_gates.csv", index=False)
