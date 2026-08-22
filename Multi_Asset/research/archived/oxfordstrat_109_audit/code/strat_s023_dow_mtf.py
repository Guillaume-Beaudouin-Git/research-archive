"""
Strategy 23/109 — Dow Theory - Multiple Time Frames (Entry). Source rating C. (Charles Dow)
https://oxfordstrat.com/trading-strategies/dow-theory-trend-2/

NEW archetype: DeMark pivot / swing-structure trend-following, multi-time-frame.
  Pivots (fractals, size s): supply pivot = high surrounded by s lower highs each side;
                             demand pivot = low surrounded by s higher lows each side.
  Filter (PRIMARY trend, big pivots S = s*Pivot_Index): long only if primary BULL
         (successive primary HH & HL) ; short only if primary BEAR (LL & LH).
  Entry : in primary BULL, buy stop above the most recent SECONDARY swing-high (sLH) pivot
          (resume the uptrend after a secondary pullback). Short symmetric.
  Exit  : Pattern Exit = trailing sell stop below the most recent SECONDARY swing-low (sHL) pivot
          + Stop Loss Exit ATR(20)*6 (catastrophic + risk normalisation). No time exit.
  Sweep : Pivot_Size [1,30] x Pivot_Index [1,10].

Pivot-structure trend continuation (buy strength in a confirmed uptrend) => entry-stop at a
meaningful swing level (Gate 1 PASS expected, like the channel breakouts) but long-in-uptrend
=> Gate 2 long-beta expected. Faithful build (vectorised fractals w/ causal confirmation lag).
Reuses ftmo_lab v2-gates (atr/_trade/cost/gates); cached run_point.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
PS_REP, PI_REP = 2, 3.0              # representative: secondary pivots of 2 bars, primary = 6 bars

def _confirmed_fractals(s_high, s_low, window):
    """Confirmed fractal levels, ffilled. A fractal at k (centred ±window extremum) is only KNOWN
       at k+window -> shift(window) makes it causal. Returns (swing_high_level, swing_low_level)."""
    rmax = s_high.rolling(2 * window + 1, center=True).max()
    rmin = s_low.rolling(2 * window + 1, center=True).min()
    hi = s_high.where((s_high >= rmax) & rmax.notna()).shift(window).ffill()
    lo = s_low.where((s_low <= rmin) & rmin.notna()).shift(window).ffill()
    return hi.values, lo.values

def dow_signals(df, pivot_size, pivot_index):
    s = max(1, int(pivot_size)); S = max(1, int(round(pivot_size * pivot_index)))
    H, L = df['high'], df['low']
    sh, sl = _confirmed_fractals(H, L, s)            # secondary swing levels (ffilled, causal)
    ph_c = H.where((H >= H.rolling(2 * S + 1, center=True).max())).shift(S).values   # primary high (at confirm bar)
    pl_c = L.where((L <= L.rolling(2 * S + 1, center=True).min())).shift(S).values   # primary low
    n = len(df); prim = np.zeros(n, np.int8)
    ph_prev = ph_last = pl_prev = pl_last = np.nan
    for i in range(n):
        if np.isfinite(ph_c[i]): ph_prev, ph_last = ph_last, ph_c[i]
        if np.isfinite(pl_c[i]): pl_prev, pl_last = pl_last, pl_c[i]
        if np.isfinite(ph_prev) and np.isfinite(pl_prev):
            if ph_last > ph_prev and pl_last > pl_prev: prim[i] = 1      # primary bull (HH & HL)
            elif ph_last < ph_prev and pl_last < pl_prev: prim[i] = -1   # primary bear (LL & LH)
    return sh, sl, prim

def simulate_dow(df, pivot_size, pivot_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                 cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    sh, sl, prim = dow_signals(df, pivot_size, pivot_index)
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        long_sig = prim[i] == 1 and np.isfinite(sh[i]) and h[i] >= sh[i] and h[i - 1] < sh[i]   # fresh breakout up
        short_sig = (allow_short and prim[i] == -1 and np.isfinite(sl[i]) and
                     l[i] <= sl[i] and l[i - 1] > sl[i])                                          # fresh breakout down
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
        cat = entry - d * risk0
        if d == 1:                                          # trailing pattern exit = max(swing-low, cat)
            stop_arr = np.maximum(np.where(np.isfinite(sl[start_j:]), sl[start_j:], -np.inf), cat)
            cond = l[start_j:] <= stop_arr
        else:
            stop_arr = np.minimum(np.where(np.isfinite(sh[start_j:]), sh[start_j:], np.inf), cat)
            cond = h[start_j:] >= stop_arr
        if cond.any():
            k = int(np.argmax(cond)); exit_j = start_j + k; exit_p, reason = float(stop_arr[k]), 'pattern/atr'
        else:
            exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

@lru_cache(maxsize=None)
def run_point(pivot_size, pivot_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_dow(df, pivot_size, pivot_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(PS_REP, PI_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(PS_REP, PI_REP, fill='next_open'))
    print(f"=== S023 Dow Theory MTF (Pivot_Size={PS_REP} Pivot_Index={PI_REP} -> primary {int(round(PS_REP*PI_REP))}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    PSs = [2, 3, 5]; PIs = [2.0, 3.0, 5.0]
    grid = np.full((len(PSs), len(PIs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ps in enumerate(PSs):
        for bb, pi in enumerate(PIs):
            m = lab.trade_metrics(run_point(ps, pi)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"PS{x}" for x in PSs], columns=[f"PI{x}" for x in PIs]).to_csv("s023_sensitivity_expectancy.csv")
    print("grid expR (Pivot_Size x Pivot_Index):\n" + pd.DataFrame(grid, index=[f"PS{x}" for x in PSs], columns=[f"PI{x}" for x in PIs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(PS_REP, PI_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s023_gates.csv", index=False)
