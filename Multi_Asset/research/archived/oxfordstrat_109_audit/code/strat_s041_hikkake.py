"""
Strategy 41/109 — Hikkake Pattern (Filter & Exit). Source rating C. (Dan Chesler)
https://oxfordstrat.com/trading-strategies/hikkake-pattern/
Inside-bar FALSE-BREAKOUT trap (two-sided fade-the-fakeout):
  Bullish: bar[i-1] inside bar (H[i-1]<H[i-2] & L[i-1]>L[i-2]); bar[i] lower-high & lower-low (false
           down-breakout). Entry: BUY STOP one tick above the inside-bar high H[i-1], within 3 bars.
  Bearish: symmetric (false up-breakout) -> sell stop below inside-bar low.
  Filter : Close[i]>=Close[i-Trend_Index] (Trend_Index=0 -> off; fiche says filter redundant).
  Exit   : Time + Pattern (stop beyond the pattern extreme) + ATR*6. Sweep Trend_Index x Time_Index.
Like False Breakout (#31): a STOP reclaim entry -> Gate 1 fill check. Reuses ftmo_lab v2-gates + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
TI_REP, TM_REP = 0, 20          # Trend_Index=0 (filter off), Time=20 (fiche: Time>10)
MAXWAIT = 3

def simulate_hikkake(df, trend_index, time_index, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; n = len(df); idx = df.index; trades = []; i = 3
    while i < n - 1:
        # pattern completes at bar k=i: inside bar at k-1, false breakout at k
        k = i
        inside = h[k - 1] < h[k - 2] and l[k - 1] > l[k - 2]
        bull = inside and h[k] < h[k - 1] and l[k] < l[k - 1]      # false down-breakout -> long
        bear = inside and h[k] > h[k - 1] and l[k] > l[k - 1]      # false up-breakout   -> short
        if not (bull or bear) or not np.isfinite(A[k]) or A[k] <= 0:
            i += 1; continue
        d = 1 if bull else -1
        if allow_short is False and d == -1:
            i += 1; continue
        # trend filter
        if trend_index and k - trend_index >= 0:
            if d == 1 and not (c[k] >= c[k - trend_index]): i += 1; continue
            if d == -1 and not (c[k] <= c[k - trend_index]): i += 1; continue
        lvl = h[k - 1] if d == 1 else l[k - 1]                     # inside-bar extreme = stop level
        entry = eb = None
        for j in range(k + 1, min(k + 1 + MAXWAIT, n)):
            trig = (h[j] >= lvl) if d == 1 else (l[j] <= lvl)
            if trig:
                if fill == 'stop': entry = (max(o[j], lvl) if d == 1 else min(o[j], lvl)); eb = j
                elif fill == 'close': entry = c[j]; eb = j
                elif fill == 'next_open': eb = j + 1; entry = o[eb] if eb <= n - 1 else None
                break
        if entry is None or eb is None or eb > n - 1 or not np.isfinite(entry):
            i = k + 1; continue
        risk0 = A[k] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        patt = np.min(l[k - 1:eb + 1]) if d == 1 else np.max(h[k - 1:eb + 1])   # pattern extreme (Pattern Exit)
        atr_lvl = entry - d * risk0
        stop_lvl = max(patt, atr_lvl) if d == 1 else min(patt, atr_lvl)
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

def run_point(trend_index, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_hikkake(df, trend_index, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(TI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(TI_REP, TM_REP, fill='next_open'))
    print(f"=== S041 Hikkake (Trend_Index={TI_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[j+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    TRs = [0, 20, 50]; TMs = [10, 20, 40]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, tr in enumerate(TRs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(tr, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"Tr{x}" for x in TRs], columns=[f"Tm{x}" for x in TMs]).to_csv("s041_sensitivity_expectancy.csv")
    print("grid expR (Trend x Time):\n" + pd.DataFrame(grid, index=[f"Tr{x}" for x in TRs], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s041_gates.csv", index=False)
