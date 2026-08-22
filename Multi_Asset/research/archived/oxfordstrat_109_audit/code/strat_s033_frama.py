"""
Strategy 33/109 — Fractal Adaptive Moving Average (Setup). Source rating C. (John Ehlers)
https://oxfordstrat.com/trading-strategies/fractal-adaptive-moving-average/

Trend-following ADAPTIVE-MA band breakout:
  FRAMA(price=(H+L)/2, L): EMA with alpha = exp(-4.6*(D-1)), D = fractal dimension from half/full ranges.
  Bands: Entry_Upper/Lower = FRAMA +/- ATR_Band*ATR(L). Exit bands at 0.5*ATR_Band.
  Setup long: Close[i-1] > Entry_Upper[i-1] (break above) -> BUY @ OPEN[i]. Short symmetric.
  Exit: Trend exit (Close[i-1] crosses back inside the 0.5 band) @ open + ATR(20)*6 stop.
  Sweep: FRAMA_Length x ATR_Band. Fiche: "not significantly better than alternatives."

Trend breakout, entry@open (no stop fill-artefact) -> expect Gate 2 long-beta (like KAMA/MA cluster).
Reuses ftmo_lab v2-gates + beta_bench. Point FRAMA_Length=80, ATR_Band=3 (base case).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_STOP_LEN, ATR_STOP = 20, 6.0
FL_REP, AB_REP = 80, 3.0

def frama(df, length):
    length = max(4, int(length) // 2 * 2); half = length // 2
    h = df['high']; l = df['low']; price = ((h + l) / 2).values
    Hh = h.rolling(length).max(); Ll = l.rolling(length).min()
    H1 = h.rolling(half).max(); L1 = l.rolling(half).min()
    H2 = h.shift(half).rolling(half).max(); L2 = l.shift(half).rolling(half).min()
    N1 = ((H1 - L1) / half).values; N2 = ((H2 - L2) / half).values; N3 = ((Hh - Ll) / length).values
    with np.errstate(divide='ignore', invalid='ignore'):
        D = (np.log(N1 + N2) - np.log(N3)) / np.log(2.0)
    alpha = np.exp(-4.6 * (D - 1.0)); alpha = np.clip(alpha, 0.01, 1.0)
    n = len(price); fr = np.full(n, np.nan)
    for i in range(n):
        if not np.isfinite(alpha[i]) or not np.isfinite(price[i]):
            continue
        fr[i] = price[i] if (i == 0 or not np.isfinite(fr[i - 1])) else alpha[i] * price[i] + (1 - alpha[i]) * fr[i - 1]
    return fr

def simulate_frama(df, length, atr_band, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    fr = frama(df, length); atrL = lab.atr(df, max(4, int(length) // 2 * 2)).values
    As = lab.atr(df, ATR_STOP_LEN).values
    up = fr + atr_band * atrL; lo = fr - atr_band * atr_band * 0 - atr_band * atrL  # lower band
    xu = fr + 0.5 * atr_band * atrL; xl = fr - 0.5 * atr_band * atrL
    n = len(df); idx = df.index; trades = []; i = 1
    while i < n - 1:
        ls = np.isfinite(up[i - 1]) and c[i - 1] > up[i - 1]
        ss = allow_short and np.isfinite(lo[i - 1]) and c[i - 1] < lo[i - 1]
        if not (ls or ss) or not np.isfinite(As[i]) or As[i] <= 0:
            i += 1; continue
        d = 1 if ls else -1
        if fill == 'stop':      eb = i;     entry = o[eb]
        elif fill == 'close':   eb = i;     entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = As[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0; exit_p = exit_j = reason = None
        for j in range(eb, n):
            if d == 1 and l[j] <= stop:  exit_p, reason, exit_j = stop, 'stop', j; break
            if d == -1 and h[j] >= stop: exit_p, reason, exit_j = stop, 'stop', j; break
            # trend exit: close crosses back inside the 0.5 band -> exit at next open
            if j > eb:
                if d == 1 and np.isfinite(xl[j - 1]) and c[j - 1] < xl[j - 1]:
                    exit_p, reason, exit_j = o[j], 'trend', j; break
                if d == -1 and np.isfinite(xu[j - 1]) and c[j - 1] > xu[j - 1]:
                    exit_p, reason, exit_j = o[j], 'trend', j; break
            if j == n - 1: exit_p, reason, exit_j = c[j], 'eod', j; break
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(length, atr_band, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_frama(df, length, atr_band, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(FL_REP, AB_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(FL_REP, AB_REP, fill='next_open'))
    print(f"=== S033 FRAMA (Length={FL_REP} ATR_Band={AB_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    FLs = [40, 80, 120]; ABs = [1.0, 3.0, 5.0]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, fl in enumerate(FLs):
        for b_, ab in enumerate(ABs):
            m = lab.trade_metrics(run_point(fl, ab)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"L{x}" for x in FLs], columns=[f"B{x}" for x in ABs]).to_csv("s033_sensitivity_expectancy.csv")
    print("grid expR (FRAMA_Length x ATR_Band):\n" + pd.DataFrame(grid, index=[f"L{x}" for x in FLs], columns=[f"B{x}" for x in ABs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(FL_REP, AB_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s033_gates.csv", index=False)
