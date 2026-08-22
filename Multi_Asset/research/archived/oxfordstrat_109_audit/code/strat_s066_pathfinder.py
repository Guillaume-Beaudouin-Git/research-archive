"""
Strategy 66/109 — Intermarket Analysis: The Pathfinder (Filter). Nelson Freeburg. Rating C.
https://oxfordstrat.com/trading-strategies/intermarket-analysis-pathfinder/

INTERMARKET currency system. Setup (currency): MA2(9)>MA3(18) AND MA1(6) rising -> long
(opposite -> short). FILTER (intermarket): T-bond 3d-MA > 25d-MA confirms longs.
Entry @open; exit on MA2/MA3 cross @next open + ATR stop. Portfolio = JY/EUR/CHF/GBP.

** IMPORTANT — FTMO reproducibility **: the DEFINING feature is the T-BOND filter, and
the FTMO universe has NO Treasury instrument -> the intermarket filter is NOT reproducible.
Moreover the source's OWN benchmark (Table 2) shows the Pathfinder IMPROVED the base case in
1980-1995 (Sharpe 0.88 vs 0.79) but was WORSE in 1996-2015 (Sharpe 0.06 vs 0.17, PF 1.03 vs
1.08): the bond->currency edge DECAYED to nothing. So we test the FTMO-tradable BASE CASE =
the dual-MA currency trend system (no T-bond filter) on the Pathfinder currencies, and judge
it on the gates. Archetype = MA-trend = beta. Reuses trend_lab (entry@open state machine).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import trend_lab as tl

PAIRS = ['EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF']     # JY/EUR/CHF/GBP analogues in FTMO forex
SI_REP, SLOPE_REP = 1.0, 1
_uni0 = lab.load_universe()
uni = {t: _uni0[t] for t in PAIRS if t in _uni0}
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}


def sig(setup_index, slope_lb):
    lb1, lb2, lb3 = round(6 * setup_index), round(9 * setup_index), round(18 * setup_index)
    def f(df):
        c = df['close']; ma1 = c.rolling(lb1).mean(); ma2 = c.rolling(lb2).mean(); ma3 = c.rolling(lb3).mean()
        wl = (ma2 > ma3) & (ma1 > ma1.shift(slope_lb))
        ws = (ma2 < ma3) & (ma1 < ma1.shift(slope_lb))
        return wl.fillna(False), ws.fillna(False)
    return f


def run_pt(setup_index=SI_REP, slope_lb=SLOPE_REP, fill='stop'):
    return tl.run_state(uni, costs, sig(setup_index, slope_lb), fill=fill)


if __name__ == "__main__":
    pool = run_pt(); pm = lab.trade_metrics(pool); el, es, nl, ns = tl.two_sided(pool)
    m_no = lab.trade_metrics(run_pt(fill='next_open'))
    print("=== S066 Pathfinder — BASE CASE (dual-MA currency trend; T-bond filter NON reproductible FTMO) ===")
    print(f"Pooled(4 devises): trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(open) {pm['sharpe']:+.2f} -> open[i+1] {m_no['sharpe']:+.2f}")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    SIs = [0.5, 1.0, 2.0, 3.0]; SLs = [1, 2, 3]
    sg = np.full((len(SIs), len(SLs)), np.nan)
    for a, si in enumerate(SIs):
        for b_, sl in enumerate(SLs):
            sg[a, b_] = lab.trade_metrics(run_pt(si, sl))['sharpe']
    pd.DataFrame(sg, index=[f"SI{x}" for x in SIs], columns=[f"sl{x}" for x in SLs]).to_csv("s066_sensitivity_expectancy.csv")
    print("grid Sharpe (Setup_Index x slope_lb):\n" + pd.DataFrame(sg, index=[f"SI{x}" for x in SIs], columns=[f"sl{x}" for x in SLs]).round(2).to_string())
    res = lab.run_gates(lambda fill='stop': run_pt(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s066_gates.csv", index=False)
