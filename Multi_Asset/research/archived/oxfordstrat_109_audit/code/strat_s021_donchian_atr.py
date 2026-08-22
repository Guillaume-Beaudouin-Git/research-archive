"""
Strategy 21/109 — Donchian Channel (Entry & Exit 2). Source rating C. (Richard D. Donchian)
https://oxfordstrat.com/trading-strategies/donchian-channel-2/

SAME channel-breakout entry as #20 (S020), but the EXIT differs:
  Entry : Long = buy stop above UpperChannel[i-1] ; Short = sell stop below LowerChannel[i-1].
  Exit  : ATR Exit = fixed stop at [Entry -/+ ATR(20)*ATR_Index]  (ATR_Index swept [1.0,6.0]).
          (Stop Loss Exit ATR_Stop=6 only normalises risk/position size.) NO target, NO time exit.
  Sweep : Channel_Length [2,100] x ATR_Index [1.0,6.0].

-> HERITAGE of the channel-breakout-trend cluster {#6, #7, #20}. Same entry => Gate 1 PASS
   expected (real breakout, not an ORB fill artefact); trend-follower => Gate 2 long-beta expected.
   Reuses ftmo_lab v2-gates (atr/_trade/cost/gates), cached run_point for speed.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
CL_REP, AIX_REP = 20, 3.0           # canonical Turtle channel=20 ; representative ATR exit = 3*ATR

def simulate_donchian_atr(df, channel_len, atr_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                          cost_bps=2.0, allow_short=True, fill='stop'):
    """Channel-breakout stop entry, fixed ATR exit (Entry -/+ ATR*ATR_Index), no target/time.
       R denominator = ATR*ATR_Stop (sizing). fill = L26 lever ('stop'/'next_open'/'close')."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    up = pd.Series(h, index=df.index).rolling(channel_len).max().shift(1).values
    dn = pd.Series(l, index=df.index).rolling(channel_len).min().shift(1).values
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(up[i]) and np.isfinite(dn[i]) and np.isfinite(A[i])):
            i += 1; continue
        e = i; buy, sell = up[e], dn[e]
        long_hit = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
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
            entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        exit_stop = entry - d * A[e] * atr_index          # the (binding) ATR Exit, fixed from entry
        # vectorised first-touch of the fixed stop (no target/time exit) -> else EOD
        cond = (l[start_j:] <= exit_stop) if d == 1 else (h[start_j:] >= exit_stop)
        if cond.any():
            exit_j = start_j + int(np.argmax(cond)); exit_p, reason = exit_stop, 'atr_exit'
        else:
            exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

@lru_cache(maxsize=None)
def run_point(channel_len, atr_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_donchian_atr(df, channel_len, atr_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(CL_REP, AIX_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(CL_REP, AIX_REP, fill='next_open'))
    print(f"=== S021 Donchian Channel (E&E2, Channel={CL_REP} ATR_Index={AIX_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    CLs = [20, 40, 80]; AIXs = [1.5, 3.0, 5.0]
    grid = np.full((len(CLs), len(AIXs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, cl in enumerate(CLs):
        for bb, ax in enumerate(AIXs):
            m = lab.trade_metrics(run_point(cl, ax)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"C{x}" for x in CLs], columns=[f"A{x}" for x in AIXs]).to_csv("s021_sensitivity_expectancy.csv")
    print("grid expR (Channel x ATR_Index):\n" + pd.DataFrame(grid, index=[f"C{x}" for x in CLs], columns=[f"A{x}" for x in AIXs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(CL_REP, AIX_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s021_gates.csv", index=False)
