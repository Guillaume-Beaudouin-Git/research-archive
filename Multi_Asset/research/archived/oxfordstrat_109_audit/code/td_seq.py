"""
TD Sequential (DeMark, #86) — exhaustion mean-reversion. Faithful-pragmatic implementation.
  SETUP   (buy): setup_len(9) consecutive closes < close[-4] (resets if not).
  INTERSECTION : assumed satisfied (mild 'orderly decline' condition — documented simplification).
  COUNTDOWN(buy): after setup, count bars where close < low[-2]; complete at countdown_len(13).
                  Cancel if close > highest setup high.
  ENTRY (method 2, the tested one): after countdown completes, enter on the close of the first
                  bar where close > close[-4] (momentum turn up). Short = mirror.
  EXIT  : DeMark stop = pattern_low - (entry - pattern_low) (close-based) ; ATR catastrophe 6*ATR ;
          time cap. R = ATR(20)*6. Reuses ftmo_lab.atr/_trade UNCHANGED.
Simplifications vs literal TD Sequential (to audit): intersection assumed; cancellation rule (a)
[new setup during countdown] omitted; entry uses method 2 only (as in the source test).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
ATR_LEN = 20


def _signals(o, h, l, c, setup_len, sb, cd_len, cb):
    n = len(c); ev = []
    for side in (+1, -1):
        consec = 0; active = False; cd = 0; pat = None; setup_ext = None; pending = None
        for i in range(sb, n):
            cond = (c[i] < c[i - sb]) if side == 1 else (c[i] > c[i - sb])
            consec = consec + 1 if cond else 0
            if not active and pending is None and consec >= setup_len:
                active = True; st = i - setup_len + 1
                setup_ext = (h[st:i + 1].max() if side == 1 else l[st:i + 1].min())
                pat = (l[st:i + 1].min() if side == 1 else h[st:i + 1].max()); cd = 0
            if active:
                cnt = (c[i] < l[i - cb]) if side == 1 else (c[i] > h[i - cb])
                if cnt:
                    cd += 1; pat = (min(pat, l[i]) if side == 1 else max(pat, h[i]))
                cancel = (c[i] > setup_ext) if side == 1 else (c[i] < setup_ext)
                if cancel:
                    active = False
                elif cd >= cd_len:
                    active = False; pending = pat
            if pending is not None:
                turn = (c[i] > c[i - sb]) if side == 1 else (c[i] < c[i - sb])
                if turn:
                    ev.append((i, side, pending)); pending = None
    return ev


def simulate_tdseq(df, setup_len=9, cd_len=13, *, sb=4, cb=2, atr_stop=6.0, cost_bps=2.0,
                   fill='stop', time_cap=40):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; n = len(df); idx = df.index
    ev = sorted(_signals(o, h, l, c, setup_len, sb, cd_len, cb))
    trades = []; busy_until = -1
    for (i, d, pat) in ev:
        if i <= busy_until or not np.isfinite(A[i]) or A[i] <= 0:
            continue
        if fill == 'stop':
            entry = c[i]; start_j = i          # method-2 entry is ON THE CLOSE
        elif fill == 'next_open':
            if i + 1 > n - 1: continue
            entry = o[i + 1]; start_j = i + 1
        else:
            raise ValueError(fill)
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        risk_pat = abs(entry - pat)
        dem_stop = pat - risk_pat if d == 1 else pat + risk_pat   # DeMark stop level
        astop = entry - d * risk0
        last = min(start_j + time_cap, n - 1); exit_p = exit_j = None
        for j in range(start_j, last + 1):
            px = c[j]
            if d == 1 and (px < dem_stop or l[j] <= astop): exit_p, exit_j = (min(px, astop) if l[j] <= astop else px), j; break
            if d == -1 and (px > dem_stop or h[j] >= astop): exit_p, exit_j = (max(px, astop) if h[j] >= astop else px), j; break
            if j == last: exit_p, exit_j = c[j], j; break
        if exit_p is None: exit_j = last; exit_p = c[last]
        trades.append(lab._trade(idx[start_j], idx[exit_j], 'x', d, d * (exit_p - entry) / risk0 - cost_R, exit_j - start_j))
        busy_until = exit_j
    return pd.DataFrame(trades)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
