"""
Strategy 72/109 — RSI(2) Model (Connors). Rating C.
https://oxfordstrat.com/trading-strategies/relative-strength-index-1/

Connors 2-period RSI mean-reversion ("buy pullbacks in a bull market"), LONG-ONLY:
  Setup : Close > SMA(Setup_LB=200)           (bull-market regime)
  Filter: RSI(2) < RSI_Threshold (default 5)   (short-term oversold)
  Entry : buy at OPEN the next day after setup+filter.
  Exit  : Trend exit -> sell at OPEN if Close[i-1] > SMA(Exit_LB) ; + ATR stop (6*ATR).
Portfolio (source): 5 equity index futures -> mapped to our 'indices' class.
This is a genuine dip-buy MR. The decisive test is BETA-MATCH: buying oversold dips in
an up-trending equity index is textbook leveraged long beta. Long-only -> Gate2 N/A.
fill='stop' = open[next] (spec baseline) ; 'next_open' = +1 extra day (delay robustness).
Reuses ftmo_lab.atr/_trade/round_turn_cost + beta_bench. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

ATR_LEN, ATR_STOP = 20, 6.0
SETUP_LB = 200
THR_REP, EXIT_REP = 10, 10          # preferred zone per fiche (5<=thr<=13, 8<=exit<=13)
CLASS = lab.CLASS
uni_all = lab.load_universe()
INDICES = [t for t in uni_all if CLASS.get(t) == 'indices']
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni_all.items()}


def rsi(close, n=2):
    d = close.diff()
    up = d.clip(lower=0.0); dn = (-d).clip(lower=0.0)
    au = up.ewm(alpha=1.0/n, adjust=False).mean()
    ad = dn.ewm(alpha=1.0/n, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return (100 - 100/(1+rs)).fillna(50)


def simulate_rsi2(df, thr, exit_lb, *, cost_bps=2.0, fill='stop'):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    ma_s = c_series = pd.Series(c, index=df.index)
    maS = c_series.rolling(SETUP_LB).mean().values
    maX = c_series.rolling(exit_lb).mean().values
    R = rsi(c_series, 2).values
    n = len(df); idx = df.index; trades = []; i = SETUP_LB + 1
    while i < n - 1:
        sig = np.isfinite(maS[i]) and c[i] > maS[i] and R[i] < thr      # setup+filter at bar i
        if not (sig and np.isfinite(A[i]) and A[i] > 0):
            i += 1; continue
        eb = i + 1 if fill == 'stop' else i + 2                          # enter next open (or +1)
        if eb > n - 1: break
        entry = o[eb]; risk0 = A[i] * ATR_STOP; cost_R = (cost_bps/1e4)*abs(entry)/risk0
        stop = entry - risk0; exit_p = exit_j = None
        for j in range(eb, n):
            if l[j] <= stop: exit_p, exit_j = stop, j; break             # ATR stop intrabar
            if np.isfinite(maX[j-1]) and c[j-1] > maX[j-1]:              # trend exit -> sell open[j]
                exit_p, exit_j = o[j], j; break
            if j == n-1: exit_p, exit_j = c[j], j; break
        trades.append(lab._trade(idx[eb], idx[exit_j], 'x', 1, (exit_p-entry)/risk0 - cost_R, exit_j-eb))
        i = exit_j + 1
    return pd.DataFrame(trades)


def run_point(thr=THR_REP, exit_lb=EXIT_REP, fill='stop', pool_instr=None):
    instrs = pool_instr if pool_instr is not None else INDICES
    frames = []
    for t in instrs:
        tr = simulate_rsi2(uni_all[t], thr, exit_lb, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S072 RSI(2) Connors dip-buy (thr={THR_REP} exit_lb={EXIT_REP}, indices, LONG-only) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: entry open[+1] Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[+2] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    bb.beta_line(pool)
    THs = [5, 10, 15, 20]; EXs = [5, 10, 20]
    grid = np.full((len(THs), len(EXs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, th in enumerate(THs):
        for b_, ex in enumerate(EXs):
            m = lab.trade_metrics(run_point(th, ex)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"thr{x}" for x in THs], columns=[f"ex{x}" for x in EXs]).to_csv("s072_sensitivity_expectancy.csv")
    print("grid expR (RSI_thr x Exit_LB):\n" + pd.DataFrame(grid, index=[f"thr{x}" for x in THs], columns=[f"ex{x}" for x in EXs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s072_gates.csv", index=False)
