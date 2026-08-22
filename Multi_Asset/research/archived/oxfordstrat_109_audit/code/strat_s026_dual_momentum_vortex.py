"""
Strategy 26/109 — Dual Momentum & Vortex Indicator (Entry). Source rating C. (Botes & Siepman)
https://oxfordstrat.com/trading-strategies/dual-momentum-vortex-indicator/

SAME dual-momentum structure as #25 (slow filter + fast setup + extreme-point breakout + Time/ATR exit),
but the momentum indicator is the VORTEX (+VI / -VI) instead of ROC:
  TR[i]=max(H,C[-1])-min(L,C[-1]); +VM=|H[i]-L[i-1]|; -VM=|L[i]-H[i-1]|.
  +VI_lb = sum(+VM,lb)/sum(TR,lb) ; -VI_lb = sum(-VM,lb)/sum(TR,lb). Slow=LB1, Fast=LB2=round(LB1*0.5).
  Filter long: +VI1>-VI1 ; Setup long: +VI2>-VI2 (regime_long = both). Short symmetric.
The fiche itself states ROC and Vortex have similar risk-adjusted returns -> HERITAGE of #25.

Reuses S025.simulate_dual_mom UNCHANGED (only the regime differs). Momentum/trend => Gate 2 long-beta
expected. ftmo_lab v2-gates inchangé; cached run_point.
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab
import strat_s025_dual_momentum_roc as s25

ATR_LEN, ATR_STOP = 20, 6.0
LB1_REP, TM_REP = 100, 51
uni, costs = s25.uni, s25.costs

def vortex_regime(df, lb1):
    lb2 = max(2, int(round(lb1 * 0.5)))
    h, l, c = df['high'], df['low'], df['close']
    pc = c.shift(1)
    tr = pd.concat([h, pc], axis=1).max(axis=1) - pd.concat([l, pc], axis=1).min(axis=1)
    vmp = (h - l.shift(1)).abs(); vmm = (l - h.shift(1)).abs()
    def vi(lb):
        trs = tr.rolling(lb).sum()
        return vmp.rolling(lb).sum() / trs, vmm.rolling(lb).sum() / trs
    vip1, vim1 = vi(lb1); vip2, vim2 = vi(lb2)
    reg_long = (vip1 > vim1) & (vip2 > vim2)
    reg_short = (vim1 > vip1) & (vim2 > vip2)
    return reg_long, reg_short, lb2

@lru_cache(maxsize=None)
def run_point(lb1, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        rl, rs, lb2 = vortex_regime(df, lb1)
        tr = s25.simulate_dual_mom(df, rl, rs, lb2, time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(LB1_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB1_REP, TM_REP, fill='next_open'))
    print(f"=== S026 Dual Momentum VORTEX (LB1={LB1_REP}/LB2={max(2,round(LB1_REP*0.5))} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    LB1s = [40, 100, 160]; TMs = [26, 51, 101]
    grid = np.full((len(LB1s), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, lb1 in enumerate(LB1s):
        for bb, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb1, tm)); grid[a, bb] = m['expR']; sg[a, bb] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LB1s], columns=[f"Tm{x}" for x in TMs]).to_csv("s026_sensitivity_expectancy.csv")
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s026_gates.csv", index=False)
