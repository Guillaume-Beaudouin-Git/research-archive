"""
Strategy 3/109 — 3-Bar Momentum Pattern + Trend Filter (Test: Filter & Exit).
Source: https://oxfordstrat.com/trading-strategies/3-bar-momentum-pattern/  (rating C)
Concept: short-term momentum (3 accelerating bars) with a Donchian trend filter (J.R. Hill, 1977).

ARCHETYPE (key vs S001/S002): the 3-bar pattern is CONFIRMED AT THE CLOSE of bar i, then the
trade is entered MARKET-ON-OPEN at bar i+1 (spec: "A buy at the open is placed after a bullish
Setup"). This is NOT an intra-bar stop/limit fill -> NO intrabar fill artefact. The native entry
(open of i+1) is already executable, so Gate 1 here is a LATENCY-robustness test (open[i+1] vs
open[i+2]), not an artefact test.

Fill-token mapping (ftmo_lab gates call run(fill='stop'|'next_open'|'close') UNCHANGED):
    'stop'      -> NATIVE entry at open[i+1]   (the spec entry / baseline)
    'next_open' -> DELAYED entry at open[i+2]  (Gate 1 delay+1 adversarial)
    'close'     -> entry at close[i+1]         (secondary realistic fill, reported)
Cost model, R-normalisation (ATR*6), metrics and the 4 gates are reused from ftmo_lab v2-gates
UNCHANGED (comparability across the 109).
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
# Representative = site-recommended region (summary: trend filter improves; longer hold preferred).
# Chosen mid-region (NOT the grid max, which DSR would punish) to give the archetype a fair Gate-1 test.
FLB_REP, TM_REP = 40, 35

def momentum_signals(df, filter_lb):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    th = pd.concat([h, c.shift(1)], axis=1).max(axis=1)
    tl = pd.concat([l, c.shift(1)], axis=1).min(axis=1)
    tr = th - tl
    tr_up = (tr > tr.shift(1)) & (tr.shift(1) > tr.shift(2))                 # A (both setups)
    # ---- long setup
    Lb = (c > o) & (c.shift(1) > o.shift(1)) & (c.shift(2) > o.shift(2))     # B
    Lc = (c > c.shift(1)) & (c.shift(1) > c.shift(2))                        # C
    Ld = (c - c.shift(1)) > (c.shift(1) - c.shift(2))                        # D accel closes
    Le = (h - h.shift(1)) > (h.shift(1) - h.shift(2))                        # E accel highs
    Lf = (l > l.shift(1)) & (l.shift(1) > l.shift(2))                        # F rising lows
    long_setup = tr_up & Lb & Lc & Ld & Le & Lf
    # ---- short setup (mirror)
    Sb = (c < o) & (c.shift(1) < o.shift(1)) & (c.shift(2) < o.shift(2))
    Sc = (c < c.shift(1)) & (c.shift(1) < c.shift(2))
    Sd = (c.shift(1) - c) > (c.shift(2) - c.shift(1))
    Se = (l.shift(1) - l) > (l.shift(2) - l.shift(1))
    Sf = (h < h.shift(1)) & (h.shift(1) < h.shift(2))
    short_setup = tr_up & Sb & Sc & Sd & Se & Sf
    # ---- Donchian trend filter (FLB=2 => all trades accepted, per spec note)
    if filter_lb <= 2:
        long_ok = short_ok = pd.Series(True, index=df.index)
    else:
        upper = h.rolling(filter_lb).max().shift(1)
        lower = l.rolling(filter_lb).min().shift(1)
        long_ok = h > upper
        short_ok = l < lower
    dir_sig = np.where(long_setup & long_ok, 1, np.where(short_setup & short_ok, -1, 0))
    plow = l.rolling(3).min(); phigh = h.rolling(3).max()                    # pattern extremes
    return pd.Series(dir_sig, index=df.index), plow, phigh

def simulate_momentum(df, dir_sig, plow, phigh, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    """Entry market-on-open after a confirmed pattern; exits = Time | Pattern-extreme stop |
    ATR stop (no profit target). `fill` maps to entry bar (see module docstring)."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    ds = dir_sig.values; pl = plow.values; ph = phigh.values
    n = len(df); idx = df.index
    trades = []; i = 2
    while i < n - 1:
        d = ds[i]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        # entry bar from fill token
        if fill == 'stop':        eb = i + 1; entry = o[eb] if eb <= n-1 else np.nan
        elif fill == 'close':     eb = i + 1; entry = c[eb] if eb <= n-1 else np.nan
        elif fill == 'next_open': eb = i + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop                                # ATR known at signal close i
        cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        atr_lvl = entry - d * risk0
        pat_lvl = pl[i] if d == 1 else ph[i]                   # pattern extreme stop
        stop_lvl = max(atr_lvl, pat_lvl) if d == 1 else min(atr_lvl, pat_lvl)   # nearer stop
        last = min(eb + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(eb, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last:                    exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[i], exit=idx[exit_j], reason=reason, dir=int(d),
                           netR=grossR - cost_R, hold=exit_j - eb))
        i = exit_j + 1                                          # no overlapping positions
    return pd.DataFrame(trades)

# ----- universe + signal cache (signals depend on Filter_Look_Back) -----------
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, flb):
    k = (t, flb)
    if k not in _SIG: _SIG[k] = momentum_signals(df, flb)
    return _SIG[k]

def run_point(filter_lb, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds, pl, ph = _signals(t, df, filter_lb)
        tr = simulate_momentum(df, ds, pl, ph, time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    print(f"Universe: {len(uni)} instruments | pipeline {lab.PIPELINE_VERSION} | archetype: entry@open[i+1]\n")
    pool = run_point(FLB_REP, TM_REP); pm = lab.trade_metrics(pool)
    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    perdf = pd.DataFrame(per).T; perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf.sort_values('expR', ascending=False).to_csv("s003_per_instrument.csv")
    print(f"=== Representative  Filter_Look_Back={FLB_REP}  Time_Index={TM_REP}d ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"Instruments expR>0 : {(perdf['expR']>0).sum()}/{len(perdf)}")

    FLBs = [2, 10, 20, 40, 60, 80, 100]; TMs = [1, 5, 10, 20, 35, 50]
    grid = np.full((len(FLBs), len(TMs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, flb in enumerate(FLBs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(flb, tm)); grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"FLB{x}" for x in FLBs], columns=[f"{x}d" for x in TMs]).to_csv("s003_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), Filter_Look_Back x Time ===")
    print(pd.DataFrame(grid, index=[f"FLB{x}" for x in FLBs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
    print(f"Share of grid positive: {np.mean(grid>0)*100:.0f}%")

    # ---- CONSTITUTIONAL GATES (reused unchanged; fill tokens mapped per archetype)
    res = lab.run_gates(lambda fill='stop': run_point(FLB_REP, TM_REP, fill=fill), sharpe_grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 72)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("  [archetype entry@open: Gate1 'stop'=open[i+1] native, 'next_open'=open[i+2] delay+1]")
    print("=" * 72)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  natif(open i+1) Sharpe={d1['opt_sharpe']:+.2f}"
          f" expR={d1['opt_expR']:+.4f}  ->  délai(open i+2) Sharpe={d1['real_sharpe']:+.2f}"
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
                  for x in res['gates']]).to_csv("s003_gates.csv", index=False)
    # secondary realistic fill (close[i+1]) for the report
    mc = lab.trade_metrics(run_point(FLB_REP, TM_REP, fill='close'))
    print(f"[info] fill=close[i+1]: expR={mc['expR']:+.4f} Sharpe={mc['sharpe']:+.2f} PF={mc['pf']:.3f}")

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TMs))); ax.set_xticklabels([f"{x}d" for x in TMs])
    ax.set_yticks(range(len(FLBs))); ax.set_yticklabels([f"FLB{x}" for x in FLBs])
    ax.set_xlabel("Time exit (days held)"); ax.set_ylabel("Filter_Look_Back (Donchian trend filter)")
    ax.set_title("Strategy 3 — 3-Bar Momentum + Trend Filter (entry@open i+1)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(FLBs)):
        for b in range(len(TMs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s003_sensitivity.png", dpi=130)
    print("\nSaved: s003_sensitivity.png, s003_per_instrument.csv, s003_sensitivity_expectancy.csv, s003_gates.csv")
