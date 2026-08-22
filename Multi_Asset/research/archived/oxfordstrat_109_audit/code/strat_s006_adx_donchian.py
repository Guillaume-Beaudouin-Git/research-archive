"""
Strategy 6/109 — ADX Filter on Donchian breakout (Test 1: Filter Threshold & Entry).
Source: https://oxfordstrat.com/trading-strategies/adx/  (rating D)
Concept: Donchian channel breakout (trend-following) with an ADX trend-strength filter.
Site summary: "The ADX does not add value to the base case trend-following model."

ARCHETYPE: STOP-entry intrabar (buy stop at the prior N-bar channel high) — same family as the
S001/S002 ORB. BUT the position is held for a long time (trailing channel exit + ATR stop), so
the entry-fill artefact is DILUTED across the trade (unlike the very short-term ORB). Gate 1 will
adjudicate honestly.

Fill mapping (stop-entry archetype, like S001/S002): the L26 lever shifts the ENTRY price.
    'stop'      -> NATIVE: fill at the channel breakout level intrabar (optimistic)
    'next_open' -> realistic: open[i+1]
    'close'     -> realistic: close[i] (breakout bar close)
Exits (channel + ATR) are protective stops -> filling at the stop level is realistic/conservative.
Cost model, R-normalisation (ATR*6), metrics and the 4 gates reused from ftmo_lab v2-gates UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

ADX_LEN, ATR_LEN, ATR_STOP = 14, 20, 6.0
EC_REP, ADX_REP = 20, 0                          # base case: 20-bar Donchian, ADX filter OFF (site: ADX adds nothing)

def compute_adx(df, period=ADX_LEN):
    h, l, c = df['high'], df['low'], df['close']
    up, dn = h.diff(), -l.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr = tr.ewm(alpha=1/period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    return dx.ewm(alpha=1/period, adjust=False).mean()

def _precompute(df, entry_channel):
    ec = max(1, int(round(entry_channel * 0.5)))            # Exit_Channel = 50% of Entry_Channel
    u1 = df['high'].rolling(entry_channel).max().shift(1)
    l1 = df['low'].rolling(entry_channel).min().shift(1)
    u2 = df['high'].rolling(ec).max().shift(1)
    l2 = df['low'].rolling(ec).min().shift(1)
    adx_prev = compute_adx(df).shift(1)
    return u1.values, l1.values, u2.values, l2.values, adx_prev.values

def simulate_donchian(df, pc, *, adx_threshold, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    """Donchian breakout: enter on channel break (stop) when ADX>=threshold; exit on the opposite
    Exit_Channel (trailing) or the ATR stop; flat between trades."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    u1, l1, u2, l2, ax = pc
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (np.isfinite(ax[i]) and ax[i] >= adx_threshold and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        long_brk = np.isfinite(u1[i]) and h[i] >= u1[i]
        short_brk = allow_short and np.isfinite(l1[i]) and l[i] <= l1[i]
        if not (long_brk or short_brk):
            i += 1; continue
        d = 1 if long_brk else -1
        risk0 = A[i] * atr_stop
        if fill == 'stop':
            entry = max(o[i], u1[i]) if d == 1 else min(o[i], l1[i]); eb = i
        elif fill == 'close':
            entry = c[i]; eb = i
        elif fill == 'next_open':
            if i + 1 > n - 1: i += 1; continue
            entry = o[i + 1]; eb = i + 1
        else:
            raise ValueError(fill)
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        atr_lvl = entry - d * risk0
        exit_p = exit_j = reason = None
        j = eb + 1
        while j <= n - 1:
            ch = l2[j] if d == 1 else u2[j]                # trailing channel exit (as of j-1)
            ex = (max(atr_lvl, ch) if np.isfinite(ch) else atr_lvl) if d == 1 else \
                 (min(atr_lvl, ch) if np.isfinite(ch) else atr_lvl)
            if d == 1 and l[j] <= ex:  exit_p, reason, exit_j = ex, 'chan/atr', j; break
            if d == -1 and h[j] >= ex: exit_p, reason, exit_j = ex, 'chan/atr', j; break
            j += 1
        if exit_p is None:
            exit_j = n - 1; exit_p, reason = c[n - 1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=d,
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        i = exit_j + 1                                      # flat between trades, no overlap
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_PC = {}
def _pc(t, df, ec):
    if (t, ec) not in _PC: _PC[(t, ec)] = _precompute(df, ec)
    return _PC[(t, ec)]

def run_point(entry_channel, adx_threshold, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_donchian(df, _pc(t, df, entry_channel), adx_threshold=adx_threshold,
                               cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    print(f"Universe: {len(uni)} | {lab.PIPELINE_VERSION} | Donchian breakout + ADX (stop-entry, held long)\n")
    pool = run_point(EC_REP, ADX_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s006_per_instrument.csv")
    el, es, nl, ns = two_sided(pool)
    print(f"=== Representative  Entry_Channel={EC_REP}  ADX_Threshold={ADX_REP} (base Donchian) ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f}(n={nl}) / short {es:+.4f}(n={ns}) | instruments expR>0: {(perdf['expR']>0).sum()}/{len(perdf)}")

    ECs = [5, 10, 20, 50, 100, 150, 200]; ADXs = [0, 10, 20, 30, 40, 60]
    grid = np.full((len(ECs), len(ADXs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, ec in enumerate(ECs):
        for b, ad in enumerate(ADXs):
            m = lab.trade_metrics(run_point(ec, ad)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"EC{x}" for x in ECs], columns=[f"ADX{x}" for x in ADXs]).to_csv("s006_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), Entry_Channel x ADX_Threshold ===")
    print(pd.DataFrame(grid, index=[f"EC{x}" for x in ECs], columns=[f"ADX{x}" for x in ADXs]).round(4).to_string())
    best = np.unravel_index(np.nanargmax(grid), grid.shape)
    print(f"Share positive: {np.mean(grid>0)*100:.0f}% | best EC={ECs[best[0]]} ADX={ADXs[best[1]]} expR={grid[best]:+.4f}")
    print(f"ADX value-add (col ADX0 vs best ADX>0, per EC row): "
          f"mean expR ADX=0 {np.nanmean(grid[:,0]):+.4f} vs mean best ADX>0 {np.nanmean(np.nanmax(grid[:,1:],axis=1)):+.4f}")

    res = lab.run_gates(lambda fill='stop': run_point(EC_REP, ADX_REP, fill=fill), sharpe_grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 72)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("  [archetype STOP-entry: Gate1 'stop'=channel level, 'next_open'=open[i+1]]")
    print("=" * 72)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  natif(stop) Sharpe={d1['opt_sharpe']:+.2f}"
          f" expR={d1['opt_expR']:+.4f}  ->  réaliste(open i+1) Sharpe={d1['real_sharpe']:+.2f}"
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
                  for x in res['gates']]).to_csv("s006_gates.csv", index=False)
    bp = run_point(ECs[best[0]], ADXs[best[1]]); el2, es2, nl2, ns2 = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable EC={ECs[best[0]]} ADX={ADXs[best[1]]}] expR={mb['expR']:+.4f} Sharpe={mb['sharpe']:+.2f} | "
          f"two-sided long {el2:+.4f}(n{nl2})/short {es2:+.4f}(n{ns2})")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(ADXs))); ax.set_xticklabels([f"{x}" for x in ADXs])
    ax.set_yticks(range(len(ECs))); ax.set_yticklabels([f"EC{x}" for x in ECs])
    ax.set_xlabel("ADX_Threshold (trend-strength filter)"); ax.set_ylabel("Entry_Channel (Donchian breakout, bars)")
    ax.set_title("Strategy 6 — Donchian breakout + ADX filter (stop entry)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(ECs)):
        for b in range(len(ADXs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s006_sensitivity.png", dpi=130)
    print("\nSaved: s006_sensitivity.png, s006_per_instrument.csv, s006_sensitivity_expectancy.csv, s006_gates.csv")
