"""
Strategy 16/109 — Doji Pattern Reversal / Counter-Trend (Setup & Filter). Source rating D.
https://oxfordstrat.com/trading-strategies/doji-countertrend-1/
SECOND mean-reversion archetype — mechanically INDEPENDENT of Bollinger (candlestick, not deviation
from a moving average).

Setup  : Doji = |Close[s]-Open[s]| / (High[s]-Low[s]) <= Body_Index  (tiny body = indecision).
Filter : counter-trend — Long if Close[s] < Close[s-Trend_Index] (faded a down-move);
                          Short if Close[s] > Close[s-Trend_Index] (faded an up-move).
Entry  : STOP one tick beyond the Doji range (buy stop above Doji high / sell stop below Doji low).
Exit   : Time(20) | Quick stop (2-bar extreme around entry) | ATR(20)*6. Sweep Body_Index x Trend_Index.

ARCHETYPE = counter-trend MR with a STOP entry -> Gate 1 (delay+1 / fill artefact) is the key risk
(short-term reversal + intrabar stop = the trap). Gate 2 (two-sided) decides if the fade is symmetric.
Fills: 'stop'=Doji-range breakout level (optimistic), 'next_open'=open[s+2], 'close'=close[s+1].
Reuses ftmo_lab v2-gates UNCHANGED. 4 decisive numbers printed up top.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab

TIME_INDEX, ATR_LEN, ATR_STOP = 20, 20, 6.0
BI_REP, TI_REP = 0.10, 10                              # representative: doji body<=0.10, fade 10-day move

def doji_dir(df, body_index, trend_index):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    rng = h - l
    body = np.where(rng > 0, np.abs(c - o) / np.where(rng > 0, rng, np.nan), np.nan)
    is_doji = body <= body_index
    n = len(c); ds = np.zeros(n)
    for s in range(trend_index, n):
        if not (is_doji[s]): continue
        if c[s] < c[s - trend_index]: ds[s] = 1          # counter-trend long (fade the down)
        elif c[s] > c[s - trend_index]: ds[s] = -1       # counter-trend short (fade the up)
    return ds

def simulate_doji(df, dir_sig, *, time_index=TIME_INDEX, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                  cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values; ds = dir_sig; n = len(df); idx = df.index
    trades = []; s = 1
    while s < n - 2:
        d = ds[s]
        if d == 0 or (d == -1 and not allow_short) or not np.isfinite(A[s]) or A[s] <= 0:
            s += 1; continue
        lvl = h[s] if d == 1 else l[s]                    # Doji-range breakout level
        # confirm breakout on s+1
        if (d == 1 and not (h[s+1] >= lvl)) or (d == -1 and not (l[s+1] <= lvl)):
            s += 1; continue
        if fill == 'stop':        eb = s + 1; entry = max(o[eb], lvl) if d == 1 else min(o[eb], lvl)
        elif fill == 'close':     eb = s + 1; entry = c[eb]
        elif fill == 'next_open': eb = s + 2; entry = o[eb] if eb <= n-1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            s += 1; continue
        risk0 = A[s] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        atr_lvl = entry - d * risk0
        quick = (min(l[eb-1], l[eb]) if d == 1 else max(h[eb-1], h[eb]))   # 2-bar extreme quick stop
        stop = max(atr_lvl, quick) if d == 1 else min(atr_lvl, quick)
        last = min(eb + time_index, n - 1)
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
_SIG = {}
def _sig(t, df, bi, ti):
    if (t, bi, ti) not in _SIG: _SIG[(t, bi, ti)] = doji_dir(df, bi, ti)
    return _SIG[(t, bi, ti)]

def run_point(body_index, trend_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds = _sig(t, df, body_index, trend_index)
        tr = simulate_doji(df, ds, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

# control: NON-doji (normal body) in the same counter-trend context, same stop entry & exit
def control_dir(df, trend_index, lo=0.3, hi=0.7):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    rng = h - l; body = np.where(rng > 0, np.abs(c - o) / np.where(rng > 0, rng, np.nan), np.nan)
    normal = (body >= lo) & (body <= hi); n = len(c); ds = np.zeros(n)
    for s in range(trend_index, n):
        if not normal[s]: continue
        if c[s] < c[s - trend_index]: ds[s] = 1
        elif c[s] > c[s - trend_index]: ds[s] = -1
    return ds

if __name__ == "__main__":
    pool = run_point(BI_REP, TI_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(BI_REP, TI_REP, fill='next_open'))
    m_cl = lab.trade_metrics(run_point(BI_REP, TI_REP, fill='close'))
    # alpha vs beta: doji vs normal-body, same counter-trend context
    dl, nu_l, ds_, nu_s = [], [], [], []
    for t, df in uni.items():
        tr = simulate_doji(df, _sig(t, df, BI_REP, TI_REP), cost_bps=costs[t])
        if len(tr): dl += list(tr[tr.dir == 1]['netR']); ds_ += list(tr[tr.dir == -1]['netR'])
        ctr = simulate_doji(df, control_dir(df, TI_REP), cost_bps=costs[t])
        if len(ctr): nu_l += list(ctr[ctr.dir == 1]['netR']); nu_s += list(ctr[ctr.dir == -1]['netR'])
    # walk-forward + recent short robustness across Body/Trend
    ent = pd.to_datetime(pool['entry']); wf = []
    for lo, hi in [('2000', '2006'), ('2006', '2012'), ('2012', '2018'), ('2018', '2027')]:
        sub = pool[(ent >= pd.Timestamp(lo)) & (ent < pd.Timestamp(hi))]
        if len(sub): wf.append((lo[:4], lab.trade_metrics(sub)['sharpe'],
                                sub[sub.dir==-1]['netR'].mean() if (sub.dir==-1).any() else np.nan))

    print("############ 4 CHIFFRES DÉCISIFS — S016 Doji Reversal (Body=0.10, Trend=10) ############")
    print(f"1. DELAI+1  : natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[s+2] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f}) ; close[s+1] Sharpe {m_cl['sharpe']:+.2f}")
    print(f"2. TWO-SIDED: long expR {el:+.4f} (n={nl}) | short expR {es:+.4f} (n={ns})")
    print(f"3. ALPHA-vs-BETA: long doji {np.mean(dl):+.4f} vs normal {np.mean(nu_l):+.4f} (alpha {np.mean(dl)-np.mean(nu_l):+.4f}) | "
          f"short doji {np.mean(ds_):+.4f} vs normal {np.mean(nu_s):+.4f} (alpha {np.mean(ds_)-np.mean(nu_s):+.4f})")
    print(f"4. WALK-FWD Sharpe: " + " -> ".join(f"{y}:{sh:+.2f}" for y, sh, _ in wf) +
          " | short/bloc: " + " ".join(f"{y}:{ss:+.3f}" for y, _, ss in wf))
    print("######################################################################################\n")
    print(f"Pooled (réf): trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} "
          f"Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")

    # short robustness across the grid + recent regime
    print("\n[ROBUSTESSE SHORT & 2018+] (Body x Trend):")
    for bi in [0.05, 0.10, 0.20]:
        for ti in [5, 10, 20]:
            p = run_point(bi, ti); rr, dd = p['netR'].values, p['dir'].values
            e2 = pd.to_datetime(p['entry']); rec = p[e2 >= pd.Timestamp('2018')]
            print(f"  Body{bi} Trend{ti}: long {rr[dd==1].mean():+.4f} short {rr[dd==-1].mean():+.4f} | "
                  f"2018+ Sharpe {lab.trade_metrics(rec)['sharpe']:+.2f} short {rec[rec.dir==-1]['netR'].mean() if (rec.dir==-1).any() else float('nan'):+.4f}")

    BIs = [0.05, 0.10, 0.20, 0.30]; TIs = [1, 5, 10, 20, 40]
    grid = np.full((len(BIs), len(TIs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, bi in enumerate(BIs):
        for bb, ti in enumerate(TIs):
            m = lab.trade_metrics(run_point(bi, ti)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"T{x}" for x in TIs]).to_csv("s016_sensitivity_expectancy.csv")
    print("\n=== Sensitivity expR (Body_Index x Trend_Index) ===")
    print(pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"T{x}" for x in TIs]).round(4).to_string())

    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    pd.DataFrame(per).T.assign(cls=lambda x:[lab.CLASS.get(i) for i in x.index]).sort_values('expR',ascending=False).to_csv("s016_per_instrument.csv")

    res = lab.run_gates(lambda fill='stop': run_point(BI_REP, TI_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s016_gates.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid)) or 0.01
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(TIs))); ax.set_xticklabels([f"T{x}" for x in TIs])
    ax.set_yticks(range(len(BIs))); ax.set_yticklabels([f"B{x}" for x in BIs])
    ax.set_xlabel("Trend_Index (counter-trend lookback)"); ax.set_ylabel("Body_Index (doji body max)")
    ax.set_title("Strategy 16 — Doji counter-trend reversal (stop entry)\nPooled net expectancy (R/trade), after costs")
    for a in range(len(BIs)):
        for bb in range(len(TIs)):
            ax.text(bb, a, f"{grid[a,bb]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout(); fig.savefig("s016_sensitivity.png", dpi=130)
    print("\nSaved: s016_sensitivity.png, s016_per_instrument.csv, s016_sensitivity_expectancy.csv, s016_gates.csv")
