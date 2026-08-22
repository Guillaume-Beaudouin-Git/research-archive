"""
Strategy 1/109 — Toby Crabel 2-Bar Narrow Range + Opening Range Breakout.
Source spec: https://oxfordstrat.com/trading-strategies/toby-crabel-narrow-range-1/
oxfordstrat rating: C.

Setup : 2-bar range is the narrowest vs any 2-day window in the previous 20 days.
Entry : next bar, ORB stop at Open +/- Stretch ; Stretch = SMA(Noise,10)*2,
        Noise = min(High-Open, Open-Low).
Exit  : Target (Target_Index * initial risk), Time (n-th bar close), ATR stop (ATR20*6).
Tested as a long/short portfolio across the FTMO universe, net of conservative costs.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

LOOK_BACK, STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 20, 10, 2.0, 20, 6.0

def crabel_signals(df, look_back=LOOK_BACK, stretch_len=STRETCH_LEN, stretch_mult=STRETCH_MULT):
    h, l, o = df['high'], df['low'], df['open']
    rng2 = (pd.concat([h, h.shift(1)], axis=1).max(axis=1)
            - pd.concat([l, l.shift(1)], axis=1).min(axis=1))
    prev_min = rng2.rolling(look_back).min().shift(1)
    setup = (rng2 <= prev_min) & rng2.notna() & prev_min.notna()
    noise = pd.concat([h - o, o - l], axis=1).min(axis=1).clip(lower=0)
    stretch = noise.rolling(stretch_len).mean() * stretch_mult
    return setup, stretch

def run(target_index, time_index, uni, costs):
    all_tr, per = [], {}
    for t, df in uni.items():
        setup, stretch = crabel_signals(df)
        tr = lab.simulate_bracket(df, setup, stretch, target_index=target_index,
                                  time_index=time_index, atr_len=ATR_LEN,
                                  atr_stop=ATR_STOP, cost_bps=costs[t])
        if len(tr):
            tr['instr'] = t; all_tr.append(tr); per[t] = lab.trade_metrics(tr)
    pool = pd.concat(all_tr, ignore_index=True) if all_tr else pd.DataFrame()
    return pool, per

def pooled_stats(pool):
    if len(pool) == 0:
        return dict(trades=0, expR=np.nan, pf=np.nan, win=np.nan)
    r = pool['netR'].values
    pf = r[r > 0].sum() / abs(r[r < 0].sum()) if (r < 0).any() else np.inf
    return dict(trades=len(r), expR=float(r.mean()), pf=float(pf), win=float((r > 0).mean()))

if __name__ == "__main__":
    uni = lab.load_universe()
    costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
    print(f"Universe: {len(uni)} instruments | cost(bps) "
          f"min={min(costs.values()):.1f} med={np.median(list(costs.values())):.1f} max={max(costs.values()):.1f}\n")

    # ---- representative parameter point (site defaults: target 3R, 10-day time exit)
    TI_REP, TM_REP = 3.0, 10
    pool, per = run(TI_REP, TM_REP, uni, costs)
    ps = pooled_stats(pool)
    pm = lab.trade_metrics(pool)
    perdf = pd.DataFrame(per).T
    perdf['class'] = [lab.CLASS.get(i) for i in perdf.index]
    perdf = perdf.sort_values('expR', ascending=False)
    perdf.to_csv("s001_per_instrument.csv")

    print(f"=== Representative point  Target_Index={TI_REP}R  Time_Index={TM_REP}d ===")
    print(f"Pooled: trades={ps['trades']}  win={ps['win']*100:.1f}%  "
          f"expectancy={ps['expR']:+.4f} R/trade  profit_factor={ps['pf']:.3f}")
    print(f"Pooled equity: Sharpe={pm['sharpe']:.2f}  CAGR={pm['cagr']*100:+.1f}%  MaxDD={pm['maxdd']*100:.1f}%")
    pos = (perdf['expR'] > 0).sum()
    print(f"Instruments with positive net expectancy: {pos}/{len(perdf)}")
    print("\nTop 8 instruments by net expectancy (R/trade):")
    print(perdf[['class','trades','win','expR','pf']].head(8).round(3).to_string())
    print("\nBottom 5:")
    print(perdf[['class','trades','win','expR','pf']].tail(5).round(3).to_string())

    # ---- sensitivity sweep (capture per-cell Sharpe for the DSR gate)
    TIs = [1, 2, 3, 4, 6, 8, 10]; TMs = [1, 3, 5, 10, 20, 40]
    grid = np.full((len(TIs), len(TMs)), np.nan)
    pf_grid = np.full_like(grid, np.nan)
    sharpe_grid = np.full_like(grid, np.nan)
    for a, ti in enumerate(TIs):
        for b, tm in enumerate(TMs):
            pool_cell = run(ti, tm, uni, costs)[0]
            s = pooled_stats(pool_cell); m = lab.trade_metrics(pool_cell)
            grid[a, b] = s['expR']; pf_grid[a, b] = s['pf']; sharpe_grid[a, b] = m['sharpe']
    sweep = pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs])
    sweep.to_csv("s001_sensitivity_expectancy.csv")
    print("\n=== Sensitivity: pooled net expectancy (R/trade) ===")
    print(sweep.round(4).to_string())
    best = np.unravel_index(np.nanargmax(grid), grid.shape)
    print(f"\nBest cell: Target={TIs[best[0]]}R Time={TMs[best[1]]}d -> expR={grid[best]:+.4f}, "
          f"PF={pf_grid[best]:.3f}")
    frac_pos = np.mean(grid > 0)
    print(f"Share of parameter grid with positive expectancy: {frac_pos*100:.0f}%")

    # ---- CONSTITUTIONAL GATES (v2) — mandatory before any KEEP ------------
    def make_run(target_index, time_index):
        def _run(fill='stop'):
            frames = []
            for t, df in uni.items():
                setup, stretch = crabel_signals(df)
                tr = lab.simulate_bracket(df, setup, stretch, target_index=target_index,
                                          time_index=time_index, atr_len=ATR_LEN,
                                          atr_stop=ATR_STOP, cost_bps=costs[t], fill=fill)
                if len(tr):
                    tr['instr'] = t; frames.append(tr)
            return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        return _run

    res = lab.run_gates(make_run(TI_REP, TM_REP), sharpe_grid, split='2015-12-31')
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
          f" vs E[max bruit]={d3['E_max_SR']:.3f}  DSR_z={d3['DSR_z']:.1f}"
          + (f"  << {d3['tag']}" if d3['tag'] else ""))
    o4 = g['oos (L31)']
    print(f"[{'PASS' if o4['pass'] else 'FAIL'}] 4. OOS (L31)  train expR={o4['train_expR']:+.4f}"
          f" (Sh {o4['train_sharpe']:+.2f}, n={o4['n_train']}) -> test expR={o4['test_expR']:+.4f}"
          f" (Sh {o4['test_sharpe']:+.2f}, n={o4['n_test']})" + (f"  << {o4['tag']}" if o4['tag'] else ""))
    print("-" * 70)
    print(f"Edge positif après coûts : {res['edge_positive']}   |   gates FAIL : {res['n_fail']}/4")
    print(f">>> VERDICT FINAL : {res['verdict']}   ({res['reason']})")
    print("=" * 70)
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''}
                  for x in res['gates']]).to_csv("s001_gates.csv", index=False)

    # ---- heatmap
    fig, ax = plt.subplots(figsize=(8, 5.2))
    vlim = np.nanmax(np.abs(grid))
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TMs))); ax.set_xticklabels([f"{x}d" for x in TMs])
    ax.set_yticks(range(len(TIs))); ax.set_yticklabels([f"{x}R" for x in TIs])
    ax.set_xlabel("Time exit (days held)"); ax.set_ylabel("Target (multiple of initial risk)")
    ax.set_title("Strategy 1 — Crabel 2-Bar NR + ORB\nPooled net expectancy (R/trade), FTMO universe, after costs")
    for a in range(len(TIs)):
        for b in range(len(TMs)):
            ax.text(b, a, f"{grid[a,b]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)")
    fig.tight_layout(); fig.savefig("s001_sensitivity.png", dpi=130)
    print("\nSaved: s001_sensitivity.png, s001_per_instrument.csv, s001_sensitivity_expectancy.csv")
