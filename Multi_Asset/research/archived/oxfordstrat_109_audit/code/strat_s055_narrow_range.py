"""
Strategy 55/109 — Narrow Range N-Day Pattern (Setup). Source rating C. (Toby Crabel)
https://oxfordstrat.com/trading-strategies/narrow-range/
Crabel NR-N setup (narrowest N-day range in last Look_Back) + Crabel ORB-stop entry (Open +/- Stretch).
-> SAME ORB-stop archetype as S001/S002/GSV -> Gate 1 fill-artefact expected. Exits Time(10)+Stretch+ATR.
Reuses ftmo_lab.simulate_bracket + s027.crabel_stretch + beta_bench. Point N=4, Look_Back=20.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import strat_s027_engulfing as s27

ATR_LEN, ATR_STOP = 20, 6.0
N_REP, LB_REP, TM = 4, 20, 10
BIG = 999.0
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_STR = {t: s27.crabel_stretch(df) for t, df in uni.items()}

def nr_setup(df, N, lb):
    rN = df['high'].rolling(N).max() - df['low'].rolling(N).min()
    return rN <= rN.rolling(lb).min()                          # narrowest N-day range in last lb days

def run_point(N, lb, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = lab.simulate_bracket(df, nr_setup(df, N, lb), _STR[t], target_index=BIG, time_index=TM,
                                  atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(N_REP, LB_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(N_REP, LB_REP, fill='next_open'))
    print(f"=== S055 Narrow Range N-Day (N={N_REP} Look_Back={LB_REP} Time={TM}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    Ns = [2, 4, 7]; LBs = [20, 35, 50]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, nn in enumerate(Ns):
        for b_, lb in enumerate(LBs):
            m = lab.trade_metrics(run_point(nn, lb)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"N{x}" for x in Ns], columns=[f"LB{x}" for x in LBs]).to_csv("s055_sensitivity_expectancy.csv")
    print("grid expR (N x Look_Back):\n" + pd.DataFrame(grid, index=[f"N{x}" for x in Ns], columns=[f"LB{x}" for x in LBs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(N_REP, LB_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s055_gates.csv", index=False)
