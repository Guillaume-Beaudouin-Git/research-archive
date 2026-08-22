"""
Strategy 27/109 — Bearish Engulfing Candlestick (Exits). Source rating D.
https://oxfordstrat.com/trading-strategies/pattern-bearish-engulfing/
(Shared engulfing module — also serves #28 bullish, #29 Type-A, #30 Type-A+filter.)

KEY: the oxfordstrat "engulfing" strategies are NOT close-entry mean-reversion — the ENTRY is the
Crabel ORB STOP (sell stop at Open-Stretch / buy stop at Open+Stretch, Stretch=SMA(noise,10)*2),
gated by an engulfing candlestick setup. => SAME archetype as S001/S002/GSV (intrabar stop fill)
=> Gate 1 (delay+1) fill-artefact death expected.

Patterns (complete on 'today' t):
  bull : (O[t-1]>C[t-1]) & (O[t]<C[t-1]) & (C[t]>O[t-1])           -> long, ORB up
  bear : (O[t-1]<C[t-1]) & (O[t]>C[t-1]) & (C[t]<O[t-1])           -> short, ORB down
  bull Type A : bull & (H[t]>H[t-1]) & (L[t]<L[t-1])               (engulfs the whole range)
Entry day = t+1 (ORB). Initial risk = Stretch-Exit distance (Open -/+ Stretch); ATR*6 = catastrophe.
Exits: Stretch Exit + Target_Index*risk + Time_Index + ATR*6. Reuses ftmo_lab (_trade/atr/cost/gates).
"""
import numpy as np, pandas as pd
from functools import lru_cache
import ftmo_lab as lab

ATR_LEN, ATR_STOP = 20, 6.0
STRETCH_LEN, STRETCH_MULT = 10, 2.0
TI_REP, TM_REP = 3.0, 10              # representative Target_Index / Time_Index (like S001)

def crabel_stretch(df):
    o, h, l = df['open'], df['high'], df['low']
    noise = np.minimum(h - o, o - l)
    return (pd.Series(noise, index=df.index).rolling(STRETCH_LEN).mean() * STRETCH_MULT).clip(lower=0)

def eng_bull(df):
    o, c = df['open'], df['close']; oy, cy = o.shift(1), c.shift(1)
    return (oy > cy) & (o < cy) & (c > oy)
def eng_bear(df):
    o, c = df['open'], df['close']; oy, cy = o.shift(1), c.shift(1)
    return (oy < cy) & (o > cy) & (c < oy)
def eng_bull_A(df):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    return eng_bull(df) & (h > h.shift(1)) & (l < l.shift(1))
def eng_bear_A(df):
    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    return eng_bear(df) & (h > h.shift(1)) & (l < l.shift(1))

def simulate_engulf(df, setup, stretch, direction, *, target_index=TI_REP, time_index=TM_REP,
                    atr_len=ATR_LEN, atr_stop=ATR_STOP, cost_bps=2.0, fill='stop'):
    """Directional Crabel-ORB on an engulfing setup. d=+1 long (buy stop Open+Stretch) / -1 short.
       Initial risk = Stretch-Exit distance (faithful 'risk defined by exits'); ATR*6 = catastrophe stop."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values; d = direction
    n = len(df); idx = df.index
    trades = []; i = 1
    while i < n - 1:
        if not (su[i - 1] and np.isfinite(st[i - 1]) and st[i - 1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i; s0 = st[i - 1]
        trig = o[e] + d * s0
        hit = (h[e] >= trig) if d == 1 else (l[e] <= trig)
        if not hit:
            i += 1; continue
        if fill == 'stop':
            entry = max(o[e], trig) if d == 1 else min(o[e], trig); start_j = e
        elif fill == 'close':
            entry = c[e]; start_j = e
        elif fill == 'next_open':
            if e + 1 > n - 1: i += 1; continue
            entry = o[e + 1]; start_j = e + 1
        else:
            raise ValueError(fill)
        stretch_exit = o[e] - d * s0                       # Open -/+ Stretch (initial protective stop)
        risk_unit = d * (entry - stretch_exit)             # initial risk = stretch-exit distance
        atr_cat = entry - d * A[e] * atr_stop              # catastrophic backstop
        if not np.isfinite(risk_unit) or risk_unit <= 0:
            i = e + 1; continue
        cost_R = (cost_bps / 1e4) * c[e] / risk_unit
        stop_lvl = max(stretch_exit, atr_cat) if d == 1 else min(stretch_exit, atr_cat)
        tgt = entry + d * target_index * risk_unit
        last = min(e + time_index, n - 1)
        exit_p = exit_j = reason = None
        for j in range(start_j, last + 1):
            if d == 1:
                if l[j] <= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
                if h[j] >= tgt:      exit_p, reason, exit_j = tgt, 'target', j; break
            else:
                if h[j] >= stop_lvl: exit_p, reason, exit_j = stop_lvl, 'stop', j; break
                if l[j] <= tgt:      exit_p, reason, exit_j = tgt, 'target', j; break
            if j == last: exit_p, reason, exit_j = c[j], 'time', j; break
        grossR = d * (exit_p - entry) / risk_unit
        trades.append(lab._trade(idx[e], idx[exit_j], reason, d, grossR - cost_R, exit_j - e))
        i = exit_j + 1
    return pd.DataFrame(trades)

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
_STR = {t: crabel_stretch(df) for t, df in uni.items()}

def run_dir(detector, direction, target_index=TI_REP, time_index=TM_REP, fill='stop'):
    frames = []
    for t, df in uni.items():
        tr = simulate_engulf(df, detector(df), _STR[t], direction,
                             target_index=target_index, time_index=time_index, cost_bps=costs[t], fill=fill)
        if len(tr): tr['instr'] = t; frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def run_combined(target_index=TI_REP, time_index=TM_REP, fill='stop'):
    """Two-sided engulfing-ORB: bullish->long + bearish->short (proper two-sided archetype test)."""
    a = run_dir(eng_bull, 1, target_index, time_index, fill)
    b = run_dir(eng_bear, -1, target_index, time_index, fill)
    return pd.concat([a, b], ignore_index=True) if len(a) or len(b) else pd.DataFrame()

def pattern_forward_edge(detector, direction, horizon=10):
    """Decomposition: does the engulfing PATTERN itself predict reversal? Mean dir*forward close-return
       (no ORB, enter at pattern-bar close), aggregated across instruments. Net of ~3bps cost."""
    rets = []
    for t, df in uni.items():
        c = df['close'].values; su = detector(df).values.astype(bool)
        n = len(c)
        for k in np.where(su)[0]:
            if k + horizon < n and c[k] > 0:
                rets.append(direction * (c[k + horizon] - c[k]) / c[k] - 0.0003)
    r = np.array(rets)
    return (float(r.mean()) if len(r) else np.nan, len(r))

def two_sided(pool):
    r = pool['netR'].values; d = pool['dir'].values
    return (r[d == 1].mean() if (d == 1).any() else np.nan,
            r[d == -1].mean() if (d == -1).any() else np.nan, int((d == 1).sum()), int((d == -1).sum()))

if __name__ == "__main__":
    # --- bearish leg (this strategy, #27, short only) ---
    bear = run_dir(eng_bear, -1); bm = lab.trade_metrics(bear)
    bear_no = lab.trade_metrics(run_dir(eng_bear, -1, fill='next_open'))
    print(f"=== S027 Bearish Engulfing (ORB-down short, Target={TI_REP} Time={TM_REP}) ===")
    print(f"Bearish leg: trades={bm['trades']} win={bm['win']*100:.1f}% expR={bm['expR']:+.4f} PF={bm['pf']:.3f} Sharpe={bm['sharpe']:.2f} MaxDD={bm['maxdd']*100:.1f}%")
    print(f"  DELAI+1 (bear): natif {bm['sharpe']:+.2f} (expR {bm['expR']:+.4f}) -> open[i+1] {bear_no['sharpe']:+.2f} (expR {bear_no['expR']:+.4f})")
    bull = run_dir(eng_bull, 1); ulm = lab.trade_metrics(bull)
    print(f"Bullish leg (#28): trades={ulm['trades']} expR={ulm['expR']:+.4f} Sharpe={ulm['sharpe']:.2f}")
    # --- combined two-sided archetype test ---
    comb = run_combined(); cm = lab.trade_metrics(comb); el, es, nl, ns = two_sided(comb)
    comb_no = lab.trade_metrics(run_combined(fill='next_open'))
    print(f"COMBINED two-sided: trades={cm['trades']} expR={cm['expR']:+.4f} Sharpe={cm['sharpe']:.2f}")
    print(f"  DELAI+1 (combined): natif {cm['sharpe']:+.2f} (expR {cm['expR']:+.4f}) -> open[i+1] {comb_no['sharpe']:+.2f} (expR {comb_no['expR']:+.4f})")
    print(f"  TWO-SIDED: long {el:+.4f}(n{nl}) / short {es:+.4f}(n{ns})")
    # --- decomposition: pure pattern forward edge (no ORB) ---
    fb, nb = pattern_forward_edge(eng_bull, 1); fr, nr = pattern_forward_edge(eng_bear, -1)
    print(f"  PURE-PATTERN 10d fwd edge (no ORB, net): bull-long {fb:+.5f}(n{nb}) / bear-short {fr:+.5f}(n{nr})")
    # --- gates on the COMBINED two-sided system (proper archetype test) ---
    TIs = [1.0, 3.0, 6.0]; TMs = [5, 10, 20]
    sg = np.full((len(TIs), len(TMs)), np.nan)
    for a, ti in enumerate(TIs):
        for bb, tm in enumerate(TMs):
            sg[a, bb] = lab.trade_metrics(run_combined(ti, tm))['sharpe']
    res = lab.run_gates(lambda fill='stop': run_combined(fill=fill), sg, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print("\nGATES (combined two-sided engulfing-ORB):")
    for k in ['delay1 (L26)', 'twosided (L25)', 'dsr', 'oos (L31)']:
        x = g[k]; print(f"  [{'PASS' if x['pass'] else 'FAIL'}] {k}: " +
                         (f"long {x['exp_long']:+.4f}/short {x['exp_short']:+.4f}" if k.startswith('two') else
                          f"natif {x.get('opt_sharpe',0):+.2f}->reel {x.get('real_sharpe',0):+.2f}" if k.startswith('del') else
                          f"SR {x.get('SR_obs',0):.3f} vs {x.get('E_max_SR',0):.3f}" if k == 'dsr' else
                          f"train {x.get('train_expR',0):+.4f}->test {x.get('test_expR',0):+.4f}") +
                         (f"  << {x['tag']}" if x.get('tag') else ""))
    print(f">>> VERDICT (combined): {res['verdict']} | edge_pos={res['edge_positive']} | FAIL {res['n_fail']}/4 | {res['reason']}")
    pd.DataFrame([{'gate': x['gate'], 'pass': x['pass'], 'tag': x.get('tag') or ''} for x in res['gates']]).to_csv("s027_gates.csv", index=False)
    pd.DataFrame({'leg': ['bear', 'bull', 'combined'],
                  'expR': [bm['expR'], ulm['expR'], cm['expR']],
                  'sharpe': [bm['sharpe'], ulm['sharpe'], cm['sharpe']]}).to_csv("s027_sensitivity_expectancy.csv", index=False)
