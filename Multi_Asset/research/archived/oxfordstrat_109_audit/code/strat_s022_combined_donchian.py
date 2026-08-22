"""
Strategy 22/109 — Combined Donchian Channels (Entry & Exit). Source rating C. (R. D. Donchian)
https://oxfordstrat.com/trading-strategies/combined-donchian-channels/

The PROPER Turtle / dual-channel breakout (canonical Donchian):
  Entry channel  #1 (long lookback):  Long = buy stop > UpperChannelOne[i-1] ; Short = < LowerChannelOne[i-1].
  Exit channel   #2 (TRAILING, shorter): Period#2 = Channel#1 * Channel#2% .
                 Long exit = sell stop < LowerChannelTwo[i-1] (trails up) ; Short exit = > UpperChannelTwo[i-1].
  + Stop Loss Exit ATR(20)*6 (catastrophic stop + risk normalisation / R denominator). No time exit.
  Sweep : Channel#1 [5,200] bars  x  Channel#2 [5,100] % of #1.

Best-constructed of the 3 Donchian variants (real TRAILING channel exit, vs #20 %-target / #21 fixed
ATR stop). HERITAGE of the channel-breakout-trend cluster {#6,#7,#20,#21}. Same entry => Gate 1 PASS
expected; trend-follower => Gate 2 long-beta expected. Canonical point Channel#1=20 / #2=50% (Turtle 20/10).
Reuses ftmo_lab v2-gates (atr/_trade/cost/gates); vectorised trailing-exit first-touch; cached run_point.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
C1_REP, C2_REP = 20, 50              # Turtle 20-day entry / 10-day trailing exit (Period#2 = 20*50% = 10)

def _roll(s, w, fn):
    return (s.rolling(w).max() if fn == 'max' else s.rolling(w).min()).shift(1).values

def simulate_combined_donchian(df, c1, c2_pct, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                               cost_bps=2.0, allow_short=True, fill='stop'):
    """Entry on Channel#1 breakout; trailing exit on Channel#2 (=c1*c2%) opposite channel OR ATR stop.
       fill = L26 lever ('stop'/'next_open'/'close'). Vectorised first-touch of the (trailing) stop."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    p2 = max(1, int(round(c1 * c2_pct / 100.0)))
    H, L = pd.Series(h, index=df.index), pd.Series(l, index=df.index)
    up1, dn1 = _roll(H, c1, 'max'), _roll(L, c1, 'min')      # entry channel [i-1]
    up2, dn2 = _roll(H, p2, 'max'), _roll(L, p2, 'min')      # exit channel (trailing) [i-1]
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(up1[i]) and np.isfinite(dn1[i]) and np.isfinite(up2[i]) and
                np.isfinite(dn2[i]) and np.isfinite(A[i])):
            i += 1; continue
        e = i; long_hit = h[e] >= up1[e]; short_hit = (l[e] <= dn1[e]) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if long_hit and short_hit:
            i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1
        if fill == 'stop':
            entry = max(o[e], up1[e]) if d == 1 else min(o[e], dn1[e]); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        cat = entry - d * risk0                               # catastrophic ATR stop
        if d == 1:                                            # trailing exit = max(lower-channel, cat)
            stop_arr = np.maximum(dn2[start_j:], cat)
            cond = l[start_j:] <= stop_arr
        else:
            stop_arr = np.minimum(up2[start_j:], cat)
            cond = h[start_j:] >= stop_arr
        if cond.any():
            k = int(np.argmax(cond)); exit_j = start_j + k; exit_p, reason = float(stop_arr[k]), 'channel/atr'
        else:
            exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

@lru_cache(maxsize=None)
def run_point(c1, c2_pct, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_combined_donchian(df, c1, c2_pct, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(C1_REP, C2_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(C1_REP, C2_REP, fill='next_open'))
    print(f"=== S022 Combined Donchian (Turtle, Channel#1={C1_REP} #2={C2_REP}% -> exit={max(1,round(C1_REP*C2_REP/100))}d) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    C1s = [20, 50, 100]; C2s = [25, 50, 75]
    grid = np.full((len(C1s), len(C2s)), np.nan); sg = np.full_like(grid, np.nan)
    for a, c1 in enumerate(C1s):
        for bb, c2 in enumerate(C2s):
            m = lab.trade_metrics(run_point(c1, c2)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"C1={x}" for x in C1s], columns=[f"C2={x}%" for x in C2s]).to_csv("s022_sensitivity_expectancy.csv")
    print("grid expR (Channel#1 x Channel#2%):\n" + pd.DataFrame(grid, index=[f"C1={x}" for x in C1s], columns=[f"C2={x}%" for x in C2s]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(C1_REP, C2_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s022_gates.csv", index=False)
