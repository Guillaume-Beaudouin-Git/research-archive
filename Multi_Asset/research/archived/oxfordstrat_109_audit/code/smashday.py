"""
Shared engine for the Smash Day cluster (#81-85, Larry Williams "failed price pattern").
A directional setup on day s (=i-1) -> next day i: stop entry at the setup day's extreme
(buy stop above High[s] for longs / sell stop below Low[s] for shorts). 1st touched = entry.
Exits: Quick stop (below min(Low[s],Low[entry]) for longs / above max(High[s],High[entry])
for shorts) | ATR stop (6*ATR) | Time. `side[s]` in {+1,-1,0} from the Type A/B/C setup
(+ trend filter). intrabar STOP entry -> gate_delay1 lever via fill. R = ATR(20,setup day)*6.
Reuses ftmo_lab.atr/_trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN = 20


def simulate_smash(df, side, time_index, *, atr_stop=6.0, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    sd = side.reindex(df.index).values
    n = len(df); idx = df.index; trades = []
    e = 2
    while e < n - 1:
        s = sd[e - 1]                       # setup decided on day e-1
        if not (s == 1 or s == -1) or not np.isfinite(A[e - 1]) or A[e - 1] <= 0:
            e += 1; continue
        d = int(s); lvl = h[e - 1] if d == 1 else l[e - 1]
        hit = (h[e] >= lvl) if d == 1 else (l[e] <= lvl)
        if not hit:
            e += 1; continue
        risk0 = A[e - 1] * atr_stop; cost_R = (cost_bps / 1e4) * abs(lvl) / risk0
        if fill == 'stop':
            entry = (max(o[e], lvl) if d == 1 else min(o[e], lvl)); start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: e += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        quick = min(l[e - 1], l[e]) if d == 1 else max(h[e - 1], h[e])
        astop = entry - d * risk0
        last = min(start_j + time_index, n - 1); exit_p = exit_j = None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= quick: exit_p, exit_j = quick, j; break
                if l[j] <= astop: exit_p, exit_j = astop, j; break
            else:
                if h[j] >= quick: exit_p, exit_j = quick, j; break
                if h[j] >= astop: exit_p, exit_j = astop, j; break
            if j == last: exit_p, exit_j = c[j], j; break
        if exit_p is None: exit_j = last; exit_p = c[last]
        trades.append(lab._trade(idx[e], idx[exit_j], 'x', d, d * (exit_p - entry) / risk0 - cost_R, exit_j - e))
        e = exit_j + 1
    return pd.DataFrame(trades)


def setup_typeA(df, trend_index):
    """Up/down day closing near the opposite extreme (weak close) + trend filter."""
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    rng = (h - l).replace(0, np.nan)
    long_s = (c > c.shift(1)) & (c <= l + 0.25 * rng) & (c > c.shift(trend_index))
    short_s = (c < c.shift(1)) & (c >= h - 0.25 * rng) & (c < c.shift(trend_index))
    return pd.Series(np.where(long_s, 1, np.where(short_s, -1, 0)), index=df.index)


def setup_typeB(df, trend_index, filt=True):
    """Close beyond the prior day's range (the 'smash') [+ trend filter]. Type C = filt False."""
    c, h, l = df['close'], df['high'], df['low']
    long_s = (c < l.shift(1)); short_s = (c > h.shift(1))
    if filt:
        long_s = long_s & (c > c.shift(trend_index)); short_s = short_s & (c < c.shift(trend_index))
    return pd.Series(np.where(long_s, 1, np.where(short_s, -1, 0)), index=df.index)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
