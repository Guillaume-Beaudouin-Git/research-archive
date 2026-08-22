"""
Shared engine for the Ross Hook cluster (#76 setup, #77/#78/#79 with filter).
Joe Ross "Ross Hook" = the FIRST correction after a 1-2-3 breakout; buy stop one tick
above the hook high (long) -> trend-CONTINUATION breakout-stop entry.

Operational definition (faithful proxy):
  Long: bar i0 is a fresh Min_Setup-bar HIGH (high[i0]==max over Min_Setup & rising) =
        the leg/breakout high H*. Then a pullback forms (>=1 bar with high<H*); arm a buy
        stop at H*. If price RESUMES (high>=H*) within Max_Hook_bars -> enter long.
        Hook low = lowest low during the pullback (the quick-exit stop).
  Short = mirror (Min_Setup-bar low, pullback up, sell stop at the hook low L*).
  Optional DEPTH filter (#78/#79): hook depth (H*-hooklow) <= depth_ratio * leg size,
        leg size = H* - min(low over the Min_Setup leg). Limits over-deep hooks.
  Exits: Quick stop (hook low/high) | ATR stop (6*ATR) | Time (Time_Index).
  fill: 'stop' optimistic intrabar at H* ; 'next_open' realistic delay+1 (gate_delay1 lever).
R-normalised by risk0 = ATR(20)*ATR_Stop. Reuses ftmo_lab.atr/_trade UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN = 20


def simulate_rosshook(df, min_setup, max_hook_bars, time_index, *, depth_ratio=None,
                      atr_stop=6.0, cost_bps=2.0, fill='stop', side='both', daily=False,
                      extra_delay=0):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    n = len(df); idx = df.index; trades = []
    dmark = pd.Series(0.0, index=df.index)            # close-to-close MTM R (honest daily series)
    hh = pd.Series(h, index=df.index).rolling(min_setup).max().values
    ll = pd.Series(l, index=df.index).rolling(min_setup).min().values
    i = min_setup + 1
    while i < n - 1:
        d = 0; Hstar = hooklow = legsize = None
        # ---- long hook candidate: fresh Min_Setup high at i ----
        if side in ('both', 'long') and np.isfinite(hh[i]) and h[i] >= hh[i] and h[i] > h[i-1] and np.isfinite(A[i]) and A[i] > 0:
            Hstar = h[i]; leg_lo = ll[i]; legsize = Hstar - leg_lo
            pulled = False; lo_acc = np.inf; j = i + 1; lim = min(i + max_hook_bars, n - 1)
            while j <= lim:
                if h[j] < Hstar: pulled = True; lo_acc = min(lo_acc, l[j])
                if pulled and h[j] >= Hstar:
                    depth = Hstar - lo_acc
                    if depth_ratio is None or (legsize > 0 and depth <= depth_ratio * legsize):
                        d = 1; hooklow = lo_acc; e_detect = i; e_bar = j
                    break
                j += 1
        # ---- short hook candidate ----
        if d == 0 and side in ('both', 'short') and np.isfinite(ll[i]) and l[i] <= ll[i] and l[i] < l[i-1] and np.isfinite(A[i]) and A[i] > 0:
            Lstar = l[i]; leg_hi = hh[i]; legsize = leg_hi - Lstar
            pulled = False; hi_acc = -np.inf; j = i + 1; lim = min(i + max_hook_bars, n - 1)
            while j <= lim:
                if l[j] > Lstar: pulled = True; hi_acc = max(hi_acc, h[j])
                if pulled and l[j] <= Lstar:
                    depth = hi_acc - Lstar
                    if depth_ratio is None or (legsize > 0 and depth <= depth_ratio * legsize):
                        d = -1; hookhigh = hi_acc; e_detect = i; e_bar = j; Hstar = Lstar
                    break
                j += 1
        if d == 0:
            i += 1; continue
        # ---- entry fill (L26 lever) ----
        lvl = Hstar
        if fill == 'stop' and extra_delay == 0:
            entry = (max(o[e_bar], lvl) if d == 1 else min(o[e_bar], lvl)); start_j = e_bar
        elif fill == 'next_open' or extra_delay > 0:
            eo = e_bar + 1 + extra_delay                      # delay+1 (+extra) realistic fill
            if eo > n - 1: i += 1; continue
            entry = o[eo]; start_j = eo
        else: raise ValueError(fill)
        risk0 = A[e_detect] * atr_stop; cost_R = (cost_bps/1e4)*abs(entry)/risk0
        quick = hooklow if d == 1 else hookhigh
        astop = entry - d * risk0
        last = min(start_j + time_index, n - 1); exit_p = exit_j = None
        for k in range(start_j, last + 1):
            if d == 1:
                if l[k] <= quick: exit_p, exit_j = quick, k; break
                if l[k] <= astop: exit_p, exit_j = astop, k; break
            else:
                if h[k] >= quick: exit_p, exit_j = quick, k; break
                if h[k] >= astop: exit_p, exit_j = astop, k; break
            if k == last: exit_p, exit_j = c[k], k; break
        if exit_p is None: exit_j = last; exit_p = c[last]
        trades.append(lab._trade(idx[e_bar], idx[exit_j], 'x', d, d*(exit_p-entry)/risk0 - cost_R, exit_j-e_bar))
        if daily:
            prev = entry
            for k in range(start_j, exit_j + 1):
                px = c[k] if k < exit_j else exit_p
                dmark.iloc[k] += d * (px - prev) / risk0; prev = c[k]
            dmark.iloc[start_j] -= cost_R
        i = exit_j + 1
    return (pd.DataFrame(trades), dmark) if daily else pd.DataFrame(trades)


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))
