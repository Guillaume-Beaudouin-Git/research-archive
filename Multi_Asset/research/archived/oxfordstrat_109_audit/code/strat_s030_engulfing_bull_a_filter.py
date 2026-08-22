"""
Strategy 30/109 — Bullish Engulfing Candlestick Type A (Filter & Exit). Source rating D.
https://oxfordstrat.com/trading-strategies/pattern-bullish-engulfing-b/
Type A bullish engulfing + COUNTER-TREND FILTER: accept the pattern only when Close[setup] < MA(Close,MA_Length)
("bearish mode" = dip). ORB-up long. Exits: Time + Stretch + ATR (no Target). Sweep MA_Length x Time_Index.
The most mean-reversion-flavoured engulfing variant (dip-buy a bullish reversal). Reuses S027 module.
"""
import numpy as np, pandas as pd
import ftmo_lab as lab
import strat_s027_engulfing as s27

MA_REP, TM_REP, NO_TARGET = 50, 10, 100.0      # target disabled (#30 has no target exit)

def det_filtered(ma_len):
    def d(df):
        return s27.eng_bull_A(df) & (df['close'] < df['close'].rolling(ma_len).mean())
    return d

run = lambda fill='stop', ma=MA_REP, tm=TM_REP: s27.run_dir(det_filtered(ma), 1, NO_TARGET, tm, fill)

if __name__ == "__main__":
    pool = run(); pm = lab.trade_metrics(pool); m_no = lab.trade_metrics(run('next_open'))
    print(f"=== S030 Bullish Engulfing TYPE A + dip-filter (MA={MA_REP} Time={TM_REP}) ===")
    print(f"Pooled: trades={pm['trades']} win={pm['win']*100:.1f}% expR={pm['expR']:+.4f} PF={pm['pf']:.3f} Sharpe={pm['sharpe']:.2f} MaxDD={pm['maxdd']*100:.1f}%")
    print(f"DELAI+1: natif {pm['sharpe']:+.2f} (expR {pm['expR']:+.4f}) -> open[i+1] {m_no['sharpe']:+.2f} (expR {m_no['expR']:+.4f})")
    # pure-pattern dip forward edge (does dip-filtered bullish engulfing predict bounce?)
    def det_rep(df): return s27.eng_bull_A(df) & (df['close'] < df['close'].rolling(MA_REP).mean())
    fb, nb = s27.pattern_forward_edge(det_rep, 1)
    print(f"PURE-PATTERN 10d fwd edge (dip-filtered, no ORB, net): {fb:+.5f}(n{nb})")
    MAs = [20, 50, 100]; TMs = [5, 10, 20]; sg = np.full((len(MAs), len(TMs)), np.nan)
    for a, ma in enumerate(MAs):
        for bb, tm in enumerate(TMs): sg[a, bb] = lab.trade_metrics(run('stop', ma, tm))['sharpe']
    res = lab.run_gates(lambda fill='stop': run(fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("GATES:")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") + (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT: {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s030_gates.csv", index=False)
