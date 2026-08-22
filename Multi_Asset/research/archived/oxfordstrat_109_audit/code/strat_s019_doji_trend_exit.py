"""
Strategy 19/109 — Doji Pattern Trend (Filter & Exit). Source rating C.
https://oxfordstrat.com/trading-strategies/doji-trend-2/
SAME trend-Doji as S018 (continuation breakout, trend filter), but Body_Index FIXED at 0.05 and the
swept axes are Trend_Index x Time_Index. Expect HERITAGE death (same Doji-stop mechanism). Closes
the Doji cluster (#16-#19). Reuses S018.doji_trend_dir + S016.simulate_doji + ftmo_lab v2-gates.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import strat_s016_doji_reversal as s16
import strat_s018_doji_trend as s18

BODY = 0.05
TI_REP, TM_REP = 10, 20
uni, costs = s16.uni, s16.costs

def run_point(trend_index, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds = s18.doji_trend_dir(df, BODY, trend_index)
        tr = s16.simulate_doji(df, ds, time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(TI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(TI_REP, TM_REP, fill='next_open'))
    print(f"=== S019 Doji-TREND (Filter&Exit, Body=0.05)  Trend={TI_REP} Time={TM_REP} ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} -> open[s+2] {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    TIs = [1, 5, 10, 20]; TMs = [5, 10, 20, 40]
    grid = np.full((len(TIs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ti in enumerate(TIs):
        for bb, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ti, tm)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"Tr{x}" for x in TIs], columns=[f"Tm{x}" for x in TMs]).to_csv("s019_sensitivity_expectancy.csv")
    print("grid expR (Trend x Time):\n" + pd.DataFrame(grid, index=[f"Tr{x}" for x in TIs], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(TI_REP, TM_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k=='dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s019_gates.csv", index=False)
