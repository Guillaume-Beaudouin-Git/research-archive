"""
Strategy 25/109 — Dual Momentum & Rate of Change (Entry). Source rating C.
https://oxfordstrat.com/trading-strategies/dual-momentum-rate-of-change/

NEW archetype: DUAL absolute-momentum (slow filter + fast setup), breakout entry.
  ROC1 (slow, Look_Back_#1) = (C[i]-C[i-LB1+1])/(LB1-1) ; ROC2 (fast, LB2=round(LB1*0.5)).
  Filter : long if ROC1>0 ; short if ROC1<0.      Setup : long if ROC2>0 ; short if ROC2<0.
  Entry  : Extreme Point Rule = buy when price moves beyond the recent extreme while both ROC>0
           (operationalised as breakout of the fast-window high) ; sell symmetric.
  Exit   : Time Exit (Time_Index) + ATR(20)*6.   Sweep : Look_Back_#1 x Time_Index.
Fiche: "longer holding preferred (Time>50)"; Sharpe 0.55-0.90 w/ cost, MaxDD -47..-78% -> classic CTA.

Defines the SHARED dual-momentum simulator reused by S026 (Vortex). Momentum/trend => Gate 2
long-beta expected (CTA = beta). ftmo_lab v2-gates inchangé; cached run_point.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
LB1_REP, TM_REP = 100, 51            # representative: slow=100 / fast=50, ~51-day hold (fiche: Time>50)

def roc(close, lb):
    return (close - close.shift(lb - 1)) / (lb - 1)

def simulate_dual_mom(df, reg_long, reg_short, lb_fast, time_index, atr_len=ATR_LEN, atr_stop=ATR_STOP,
                      cost_bps=2.0, allow_short=True, fill='stop'):
    """Shared dual-momentum extreme-point breakout. reg_long/reg_short = bool Series (slow&fast aligned),
       used CAUSALLY (shifted). Extreme point = fast-window high/low (Donchian-LB_fast) breakout. Time+ATR exit."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    ub = pd.Series(h, index=df.index).rolling(lb_fast).max().shift(1).values   # extreme-point (long)
    lb_ = pd.Series(l, index=df.index).rolling(lb_fast).min().shift(1).values  # extreme-point (short)
    rl = reg_long.shift(1, fill_value=False).values.astype(bool)               # causal regime
    rs = reg_short.shift(1, fill_value=False).values.astype(bool)
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        long_sig = rl[i] and np.isfinite(ub[i]) and h[i] >= ub[i] and h[i - 1] < ub[i]
        short_sig = allow_short and rs[i] and np.isfinite(lb_[i]) and l[i] <= lb_[i] and l[i - 1] > lb_[i]
        if not (long_sig or short_sig) or not np.isfinite(A[i]):
            i += 1; continue
        e = i; d = 1 if long_sig else -1
        lvl = ub[e] if d == 1 else lb_[e]
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk0
        if fill == 'stop':
            entry = max(o[e], lvl) if d == 1 else min(o[e], lvl); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        stop = entry - d * risk0
        last = min(e + time_index, n - 1)
        seg = slice(start_j, last + 1)
        cond = (l[seg] <= stop) if d == 1 else (h[seg] >= stop)
        if cond.any():
            k = int(np.argmax(cond)); exit_j = start_j + k; exit_p, reason = stop, 'atr'
        else:
            exit_j = last; exit_p, reason = c[last], 'time'
        grossR = d * (exit_p - entry) / risk0
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def roc_regime(df, lb1):
    lb2 = max(2, int(round(lb1 * 0.5)))
    r1, r2 = roc(df['close'], lb1), roc(df['close'], lb2)
    return (r1 > 0) & (r2 > 0), (r1 < 0) & (r2 < 0), lb2

@lru_cache(maxsize=None)
def run_point(lb1, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        rl, rs, lb2 = roc_regime(df, lb1)
        tr = simulate_dual_mom(df, rl, rs, lb2, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(LB1_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB1_REP, TM_REP, fill='next_open'))
    print(f"=== S025 Dual Momentum ROC (LB1={LB1_REP}/LB2={max(2,round(LB1_REP*0.5))} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    LB1s = [40, 100, 160]; TMs = [26, 51, 101]
    grid = np.full((len(LB1s), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, lb1 in enumerate(LB1s):
        for bb, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb1, tm)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LB1s], columns=[f"Tm{x}" for x in TMs]).to_csv("s025_sensitivity_expectancy.csv")
    print("grid expR (LB1 x Time):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LB1s], columns=[f"Tm{x}" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(LB1_REP, TM_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s025_gates.csv", index=False)
