"""
Strategy 5/109 — Kaufman Adaptive Moving Average (KAMA) (Test: Setup ONLY).
Source: https://oxfordstrat.com/trading-strategies/adaptive-moving-average-2/  (rating C)

Relation to S004 (Setup & Filter): SAME base (KAMA, entry market-on-close, always-in reversal,
ATR disaster-stop). DISTINCT ANGLE: the noise filter is essentially OFF (Filter_Index = 0.01
fixed) and the swept axes are ER_Length x FastMA_Length (the responsiveness of the AMA's fast
end), whereas S004 swept Filter_Index with FastMA fixed at 2.
  Fast = 2/(FastMA_Length+1): FastMA=2 -> 0.667 (very reactive); FastMA=28 -> 0.069 (~ Slow).

ARCHETYPE: entry MARKET-ON-CLOSE -> no intrabar fill artefact (Gate 1 has a chance, like S003/S004).
Fill mapping identical to S004: 'stop'=close[i] native, 'next_open'=open[i+1], 'close'=close[i+1].
Cost model, R-normalisation (ATR*6), metrics and the 4 gates reused from ftmo_lab v2-gates UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

SLOW_LEN, FILTER_N, FILTER_INDEX, ATR_LEN, ATR_STOP = 30, 20, 0.01, 20, 6.0
ER_REP, FAST_REP = 10, 2                        # canonical Kaufman (ER=10, FastMA=2), filter ~off

def kama(close, er_len, fast_len, slow_len=SLOW_LEN):
    change = (close - close.shift(er_len)).abs()
    vol = close.diff().abs().rolling(er_len).sum()
    er = (change / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fast, slow = 2.0 / (fast_len + 1), 2.0 / (slow_len + 1)
    sc = (er * (fast - slow) + slow) ** 2
    vals = close.values; scv = sc.values
    ama = np.full(len(vals), np.nan); start = er_len
    if start < len(vals):
        ama[start] = vals[start]
        for i in range(start + 1, len(vals)):
            ama[i] = ama[i-1] + (scv[i] if np.isfinite(scv[i]) else 0.0) * (vals[i] - ama[i-1])
    return pd.Series(ama, index=close.index)

def ama_signals(df, er_len, fast_len, filter_index=FILTER_INDEX):
    ama = kama(df['close'], er_len, fast_len)
    d1 = ama.diff()
    turn_up = (d1 > 0) & (d1.shift(1) < 0); turn_dn = (d1 < 0) & (d1.shift(1) > 0)
    min_ama = ama.shift(1).where(turn_up).ffill(); max_ama = ama.shift(1).where(turn_dn).ffill()
    filt = filter_index * d1.rolling(FILTER_N).std()
    long_entry = (d1 > 0) & min_ama.notna() & ((ama - min_ama) > filt)
    short_entry = (d1 < 0) & max_ama.notna() & ((max_ama - ama) > filt)
    return long_entry.fillna(False), short_entry.fillna(False)

def simulate_ama(df, long_entry, short_entry, *, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                 cost_bps=2.0, allow_short=True, fill='stop'):
    """Always-in reversal: enter on a filtered AMA-turn at the close; reverse on opposite signal;
    ATR*6 disaster stop. Identical mechanics to S004. `fill` shifts the signal execution."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    le, se = long_entry.values, short_entry.values
    n = len(df); idx = df.index
    off = 0 if fill == 'stop' else 1
    use_open = (fill == 'next_open')
    trades = []; pos = d = 0; entry = stop = risk0 = cost_R = 0.0; ebar = 0; t_in = None
    def rec(t_out, reason, px):
        return dict(entry=t_in, exit=t_out, reason=reason, dir=d, netR=d*(px-entry)/risk0 - cost_R, hold=np.nan)
    i = 0
    while i < n:
        if pos != 0 and i > ebar and np.isfinite(stop):
            if (d == 1 and l[i] <= stop) or (d == -1 and h[i] >= stop):
                trades.append(rec(idx[i], 'stop', stop)); pos = 0
        sig = 1 if le[i] else (-1 if se[i] else 0)
        if sig == -1 and not allow_short: sig = 0
        if sig != 0 and sig != pos and np.isfinite(A[i]) and A[i] > 0:
            eb = i + off
            if eb <= n - 1:
                price = o[eb] if use_open else c[eb]
                if pos != 0: trades.append(rec(idx[eb], 'reverse', price))
                d = pos = sig; entry = price; ebar = eb
                risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
                stop = entry - d * risk0; t_in = idx[eb]
        i += 1
    if pos != 0: trades.append(rec(idx[n-1], 'eod', c[n-1]))
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, er, fa):
    k = (t, er, fa)
    if k not in _SIG: _SIG[k] = ama_signals(df, er, fa)
    return _SIG[k]

def run_point(er_len, fast_len, fill='stop'):
    frames = []
    for t, df in uni.items():
        le, se = _signals(t, df, er_len, fast_len)
        tr = simulate_ama(df, le, se, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    el = r[d == 1].mean() if (d == 1).any() else np.nan
    es = r[d == -1].mean() if (d == -1).any() else np.nan
    return el, es, int((d == 1).sum()), int((d == -1).sum())

if __name__ == "__main__":
    print(f"Universe: {len(uni)} | {lab.PIPELINE_VERSION} | KAMA setup-only (filter=0.01), sweep ER x FastMA\n")
    pool = run_point(ER_REP, FAST_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s005_per_instrument.csv")
    el, es, nl, ns = two_sided(pool)
    print(f"=== Representative  ER_Length={ER_REP}  FastMA_Length={FAST_REP}  (Filter_Index=0.01) ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"two-sided: long {el:+.4f} (n={nl}) / short {es:+.4f} (n={ns}) | instruments expR>0: {(perdf['expR']>0).sum()}/{len(perdf)}")

    ERs = [2, 10, 20, 40, 60, 80, 100]; FAs = [2, 4, 8, 14, 20, 28]
    grid = np.full((len(ERs), len(FAs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, er in enumerate(ERs):
        for b, fa in enumerate(FAs):
            m = lab.trade_metrics(run_point(er, fa)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"ER{x}" for x in ERs], columns=[f"FA{x}" for x in FAs]).to_csv("s005_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), ER_Length x FastMA_Length ===")
    print(pd.DataFrame(grid, index=[f"ER{x}" for x in ERs], columns=[f"FA{x}" for x in FAs]).round(4).to_string())
    best = np.unravel_index(np.nanargmax(grid), grid.shape)
    print(f"Share positive: {np.mean(grid>0)*100:.0f}% | best ER={ERs[best[0]]} FastMA={FAs[best[1]]} expR={grid[best]:+.4f}")

    res = lab.run_gates(lambda fill='stop': run_point(ER_REP, FAST_REP, fill=fill), sharpe_grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 72)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("  [archetype entry@close: Gate1 'stop'=close[i] native, 'next_open'=open[i+1]]")
    print("=" * 72)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  natif(close i) Sharpe={d1['opt_sharpe']:+.2f}"
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
                  for x in res['gates']]).to_csv("s005_gates.csv", index=False)
    # give the archetype its chance: two-sided at the best favorable cell
    bp = run_point(ERs[best[0]], FAs[best[1]]); el2, es2, nl2, ns2 = two_sided(bp); mb = lab.trade_metrics(bp)
    print(f"[favorable ER={ERs[best[0]]} FastMA={FAs[best[1]]}] expR={mb['expR']:+.4f} Sharpe={mb['sharpe']:+.2f} | "
          f"two-sided long {el2:+.4f}(n{nl2})/short {es2:+.4f}(n{ns2})")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(FAs))); ax.set_xticklabels([f"FA{x}" for x in FAs])
    ax.set_yticks(range(len(ERs))); ax.set_yticklabels([f"ER{x}" for x in ERs])
    ax.set_xlabel("FastMA_Length (fast end of the AMA)"); ax.set_ylabel("ER_Length (Efficiency Ratio lookback)")
    ax.set_title("Strategy 5 — Kaufman AMA setup-only (filter=0.01, entry@close)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(ERs)):
        for b in range(len(FAs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s005_sensitivity.png", dpi=130)
    print("\nSaved: s005_sensitivity.png, s005_per_instrument.csv, s005_sensitivity_expectancy.csv, s005_gates.csv")
