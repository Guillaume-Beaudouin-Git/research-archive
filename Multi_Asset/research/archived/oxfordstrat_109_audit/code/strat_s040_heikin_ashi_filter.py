"""
Strategy 40/109 — Heikin-Ashi Technique (Setup & Filter). Source rating D.
https://oxfordstrat.com/trading-strategies/heikin-ashi-2/
HA trend follower (raw-bar HA) + BODY filter (small opposite shadow) + TREND filter:
  Setup long: HA green AND (HaOpen-HaLow) <= (HaHigh-HaLow)*Body_Index AND Close[i-1]>Close[i-1-Trend_Index].
  Entry @open. Exit: HA flip (HaClose<HaOpen) @open + ATR*6. Sweep Body_Index x Trend_Index.
  -> trend follower (heritage of #39 HA) -> expect beta long. Reuses ftmo_lab v2-gates + beta_bench.
Point Body_Index=0.1, Trend_Index=20.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
BODY_REP, TI_REP = 0.10, 20

def ha_full(df):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    n = len(df); hac = (o + h + l + c) / 4.0; hao = np.full(n, np.nan)
    for i in range(n):
        hao[i] = (o[i] + c[i]) / 2.0 if i == 0 else (hao[i - 1] + hac[i - 1]) / 2.0
    hah = np.maximum.reduce([h, hao, hac]); hal = np.minimum.reduce([l, hao, hac])
    return hao, hah, hal, hac

def simulate_ha_f(df, body, trend_index, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values; hao, hah, hal, hac = ha_full(df)
    rng = (hah - hal); n = len(df); idx = df.index; trades = []; i = trend_index + 2
    while i < n - 1:
        s = i - 1
        green = hac[s] > hao[s]; red = hac[s] < hao[s]
        body_l = (hao[s] - hal[s]) <= rng[s] * body if rng[s] > 0 else False     # small lower shadow
        body_s = (hah[s] - hao[s]) <= rng[s] * body if rng[s] > 0 else False     # small upper shadow
        tup = c[i - 1] > c[i - 1 - trend_index]; tdn = c[i - 1] < c[i - 1 - trend_index]
        d = 0
        if green and body_l and tup: d = 1
        elif allow_short and red and body_s and tdn: d = -1
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        if fill == 'stop':      eb = i;     entry = o[eb]
        elif fill == 'close':   eb = i;     entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            if j > eb:                                                            # HA-flip exit @open
                if d == 1 and hac[j - 1] < hao[j - 1]: exit_p, reason, exit_j = o[j], 'haflip', j; break
                if d == -1 and hac[j - 1] > hao[j - 1]: exit_p, reason, exit_j = o[j], 'haflip', j; break
            if j == n - 1: exit_p, reason, exit_j = c[j], 'eod', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(body, trend_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_ha_f(df, body, trend_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(BODY_REP, TI_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(BODY_REP, TI_REP, fill='next_open'))
    print(f"=== S040 Heikin-Ashi + body/trend filter (Body={BODY_REP} Trend={TI_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    BIs = [0.05, 0.10, 0.20]; TIs = [10, 20, 40]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, bi in enumerate(BIs):
        for b_, ti in enumerate(TIs):
            m = lab.trade_metrics(run_point(bi, ti)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"Tr{x}" for x in TIs]).to_csv("s040_sensitivity_expectancy.csv")
    print("grid expR (Body x Trend):\n" + pd.DataFrame(grid, index=[f"B{x}" for x in BIs], columns=[f"Tr{x}" for x in TIs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(BODY_REP, TI_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    e = pd.to_datetime(pool['entry']); rec = lab.trade_metrics(pool[e > pd.Timestamp('2018-12-31')])
    print(f"RECENT 2019+: expR {rec['expR']:+.4f} Sh {rec['sharpe']:+.2f}")
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s040_gates.csv", index=False)
