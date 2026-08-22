"""
Shared engine for the Price-Breakout-with-NR7 pair (#67 Setup&Exit, #68 Setup&Entry).
Connors/Raschke entry on a Crabel NR7 setup:
  Setup day s: NR(NR_Length) = today's range < each of the prior NR_Length days' ranges.
  Next day i=s+1: buy stop at UpperChannel(CL)[i-1] (highest high over CL ending yesterday),
                  sell stop at LowerChannel(CL)[i-1] (lowest low over CL). 1st touched = position.
  Exit: Time N at close + ATR stop (ATR*atr_stop). Both stops same day -> loser (spec).
Identical intrabar-STOP fill family as NR7-ORB (#56) -> Gate1 fill check is the discriminator.
#67: Channel_Length=1 (prev day H/L), sweep NR_Length x N. #68: N=10, sweep Channel_Length x NR_Length.
Reuses ftmo_lab.atr/_trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN = 20


def nr_setup(df, nr_len):
    """True on day i if range[i] strictly < each of the prior nr_len daily ranges."""
    rng = (df['high'] - df['low'])
    out = pd.Series(True, index=df.index)
    for k in range(1, nr_len + 1):
        out &= rng < rng.shift(k)
    out.iloc[:nr_len] = False
    return out


def simulate_pricebreak(df, setup, channel_len, time_index, *, atr_stop=6.0,
                        cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    uc = pd.Series(h, index=df.index).rolling(channel_len).max().values   # highest high incl. today
    lc = pd.Series(l, index=df.index).rolling(channel_len).min().values   # lowest low incl. today
    su = setup.values.astype(bool); n = len(df); idx = df.index; trades = []; i = 1
    while i < n - 1:
        if not (su[i - 1] and np.isfinite(A[i]) and A[i] > 0
                and np.isfinite(uc[i - 1]) and np.isfinite(lc[i - 1])):
            i += 1; continue
        e = i
        buy, sell = uc[i - 1], lc[i - 1]            # channel of yesterday
        long_hit = h[e] >= buy
        short_hit = l[e] <= sell
        risk0 = A[e] * atr_stop
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if long_hit and short_hit:                  # both -> loser (spec), risk in R
            trades.append(lab._trade(idx[e], idx[e], 'both', 0, -(buy - sell) / risk0 - cost_R, 0))
            i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1
        lvl = buy if d == 1 else sell
        if fill == 'stop':       entry = max(o[e], lvl) if d == 1 else min(o[e], lvl); start_j = e
        elif fill == 'close':    entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else: raise ValueError(fill)
        stop = entry - d * risk0
        last = min(e + time_index, n - 1); exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None: exit_j = last; exit_p, reason = c[last], 'eod'
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, d * (exit_p - entry) / risk0 - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
