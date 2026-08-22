"""Corrected version of strat_s002's simulate_setupexit (own exit rule: ATR-stop OR
Stretch-band exit OR time, no target), same fair-coin-flip resolution for 'both'."""
import numpy as np, pandas as pd


def simulate_setupexit_corrected(df, setup, stretch, *, time_index, atr_len=20, atr_stop=6.0,
                                  cost_bps=2.0, allow_short=True, fill='stop'):
    import ftmo_lab as lab
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit, short_hit = h[e] >= buy, (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0

        def forced(d):
            if fill == 'stop':
                entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
            elif fill == 'next_open':
                if e + 1 > n - 1: return np.nan
                entry = o[e + 1]; start_j = e + 1
            elif fill == 'close':
                entry = c[e]; start_j = e
            else:
                raise ValueError(fill)
            atr_lvl = entry - d * risk0
            str_lvl = o[e] - d * st[i-1]
            stop_lvl = max(atr_lvl, str_lvl) if d == 1 else min(atr_lvl, str_lvl)
            last = min(e + time_index, n - 1)
            exit_p = None
            for j in range(start_j, last + 1):
                if d == 1 and l[j] <= stop_lvl: exit_p = stop_lvl; break
                if d == -1 and h[j] >= stop_lvl: exit_p = stop_lvl; break
                if j == last: exit_p = c[j]; break
            if exit_p is None: exit_p = c[last]
            return d * (exit_p - entry) / risk0 - cost_R

        if long_hit and short_hit:
            lr, sr = forced(1), forced(-1)
            unbiased_R = 0.5*(lr+sr) if (np.isfinite(lr) and np.isfinite(sr)) else -2*st[i-1]/risk0 - cost_R
            trades.append(dict(entry=idx[e], exit=idx[e], reason='both_corrected', dir=0,
                               netR=unbiased_R, hold=0)); i = e + 1; continue
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
        atr_lvl = entry - d * risk0
        str_lvl = o[e] - d * st[i-1]
        stop_lvl = max(atr_lvl, str_lvl) if d == 1 else min(atr_lvl, str_lvl)
        last = min(e + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1 and l[j] <= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[e], exit=idx[exit_j], reason=reason, dir=d,
                           netR=grossR - cost_R, hold=exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)
