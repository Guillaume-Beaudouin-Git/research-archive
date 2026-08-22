"""
Shared engine for Turtle Soup (#89/#90, Connors/Raschke) — a FALSE-BREAKOUT FADE that
trades AGAINST the Turtle 20-bar breakout (mean-reversion).
Long setup at bar s: new Channel_#1 low (low[s] < prior channel low) whose close is at/below
the prior breakout level, and the prior low was set >=3 bars earlier. Next bar: buy stop at
the OLD breakout level (prior channel low) -> if price reclaims it, the breakdown failed -> long.
Short = mirror. Exits: quick stop (below Low[entry-1]) | Channel_#2 trailing | ATR stop | time.
intrabar STOP entry -> gate_delay1 lever. R = ATR(20)*6. Reuses ftmo_lab.atr/_trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
ATR_LEN = 20


def simulate_turtlesoup(df, ch1, ch2, *, atr_stop=6.0, cost_bps=2.0, fill='stop', time_cap=40):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    ll = pd.Series(l, index=df.index).rolling(ch1).min().values
    hh = pd.Series(h, index=df.index).rolling(ch1).max().values
    lle = pd.Series(l, index=df.index).rolling(ch2).min().values
    hhe = pd.Series(h, index=df.index).rolling(ch2).max().values
    n = len(df); idx = df.index; trades = []
    e = ch1 + 5
    while e < n - 1:
        s = e - 1                                   # setup bar (day before entry)
        d = 0; lvl = None
        prev_ll = ll[s - 1]; prev_hh = hh[s - 1]
        if np.isfinite(prev_ll) and l[s] < prev_ll and c[s] <= prev_ll and prev_ll == ll[s - 4] and np.isfinite(A[s]):
            d = 1; lvl = prev_ll                     # failed downside breakout -> fade long
        elif np.isfinite(prev_hh) and h[s] > prev_hh and c[s] >= prev_hh and prev_hh == hh[s - 4] and np.isfinite(A[s]):
            d = -1; lvl = prev_hh
        if d == 0 or not (A[s] > 0):
            e += 1; continue
        hit = (h[e] >= lvl) if d == 1 else (l[e] <= lvl)
        if not hit:
            e += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(lvl) / risk0
        if fill == 'stop':
            entry = (max(o[e], lvl) if d == 1 else min(o[e], lvl)); start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: e += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        quick = l[e - 1] if d == 1 else h[e - 1]
        astop = entry - d * risk0
        last = min(start_j + time_cap, n - 1); exit_p = exit_j = None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= quick: exit_p, exit_j = quick, j; break
                if l[j] <= astop: exit_p, exit_j = astop, j; break
                if j > start_j and np.isfinite(lle[j - 1]) and l[j] <= lle[j - 1]: exit_p, exit_j = lle[j - 1], j; break
            else:
                if h[j] >= quick: exit_p, exit_j = quick, j; break
                if h[j] >= astop: exit_p, exit_j = astop, j; break
                if j > start_j and np.isfinite(hhe[j - 1]) and h[j] >= hhe[j - 1]: exit_p, exit_j = hhe[j - 1], j; break
            if j == last: exit_p, exit_j = c[j], j; break
        if exit_p is None: exit_j = last; exit_p = c[last]
        trades.append(lab._trade(idx[e], idx[exit_j], 'x', d, d * (exit_p - entry) / risk0 - cost_R, exit_j - e))
        e = exit_j + 1
    return pd.DataFrame(trades)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
