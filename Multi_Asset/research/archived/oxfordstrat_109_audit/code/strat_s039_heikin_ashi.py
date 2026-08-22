"""
Strategy 39/109 — Heikin-Ashi Technique (Setup & Exit). Source rating C.
https://oxfordstrat.com/trading-strategies/heikin-ashi-1/
Trend-following on smoothed HA candles:
  Avg OHLC over Look_Back, then HA: HaClose=(aO+aH+aL+aC)/4 ; HaOpen=(HaOpen[-1]+HaClose[-1])/2.
  Setup long: HaClose[i-1] > HaOpen[i-1] (HA green). Short: HA red. Entry @open. Exit Time + ATR*6.
  Sweep Look_Back x Time_Index. -> trend follower, entry@open -> expect Gate 2 long-beta.
Reuses ftmo_lab v2-gates + beta_bench. Point Look_Back=1 (std HA), Time=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
LB_REP, TM_REP = 1, 10

def ha_bars(df, lb):
    if lb <= 1:
        aO, aH, aL, aC = df['open'].values, df['high'].values, df['low'].values, df['close'].values
    else:
        aO = df['open'].rolling(lb).mean().values; aH = df['high'].rolling(lb).mean().values
        aL = df['low'].rolling(lb).mean().values; aC = df['close'].rolling(lb).mean().values
    n = len(df); hac = (aO + aH + aL + aC) / 4.0; hao = np.full(n, np.nan)
    for i in range(n):
        if not np.isfinite(aO[i]): continue
        hao[i] = (aO[i] + aC[i]) / 2.0 if (i == 0 or not np.isfinite(hao[i - 1])) else (hao[i - 1] + hac[i - 1]) / 2.0
    return hao, hac

def simulate_ha(df, lb, time_index, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; hao, hac = ha_bars(df, lb)
    n = len(df); idx = df.index; trades = []; i = max(2, lb + 1)
    while i < n - 1:
        green = np.isfinite(hao[i - 1]) and hac[i - 1] > hao[i - 1]
        red = np.isfinite(hao[i - 1]) and hac[i - 1] < hao[i - 1]
        if not (green or red) or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        d = 1 if green else -1
        if not allow_short and d == -1:
            i += 1; continue
        if fill == 'stop':      eb = i;     entry = o[eb]
        elif fill == 'close':   eb = i;     entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; last = min(eb + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(lb, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_ha(df, lb, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(LB_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, TM_REP, fill='next_open'))
    print(f"=== S039 Heikin-Ashi (Look_Back={LB_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    LBs = [1, 10, 40]; TMs = [5, 10, 40]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, lb in enumerate(LBs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"Tm{x}" for x in TMs]).to_csv("s039_sensitivity_expectancy.csv")
    print("grid expR (Look_Back x Time):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s039_gates.csv", index=False)
