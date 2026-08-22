"""S104 — TD Setup-Trend (DeMark). Rating N/A (indicator).
https://oxfordstrat.com/indicators/td-setup-trend/
Reverse of TD reversal: trade IN the direction of a completed 9-bar setup (momentum continuation).
Long: 9 consecutive Close>Close[-4] -> buy at completion close. Short mirror. Time exit + ATR.
= momentum/trend -> beta. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd, ftmo_lab as lab, beta_bench as bb
SL_REP, TM_REP, SB = 9, 10, 4
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
def simulate(df, sl, tm, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close')); A = lab.atr(df, 20).values
    cs = pd.Series(c, index=df.index)
    up = (cs > cs.shift(SB)).rolling(sl).sum().values    # 9 consecutive up vs close[-4]
    dn = (cs < cs.shift(SB)).rolling(sl).sum().values
    n = len(df); idx = df.index; trades = []; i = sl + SB
    while i < n - 1:
        d = 1 if up[i] == sl else (-1 if dn[i] == sl else 0)
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0: i += 1; continue
        eb = i if fill == 'stop' else i + 1            # 'stop'=enter at completion close; next_open=+1
        entry = c[i] if fill == 'stop' else (o[eb] if eb <= n-1 else np.nan)
        if eb > n-1 or not np.isfinite(entry): i += 1; continue
        risk0 = A[i]*6; cost_R = (cost_bps/1e4)*abs(entry)/risk0; stop = entry - d*risk0
        last = min(eb+tm, n-1); xp = xj = None
        for j in range(eb, last+1):
            if d == 1 and l[j] <= stop: xp, xj = stop, j; break
            if d == -1 and h[j] >= stop: xp, xj = stop, j; break
            if j == last: xp, xj = c[j], j; break
        trades.append(lab._trade(idx[eb], idx[xj], 'x', d, d*(xp-entry)/risk0 - cost_R, xj-eb))
        i = xj + 1
    return pd.DataFrame(trades)
def run_point(sl=SL_REP, tm=TM_REP, fill='stop'):
    fr = []
    for t, df in uni.items():
        tr = simulate(df, sl, tm, costs[t], fill)
        if len(tr): tr['instr'] = t; fr.append(tr)
    return pd.concat(fr, ignore_index=True) if fr else pd.DataFrame()
def two_sided(p):
    r = p['netR'].values; d = p['dir'].values
    return (r[d==1].mean() if (d==1).any() else np.nan, r[d==-1].mean() if (d==-1).any() else np.nan, int((d==1).sum()), int((d==-1).sum()))
if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S104 TD Setup-Trend (Setup={SL_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(close) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})"); bb.beta_line(pool)
    SLs = [7, 9, 13]; TMs = [5, 10, 20]; sg = np.full((3, 3), np.nan)
    for a, sl in enumerate(SLs):
        for b_, tm in enumerate(TMs): sg[a, b_] = lab.trade_metrics(run_point(sl, tm))['sharpe']
    pd.DataFrame(sg).to_csv("s104_sensitivity_expectancy.csv")
    res = lab.run_gates(lambda fill='stop': run_point(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s104_gates.csv", index=False)
