"""Shared helpers for entry@open trend-state strategies (Keltner / LR-slope / HMA families).
A 'state' system: desired position want_long/want_short (known at close i), acted at open[i+1];
hold while the desired sign persists, exit@open on flip/flat or ATR*6 stop. Reuses ftmo_lab (unchanged)."""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0

def simulate_state(df, wl, ws, *, atr_stop=ATR_STOP, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    WL = wl.values.astype(bool); WS = ws.values.astype(bool)
    n = len(df); idx = df.index; trades = []; i = 1
    while i < n - 1:
        d = 1 if WL[i - 1] else (-1 if WS[i - 1] else 0)
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        if fill == 'stop':      eb = i;     entry = o[eb]
        elif fill == 'close':   eb = i;     entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; exit_p = exit_j = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, exit_j = stop, j; break
            if d == -1 and h[j] >= stop: exit_p, exit_j = stop, j; break
            dj = 1 if WL[j] else (-1 if WS[j] else 0)        # desired state at close j
            if dj != d:                                       # signal left our direction -> exit next open
                ej = j + 1
                if ej <= n - 1: exit_p, exit_j = o[ej], ej
                else: exit_p, exit_j = c[j], j
                break
            if j == n - 1: exit_p, exit_j = c[j], j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

def run_state(uni, costs, sigfunc, fill='stop'):
    frames = []
    for t, df in uni.items():
        wl, ws = sigfunc(df)
        tr = simulate_state(df, wl, ws, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

# ---- indicators ----
def lrs(close, lb):
    """Linear-regression slope over lb (vectorised; x=0..lb-1)."""
    lb = int(lb); c = np.asarray(close, float); n = len(c)
    sx = lb * (lb - 1) / 2.0; sxx = (lb - 1) * lb * (2 * lb - 1) / 6.0
    denom = lb * sxx - sx * sx
    w = np.arange(lb)
    sy = pd.Series(c).rolling(lb).sum().values
    sxy = np.convolve(c, w[::-1], mode='full')[lb - 1:n]      # sum_{k} w[k]*c[i-lb+1+k]
    sxy = np.concatenate([np.full(lb - 1, np.nan), sxy[:n - lb + 1]])
    return (lb * sxy - sx * sy) / denom

def keltner_regime(df, look_back, rm):
    h, l, c = df['high'].values, df['low'].values, df['close'].values
    tp = (h + l + c) / 3.0; rng = h - l
    matp = pd.Series(tp).rolling(look_back).mean().values
    marng = pd.Series(rng).rolling(look_back).mean().values
    buy = matp + marng * rm; sell = matp - marng * rm
    n = len(c); reg = np.zeros(n, np.int8); st = 0
    for i in range(n):
        if np.isfinite(buy[i]):
            if c[i] > buy[i]: st = 1
            elif c[i] < sell[i]: st = -1
        reg[i] = st
    return reg, buy, sell
