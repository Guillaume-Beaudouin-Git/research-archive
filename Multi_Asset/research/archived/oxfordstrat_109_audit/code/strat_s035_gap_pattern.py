"""
Strategy 35/109 — Gap Pattern Type A (Filter & Exit). Source rating B (best of the registry so far).
https://oxfordstrat.com/trading-strategies/gap-pattern/  (Dahlquist & Bauer)

Gap-continuation momentum with a trend filter:
  Setup long : Low[i] > High[i-1] (gap UP). Short : High[i] < Low[i-1] (gap DOWN).
  Filter     : long only if High[i] > UpperChannel(FLB)[i-1] (uptrend) ; short only if Low[i] < LowerChannel[i-1].
  Entry      : buy/sell at the OPEN after the setup (no stop -> no fill artefact).
  Exit       : Time_Index + Pattern Exit (stop beyond the gap = prior bar extreme) + ATR(20)*6.
  Sweep      : Filter_Look_Back x Time_Index. Fiche: trend filter + longer holds help; rated B.

Directional gap momentum + trend filter -> likely Gate 2 long-beta, but rated B => fair test +
beta-matched check. Reuses ftmo_lab v2-gates + beta_bench. Point Filter_LB=20, Time=10.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
FLB_REP, TM_REP = 20, 10

def simulate_gap(df, flb, time_index, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    upc = pd.Series(h, index=df.index).rolling(flb).max().shift(1).values
    loc = pd.Series(l, index=df.index).rolling(flb).min().shift(1).values
    n = len(df); idx = df.index; trades = []; i = flb + 1
    while i < n - 2:
        k = i
        long_s = l[k] > h[k - 1] and np.isfinite(upc[k]) and h[k] > upc[k]
        short_s = allow_short and h[k] < l[k - 1] and np.isfinite(loc[k]) and l[k] < loc[k]
        if not (long_s or short_s) or not np.isfinite(A[k]) or A[k] <= 0:
            i += 1; continue
        d = 1 if long_s else -1
        if fill == 'stop':       eb = k + 1; entry = o[eb] if eb <= n - 1 else np.nan
        elif fill == 'close':    eb = k + 1; entry = c[eb] if eb <= n - 1 else np.nan
        elif fill == 'next_open': eb = k + 2; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i = k + 1; continue
        risk0 = A[k] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        gapfloor = h[k - 1] if d == 1 else l[k - 1]                 # Pattern-exit level (the gap edge)
        atr_lvl = entry - d * risk0
        stop_lvl = max(gapfloor, atr_lvl) if d == 1 else min(gapfloor, atr_lvl)
        last = min(eb + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(flb, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_gap(df, flb, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(FLB_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(FLB_REP, TM_REP, fill='next_open'))
    print(f"=== S035 Gap Pattern Type A (Filter_LB={FLB_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    FLs = [10, 20, 40]; TMs = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, fl in enumerate(FLs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(fl, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"F{x}" for x in FLs], columns=[f"T{x}" for x in TMs]).to_csv("s035_sensitivity_expectancy.csv")
    print("grid expR (Filter_LB x Time):\n" + pd.DataFrame(grid, index=[f"F{x}" for x in FLs], columns=[f"T{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(FLB_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s035_gates.csv", index=False)
