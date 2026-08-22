"""
Strategy 65/109 — ORBP with Price Channel Filter (Filter & Exit). Crabel +
Donchian. Rating C. https://oxfordstrat.com/trading-strategies/orbp-with-price-channel-filter/

ORB stop entry restricted to the side confirmed by a Donchian price-channel breakout:
  bullish  High[t] > UpperChannel[t-1] (highest high, Look_Back) -> LONG only
  bearish  Low[t]  < LowerChannel[t-1] (lowest low,  Look_Back) -> SHORT only
Stretch = SMA(min(H-O,O-L),10)*1. Exit: Time_Index + ATR stop(6) (no target).
Swept: Filter_Look_Back x Time_Index. Side on bar t, trade t+1 (no look-ahead).
-> Donchian-confirmed directional ORB: trend-beta (channel breakout) + intrabar-stop
   fill. Test delay+1 AND beta-matched buy&hold. Reuses orb_filtered + gates + beta_bench.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import beta_bench as bb
import orb_filtered as of

STRETCH_LEN, STRETCH_MULT, ATR_LEN, ATR_STOP = 10, 1.0, 20, 6.0
LB_REP, TM_REP = 20, 10           # Filter_Look_Back x Time_Index reference

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_ST = {t: of.crabel_stretch(df, STRETCH_LEN, STRETCH_MULT) for t, df in uni.items()}


def side_chan(df, look_back):
    upper = df['high'].rolling(look_back).max().shift(1)
    lower = df['low'].rolling(look_back).min().shift(1)
    up = df['high'] > upper        # channel breakout up -> long
    dn = df['low'] < lower         # channel breakout dn -> short
    return pd.Series(np.where(up, 1, np.where(dn, -1, 0)), index=df.index)


def run_point(look_back, time_index, fill='stop'):
    frames = []
    for t, df in uni.items():
        sd = side_chan(df, look_back)
        tr = of.simulate_orb_filtered(df, sd, _ST[t], time_index=time_index, atr_len=ATR_LEN,
                                      atr_stop=ATR_STOP, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


if __name__ == "__main__":
    pool = run_point(LB_REP, TM_REP); pm = lab.trade_metrics(pool); el, es, nl, ns = of.two_sided(pool)
    m_no = lab.trade_metrics(run_point(LB_REP, TM_REP, fill='next_open'))
    print(f"=== S065 ORBP Price Channel Filter (Look_Back={LB_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif(stop) Sharpe {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] Sharpe {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    print(f"TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    bb.beta_line(pool)
    LBs = [10, 20, 50, 100]; TMs = [1, 5, 10, 50]
    grid = np.full((len(LBs), len(TMs)), np.nan); sg = np.full_like(grid, np.nan)
    for a, lb in enumerate(LBs):
        for b_, tm in enumerate(TMs):
            m = lab.trade_metrics(run_point(lb, tm)); grid[a, b_] = m['expR']; sg[a, b_] = m['sharpe']
    pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"{x}d" for x in TMs]).to_csv("s065_sensitivity_expectancy.csv")
    print("grid expR (Look_Back x Time):\n" + pd.DataFrame(grid, index=[f"LB{x}" for x in LBs], columns=[f"{x}d" for x in TMs]).round(4).to_string())
    res = lab.run_gates(lambda fill='stop': run_point(LB_REP, TM_REP, fill=fill), sg, split='2015-12-31')
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
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s065_gates.csv", index=False)
