"""
Strategy 38/109 — Greatest Swing Value - Trend (Filter & Exit). Source rating C. (Larry Williams)
https://oxfordstrat.com/trading-strategies/greatest-swing-value-trend/
GSV ORB-stop entry made DIRECTIONAL by a trend filter:
  Filter: long if Close[i-1] > Close[i-Trend_Index] (uptrend) ; short if <.
  Entry : buy stop Open+GSV (uptrend only) / sell stop Open-GSV (downtrend only). Exit: Time + ATR*6.
  Sweep : Trend_Index x Time_Index. -> ORB-stop -> Gate 1 fill-artefact (heritage of GSV #37) + beta.
Reuses GSV stretch from s037 + ftmo_lab + beta_bench. Point Trend_Index=10, Time=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import strat_s037_gsv as g37

ATR_LEN, ATR_STOP = 20, 6.0
TI_REP, TM_REP = 10, 10
uni, costs = g37.uni, g37.costs
_ST = g37._ST

def simulate_gsv_trend(df, gsv, trend_index, time_index, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; st = gsv.values
    cv = c; n = len(df); idx = df.index; trades = []; i = trend_index + 1
    while i < n - 1:
        up = cv[i - 1] > cv[i - 1 - trend_index]; dn = cv[i - 1] < cv[i - 1 - trend_index]
        if not np.isfinite(st[i - 1]) or st[i - 1] <= 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        d = 0
        if up: d = 1; lvl = o[i] + st[i - 1]; hit = h[i] >= lvl
        elif allow_short and dn: d = -1; lvl = o[i] - st[i - 1]; hit = l[i] <= lvl
        else: i += 1; continue
        if not hit:
            i += 1; continue
        e = i
        if fill == 'stop':      entry = max(o[e], lvl) if d == 1 else min(o[e], lvl); start = e
        elif fill == 'close':   entry = c[e]; start = e
        elif fill == 'next_open': start = e + 1; entry = o[start] if start <= n - 1 else np.nan
        else: raise ValueError(fill)
        if start > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[e] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; last = min(e + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(start, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[e], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

def run_point(trend_index, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_gsv_trend(df, _ST[t], trend_index, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(TI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(TI_REP, TM_REP, fill='next_open'))
    print(f"=== S038 GSV-Trend (Trend_Index={TI_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    TIs = [5, 10, 20]; TMs = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, ti in enumerate(TIs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ti, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"Tr{x}" for x in TIs], columns=[f"Tm{x}" for x in TMs]).to_csv("s038_sensitivity_expectancy.csv")
    print("grid expR (Trend x Time):\n" + pd.DataFrame(grid, index=[f"Tr{x}" for x in TIs], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(TI_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s038_gates.csv", index=False)
