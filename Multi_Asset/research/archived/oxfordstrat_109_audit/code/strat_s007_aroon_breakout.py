"""
Strategy 7/109 — Aroon Indicator Breakout (Test: Setup). Source rating C.
https://oxfordstrat.com/trading-strategies/aroon-indicator-breakout-1/  (Tushar Chande)
Concept: trend-following oscillator. AroonUp/AroonDown measure how recently the highest high /
lowest low occurred over Aroon_Index bars (100 = today, 0 = Aroon_Index bars ago).

ARCHETYPE: setup on AroonUp[i-1]/AroonDown[i-1] -> entry MARKET-ON-OPEN at bar i (spec:
"A buy at the open after a bullish setup"). NOT an intrabar stop -> no fill artefact (like S003).
Fill mapping: 'stop'=open[s+1] native, 'next_open'=open[s+2] (Gate1 delay+1), 'close'=close[s+1].
Cost model, R-normalisation (ATR*6), metrics and the 4 gates reused from ftmo_lab v2-gates UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

TIME_INDEX, ATR_LEN, ATR_STOP = 20, 20, 6.0          # Time_Index fixed at 20 (spec)
AI_REP, MA_REP = 25, 70                               # Aroon_Index default 25 (spec); Min_Aroon 70 (strong trend)

def aroon_updown(df, aroon_index):
    W = aroon_index + 1
    hv, lv = df['high'].values, df['low'].values; n = len(hv)
    up = np.full(n, np.nan); dn = np.full(n, np.nan)
    if n >= W:
        swh = np.lib.stride_tricks.sliding_window_view(hv, W)
        swl = np.lib.stride_tricks.sliding_window_view(lv, W)
        ps_high = swh[:, ::-1].argmax(axis=1).astype(float)   # periods since most-recent highest high
        ps_low = swl[:, ::-1].argmin(axis=1).astype(float)    # periods since most-recent lowest low
        up[W-1:] = 100.0 * (aroon_index - ps_high) / aroon_index
        dn[W-1:] = 100.0 * (aroon_index - ps_low) / aroon_index
    return up, dn

def aroon_dir(df, aroon_index, min_aroon):
    up, dn = aroon_updown(df, aroon_index)
    long_sig = (up > dn) & (up >= min_aroon)
    short_sig = (dn > up) & (dn >= min_aroon)
    return np.where(long_sig, 1, np.where(short_sig, -1, 0))

def simulate_aroon(df, dir_sig, *, time_index=TIME_INDEX, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                   cost_bps=2.0, allow_short=True, fill='stop'):
    """Entry market-on-open after the Aroon setup; exits = Time(20) or ATR stop (no target).
    One position at a time, re-enter after exit. `fill` shifts the entry bar (archetype open)."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    ds = dir_sig; n = len(df); idx = df.index
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
        s = exit_j                                          # re-enter after exit (trend participation)
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_AR = {}
def _updown(t, df, ai):
    if (t, ai) not in _AR: _AR[(t, ai)] = aroon_updown(df, ai)
    return _AR[(t, ai)]

def run_point(aroon_index, min_aroon, fill='stop'):
    frames = []
    for t, df in uni.items():
        up, dn = _updown(t, df, aroon_index)
        ds = np.where((up > dn) & (up >= min_aroon), 1, np.where((dn > up) & (dn >= min_aroon), -1, 0))
        tr = simulate_aroon(df, ds, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    print(f"Universe: {len(uni)} | {lab.PIPELINE_VERSION} | Aroon breakout (entry@open, Time=20)\n")
    pool = run_point(AI_REP, MA_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s007_per_instrument.csv")
    el, es, nl, ns = two_sided(pool)
    print(f"=== Representative  Aroon_Index={AI_REP}  Min_Aroon={MA_REP} (Time=20) ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns}) | instruments expR>0: {(perdf['expR']>0).sum()}/{len(perdf)}")

    AIs = [10, 25, 50, 75, 100, 150, 200]; MAs = [30, 50, 70, 80, 90, 100]
    grid = np.full((len(AIs), len(MAs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, ai in enumerate(AIs):
        for b, ma in enumerate(MAs):
            m = lab.trade_metrics(run_point(ai, ma)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"AI{x}" for x in AIs], columns=[f"MA{x}" for x in MAs]).to_csv("s007_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), Aroon_Index x Min_Aroon ===")
    print(pd.DataFrame(grid, index=[f"AI{x}" for x in AIs], columns=[f"MA{x}" for x in MAs]).round(4).to_string())
    best = np.unravel_index(np.nanargmax(grid), grid.shape)
    print(f"Share positive: {np.mean(grid>0)*100:.0f}% | best AI={AIs[best[0]]} MinAroon={MAs[best[1]]} expR={grid[best]:+.4f}")

    res = lab.run_gates(lambda fill='stop': run_point(AI_REP, MA_REP, fill=fill), sharpe_grid, split='2015-12-31')
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
                  for x in res['gates']]).to_csv("s007_gates.csv", index=False)
    bp = run_point(AIs[best[0]], MAs[best[1]]); el2, es2, nl2, ns2 = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable AI={AIs[best[0]]} MinAroon={MAs[best[1]]}] expR={mb['expR']:+.4f} Sharpe={mb['sharpe']:+.2f} | "
          f"two-sided long {el2:+.4f}(n{nl2})/short {es2:+.4f}(n{ns2})")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(MAs))); ax.set_xticklabels([f"{x}" for x in MAs])
    ax.set_yticks(range(len(AIs))); ax.set_yticklabels([f"AI{x}" for x in AIs])
    ax.set_xlabel("Min_Aroon (trend-strength threshold, %)"); ax.set_ylabel("Aroon_Index (lookback, bars)")
    ax.set_title("Strategy 7 — Aroon breakout (entry@open, Time=20)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(AIs)):
        for b in range(len(MAs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s007_sensitivity.png", dpi=130)
    print("\nSaved: s007_sensitivity.png, s007_per_instrument.csv, s007_sensitivity_expectancy.csv, s007_gates.csv")
