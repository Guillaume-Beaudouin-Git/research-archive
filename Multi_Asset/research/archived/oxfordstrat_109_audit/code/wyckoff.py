"""
Wyckoff Mean Reversion (#98/#99/#100) — false-breakout fade (Bull/Bear Trap).
Bear Trap (long): a fresh Pattern_Size-bar LOW (B) then a reaction high (C); buy stop at
Entry = B + (C-B)*Entry_Index when price recovers (the breakdown failed). Cancel if price
drops below B - (C-B)*Cancel_Index. Bull Trap (short) = mirror. Exits: Risk stop
(Entry -/+ range*Risk_Index), Reward limit (Entry +/- range*Reward_Index), ATR stop, time.
range = |C-B|. R = ATR(20)*6. Reuses ftmo_lab.atr/_trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
ATR_LEN = 20


def simulate_wyckoff(df, entry_index, cancel_index, *, risk_index=1.0, reward_index=2.0,
                     pattern_size=10, atr_stop=6.0, cost_bps=2.0, fill='stop', time_cap=20, side='both'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    llv = pd.Series(l, index=df.index).rolling(pattern_size).min().values
    hhv = pd.Series(h, index=df.index).rolling(pattern_size).max().values
    n = len(df); idx = df.index; trades = []
    b = pattern_size + 1
    while b < n - 2:
        # ---- bear trap (long): fresh pattern_size low at b ----
        got = 0; entry = lvl = rng = None
        if side in ('both', 'long') and np.isfinite(llv[b]) and l[b] <= llv[b] and np.isfinite(A[b]) and A[b] > 0:
            B = l[b]; C = h[b]; j = b + 1; lim = min(b + pattern_size, n - 1)
            while j <= lim:
                C = max(C, h[j]); rg = C - B
                if rg > 0:
                    if l[j] < B - rg*cancel_index: break          # cancelled (made new low)
                    elv = B + rg*entry_index
                    if h[j] >= elv:
                        got = 1; lvl = elv; rng = rg; e = j; break
                j += 1
        if got == 0 and side in ('both', 'short') and np.isfinite(hhv[b]) and h[b] >= hhv[b] and np.isfinite(A[b]) and A[b] > 0:
            T = h[b]; C = l[b]; j = b + 1; lim = min(b + pattern_size, n - 1)
            while j <= lim:
                C = min(C, l[j]); rg = T - C
                if rg > 0:
                    if h[j] > T + rg*cancel_index: break
                    elv = T - rg*entry_index
                    if l[j] <= elv:
                        got = -1; lvl = elv; rng = rg; e = j; break
                j += 1
        if got == 0:
            b += 1; continue
        d = got
        if fill == 'stop':
            entry = (max(o[e], lvl) if d == 1 else min(o[e], lvl)); start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: b += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        risk0 = A[b] * atr_stop; cost_R = (cost_bps/1e4)*abs(entry)/risk0
        rstop = entry - d*rng*risk_index; rwd = entry + d*rng*reward_index; astop = entry - d*risk0
        last = min(start_j + time_cap, n - 1); exit_p = exit_j = None
        for k in range(start_j, last + 1):
            if d == 1:
                if l[k] <= rstop: exit_p, exit_j = rstop, k; break
                if l[k] <= astop: exit_p, exit_j = astop, k; break
                if h[k] >= rwd: exit_p, exit_j = rwd, k; break
            else:
                if h[k] >= rstop: exit_p, exit_j = rstop, k; break
                if h[k] >= astop: exit_p, exit_j = astop, k; break
                if l[k] <= rwd: exit_p, exit_j = rwd, k; break
            if k == last: exit_p, exit_j = c[k], k; break
        if exit_p is None: exit_j = last; exit_p = c[last]
        trades.append(lab._trade(idx[e], idx[exit_j], 'x', d, d*(exit_p-entry)/risk0 - cost_R, exit_j-e))
        b = exit_j + 1
    return pd.DataFrame(trades)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
