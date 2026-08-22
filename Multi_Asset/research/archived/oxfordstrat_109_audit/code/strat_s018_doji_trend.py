"""
Strategy 18/109 — Doji Pattern Trend (Setup & Filter). Source rating C.
https://oxfordstrat.com/trading-strategies/doji-trend-1/
SAME Doji + stop entry + Time/Quick/ATR exits as S016, but the FILTER is REVERSED (trend-following):
  Long if Close[s] > Close[s-Trend_Index] (Doji after an UP move -> continuation breakout up).
  Short if Close[s] < Close[s-Trend_Index].
=> a TREND-FOLLOWING use of the Doji (continuation breakout). Expect HERITAGE of the TREND cluster
(Gate 2 beta long), NOT the Doji counter-trend. Reuses S016.simulate_doji + ftmo_lab v2-gates.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import strat_s016_doji_reversal as s16

BI_REP, TI_REP = 0.10, 10
uni, costs = s16.uni, s16.costs

def doji_trend_dir(df, body_index, trend_index):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    rng = h - l; body = np.where(rng > 0, np.abs(c - o) / np.where(rng > 0, rng, np.nan), np.nan)
    is_doji = body <= body_index; n = len(c); ds = np.zeros(n)
    for s in range(trend_index, n):
        if not is_doji[s]: continue
        if c[s] > c[s - trend_index]: ds[s] = 1            # trend-following (up move -> long)
        elif c[s] < c[s - trend_index]: ds[s] = -1
    return ds

def run_point(body_index, trend_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds = doji_trend_dir(df, body_index, trend_index)
        tr = s16.simulate_doji(df, ds, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(BI_REP, TI_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(BI_REP, TI_REP, fill='next_open'))
    pd.DataFrame({t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}).T.to_csv("s018_per_instrument.csv")
    print(f"=== S018 Doji-TREND (Body=0.10, Trend=10) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} -> open[s+2] {m_no['sharpe']:+.2f} | TWO-SIDED long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    BIs = [0.05, 0.10, 0.20, 0.30]; TIs = [1, 5, 10, 20, 40]
    grid = np.full((len(BIs), len(TIs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, bi in enumerate(BIs):
        for bb, ti in enumerate(TIs):
            m = lab.trade_metrics(run_point(bi, ti)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"T{x}" for x in TIs]).to_csv("s018_sensitivity_expectancy.csv")
    print("grid expR (Body x Trend):\n" + pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"T{x}" for x in TIs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(BI_REP, TI_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s018_gates.csv", index=False)
