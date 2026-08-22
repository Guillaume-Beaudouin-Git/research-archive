"""
Strategy 9/109 — Aroon Indicator Breakout (Test: Setup 2 & Exit). Source rating C. (Chande)
https://oxfordstrat.com/trading-strategies/aroon-indicator-breakout-3/

Relation to S007/S008: SAME base (Aroon, entry market-on-open, Time+ATR exit). DISTINCT ANGLE:
Aroon_Index is FIXED at 100 (a SLOW lookback — exactly the region where S007/S008 turned positive),
and the swept axes are Min_Aroon x Time_Index. This is "the slow Aroon trend-follower".

ARCHETYPE: entry MARKET-ON-OPEN (no intrabar stop) -> no fill artefact.
Fill mapping: 'stop'=open[s+1] native, 'next_open'=open[s+2] (Gate1), 'close'=close[s+1].
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

AROON_INDEX, ATR_LEN, ATR_STOP = 100, 20, 6.0        # Aroon_Index fixed at 100 (slow)
MA_REP, TM_REP = 50, 20                               # representative: moderate threshold, mid hold

def aroon_updown(df, aroon_index):
    W = aroon_index + 1; hv, lv = df['high'].values, df['low'].values; n = len(hv)
    up = np.full(n, np.nan); dn = np.full(n, np.nan)
    if n >= W:
        swh = np.lib.stride_tricks.sliding_window_view(hv, W)
        swl = np.lib.stride_tricks.sliding_window_view(lv, W)
        up[W-1:] = 100.0 * (aroon_index - swh[:, ::-1].argmax(axis=1)) / aroon_index
        dn[W-1:] = 100.0 * (aroon_index - swl[:, ::-1].argmin(axis=1)) / aroon_index
    return up, dn

def simulate_aroon(df, dir_sig, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                   cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig; n = len(df); idx = df.index
    trades = []; s = 1
    while s < n - 1:
        d = ds[s]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[s]) or A[s] <= 0:
            s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = o[eb] if eb <= n-1 else np.nan
        elif fill == 'close':     eb = s + 1; entry = c[eb] if eb <= n-1 else np.nan
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; last = min(eb + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j == last:                exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_AR = {t: aroon_updown(df, AROON_INDEX) for t, df in uni.items()}   # Aroon_Index fixed -> compute once

def run_point(min_aroon, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        up, dn = _AR[t]
        ds = np.where((up > dn) & (up >= min_aroon), 1, np.where((dn > up) & (dn >= min_aroon), -1, 0))
        tr = simulate_aroon(df, ds, time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    print(f"Universe: {len(uni)} | {lab.PIPELINE_VERSION} | Aroon slow (Aroon_Index=100, entry@open)\n")
    pool = run_point(MA_REP, TM_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s009_per_instrument.csv")
    el, es, nl, ns = two_sided(pool)
    print(f"=== Representative  Aroon_Index=100  Min_Aroon={MA_REP}  Time_Index={TM_REP} ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns}) | instruments expR>0: {(perdf['expR']>0).sum()}/{len(perdf)}")

    MAs = [30, 50, 70, 90, 100]; TMs = [1, 10, 20, 40]
    grid = np.full((len(MAs), len(TMs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, ma in enumerate(MAs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ma, tm)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"MA{x}" for x in MAs], columns=[f"T{x}" for x in TMs]).to_csv("s009_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), Min_Aroon x Time_Index ===")
    print(pd.DataFrame(grid, index=[f"MA{x}" for x in MAs], columns=[f"T{x}" for x in TMs]).round(4).to_string())
    best = np.unravel_index(np.nanargmax(grid), grid.shape)
    print(f"Share positive: {np.mean(grid>0)*100:.0f}% | best MinAroon={MAs[best[0]]} Time={TMs[best[1]]} expR={grid[best]:+.4f}")

    res = lab.run_gates(lambda fill='stop': run_point(MA_REP, TM_REP, fill=fill), sharpe_grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 72)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("  [archetype entry@open: Gate1 'stop'=open[s+1] native, 'next_open'=open[s+2]]")
    print("=" * 72)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  natif(open s+1) Sharpe={d1['opt_sharpe']:+.2f}"
          f" expR={d1['opt_expR']:+.4f}  ->  délai(open s+2) Sharpe={d1['real_sharpe']:+.2f}"
          f" expR={d1['real_expR']:+.4f}" + (f"  << {d1['tag']}" if d1['tag'] else ""))
    t2 = g['twosided (L25)']
    print(f"[{'PASS' if t2['pass'] else 'FAIL'}] 2. Two-sided (L25)  long expR={t2['exp_long']:+.4f}"
          f" (n={t2['n_long']}) | short expR={t2['exp_short']:+.4f} (n={t2['n_short']})"
          + (f"  << {t2['tag']}" if t2['tag'] else ""))
    d3 = g['dsr']
    print(f"[{'PASS' if d3['pass'] else 'FAIL'}] 3. DSR (N={d3['N_trials']})  SR_obs={d3['SR_obs']:.3f}"
          f" vs E[max bruit]={d3['E_max_SR']:.3f}  DSR_z={d3['DSR_z']:.1f}" + (f"  << {d3['tag']}" if d3['tag'] else ""))
    o4 = g['oos (L31)']
    print(f"[{'PASS' if o4['pass'] else 'FAIL'}] 4. OOS (L31)  train expR={o4['train_expR']:+.4f}"
          f" (Sh {o4['train_sharpe']:+.2f}) -> test expR={o4['test_expR']:+.4f} (Sh {o4['test_sharpe']:+.2f})"
          + (f"  << {o4['tag']}" if o4['tag'] else ""))
    print("-" * 72)
    print(f"Edge positif après coûts : {res['edge_positive']}   |   gates FAIL : {res['n_fail']}/4")
    print(f">>> VERDICT FINAL : {res['verdict']}   ({res['reason']})")
    print("=" * 72)
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''}
                  for x in res['gates']]).to_csv("s009_gates.csv", index=False)
    bp = run_point(MAs[best[0]], TMs[best[1]]); el2, es2, nl2, ns2 = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable MinAroon={MAs[best[0]]} Time={TMs[best[1]]}] expR={mb['expR']:+.4f} Sharpe={mb['sharpe']:+.2f} | "
          f"two-sided long {el2:+.4f}(n{nl2})/short {es2:+.4f}(n{ns2})")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TMs))); ax.set_xticklabels([f"{x}d" for x in TMs])
    ax.set_yticks(range(len(MAs))); ax.set_yticklabels([f"MA{x}" for x in MAs])
    ax.set_xlabel("Time exit (days held)"); ax.set_ylabel("Min_Aroon (threshold, %)")
    ax.set_title("Strategy 9 — Aroon slow (Aroon_Index=100, entry@open)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(MAs)):
        for b in range(len(TMs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s009_sensitivity.png", dpi=130)
    print("\nSaved: s009_sensitivity.png, s009_per_instrument.csv, s009_sensitivity_expectancy.csv, s009_gates.csv")
