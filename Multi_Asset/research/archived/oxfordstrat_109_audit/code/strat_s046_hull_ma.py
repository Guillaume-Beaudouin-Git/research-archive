"""
Strategy 46/109 — Hull Moving Average Filter (Entry & Exit). Source rating C. (Alan Hull)
https://oxfordstrat.com/trading-strategies/hull-moving-average/
TREND-FOLLOWING dual-HMA slope: long when Slow_HMA AND Fast_HMA both turn up; short when both down.
  Entry @open ; exit when either HMA no longer in trend or ATR*6. -> expect Gate 2 long-beta (MA cluster).
Reuses trend_lab + ftmo_lab + beta_bench. Point Slow=250, Fast_Index=1 (fiche base case; fast redundant).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab, trend_lab as T, beta_bench as bb

SLOW_REP, FIDX_REP = 250, 1.0
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def _wma(c, n):
    n = max(1, int(n)); w = np.arange(1, n + 1, dtype=float); n2 = len(c)
    num = np.convolve(c, w[::-1], mode='full')[n - 1:n2]
    num = np.concatenate([np.full(n - 1, np.nan), num[:n2 - n + 1]])
    return num / w.sum()

def hma(c, n):
    n = max(2, int(n))
    w1 = _wma(c, n); w2 = _wma(c, max(1, round(n / 2)))
    delta = 2 * w2 - w1
    return _wma(np.nan_to_num(delta, nan=0.0), max(1, round(np.sqrt(n)))) * np.where(np.isfinite(delta), 1, np.nan)

def sig(slow_len, fast_index):
    fast_len = max(2, int(round(fast_index * slow_len)))
    def f(df):
        c = df['close'].values; sh = hma(c, slow_len); fh = hma(c, fast_len)
        su = np.concatenate([[False], sh[1:] > sh[:-1]]); sd = np.concatenate([[False], sh[1:] < sh[:-1]])
        fu = np.concatenate([[False], fh[1:] > fh[:-1]]); fd = np.concatenate([[False], fh[1:] < fh[:-1]])
        return pd.Series(su & fu, index=df.index), pd.Series(sd & fd, index=df.index)
    return f

def run_point(slow_len, fast_index, fill='stop'):
    return T.run_state(uni, costs, sig(slow_len, fast_index), fill=fill)

if __name__ == "__main__":
    pool = run_point(SLOW_REP, FIDX_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = T.two_sided(pool)
    m_no = lab.trade_metrics(run_point(SLOW_REP, FIDX_REP, fill='next_open'))
    print(f"=== S046 Hull MA (Slow={SLOW_REP} Fast_Index={FIDX_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    SLs = [100, 250, 500]; FIs = [0.5, 1.0]; grid = np.full((3, 2), np.nan); sg = np.full((3, 2), np.nan)
    for a, sl in enumerate(SLs):
        for b_, fi in enumerate(FIs):
            m = lab.trade_metrics(run_point(sl, fi)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"S{x}" for x in SLs], columns=[f"FI{x}" for x in FIs]).to_csv("s046_sensitivity_expectancy.csv")
    print("grid expR (Slow x Fast_Index):\n" + pd.DataFrame(grid, index=[f"S{x}" for x in SLs], columns=[f"FI{x}" for x in FIs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(SLOW_REP, FIDX_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s046_gates.csv", index=False)
