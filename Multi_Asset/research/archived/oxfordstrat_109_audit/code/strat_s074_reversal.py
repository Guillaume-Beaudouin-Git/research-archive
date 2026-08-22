"""
Strategy 74/109 — Reversal Patterns Part 1 (Wyckoff/Crabel). Rating C.
https://oxfordstrat.com/trading-strategies/reversal-patterns-1/

Supply/Demand PIVOT reversal (two-sided):
  Demand pivot = fractal low (low[q] is min over +/-Pivot_Size bars), confirmed q+PS.
  Bottom reversal (LONG) at bar i: price broke BELOW a confirmed demand pivot within
    Trap_Duration bars, then a reversal bar i with:
      (A) close[i] > close[i-1] and close[i] > close[i-2]
      (B) close[i] > demand-pivot level
      (C) close[i] > open[i] and close[i] > mid-range (H+L)/2
      (D) range[i] > range[i-1]
  Top reversal (SHORT) = mirror (supply pivot = fractal high).
  Entry: open[i+1]. Exits: Quick stop (true low/high of setup bar) | RR target
    (Entry +/- initial_risk*Reward_Ratio, initial_risk = entry-quick_stop) | ATR stop
    (6*ATR) | Time (Trade_Duration). R-normalised by risk0 = ATR*6.
Fiche: "very sensitive to costs; only large targets (RR~8) work" (Case#1 RR=2 Sharpe -0.32).
Sweep Reward_Ratio x Trade_Duration. Reuses ftmo_lab + beta_bench. ftmo_lab UNCHANGED.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb

PS, TRAP, ATR_LEN, ATR_STOP = 5, 5, 20, 6.0
RR_REP, TD_REP = 4.0, 20
uni = lab.load_universe(); costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def simulate_rev(df, reward_ratio, trade_dur, *, cost_bps=2.0, fill='stop', macd_div=False):
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, ATR_LEN).values
    cs = pd.Series(c, index=df.index)
    is_dlow = (pd.Series(l, index=df.index) == pd.Series(l, index=df.index).rolling(2*PS+1, center=True).min()).values
    is_shigh = (pd.Series(h, index=df.index) == pd.Series(h, index=df.index).rolling(2*PS+1, center=True).max()).values
    ml = (cs.ewm(span=12, adjust=False).mean() - cs.ewm(span=26, adjust=False).mean()).values  # MACD line (#75)
    n = len(df); idx = df.index; trades = []
    dp = sp = np.nan; dp_bar = sp_bar = -1; broke_below = broke_above = -10**9
    i = PS + 2
    while i < n - 1:
        q = i - PS                                   # pivot bar now confirmable
        if q >= 0 and is_dlow[q]: dp = l[q]; dp_bar = q
        if q >= 0 and is_shigh[q]: sp = h[q]; sp_bar = q
        if np.isfinite(dp) and l[i] < dp and i > dp_bar: broke_below = i
        if np.isfinite(sp) and h[i] > sp and i > sp_bar: broke_above = i
        rng = h[i] - l[i]; mid = (h[i] + l[i]) / 2.0
        d = 0
        long_ok = (np.isfinite(dp) and (i - broke_below) <= TRAP and broke_below > dp_bar
                   and c[i] > c[i-1] and c[i] > c[i-2] and c[i] > dp
                   and c[i] > o[i] and c[i] > mid and rng > (h[i-1]-l[i-1]))
        short_ok = (np.isfinite(sp) and (i - broke_above) <= TRAP and broke_above > sp_bar
                    and c[i] < c[i-1] and c[i] < c[i-2] and c[i] < sp
                    and c[i] < o[i] and c[i] < mid and rng > (h[i-1]-l[i-1]))
        if macd_div:        # #75: require price-momentum (MACD) divergence at the pivot
            long_ok = long_ok and dp_bar >= 0 and ml[i] > ml[dp_bar]    # lower low, higher MACD
            short_ok = short_ok and sp_bar >= 0 and ml[i] < ml[sp_bar]
        if long_ok: d = 1
        elif short_ok: d = -1
        if d == 0 or not np.isfinite(A[i]) or A[i] <= 0:
            i += 1; continue
        eb = i + 1 if fill == 'stop' else i + 2
        if eb > n - 1: break
        entry = o[eb]; risk0 = A[i]*ATR_STOP; cost_R = (cost_bps/1e4)*abs(entry)/risk0
        tl = min(l[i], c[i-1]); th = max(h[i], c[i-1])           # true low/high of setup bar
        if d == 1:
            quick = tl; ini = max(entry - quick, 1e-9); tgt = entry + ini*reward_ratio; astop = entry - A[i]*ATR_STOP
        else:
            quick = th; ini = max(quick - entry, 1e-9); tgt = entry - ini*reward_ratio; astop = entry + A[i]*ATR_STOP
        last = min(eb + trade_dur, n - 1); exit_p = exit_j = None
        for j in range(eb, last + 1):
            if d == 1:
                if l[j] <= quick: exit_p, exit_j = quick, j; break
                if l[j] <= astop: exit_p, exit_j = astop, j; break
                if h[j] >= tgt: exit_p, exit_j = tgt, j; break
            else:
                if h[j] >= quick: exit_p, exit_j = quick, j; break
                if h[j] >= astop: exit_p, exit_j = astop, j; break
                if l[j] <= tgt: exit_p, exit_j = tgt, j; break
            if j == last: exit_p, exit_j = c[j], j; break
        trades.append(lab._trade(idx[eb], idx[exit_j], 'x', d, d*(exit_p-entry)/risk0 - cost_R, exit_j-eb))
        i = exit_j + 1
    return pd.DataFrame(trades)


def run_point(reward_ratio=RR_REP, trade_dur=TD_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_rev(df, reward_ratio, trade_dur, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan, r[d == -1].mean() if (d == -1).any() else np.nan,
            int((d == 1).sum()), int((d == -1).sum()))


if __name__ == "__main__":
    pool = run_point(); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(fill='next_open'))
    print(f"=== S074 Reversal Patterns (pivots, RR={RR_REP} Trade_Dur={TD_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: open[+1] {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[+2] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    RRs = [2.0, 4.0, 8.0]; TDs = [10, 20, 40]
    grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, rr in enumerate(RRs):
        for b_, td in enumerate(TDs):
            m = lab.trade_metrics(run_point(rr, td)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"RR{x}" for x in RRs], columns=[f"TD{x}" for x in TDs]).to_csv("s074_sensitivity_expectancy.csv")
    print("grid expR (Reward_Ratio x Trade_Dur):\n" + pd.DataFrame(grid, index=[f"RR{x}" for x in RRs], columns=[f"TD{x}" for x in TDs]).round(4).to_string())
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s074_gates.csv", index=False)
