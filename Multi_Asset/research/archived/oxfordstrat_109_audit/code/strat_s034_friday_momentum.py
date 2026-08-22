"""
Strategy 34/109 — Short-Term Trading: Friday Momentum (Filter). Source rating D. (Krutsinger "One Night Stand")
https://oxfordstrat.com/trading-strategies/short-term-trading-friday-momentum/

NEW archetype: WEEKDAY/seasonality momentum (weekend effect).
  Setup : FastMA(0.25*Slow) > SlowMA -> long bias ; < -> short bias.
  Filter: entry only on a FRIDAY.
  Entry : long = buy stop above HighestHigh(Long_LB)[i-1] ; short = sell stop below LowestLow(2*Long_LB)[i-1].
  Exit  : next day's open (normally Monday) + ATR(20)*6 stop.  -> "one night stand" weekend hold.
  Sweep : Slow_MA [20,80] x Long_Entry_LB [1,30]. Default 10/40 MA, 4-day(long)/8-day(short).
Fiche: "stopped working since 1993 once realistic cost applied." -> expect cost/beta death.
Reuses ftmo_lab v2-gates + beta_bench. Point Slow=40 (Fast=10), Long_LB=4.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
SLOW_REP, LLB_REP = 40, 4

def simulate_friday(df, slow, long_lb, *, atr_stop=ATR_STOP, cost_bps=2.0, allow_short=True, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    fast = max(2, int(round(0.25 * slow))); short_lb = 2 * int(long_lb)
    fma = pd.Series(c, index=df.index).rolling(fast).mean().values
    sma = pd.Series(c, index=df.index).rolling(slow).mean().values
    HH = pd.Series(h, index=df.index).rolling(int(long_lb)).max().shift(1).values
    LL = pd.Series(l, index=df.index).rolling(short_lb).min().shift(1).values
    fri = (df.index.dayofweek == 4)
    n = len(df); idx = df.index; trades = []; i = slow + 1
    while i < n - 1:
        if not fri[i] or not np.isfinite(A[i]) or A[i] <= 0 or not np.isfinite(fma[i - 1]) or not np.isfinite(sma[i - 1]):
            i += 1; continue
        d = 0
        if fma[i - 1] > sma[i - 1] and np.isfinite(HH[i]) and h[i] >= HH[i]: d = 1; lvl = HH[i]
        elif allow_short and fma[i - 1] < sma[i - 1] and np.isfinite(LL[i]) and l[i] <= LL[i]: d = -1; lvl = LL[i]
        if d == 0:
            i += 1; continue
        if fill == 'stop':      eb = i;     entry = (max(o[eb], lvl) if d == 1 else min(o[eb], lvl))
        elif fill == 'close':   eb = i;     entry = c[eb]
        elif fill == 'next_open': eb = i + 1; entry = o[eb] if eb <= n - 1 else np.nan
        else: raise ValueError(fill)
        if eb > n - 1 or not np.isfinite(entry):
            i += 1; continue
        risk0 = A[i] * atr_stop; cost_R = (cost_bps / 1e4) * abs(entry) / risk0
        stop = entry - d * risk0
        # intrabar ATR stop on entry bar, else exit at next day's open
        if d == 1 and l[eb] <= stop:   exit_p, exit_j, reason = stop, eb, 'stop'
        elif d == -1 and h[eb] >= stop: exit_p, exit_j, reason = stop, eb, 'stop'
        else:
            exit_j = eb + 1
            if exit_j > n - 1: i = eb + 1; continue
            exit_p, reason = o[exit_j], 'nextopen'
        grossR = d * (exit_p - entry) / risk0
        trades.append(dict(entry=idx[eb], exit=idx[exit_j], dir=int(d), netR=grossR - cost_R, instr=None))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_point(slow, long_lb, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_friday(df, slow, long_lb, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(SLOW_REP, LLB_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(SLOW_REP, LLB_REP, fill='next_open'))
    print(f"=== S034 Friday Momentum (Slow={SLOW_REP} Fast={max(2,round(0.25*SLOW_REP))} Long_LB={LLB_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    SLs = [20, 40, 80]; LBs = [2, 4, 8]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, sl in enumerate(SLs):
        for b_, lb_ in enumerate(LBs):
            m = lab.trade_metrics(run_point(sl, lb_)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"S{x}" for x in SLs], columns=[f"L{x}" for x in LBs]).to_csv("s034_sensitivity_expectancy.csv")
    print("grid expR (Slow x Long_LB):\n" + pd.DataFrame(grid, index=[f"S{x}" for x in SLs], columns=[f"L{x}" for x in LBs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(SLOW_REP, LLB_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s034_gates.csv", index=False)
