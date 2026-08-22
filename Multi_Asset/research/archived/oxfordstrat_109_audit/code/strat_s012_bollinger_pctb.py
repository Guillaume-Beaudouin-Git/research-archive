"""
Strategy 12/109 — Bollinger Bands %b (Test: Setup). Source rating D. (Connors Group)
https://oxfordstrat.com/trading-strategies/bollinger-bands-reversal/
FIRST MEAN-REVERSION archetype of the pipeline.

%b = (Close - LowerBand)/(UpperBand - LowerBand) on a SMA(MA_Length)+/-St_Dev*std band.
Setup Long : Close[i-1] > MA200[i-1]  AND  %b<0.2 for i-1, i-2, i-3 (oversold dip in an uptrend).
Setup Short: Close[i-1] < MA200[i-1]  AND  %b>0.8 for i-1, i-2, i-3 (overbought pop in a downtrend).
Entry : MARKET-ON-OPEN at i. Exit : Trend Exit (%b reverts past 0.8 long / 0.2 short, at the close)
        OR ATR(20)*6 stop. Sweep MA_Length x St_Dev.

ARCHETYPE: trend-aligned mean reversion, entry@open (not an intrabar stop, not a close-fill).
  -> Gate 1 (delay+1) tests open[s+1] (native) vs open[s+2]; also report close[s+1].
  -> Gate 2 (two-sided) is THE deciding test: dip-buy (long) vs rip-sell (short) must BOTH work,
     else it is just disguised long beta like the trend cluster.
Reuses ftmo_lab v2-gates (costs, trade_metrics, 4 gates, atr, RISK_FRAC) UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

MA_TREND, ATR_LEN, ATR_STOP = 200, 20, 6.0
ML_REP, SD_REP = 5, 1.0                               # Connors defaults: MA_Length=5, St_Dev=1.0

def pctb(close, ma_len, st_dev):
    ma = close.rolling(ma_len).mean()
    sd = close.rolling(ma_len).std(ddof=1)
    width = 2.0 * st_dev * sd
    b = (close - (ma - st_dev * sd)) / width.replace(0, np.nan)
    return b

def signals(df, ma_len, st_dev):
    c = df['close']
    b = pctb(c, ma_len, st_dev).values
    mat = c.rolling(MA_TREND).mean().values
    cv = c.values; n = len(cv)
    long_sig = np.zeros(n, bool); short_sig = np.zeros(n, bool)
    ok = np.isfinite(b)
    for s in range(3, n):
        if not (np.isfinite(mat[s]) and ok[s] and ok[s-1] and ok[s-2]):
            continue
        if cv[s] > mat[s] and b[s] < 0.2 and b[s-1] < 0.2 and b[s-2] < 0.2:
            long_sig[s] = True
        elif cv[s] < mat[s] and b[s] > 0.8 and b[s-1] > 0.8 and b[s-2] > 0.8:
            short_sig[s] = True
    return np.where(long_sig, 1, np.where(short_sig, -1, 0)), b

def simulate_meanrev(df, dir_sig, b, *, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                     cost_bps=2.0, allow_short=True, fill='stop'):
    """Entry market-on-open after the %b setup; exit = trend exit (%b reverts, at close) OR ATR stop."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig; n = len(df); idx = df.index
    trades = []; s = 3
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
        stop = entry - d * risk0
        exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if d == 1 and np.isfinite(b[j]) and b[j] > 0.8:  exit_p, reason, exit_j = c[j], 'trend', j; break
            if d == -1 and np.isfinite(b[j]) and b[j] < 0.2:  exit_p, reason, exit_j = c[j], 'trend', j; break
        if exit_p is None:
            exit_j = n - 1; exit_p, reason = c[n-1], 'eod'
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=d * (exit_p - entry) / risk0 - cost_R, hold=exit_j - eb))
        s = exit_j
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _sig(t, df, ml, sd):
    if (t, ml, sd) not in _SIG: _SIG[(t, ml, sd)] = signals(df, ml, sd)
    return _SIG[(t, ml, sd)]

def run_point(ma_len, st_dev, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds, b = _sig(t, df, ma_len, st_dev)
        tr = simulate_meanrev(df, ds, b, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    print(f"Universe: {len(uni)} | {lab.PIPELINE_VERSION} | Bollinger %b MEAN-REVERSION (entry@open)\n")
    pool = run_point(ML_REP, SD_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s012_per_instrument.csv")
    el, es, nl, ns = two_sided(pool)
    # decisive fills
    m_no = lab.trade_metrics(run_point(ML_REP, SD_REP, fill='next_open'))
    m_cl = lab.trade_metrics(run_point(ML_REP, SD_REP, fill='close'))
    print("############ DEUX CHIFFRES DÉCISIFS ############")
    print(f"DELAI+1 : natif open[s+1] Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> "
          f"open[s+2] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f}) ; close[s+1] Sharpe {m_cl['sharpe']:+.2f}")
    print(f"TWO-SIDED: long expR {el:+.4f} (n={nl})  |  short expR {es:+.4f} (n={ns})")
    print("###############################################\n")
    print(f"=== Representative  MA_Length={ML_REP}  St_Dev={SD_REP} (MA_Trend=200) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} CAGR={pm['cagr']*100:+.1f}% MaxDD={pm['maxdd']*100:.1f}% | instr expR>0: {(perdf['expR']>0).sum()}/{len(perdf)}")

    MLs = [5, 10, 20, 40, 60]; SDs = [0.5, 1.0, 1.5, 2.5]
    grid = np.full((len(MLs), len(SDs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ml in enumerate(MLs):
        for bb, sd in enumerate(SDs):
            m = lab.trade_metrics(run_point(ml, sd)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"SD{x}" for x in SDs]).to_csv("s012_sensitivity_expectancy.csv")
    print("\n=== Sensitivity expR (MA_Length x St_Dev) ===")
    print(pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"SD{x}" for x in SDs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")

    res = lab.run_gates(lambda fill='stop': run_point(ML_REP, SD_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 72)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("=" * 72)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  natif Sharpe={d1['opt_sharpe']:+.2f} expR={d1['opt_expR']:+.4f}"
          f"  ->  réaliste(open s+2) Sharpe={d1['real_sharpe']:+.2f} expR={d1['real_expR']:+.4f}" + (f"  << {d1['tag']}" if d1['tag'] else ""))
    t2 = g['twosided (L25)']
    print(f"[{'PASS' if t2['pass'] else 'FAIL'}] 2. Two-sided (L25)  long expR={t2['exp_long']:+.4f} (n={t2['n_long']})"
          f" | short expR={t2['exp_short']:+.4f} (n={t2['n_short']})" + (f"  << {t2['tag']}" if t2['tag'] else ""))
    d3 = g['dsr']
    print(f"[{'PASS' if d3['pass'] else 'FAIL'}] 3. DSR (N={d3['N_trials']})  SR_obs={d3['SR_obs']:.3f} vs E[max]={d3['E_max_SR']:.3f}"
          f"  z={d3['DSR_z']:.1f}" + (f"  << {d3['tag']}" if d3['tag'] else ""))
    o4 = g['oos (L31)']
    print(f"[{'PASS' if o4['pass'] else 'FAIL'}] 4. OOS (L31)  train expR={o4['train_expR']:+.4f} (Sh {o4['train_sharpe']:+.2f})"
          f" -> test expR={o4['test_expR']:+.4f} (Sh {o4['test_sharpe']:+.2f})" + (f"  << {o4['tag']}" if o4['tag'] else ""))
    print("-" * 72)
    print(f"Edge positif après coûts : {res['edge_positive']}  |  gates FAIL : {res['n_fail']}/4")
    print(f">>> VERDICT FINAL : {res['verdict']}  ({res['reason']})")
    print("=" * 72)
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s012_gates.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid)) or 0.01
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(SDs))); ax.set_xticklabels([f"{x}sd" for x in SDs])
    ax.set_yticks(range(len(MLs))); ax.set_yticklabels([f"MA{x}" for x in MLs])
    ax.set_xlabel("St_Dev (band width)"); ax.set_ylabel("MA_Length (band MA, bars)")
    ax.set_title("Strategy 12 — Bollinger %b mean-reversion (entry@open)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(MLs)):
        for bb in range(len(SDs)):
            ax.text(bb, a, f"{grid[a,bb]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s012_sensitivity.png", dpi=130)
    print("\nSaved: s012_sensitivity.png, s012_per_instrument.csv, s012_sensitivity_expectancy.csv, s012_gates.csv")
