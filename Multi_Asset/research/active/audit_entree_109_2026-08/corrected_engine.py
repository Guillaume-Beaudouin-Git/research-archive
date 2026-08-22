"""
A general-purpose, parameter-generic "corrected" bracket engine: byte-identical to
ftmo_lab.simulate_bracket (read-only import, not modified) EXCEPT that the 'both'
branch (dual-breakout same-bar ambiguity) is resolved by a fair coin-flip
(0.5*forced-long + 0.5*forced-short), continuing the SAME target/time/ATR-stop exit
logic and the SAME `fill` mode as the rest of the run, instead of the corpus's
hardcoded "assume loser" (-2*stretch/risk0 - cost_R). Used to re-run the FULL 4-gate
pipeline (Gate1 delay+1, Gate2 two-sided, Gate3 DSR, Gate4 OOS) honestly, at every
grid cell, not just the representative point.
"""
import numpy as np, pandas as pd


def _trade(t_in, t_out, reason, d, netR, hold):
    return {'entry': t_in, 'exit': t_out, 'reason': reason, 'dir': d, 'netR': netR, 'hold': hold}


def _exit_from(o, h, l, c, A, e, n, d, target_index, time_index, atr_stop, cost_bps, fill):
    risk0 = A[e] * atr_stop
    if not np.isfinite(risk0) or risk0 <= 0:
        return np.nan, e, np.nan
    cost_R = (cost_bps / 1e4) * c[e] / risk0
    buy_lvl = None
    if fill == 'stop':
        start_j = e
    elif fill == 'next_open':
        if e + 1 > n - 1:
            return np.nan, e, np.nan
        start_j = e + 1
    elif fill == 'close':
        start_j = e
    else:
        raise ValueError(fill)
    return risk0, start_j, cost_R


def simulate_bracket_corrected(df, setup, stretch, *, target_index, time_index,
                                atr_len=20, atr_stop=6.0, cost_bps=2.0, allow_short=True, fill='stop'):
    """Same signature/semantics as ftmo_lab.simulate_bracket, EXCEPT the 'both' bar
    is resolved by a fair 50/50 average of forced-long/forced-short (same `fill`
    mode), instead of the hardcoded -2R 'assume loser' penalty."""
    import ftmo_lab as lab
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []
    i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps/1e4) * c[e] / risk0

        def forced(d):
            if fill == 'stop':
                entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
            elif fill == 'next_open':
                if e + 1 > n - 1:
                    return np.nan, e
                entry = o[e + 1]; start_j = e + 1
            elif fill == 'close':
                entry = c[e]; start_j = e
            else:
                raise ValueError(fill)
            stop = entry - d * risk0
            tgt = entry + d * target_index * risk0
            last = min(e + time_index, n - 1)
            exit_p = None; exit_j = last
            for j in range(start_j, last + 1):
                if d == 1:
                    if l[j] <= stop: exit_p = stop; exit_j = j; break
                    if h[j] >= tgt: exit_p = tgt; exit_j = j; break
                else:
                    if h[j] >= stop: exit_p = stop; exit_j = j; break
                    if l[j] <= tgt: exit_p = tgt; exit_j = j; break
                if j == last:
                    exit_p = c[j]; exit_j = j; break
            if exit_p is None:
                exit_p = c[last]; exit_j = last
            grossR = d * (exit_p - entry) / risk0
            return grossR - cost_R, exit_j

        if long_hit and short_hit:
            long_R, long_j = forced(1)
            short_R, short_j = forced(-1)
            if np.isfinite(long_R) and np.isfinite(short_R):
                unbiased_R = 0.5 * (long_R + short_R)
            else:
                unbiased_R = -2*st[i-1]/risk0 - cost_R  # fallback: fill='next_open' ran off the end of data
            trades.append(_trade(idx[e], idx[e], 'both_corrected', 0, unbiased_R, 0))
            i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1

        if fill == 'stop':
            entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1:
                i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(f"unknown fill mode: {fill}")
        stop = entry - d * risk0
        tgt = entry + d * target_index * risk0
        last = min(e + time_index, n - 1)
        exit_p, exit_j, reason = None, None, None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= stop: exit_p, reason, exit_j = stop, 'stop', j; break
                if h[j] >= tgt: exit_p, reason, exit_j = tgt, 'target', j; break
            else:
                if h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
                if l[j] <= tgt: exit_p, reason, exit_j = tgt, 'target', j; break
            if j == last:
                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(_trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)
