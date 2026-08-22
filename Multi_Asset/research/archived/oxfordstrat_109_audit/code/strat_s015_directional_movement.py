"""
Strategy 15/109 — Directional Movement (Wilder DI-cross). Source rating C.
https://oxfordstrat.com/trading-strategies/directional-movement/  -> TREND-FOLLOWING.
Entry: +DI crosses above -DI (long) / -DI above +DI (short), confirmed by price breaking the
cross-bar extreme (extreme-point rule, stop entry). Exit: opposite DI cross (at next open) or
ATR(20)*6 stop. Filter: ADXR[i-1] >= ADXR_Threshold. Sweep ADXR_Look_Back x ADXR_Threshold.
Site: "ADXR filter adds no value; DI-cross momentum performs WORSE than alternatives."

Trend clone -> HERITAGE mode. Reuses ftmo_lab v2-gates UNCHANGED.
Fills (stop-entry archetype): 'stop'=cross-bar extreme intrabar, 'next_open'=open after breakout, 'close'=close of breakout bar.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
LB_REP, THR_REP = 14, 0                                # Wilder default period; ADXR filter off (site: adds nothing)

def dmi(df, period):
    h, l, c = df['high'], df['low'], df['close']
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    pdi = 100 * pdm.ewm(alpha=1/period, adjust=False).mean() / atr
    mdi = 100 * mdm.ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi).replace(0, np.nan)
    adx = dx.ewm(alpha=1/period, adjust=False).mean()
    adxr = 0.5 * (adx + adx.shift(period - 1))
    return pdi.values, mdi.values, adxr.values

def simulate_dmi(df, pdi, mdi, adxr, *, threshold, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                 cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; n = len(df); idx = df.index
    cu = (pdi > mdi) & (np.r_[False, (pdi[:-1] <= mdi[:-1])])   # +DI cross up
    cd = (mdi > pdi) & (np.r_[False, (mdi[:-1] <= pdi[:-1])])   # -DI cross up
    trades = []; s = 1
    while s < n - 1:
        if not (np.isfinite(A[s]) and A[s] > 0 and np.isfinite(adxr[s]) and adxr[s] >= threshold):
            s += 1; continue
        d = 1 if cu[s] else (-1 if (cd[s] and allow_short) else 0)
        if d == 0: s += 1; continue
        ext = h[s] if d == 1 else l[s]                          # extreme point of the cross bar
        # confirm breakout beyond the extreme on bar s+1
        if s + 1 > n - 1: s += 1; continue
        if d == 1 and not (h[s+1] >= ext): s += 1; continue
        if d == -1 and not (l[s+1] <= ext): s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = max(o[eb], ext) if d == 1 else min(o[eb], ext)
        elif fill == 'close':     eb = s + 1; entry = c[eb]
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0
        exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            # opposite DI cross -> exit at next open
            if (d == 1 and cd[j]) or (d == -1 and cu[j]):
                ej = j + 1
                if ej <= n - 1: exit_p, reason, exit_j = o[ej], 'dicross', ej
                else: exit_p, reason, exit_j = c[j], 'dicross', j
                break
        if exit_p is None:
            exit_j = n - 1; exit_p, reason = c[n-1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_D = {}
def _dmi(t, df, lb):
    if (t, lb) not in _D: _D[(t, lb)] = dmi(df, lb)
    return _D[(t, lb)]

def run_point(adxr_lb, threshold, fill='stop'):
    frames = []
    for t, df in uni.items():
        pdi, mdi, adxr = _dmi(t, df, adxr_lb)
        tr = simulate_dmi(df, pdi, mdi, adxr, threshold=threshold, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(LB_REP, THR_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    pd.DataFrame({t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}).T.to_csv("s015_per_instrument.csv")
    print(f"=== S015 Directional Movement  ADXR_LB={LB_REP} Thr={THR_REP} (trend) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns})")
    LBs = [10, 14, 20, 30, 60]; THRs = [0, 10, 20, 30]
    grid = np.full((len(LBs), len(THRs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, lb in enumerate(LBs):
        for bb, thr in enumerate(THRs):
            m = lab.trade_metrics(run_point(lb, thr)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"T{x}" for x in THRs]).to_csv("s015_sensitivity_expectancy.csv")
    print("grid expR (ADXR_LB x Threshold):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"T{x}" for x in THRs]).round(4).to_string())
    print(f"ADXR value-add: col Thr0 mean {np.nanmean(grid[:,0]):+.4f} vs best Thr>0 mean {np.nanmean(np.nanmax(grid[:,1:],axis=1)):+.4f}")
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, THR_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k=='dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s015_gates.csv", index=False)
