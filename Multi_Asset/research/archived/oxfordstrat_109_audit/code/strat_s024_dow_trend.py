"""
Strategy 24/109 — Dow Theory - Trend (Entry & Exit). Source rating C. (Charles Dow)
https://oxfordstrat.com/trading-strategies/dow-theory-trend/

BASE CASE of #23 (the MTF #23 benchmarks against this). DeMark pivots, BUT:
  Filter : N/A (no primary/multi-time-frame trend filter -> trades both directions on secondary swings).
  Entry  : Long = buy stop above the lowest-high (supply) pivot ; Short = sell stop below highest-low (demand) pivot.
  Exit   : TIME exit (Time_Index days at close) + ATR(20)*6 stop. (No trailing pattern exit.)
  Sweep  : Pivot_Size [1,40] x Time_Index [1,141].

HERITAGE of the pivot/Dow archetype (S023). Reuses S023 fractal engine. Same entry-stop at a swing
level => Gate 1 PASS expected; symmetric swing breakout but on an up-drifting universe => Gate 2
long-beta likely. ftmo_lab v2-gates inchangé; cached run_point.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab
import strat_s023_dow_mtf as s23

ATR_LEN, ATR_STOP = 20, 6.0
PS_REP, TM_REP = 3, 21              # representative: pivots of 3 bars, ~21-day time exit

def simulate_dow_base(df, pivot_size, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    s = max(1, int(pivot_size))
    sh, sl = s23._confirmed_fractals(df['high'], df['low'], s)    # confirmed swing levels (causal, ffilled)
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        long_sig = np.isfinite(sh[i]) and h[i] >= sh[i] and h[i - 1] < sh[i]        # fresh breakout above swing-high
        short_sig = allow_short and np.isfinite(sl[i]) and l[i] <= sl[i] and l[i - 1] > sl[i]
        if not (long_sig or short_sig) or not np.isfinite(A[i]):
            i += 1; continue
        e = i; d = 1 if long_sig else -1
        lvl = sh[e] if d == 1 else sl[e]
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if fill == 'stop':
            entry = max(o[e], lvl) if d == 1 else min(o[e], lvl); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        stop = entry - d * risk0
        last = min(e + time_index, n - 1)
        seg = slice(start_j, last + 1)
        cond = (l[seg] <= stop) if d == 1 else (h[seg] >= stop)
        if cond.any():
            k = int(np.argmax(cond)); exit_j = start_j + k; exit_p, reason = stop, 'atr'
        else:
            exit_j = last; exit_p, reason = c[last], 'time'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

@lru_cache(maxsize=None)
def run_point(pivot_size, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_dow_base(df, pivot_size, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(PS_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(PS_REP, TM_REP, fill='next_open'))
    print(f"=== S024 Dow Theory Trend (base, Pivot_Size={PS_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    PSs = [2, 3, 5]; TMs = [6, 21, 51]
    grid = np.full((len(PSs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ps in enumerate(PSs):
        for bb, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ps, tm)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"PS{x}" for x in PSs], columns=[f"Tm{x}" for x in TMs]).to_csv("s024_sensitivity_expectancy.csv")
    print("grid expR (Pivot_Size x Time):\n" + pd.DataFrame(grid, index=[f"PS{x}" for x in PSs], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(PS_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s024_gates.csv", index=False)
