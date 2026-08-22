"""
Shared engine for the ORBP family (#63 counter-trend, #64 momentum filter,
#65 price-channel filter): a Crabel Opening-Range-Breakout STOP entry that is
restricted to ONE side per day by a directional `filter`.

Entry is identical to ftmo_lab.simulate_bracket (buy stop Open+Stretch / sell
stop Open-Stretch) but only the *allowed* side is armed on each day:
    side[i-1] = +1  -> long-only that day  (arm buy stop)
    side[i-1] = -1  -> short-only that day (arm sell stop)
    side[i-1] =  0  -> stand aside
`side[i-1]` is the regime computed with information up to & incl. bar i-1, and
the trade is taken on bar i -> NO look-ahead (same indexing as simulate_bracket).

Exit mirrors simulate_bracket: ATR stop (Entry -/+ ATR*atr_stop), time exit at
the close of the n-th bar, and an OPTIONAL target (target_index in R). The ORBP
fiches use Time + ATR only, so target_index defaults to None (disabled).

`fill` is the SAME L26 lever consumed by gate_delay1:
    'stop'      OPTIMISTIC intra-bar fill at the breakout level
    'close'     fill at the breakout-bar close
    'next_open' realistic delay+1 fill at the next bar's open
Reuses ftmo_lab.atr / _trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab


def simulate_orb_filtered(df, side, stretch, *, time_index, atr_len=20,
                          atr_stop=6.0, cost_bps=2.0, fill='stop',
                          target_index=None):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    sd = side.reindex(df.index).values
    st = stretch.reindex(df.index).values
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        s = sd[i - 1]
        if not (s == 1 or s == -1) or not (np.isfinite(st[i - 1]) and st[i - 1] > 0) \
           or not np.isfinite(A[i]):
            i += 1; continue
        e = i
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        if s == 1:
            lvl = o[e] + st[i - 1]
            if not (h[e] >= lvl):          # long stop not touched
                i += 1; continue
        else:
            lvl = o[e] - st[i - 1]
            if not (l[e] <= lvl):          # short stop not touched
                i += 1; continue
        d = int(s)
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        # ---- entry fill (L26 lever) ----
        if fill == 'stop':
            entry = max(o[e], lvl) if d == 1 else min(o[e], lvl); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1:
                i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        stop = entry - d * risk0
        tgt = entry + d * target_index * risk0 if target_index is not None else None
        last = min(e + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= stop:                 exit_p, reason, exit_j = stop, 'stop', j; break
                if tgt is not None and h[j] >= tgt: exit_p, reason, exit_j = tgt, 'target', j; break
            else:
                if h[j] >= stop:                 exit_p, reason, exit_j = stop, 'stop', j; break
                if tgt is not None and l[j] <= tgt: exit_p, reason, exit_j = tgt, 'target', j; break
            if j == last:
                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)


def crabel_stretch(df, length=10, mult=2.0):
    """Symmetric Crabel noise: SMA(min(H-O, O-L), length) * mult."""
    o, h, l = df['open'], df['high'], df['low']
    noise = np.minimum(h - o, o - l)
    return (pd.Series(noise, index=df.index).rolling(length).mean() * mult).clip(lower=0)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
