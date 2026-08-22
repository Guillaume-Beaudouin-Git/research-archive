"""
Strategy 62/109 — Opening Range Breakout, WEEKLY BARS (Entry). Crabel. Rating D.
https://oxfordstrat.com/trading-strategies/opening-range-breakout-weekly/

Same ORB entry but on WEEKLY bars: buy stop [WeekOpen+Stretch] / sell stop
[WeekOpen-Stretch], first touched = position. Stretch = SMA(min(H-O,O-L),L)*M on
weekly noise. Exit: ATR stop ONLY (no time, no target) -> hold until ATR stop.
Swept vars: Stretch_Length x Stretch_Multiple.
Fiche summary: "since 1990 the strategy stopped working once realistic cost is
applied; without cost it holds." -> a COST/fill artefact. Reuses
ftmo_lab.simulate_bracket UNCHANGED on weekly-resampled OHLC + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
from orb_filtered import crabel_stretch

ATR_LEN, ATR_STOP = 20, 6.0
SL_REP, SM_REP = 10, 2.0          # Stretch_Length x Stretch_Multiple reference
BIG_TIME, NO_TGT = 52, 999.0      # ATR-stop-only: target never hit, time caps 1y

uni_d = lab.load_universe()
_AGG = {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}
uni = {t: df.resample('W-FRI').agg(_AGG).dropna() for t, df in uni_d.items()}
uni = {t: df for t, df in uni.items() if len(df) > 60}
costs = {t: lab.round_turn_cost_bps(t, uni_d[t]) for t in uni}


def run_point(sl, sm, fill='stop'):
    frames = []
    for t, df in uni.items():
        st = crabel_stretch(df, int(sl), float(sm))
        setup = pd.Series(True, index=df.index)
        tr = lab.simulate_bracket(df, setup, st, target_index=NO_TGT, time_index=BIG_TIME,
                                  atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))


if __name__ == "__main__":
    pool = run_point(SL_REP, SM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(SL_REP, SM_REP, fill='next_open'))
    print(f"=== S062 ORB Weekly Bars (Stretch_Len={SL_REP} Mult={SM_REP}, ATR-stop only) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    SLs = [5, 10, 20, 40]; SMs = [1.0, 2.0, 3.0, 4.0]
    grid = np.full((len(SLs), len(SMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, sl in enumerate(SLs):
        for b_, sm in enumerate(SMs):
            m = lab.trade_metrics(run_point(sl, sm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"L{x}" for x in SLs], columns=[f"M{x}" for x in SMs]).to_csv("s062_sensitivity_expectancy.csv")
    print("grid expR (Len x Mult):\n" + pd.DataFrame(grid, index=[f"L{x}" for x in SLs], columns=[f"M{x}" for x in SMs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(SL_REP, SM_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s062_gates.csv", index=False)
