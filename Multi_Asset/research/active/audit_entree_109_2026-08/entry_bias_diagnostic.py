"""
Chantier A/B -- quantify the ENTRY dual-breakout ambiguity bias.

Method (mirrors the sister exit-bias study's chantier A.2 -- the SAME clean
decomposition, no guessed "fair" rule): for every ambiguous bar (both the buy-stop
and the sell-stop touched on the same daily bar), compute what the trade's outcome
WOULD have been under a forced-long resolution and under a forced-short resolution
(same subsequent exit logic: target / time / ATR stop, exactly the tail of
ftmo_lab.simulate_bracket, unchanged). unbiased_R = 0.5*(long_R + short_R) -- a fair
coin-flip assumption, consistent with the ORB stretch being symmetric around the
day's open (no directional prior). bias = current_code_R (-2*stretch/risk0 - cost_R)
minus unbiased_R.

This is a DIAGNOSTIC wrapper: it reproduces ftmo_lab.simulate_bracket's entry/exit
mechanics verbatim for the counterfactual continuations, but does not modify or
import-patch ftmo_lab.py itself (read-only on the archived corpus).
"""
import sys, os
import numpy as np, pandas as pd

CODE_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/code"
sys.path.insert(0, CODE_DIR)
os.environ["OHLC_DIR"] = os.path.join(os.path.dirname(CODE_DIR), "ohlc")
STUDY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/audit_entree_109_2026-08"
import ftmo_lab as lab


def _forced_exit(o, h, l, c, A, e, n, d, target_index, time_index, atr_stop, cost_bps, buy, sell,
                  fill='stop'):
    """Verbatim re-implementation of the post-entry-fill tail of
    ftmo_lab.simulate_bracket (lines ~127-149), forcing direction `d` at bar e.
    `fill` mirrors the corpus's own L26 lever: 'stop' = optimistic native fill (the
    corpus default), 'next_open' = realistic delay+1 fill (Gate 1's own realistic
    leg) -- needed because ftmo_lab's 'both' short-circuit hardcodes -2R regardless
    of `fill`, so the REALISTIC (delay+1) reported number is ALSO contaminated by
    this same entry-ambiguity bug and must be corrected on its own terms, not by
    assuming the stop-fill correction transfers unchanged."""
    risk0 = A[e] * atr_stop
    if not np.isfinite(risk0) or risk0 <= 0:
        return np.nan, e
    cost_R = (cost_bps / 1e4) * c[e] / risk0
    if fill == 'stop':
        entry = max(o[e], buy) if d == 1 else min(o[e], sell); start_j = e
    elif fill == 'next_open':
        if e + 1 > n - 1:
            return np.nan, e
        entry = o[e + 1]; start_j = e + 1
    elif fill == 'close':
        entry = c[e]; start_j = e
    else:
        raise ValueError(fill)
    stop = entry - d * risk0
    tgt = entry + d * target_index * risk0
    last = min(e + time_index, n - 1)
    exit_p = None; exit_j = last
    for j in range(start_j, last + 1):
        if d == 1:
            if l[j] <= stop: exit_p = stop; exit_j = j; break
            if h[j] >= tgt: exit_p = tgt; exit_j = j; break
        else:
            if h[j] >= stop: exit_p = stop; exit_j = j; break
            if l[j] <= tgt: exit_p = tgt; exit_j = j; break
        if j == last:
            exit_p = c[j]; exit_j = j; break
    if exit_p is None:
        exit_p = c[last]; exit_j = last
    grossR = d * (exit_p - entry) / risk0
    return grossR - cost_R, exit_j


def diagnostic_bracket(df, setup, stretch, *, target_index, time_index, atr_len=20, atr_stop=6.0,
                        cost_bps=2.0, allow_short=True, instr=""):
    """Runs the ORIGINAL simulate_bracket sequencing unchanged (so pooled counts /
    aggregate stats reproduce the corpus exactly) but additionally records, for every
    'both' bar, the forced-long and forced-short counterfactual R -- without altering
    which bar the main loop resumes from (i = e+1 for 'both', exactly as ftmo_lab)."""
    o, h, l, c = (df[x].values for x in ('open', 'high', 'low', 'close'))
    A = lab.atr(df, atr_len).values
    su = setup.values.astype(bool); st = stretch.values
    n = len(df); idx = df.index
    diag = []
    i = 1
    while i < n - 1:
        if not (su[i-1] and np.isfinite(st[i-1]) and st[i-1] > 0 and np.isfinite(A[i])):
            i += 1; continue
        e = i
        buy, sell = o[e] + st[i-1], o[e] - st[i-1]
        long_hit = h[e] >= buy
        short_hit = (l[e] <= sell) and allow_short
        risk0 = A[e] * atr_stop
        if not np.isfinite(risk0) or risk0 <= 0:
            i += 1; continue
        cost_R = (cost_bps/1e4) * c[e] / risk0
        if long_hit and short_hit:
            assumed_R = -2*st[i-1]/risk0 - cost_R  # ftmo_lab's hardcoded penalty, SAME regardless of fill
            long_R, long_j = _forced_exit(o, h, l, c, A, e, n, 1, target_index, time_index, atr_stop, cost_bps, buy, sell, fill='stop')
            short_R, short_j = _forced_exit(o, h, l, c, A, e, n, -1, target_index, time_index, atr_stop, cost_bps, buy, sell, fill='stop')
            long_R_no1, _ = _forced_exit(o, h, l, c, A, e, n, 1, target_index, time_index, atr_stop, cost_bps, buy, sell, fill='next_open')
            short_R_no1, _ = _forced_exit(o, h, l, c, A, e, n, -1, target_index, time_index, atr_stop, cost_bps, buy, sell, fill='next_open')
            day_range_over_atr = (h[e] - l[e]) / A[e] if np.isfinite(A[e]) and A[e] > 0 else np.nan
            stretch_over_atr = st[i-1] / A[e] if np.isfinite(A[e]) and A[e] > 0 else np.nan
            diag.append(dict(instr=instr, date=idx[e], assumed_R=assumed_R, long_R=long_R, short_R=short_R,
                              unbiased_R=0.5*(long_R+short_R),
                              unbiased_R_next_open=0.5*(long_R_no1+short_R_no1) if np.isfinite(long_R_no1) and np.isfinite(short_R_no1) else np.nan,
                              stretch_over_atr=stretch_over_atr,
                              day_range_over_atr=day_range_over_atr, risk0=risk0, cost_R=cost_R,
                              price=c[e], stretch_abs=st[i-1]))
            i = e + 1; continue  # matches ftmo_lab.simulate_bracket: 'both' always resumes at e+1
        if not (long_hit or short_hit):
            i += 1; continue
        d = 1 if long_hit else -1
        _, exit_j = _forced_exit(o, h, l, c, A, e, n, d, target_index, time_index, atr_stop, cost_bps, buy, sell)
        i = exit_j + 1  # matches ftmo_lab.simulate_bracket: 'no overlapping positions' (i = exit_j + 1)
    return pd.DataFrame(diag)


# -------------------------------------------------------------------------------
STRATS = {}

import strat_s001_crabel_nr_orb as s001
uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}
STRATS["S001_crabel_nr_orb"] = dict(setup_stretch=s001.crabel_signals, target_index=3.0, time_index=10,
                                     atr_len=s001.ATR_LEN, atr_stop=s001.ATR_STOP)

import strat_s002_crabel_nr_setupexit as s002
def s002_ss(df): return s002.crabel_signals(df, look_back=s002.LB_REP)
STRATS["S002_crabel_nr_setupexit"] = dict(setup_stretch=s002_ss, target_index=999.0, time_index=s002.TM_REP,
                                           atr_len=s002.ATR_LEN, atr_stop=s002.ATR_STOP)
# NOTE: S002 has no profit target (time/stretch/ATR exits only); target_index=999
# approximates "no target" for this diagnostic tail (matches BIG sentinel used by
# S055/S056 in the real corpus). Its OWN exit also has a Stretch-band exit not
# modelled in _forced_exit (time+target+ATR only) -- a conservative simplification,
# flagged in the report; effect is second-order (Stretch exit is usually looser
# than the target grid explored here for the other 6 strategies).

import strat_s037_gsv as s037
STRATS["S037_gsv"] = dict(setup_stretch=lambda df: (s037._SETUP[[k for k,v in uni.items() if v is df][0]] if False else pd.Series(True, index=df.index), s037.gsv_stretch(df)),
                           target_index=s037.TI_REP, time_index=s037.TM_REP,
                           atr_len=s037.ATR_LEN, atr_stop=s037.ATR_STOP)

import strat_s055_narrow_range as s055
import strat_s027_engulfing as s27
STRATS["S055_narrow_range"] = dict(setup_stretch=lambda df: (s055.nr_setup(df, s055.N_REP, s055.LB_REP), s27.crabel_stretch(df)),
                                    target_index=s055.BIG, time_index=s055.TM,
                                    atr_len=s055.ATR_LEN, atr_stop=s055.ATR_STOP)

import strat_s056_nr7 as s056
STRATS["S056_nr7"] = dict(setup_stretch=lambda df: (s056.nr_setup(df, s056.NR_REP), s27.crabel_stretch(df)),
                           target_index=s056.BIG, time_index=s056.N_REP,
                           atr_len=s056.ATR_LEN, atr_stop=s056.ATR_STOP)

import strat_s061_orb as s061
STRATS["S061_orb"] = dict(setup_stretch=lambda df: (pd.Series(True, index=df.index),
                                                     s061.crabel_stretch(df, s061.STRETCH_LEN, s061.STRETCH_MULT)),
                           target_index=s061.TI_REP, time_index=s061.TM_REP,
                           atr_len=s061.ATR_LEN, atr_stop=s061.ATR_STOP)

import strat_s096_wide_range as s096
STRATS["S096_wide_range"] = dict(setup_stretch=lambda df: (s096.wide_setup(df, s096.N_REP, s096.LB_REP), s096.crabel_stretch(df, 10, 2.0) if hasattr(s096,'crabel_stretch') else None),
                                  target_index=s096.AIX, time_index=s096.TM,
                                  atr_len=20, atr_stop=6.0)

results = {}
for name, cfg in STRATS.items():
    frames = []
    for t, df in uni.items():
        try:
            setup, stretch = cfg["setup_stretch"](df)
        except Exception as ex:
            print(f"SKIP {name}/{t}: setup_stretch error {ex}"); continue
        if stretch is None:
            print(f"SKIP {name}/{t}: no stretch fn resolved"); continue
        d = diagnostic_bracket(df, setup, stretch, target_index=cfg["target_index"], time_index=cfg["time_index"],
                                atr_len=cfg["atr_len"], atr_stop=cfg["atr_stop"], cost_bps=costs[t], instr=t)
        if len(d):
            frames.append(d)
    pooled = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    results[name] = pooled
    if len(pooled):
        bias = pooled['assumed_R'] - pooled['unbiased_R']
        print(f"{name}: n_ambiguous={len(pooled)} mean_assumed_R={pooled['assumed_R'].mean():+.4f} "
              f"mean_unbiased_R={pooled['unbiased_R'].mean():+.4f} mean_bias_R={bias.mean():+.4f} "
              f"t={bias.mean()/bias.std(ddof=1)*np.sqrt(len(bias)):.2f}")
        pooled.to_csv(os.path.join(STUDY_DIR, f"diag_{name}.csv"), index=False)
    else:
        print(f"{name}: 0 ambiguous rows resolved")
