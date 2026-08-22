"""
Strategy 13/109 — Bollinger Bands %b (Test: Setup & Filter). Source rating D. (Connors)
https://oxfordstrat.com/trading-strategies/bollinger-bands-reversal-2/

SAME mean-reversion setup as S012 (the only real MR alpha found, but decayed). The ONLY difference:
the swept axes are MA_Length x MA_Trend_Length (the trend-filter period), with St_Dev fixed at 1.
(S012 swept MA_Length x St_Dev with MA_Trend fixed=200.) The canonical cell (MA5/MA_Trend200) is
IDENTICAL to S012.

HYPOTHESIS (user): does varying the trend-filter length clean up S012's fragile SHORT side
(which dies post-2012) and slow the decay? Prior: filters degraded 0/5 in our combo batches.

Reuses S012's pctb + simulate_meanrev + universe + costs, and ftmo_lab v2-gates UNCHANGED.
Decisive numbers reported up top: delay+1, two-sided (+ short robustness across MA_Trend),
alpha-vs-beta, walk-forward.
"""
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
import ftmo_lab as lab
import strat_s012_bollinger_pctb as s12

ST_DEV, ATR_LEN, ATR_STOP = 1.0, 20, 6.0
ML_REP, MT_REP = 5, 200                               # canonical = S012 cell
uni, costs = s12.uni, s12.costs

def signals_mt(df, ma_len, ma_trend, st_dev=ST_DEV):
    c = df['close']; b = s12.pctb(c, ma_len, st_dev).values
    mat = c.rolling(ma_trend).mean().values; cv = c.values; n = len(cv)
    ds = np.zeros(n)
    for s in range(3, n):
        if not (np.isfinite(mat[s]) and np.isfinite(b[s]) and np.isfinite(b[s-1]) and np.isfinite(b[s-2])):
            continue
        if cv[s] > mat[s] and b[s] < 0.2 and b[s-1] < 0.2 and b[s-2] < 0.2: ds[s] = 1
        elif cv[s] < mat[s] and b[s] > 0.8 and b[s-1] > 0.8 and b[s-2] > 0.8: ds[s] = -1
    return ds, b

_SIG = {}
def _sig(t, df, ml, mt):
    if (t, ml, mt) not in _SIG: _SIG[(t, ml, mt)] = signals_mt(df, ml, mt)
    return _SIG[(t, ml, mt)]

def run_point(ma_len, ma_trend, fill='stop'):
    frames = []
    for t, df in uni.items():
        ds, b = _sig(t, df, ma_len, ma_trend)
        tr = s12.simulate_meanrev(df, ds, b, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

def neutral_mt(df, ma_len, ma_trend, lo=0.4, hi=0.6):
    c = df['close']; b = s12.pctb(c, ma_len, ST_DEV).values
    mat = c.rolling(ma_trend).mean().values; cv = c.values; n = len(cv); ds = np.zeros(n)
    for s in range(3, n):
        if not (np.isfinite(mat[s]) and np.isfinite(b[s])): continue
        if cv[s] > mat[s] and lo <= b[s] <= hi: ds[s] = 1
        elif cv[s] < mat[s] and lo <= b[s] <= hi: ds[s] = -1
    return ds, b

if __name__ == "__main__":
    pool = run_point(ML_REP, MT_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(ML_REP, MT_REP, fill='next_open'))
    # alpha vs beta (dip vs neutral, same MA_Trend)
    dl, nu_l, ds_, nu_s = [], [], [], []
    for t, df in uni.items():
        ds, b = _sig(t, df, ML_REP, MT_REP); tr = s12.simulate_meanrev(df, ds, b, cost_bps=costs[t])
        if len(tr): dl += list(tr[tr.dir == 1]['netR']); ds_ += list(tr[tr.dir == -1]['netR'])
        nds, nb = neutral_mt(df, ML_REP, MT_REP); ntr = s12.simulate_meanrev(df, nds, nb, cost_bps=costs[t])
        if len(ntr): nu_l += list(ntr[ntr.dir == 1]['netR']); nu_s += list(ntr[ntr.dir == -1]['netR'])
    a_long = np.mean(dl) - np.mean(nu_l); a_short = np.mean(ds_) - np.mean(nu_s)
    # walk-forward (canonical)
    ent = pd.to_datetime(pool['entry'])
    wf = []
    for lo, hi in [('2000', '2006'), ('2006', '2012'), ('2012', '2018'), ('2018', '2027')]:
        sub = pool[(ent >= pd.Timestamp(lo)) & (ent < pd.Timestamp(hi))]
        if len(sub): wf.append((lo[:4], lab.trade_metrics(sub)['sharpe'],
                                 sub[sub.dir==-1]['netR'].mean() if (sub.dir==-1).any() else np.nan))

    print("############ 4 CHIFFRES DÉCISIFS (S013, cellule canonique MA5/MA_Trend200 = identique S012) ############")
    print(f"1. DELAI+1 : natif Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[s+2] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"2. TWO-SIDED: long {el:+.4f}(n{nl}) | short {es:+.4f}(n{ns})")
    print(f"3. ALPHA vs BETA: long dip {np.mean(dl):+.4f} vs neutre {np.mean(nu_l):+.4f} (alpha {a_long:+.4f}) | "
          f"short pop {np.mean(ds_):+.4f} vs neutre {np.mean(nu_s):+.4f} (alpha {a_short:+.4f})")
    print(f"4. WALK-FWD Sharpe: " + " -> ".join(f"{y}:{sh:+.2f}" for y, sh, _ in wf) +
          "  | short par bloc: " + " ".join(f"{y}:{ss:+.3f}" for y, _, ss in wf))
    print("######################################################################################################\n")

    # ---- FILTER HYPOTHESIS: does any MA_Trend rescue the short / recent regime? (MA_Length=5)
    print("[HYPOTHÈSE FILTRE] effet de MA_Trend_Length (MA_Length=5) sur short & régime récent (2018+):")
    for mt in [80, 120, 160, 200, 250]:
        p = run_point(5, mt); rr, dd = p['netR'].values, p['dir'].values
        e2 = pd.to_datetime(p['entry']); rec = p[e2 >= pd.Timestamp('2018')]
        rsh = rec[rec.dir == -1]['netR'].mean() if (rec.dir == -1).any() else np.nan
        rec_sh = lab.trade_metrics(rec)['sharpe']
        print(f"  MA_Trend={mt:3d}: long {rr[dd==1].mean():+.4f} short {rr[dd==-1].mean():+.4f} | "
              f"2018+ Sharpe {rec_sh:+.2f} short {rsh:+.4f}")

    # ---- grid MA_Length x MA_Trend + gates
    MLs = [5, 10, 20, 40, 60]; MTs = [80, 150, 200, 250]
    grid = np.full((len(MLs), len(MTs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, ml in enumerate(MLs):
        for bb, mt in enumerate(MTs):
            m = lab.trade_metrics(run_point(ml, mt)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"MT{x}" for x in MTs]).to_csv("s013_sensitivity_expectancy.csv")
    print("\n=== Sensitivity expR (MA_Length x MA_Trend) ===")
    print(pd.DataFrame(grid, index=[f"MA{x}" for x in MLs], columns=[f"MT{x}" for x in MTs]).round(4).to_string())

    per = {t: lab.trade_metrics(pool[pool['instr'] == t]) for t in uni if len(pool[pool['instr'] == t])}
    pd.DataFrame(per).T.assign(cls=lambda x: [lab.CLASS.get(i) for i in x.index]).sort_values('expR', ascending=False).to_csv("s013_per_instrument.csv")

    res = lab.run_gates(lambda fill='stop': run_point(ML_REP, MT_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES (canonique):")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k=='dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s013_gates.csv", index=False)

    fig, ax = plt.subplots(figsize=(8, 5.2)); vlim = np.nanmax(np.abs(grid)) or 0.01
    im = ax.imshow(grid, cmap='RdYlGn', vmin=-vlim, vmax=vlim, aspect='auto')
    ax.set_xticks(range(len(MTs))); ax.set_xticklabels([f"MT{x}" for x in MTs])
    ax.set_yticks(range(len(MLs))); ax.set_yticklabels([f"MA{x}" for x in MLs])
    ax.set_xlabel("MA_Trend_Length (trend filter, bars)"); ax.set_ylabel("MA_Length (band MA, bars)")
    ax.set_title("Strategy 13 — Bollinger %b Setup & Filter (entry@open)\nPooled net expectancy (R/trade), after costs")
    for a in range(len(MLs)):
        for bb in range(len(MTs)):
            ax.text(bb, a, f"{grid[a,bb]:+.3f}", ha='center', va='center', fontsize=8)
    fig.colorbar(im, label="Net expectancy (R/trade)"); fig.tight_layout(); fig.savefig("s013_sensitivity.png", dpi=130)
    print("\nSaved: s013_sensitivity.png, s013_per_instrument.csv, s013_sensitivity_expectancy.csv, s013_gates.csv")
