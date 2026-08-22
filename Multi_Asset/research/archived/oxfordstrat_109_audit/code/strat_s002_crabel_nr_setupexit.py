"""
Strategy 2/109 — Toby Crabel 2-Bar Narrow Range + ORB (Test: Setup & Exit).
Source: https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-2/  (rating C)

Difference vs S001 (which fixed Look_Back=20 and swept Target x Time):
  - SETUP variable swept: Look_Back in [10,50] (NR pattern lookback).
  - NO profit target. Exits = Time Exit (Time_Index) OR Stretch Exit (Open -/+ Stretch)
    OR ATR stop (ATR*6) — whichever first.
  - Sensitivity grid = Look_Back x Time_Index.

Same archetype (ORB stop entry + protective stops) but the bracket differs from
simulate_bracket (no target, adds a Stretch exit), so a minimal faithful sim is written
here. Cost model, R-normalisation, metrics and the 4 constitutional gates are reused from
ftmo_lab v2-gates UNCHANGED (comparability across the 109).
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 10, 2.0, 20, 6.0
LB_REP, TM_REP = 20, 10                                  # representative point (site default LB=20)

def crabel_signals(df, look_back):
    h, l, o = df['high'], df['low'], df['open']
    rng2 = (pd.concat([h, h.shift(1)], axis=1).max(axis=1)
            - pd.concat([l, l.shift(1)], axis=1).min(axis=1))
    prev_min = rng2.rolling(look_back).min().shift(1)
    setup = (rng2 <= prev_min) & rng2.notna() & prev_min.notna()
    noise = pd.concat([h - o, o - l], axis=1).min(axis=1).clip(lower=0)
    stretch = noise.rolling(STRETCH_LEN).mean() * STRETCH_MULT
    return setup, stretch

def simulate_setupexit(df, setup, stretch, *, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                       cost_bps=2.0, allow_short=True, fill='stop'):
    """ORB stop entry; exits = Time | Stretch-band stop | ATR stop (no profit target).
    `fill` ('stop'|'close'|'next_open') is the L26 lever, identical semantics to
    ftmo_lab.simulate_bracket. R = ATR*atr_stop (site sizing). Trades carry `dir`."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit, short_hit = h[e] >= buy, (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if long_hit and short_hit:
            trades.append(dict(entry=idx[e], exit=idx[e], reason='both', dir=0,
                               netR=-2*st[i-1]/risk0 - cost_R, hold=0)); i = e + 1; continue
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1
        if fill == 'stop':
            entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1:
                i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        atr_lvl = entry - d * risk0                      # ATR protective stop
        str_lvl = o[e] - d * st[i-1]                     # Stretch exit (Open -/+ Stretch)
        stop_lvl = max(atr_lvl, str_lvl) if d == 1 else min(atr_lvl, str_lvl)   # nearer stop
        last = min(e + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1 and l[j] <= stop_lvl:  exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if d == -1 and h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
            if j == last:                    exit_p, reason, exit_j = c[j], 'time', j; break
        if exit_p is None:
            exit_j = last; exit_p, reason = c[last], 'eod'
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[e], exit=idx[exit_j], reason=reason, dir=d,
                           netR=grossR - cost_R, hold=exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

# ----- universe + signal cache (signals depend only on Look_Back) -------------
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_SIG = {}
def _signals(t, df, lb):
    k = (t, lb)
    if k not in _SIG: _SIG[k] = crabel_signals(df, lb)
    return _SIG[k]

def run_point(look_back, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        setup, stretch = _signals(t, df, look_back)
        tr = simulate_setupexit(df, setup, stretch, time_index=time_index,
                                cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

if __name__ == "__main__":
    print(f"Universe: {len(uni)} instruments | pipeline {lab.PIPELINE_VERSION}\n")

    # ---- representative point + per-instrument
    pool = run_point(LB_REP, TM_REP)
    pm = lab.trade_metrics(pool)
    per = {}
    for t in uni:
        sub = pool[pool['instr'] == t]
        if len(sub): per[t] = lab.trade_metrics(sub)
    perdf = pd.DataFrame(per).T
    perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf = perdf.sort_values('expR', ascending=False); perdf.to_csv("s002_per_instrument.csv")
    print(f"=== Representative  Look_Back={LB_REP}  Time_Index={TM_REP}d ===")
    print(f"Pooled: trades={pm['trades']}  win={pm['win']*100:.1f}%  expR={pm['expR']:+.4f}  "
          f"PF={pm['pf']:.3f}  Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    print(f"Instruments expR>0 : {(perdf['expR']>0).sum()}/{len(perdf)}")

    # ---- sensitivity sweep Look_Back x Time_Index (N cells -> DSR)
    LBs = [10, 15, 20, 25, 30, 40, 50]; TMs = [1, 3, 5, 10, 20, 40]
    grid = np.full((len(LBs), len(TMs)), np.nan); sharpe_grid = np.full_like(grid, np.nan)
    for a, lb in enumerate(LBs):
        for b, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb, tm))
            grid[a, b] = m['expR']; sharpe_grid[a, b] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"{x}d" for x in TMs]).to_csv("s002_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade), Look_Back x Time ===")
    print(pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
    print(f"Share of grid positive: {np.mean(grid>0)*100:.0f}%")

    # ---- CONSTITUTIONAL GATES (reused unchanged) -------------------------
    def make_run(look_back, time_index):
        return lambda fill='stop': run_point(look_back, time_index, fill=fill)
    res = lab.run_gates(make_run(LB_REP, TM_REP), sharpe_grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\n" + "=" * 70)
    print(f"CONSTITUTIONAL GATES (pipeline {lab.PIPELINE_VERSION}) — KEEP requires edge + 4/4")
    print("=" * 70)
    d1 = g['delay1 (L26)']
    print(f"[{'PASS' if d1['pass'] else 'FAIL'}] 1. Délai+1 (L26)  optimiste Sharpe={d1['opt_sharpe']:+.2f}"
          f" expR={d1['opt_expR']:+.4f}  ->  réaliste({d1['fill']}) Sharpe={d1['real_sharpe']:+.2f}"
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
    print("-" * 70)
    print(f"Edge positif après coûts : {res['edge_positive']}   |   gates FAIL : {res['n_fail']}/4")
    print(f">>> VERDICT FINAL : {res['verdict']}   ({res['reason']})")
    print("=" * 70)
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''}
                  for x in res['gates']]).to_csv("s002_gates.csv", index=False)

    # ---- heatmap
    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TMs))); ax.set_xticklabels([f"{x}d" for x in TMs])
    ax.set_yticks(range(len(LBs))); ax.set_yticklabels([f"LB{x}" for x in LBs])
    ax.set_xlabel("Time exit (days held)"); ax.set_ylabel("Look_Back (NR lookback, days)")
    ax.set_title("Strategy 2 — Crabel 2-Bar NR + ORB (Setup & Exit)\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(LBs)):
        for b in range(len(TMs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout()
    fig.savefig("s002_sensitivity.png", dpi=130)
    print("\nSaved: s002_sensitivity.png, s002_per_instrument.csv, s002_sensitivity_expectancy.csv, s002_gates.csv")
