"""
Strategy 20/109 — Donchian Channel (Entry & Exit 1). Source rating C. (Richard D. Donchian)
https://oxfordstrat.com/trading-strategies/donchian-channel-1/

Canonical Donchian CHANNEL BREAKOUT (no filter):
  UpperChannel(L) = highest high over L ; LowerChannel(L) = lowest low over L.
  Entry  : Long  = buy stop one tick above UpperChannel[i-1] ; Short = sell stop below LowerChannel[i-1].
  Exit   : %-Target at close  (Long: Close >= Entry*(1+T/100) ; Short: Close <= Entry*(1-T/100))
           + ATR stop          (Entry -/+ ATR(20)*6).  NO time exit.
  Sweep  : Channel_Length [2,100] x Target_Exit% [2,100].

Same ENTRY archetype as S006/S011 (channel-breakout stop = real momentum trigger, NOT an ORB
fill artefact -> Gate 1 expected PASS), but this is the *canonical* Donchian with a %-target exit
and NO ADX filter -> fair test at the Turtle-canonical Channel=20. Trend-follower => Gate 2
(long-beta) is the expected failure mode. Reuses ftmo_lab v2-gates (atr/_trade/cost/gates).
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
CL_REP, TG_REP = 20, 20.0          # canonical Turtle channel=20 ; representative %-target=20%

def simulate_donchian_pct(df, channel_len, target_pct, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                          cost_bps=2.0, allow_short=True, fill='stop'):
    """Channel-breakout stop entry, %-target-at-close OR ATR stop. fill = L26 lever:
       'stop' = fill at channel level (optimistic) ; 'next_open' = open[i+1] ; 'close' = breakout close."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    up = pd.Series(h, index=df.index).rolling(channel_len).max().shift(1).values   # UpperChannel[i-1]
    dn = pd.Series(l, index=df.index).rolling(channel_len).min().shift(1).values   # LowerChannel[i-1]
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(up[i]) and np.isfinite(dn[i]) and np.isfinite(A[i])):
            i += 1; continue
        e = i; buy, sell = up[e], dn[e]                       # 'one tick' ~ 0 (conservative)
        long_hit = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if long_hit and short_hit:                            # whole channel engulfed (rare) -> skip
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
        stop = entry - d * risk0
        tgt = entry * (1 + d * target_pct / 100.0)
        exit_p = exit_j = reason = None
        for j in range(start_j, n):
            if d == 1:
                if l[j] <= stop: exit_p, reason, exit_j = stop, 'stop', j; break
                if c[j] >= tgt:  exit_p, reason, exit_j = c[j], 'target', j; break
            else:
                if h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
                if c[j] <= tgt:  exit_p, reason, exit_j = c[j], 'target', j; break
            if j == n - 1: exit_p, reason, exit_j = c[j], 'eod', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

@lru_cache(maxsize=None)                      # collapse identical (cl,tg,fill) runs the gates request
def run_point(channel_len, target_pct, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_donchian_pct(df, channel_len, target_pct, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(CL_REP, TG_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(CL_REP, TG_REP, fill='next_open'))
    print(f"=== S020 Donchian Channel (E&E1, Channel={CL_REP} Target={TG_REP}%) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    CLs = [20, 40, 80]; TGs = [10, 20, 40]
    grid = np.full((len(CLs), len(TGs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, cl in enumerate(CLs):
        for bb, tg in enumerate(TGs):
            m = lab.trade_metrics(run_point(cl, tg)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"C{x}" for x in CLs], columns=[f"T{x}%" for x in TGs]).to_csv("s020_sensitivity_expectancy.csv")
    print("grid expR (Channel x Target%):\n" + pd.DataFrame(grid, index=[f"C{x}" for x in CLs], columns=[f"T{x}%" for x in TGs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(CL_REP, TG_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s020_gates.csv", index=False)
