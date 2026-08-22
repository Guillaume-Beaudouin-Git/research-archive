"""
Strategy 61/109 — Opening Range Breakout (Exits). Toby Crabel. Source rating D.
https://oxfordstrat.com/trading-strategies/opening-range-breakout/

THE canonical ORB. No setup, no filter: every day a buy stop at [Open+Stretch]
and a sell stop at [Open-Stretch]; first stop touched = position, other =
protective stop. Stretch = SMA(min(H-O,O-L),10) * 2 (symmetric Crabel noise).
Exits: Target_Index (R) + Time_Index + ATR stop(6).
-> Intrabar STOP entry on both sides every day = the S001/GSV fill-artefact trap.
   Gate 1 (delay+1) expected fatal. Reuses ftmo_lab.simulate_bracket UNCHANGED
   (setup = all True, stretch = Crabel noise) + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
from orb_filtered import crabel_stretch

STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 10, 2.0, 20, 6.0
TI_REP, TM_REP = 3.0, 10          # Target_Index x Time_Index reference point

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_ST = {t: crabel_stretch(df, STRETCH_LEN, STRETCH_MULT) for t, df in uni.items()}
_SETUP = {t: pd.Series(True, index=df.index) for t, df in uni.items()}


def run_point(target_index, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = lab.simulate_bracket(df, _SETUP[t], _ST[t], target_index=target_index,
                                  time_index=time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                                  cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))


if __name__ == "__main__":
    pool = run_point(TI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(TI_REP, TM_REP, fill='next_open'))
    print(f"=== S061 Opening Range Breakout (ORB-stop, Target={TI_REP}R Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    TIs = [1, 2, 4, 6, 10]; TMs = [1, 5, 10, 40]
    grid = np.full((len(TIs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ti in enumerate(TIs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ti, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs]).to_csv("s061_sensitivity_expectancy.csv")
    print("grid expR (Target x Time):\n" + pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(TI_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s061_gates.csv", index=False)
