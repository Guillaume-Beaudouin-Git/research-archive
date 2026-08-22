"""
Strategy 43/109 — Hook Pattern (Exits). Source rating D. (Toby Crabel)
https://oxfordstrat.com/trading-strategies/pattern-hook/
Hook setup + Crabel ORB-stop entry (SAME engine as S001/Engulfing):
  Long hook : Open[i] > High[i-1] & Close[i] < Close[i-1] & range narrowing (failed gap-up, weak close).
  Short hook: Open[i] < Low[i-1] & Close[i] > Close[i-1] & narrowing.
  Entry: ORB next day, buy stop Open+Stretch (long) / sell stop Open-Stretch (short), Stretch=Crabel noise*2.
  Exit: Target_Index x Time_Index (+ ATR). -> ORB-stop -> Gate 1 fill-artefact (heritage S001/GSV/Engulfing).
Reuses s027.simulate_engulf (directional Crabel-ORB) + s027.crabel_stretch + ftmo_lab + beta_bench.
#43 = both hooks (long+short) ; #44 = bear (short) ; #45 = bull (long).
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import strat_s027_engulfing as s27

TI_REP, TM_REP = 3.0, 10
uni, costs = s27.uni, s27.costs
_STR = {t: s27.crabel_stretch(df) for t, df in uni.items()}

def hook_long(df):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    rng = h - l
    return (o > h.shift(1)) & (c < c.shift(1)) & (rng < rng.shift(1))
def hook_short(df):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    rng = h - l
    return (o < l.shift(1)) & (c > c.shift(1)) & (rng < rng.shift(1))

def run_point(target_index, time_index, fill='stop', side='both'):
    frames = []
    for t, df in uni.items():
        if side in ('both', 'long'):
            a = s27.simulate_engulf(df, hook_long(df), _STR[t], 1, target_index=target_index,
                                    time_index=time_index, cost_bps=costs[t], fill=fill)
            if len(a): a['instr'] = t; frames.append(a)
        if side in ('both', 'short'):
            b = s27.simulate_engulf(df, hook_short(df), _STR[t], -1, target_index=target_index,
                                    time_index=time_index, cost_bps=costs[t], fill=fill)
            if len(b): b['instr'] = t; frames.append(b)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    pool = run_point(TI_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = two_sided(pool)
    m_no = lab.trade_metrics(run_point(TI_REP, TM_REP, fill='next_open'))
    print(f"=== S043 Hook Pattern (Crabel-ORB, Target={TI_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    TIs = [1.0, 3.0, 6.0]; TMs = [5, 10, 20]; grid = np.full((3, 3), np.nan); sg = np.full((3, 3), np.nan)
    for a, ti in enumerate(TIs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(ti, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs]).to_csv("s043_sensitivity_expectancy.csv")
    print("grid expR (Target x Time):\n" + pd.DataFrame(grid, index=[f"{x}R" for x in TIs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
    print(f"Share positive: {np.mean(grid>0)*100:.0f}%")
    res = lab.run_gates(lambda fill='stop': run_point(TI_REP, TM_REP, fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for kk in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[kk]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {kk}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if kk.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if kk.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if kk == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    e = pd.to_datetime(pool['entry']); rec = lab.trade_metrics(pool[e > pd.Timestamp('2018-12-31')])
    print(f"RECENT 2019+: expR {rec['expR']:+.4f} Sh {rec['sharpe']:+.2f}  | (#45 bull-only / #44 bear-only computed in their files)")
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s043_gates.csv", index=False)
