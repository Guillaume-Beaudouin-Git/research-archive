"""
Strategy 4/109 — Kaufman Adaptive Moving Average (KAMA) (Test: Setup & Filter).
Source: https://oxfordstrat.com/trading-strategies/adaptive-moving-average-1/  (rating C)
Concept: adaptive noise filter (Kaufman 1995). Trend-following.

ARCHETYPE: KAMA computed on CLOSE; signal = AMA turns + move beyond a std-dev filter; entry is
MARKET-ON-CLOSE ("A buy at the close after a bullish setup"). NOT an intrabar stop -> no intrabar
fill artefact (like S003). The documented exit is only an ATR disaster-stop; a fixed stop alone
would make the system degenerate (losses only), so the faithful coherent reading is an ALWAYS-IN
reversal system: hold until the opposite AMA-turn signal (reverse) OR the ATR stop, whichever first.

Fill-token mapping (ftmo_lab gates call run(fill='stop'|'next_open'|'close') UNCHANGED):
    'stop'      -> NATIVE entry at close[i]   (spec entry: signal & fill both on the close = mildly optimistic)
    'next_open' -> entry at open[i+1]         (Gate 1 realistic: act next bar)
    'close'     -> entry at close[i+1]        (secondary realistic fill, reported)
Cost model, R-normalisation (ATR*6), metrics and the 4 gates reused from ftmo_lab v2-gates UNCHANGED.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

FAST_LEN, SLOW_LEN, FILTER_N, ATR_LEN, ATR_STOP = 2, 30, 20, 20, 6.0
ER_REP, FI_REP = 10, 0.2                       # representative: Kaufman-canonical ER=10, modest filter

def kama(close, er_len, fast_len=FAST_LEN, slow_len=SLOW_LEN):
    change = (close - close.shift(er_len)).abs()
    vol = close.diff().abs().rolling(er_len).sum()
    er = (change / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    fast, slow = 2.0 / (fast_len + 1), 2.0 / (slow_len + 1)
    sc = (er * (fast - slow) + slow) ** 2
    vals = close.values; scv = sc.values
    ama = np.full(len(vals), np.nan)
    start = er_len
    if start < len(vals):
        ama[start] = vals[start]
        for i in range(start + 1, len(vals)):
            ama[i] = ama[i-1] + (scv[i] if np.isfinite(scv[i]) else 0.0) * (vals[i] - ama[i-1])
    return pd.Series(ama, index=close.index)

def ama_signals(df, er_len, filter_index):
    ama = kama(df['close'], er_len)
    d1 = ama.diff()
    turn_up = (d1 > 0) & (d1.shift(1) < 0)            # trough at i-1
    turn_dn = (d1 < 0) & (d1.shift(1) > 0)            # peak at i-1
    min_ama = ama.shift(1).where(turn_up).ffill()     # last trough value
    max_ama = ama.shift(1).where(turn_dn).ffill()     # last peak value
    filt = filter_index * d1.rolling(FILTER_N).std()
    long_entry = (d1 > 0) & min_ama.notna() & ((ama - min_ama) > filt)
    short_entry = (d1 < 0) & max_ama.notna() & ((max_ama - ama) > filt)
    return long_entry.fillna(False), short_entry.fillna(False)

def simulate_ama(df, long_entry, short_entry, *, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                 cost_bps=2.0, allow_short=True, fill='stop'):
    """Always-in reversal: enter on a filtered AMA-turn at the close; reverse on the opposite
    signal; ATR*6 disaster stop. `fill` shifts the signal execution (see module docstring)."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    le, se = long_entry.values, short_entry.values
    n = len(df); idx = df.index
    off = 0 if fill == 'stop' else 1                  # exec bar = signal bar + off
    use_open = (fill == 'next_open')
    trades = []
    pos = d = 0; entry = stop = risk0 = cost_R = 0.0; ebar = 0; t_in = None
    def rec(t_out, reason, exitpx):
        return dict(entry=t_in, exit=t_out, reason=reason, dir=d,
                    netR=d * (exitpx - entry) / risk0 - cost_R, hold=np.nan)
    i = 0
    while i < n:
        # 1) ATR disaster stop on open position (bars strictly after entry exec bar)
        if pos != 0 and i > ebar and np.isfinite(stop):
            if (d == 1 and l[i] <= stop) or (d == -1 and h[i] >= stop):
                trades.append(rec(idx[i], 'stop', stop)); pos = 0
        # 2) entry signal at bar i
        sig = 1 if le[i] else (-1 if se[i] else 0)
        if sig == -1 and not allow_short:
            sig = 0
        if sig != 0 and sig != pos and np.isfinite(A[i]) and A[i] > 0:
            eb = i + off
            if eb <= n - 1:
                price = o[eb] if use_open else c[eb]
                if pos != 0:                          # reverse: close current at exec price
                    trades.append(rec(idx[eb], 'reverse', price))
                d = pos = sig; entry = price; ebar = eb
                risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
                stop = entry - d * risk0; t_in = idx[eb]
        i += 1
    if pos != 0:
        trades.append(rec(idx[n-1], 'eod', c[n-1]))
    return pd.DataFrame(trades)

# ----- universe + signal cache (signals depend on ER_Length & Filter_Index) ---
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, er, fi):
    k = (t, er, fi)
    if k not in _SIG: _SIG[k] = ama_signals(df, er, fi)
    return _SIG[k]

def run_point(er_len, filter_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        le, se = _signals(t, df, er_len, filter_index)
        tr = simulate_ama(df, le, se, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    print(f"Universe: {len(uni)} instruments | pipeline {lab.PIPELINE_VERSION} | archetype: entry@close (always-in reversal)\n")
    pool = run_point(ER_REP, FI_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s004_per_instrument.csv")
    print(f"=== Representative  ER_Length={ER_REP}  Filter_Index={FI_REP} ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"Instruments expR>0 : {(perdf['expR']>0).sum()}/{len(perdf)}")

    ERs = [2, 10, 20, 40, 60, 80, 100]; FIs = [0.0, 0.1, 0.2, 0.3, 0.5, 1.0]
    grid = np.full((len(ERs), len(FIs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, er in enumerate(ERs):
        for b, fi in enumerate(FIs):
            m = lab.trade_metrics(run_point(er, fi)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"ER{x}" for x in ERs], columns=[f"FI{x}" for x in FIs]).to_csv("s004_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), ER_Length x Filter_Index ===")
    print(pd.DataFrame(grid, index=[f"ER{x}" for x in ERs], columns=[f"FI{x}" for x in FIs]).round(4).to_string())
    print(f"Share of grid positive: {np.mean(grid>0)*100:.0f}%")

    res = lab.run_gates(lambda fill='stop': run_point(ER_REP, FI_REP, fill=fill), sharpe_grid, split='2015-12-31')
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
          f" (n={t2['n_long']}) | short expR={t2['exp_short']:+.4f} (n={t2['n_short']}) |"
          f" contrib long={t2['contrib_long_pct']:.0f}%" + (f"  << {t2['tag']}" if t2['tag'] else ""))
    d3 = g['dsr']
    print(f"[{'PASS' if d3['pass'] else 'FAIL'}] 3. DSR (N={d3['N_trials']})  SR_obs={d3['SR_obs']:.3f}"
          f" vs E[max bruit]={d3['E_max_SR']:.3f}  DSR_z={d3['DSR_z']:.1f}" + (f"  << {d3['tag']}" if d3['tag'] else ""))
    o4 = g['oos (L31)']
    print(f"[{'PASS' if o4['pass'] else 'FAIL'}] 4. OOS (L31)  train expR={o4['train_expR']:+.4f}"
          f" (Sh {o4['train_sharpe']:+.2f}, n={o4['n_train']}) -> test expR={o4['test_expR']:+.4f}"
          f" (Sh {o4['test_sharpe']:+.2f}, n={o4['n_test']})" + (f"  << {o4['tag']}" if o4['tag'] else ""))
    print("-" * 72)
    print(f"Edge positif après coûts : {res['edge_positive']}   |   gates FAIL : {res['n_fail']}/4")
    print(f">>> VERDICT FINAL : {res['verdict']}   ({res['reason']})")
    print("=" * 72)
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''}
                  for x in res['gates']]).to_csv("s004_gates.csv", index=False)
    mc = lab.trade_metrics(run_point(ER_REP, FI_REP, fill='close'))
    print(f"[info] fill=close[i+1]: expR={mc['expR']:+.4f} Sharpe={mc['sharpe']:+.2f} PF={mc['pf']:.3f}")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(FIs))); ax.set_xticklabels([f"{x}" for x in FIs])
    ax.set_yticks(range(len(ERs))); ax.set_yticklabels([f"ER{x}" for x in ERs])
    ax.set_xlabel("Filter_Index (std-dev noise filter)"); ax.set_ylabel("ER_Length (Efficiency Ratio lookback)")
    ax.set_title("Strategy 4 — Kaufman AMA (entry@close, always-in reversal)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(ERs)):
        for b in range(len(FIs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s004_sensitivity.png", dpi=130)
    print("\nSaved: s004_sensitivity.png, s004_per_instrument.csv, s004_sensitivity_expectancy.csv, s004_gates.csv")
