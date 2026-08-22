"""
Chantier C -- full 4-gate re-run (Gate1/2/3/4) with the corrected entry-ambiguity
engine, for the 3 strategies whose Gate-1 flips under the precise re-pricing
(S037 GSV, S061 canonical ORB, S096 Wide Range). Compares ORIGINAL vs CORRECTED
verdict end-to-end (not just Gate1), including a re-run of the DSR parameter grid
(the grid must ALSO be recomputed on the corrected engine, since the assumed-loser
penalty scales with target_index/time_index and contaminates every grid cell, not
just the representative point).
"""
import sys, os
import numpy as np, pandas as pd

CODE_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/code"
sys.path.insert(0, CODE_DIR)
os.environ["OHLC_DIR"] = os.path.join(os.path.dirname(CODE_DIR), "ohlc")
STUDY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/audit_entree_109_2026-08"
sys.path.insert(0, STUDY_DIR)
import ftmo_lab as lab
from corrected_engine import simulate_bracket_corrected

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def make_runs(setup_stretch_fn, target_index, time_index, atr_len, atr_stop, engine):
    def _run(fill='stop'):
        frames = []
        for t, df in uni.items():
            setup, stretch = setup_stretch_fn(df)
            tr = engine(df, setup, stretch, target_index=target_index, time_index=time_index,
                        atr_len=atr_len, atr_stop=atr_stop, cost_bps=costs[t], fill=fill)
            if len(tr):
                tr['instr'] = t; frames.append(tr)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _run

def run_full(name, setup_stretch_fn, ti_rep, tm_rep, atr_len, atr_stop, TIs, TMs, split='2015-12-31'):
    print(f"\n{'='*70}\n{name}\n{'='*70}")
    for label, engine in [("ORIGINAL", lab.simulate_bracket), ("CORRECTED", simulate_bracket_corrected)]:
        run = make_runs(setup_stretch_fn, ti_rep, tm_rep, atr_len, atr_stop, engine)
        grid = np.full((len(TIs), len(TMs)), np.nan)
        for a, ti in enumerate(TIs):
            for b, tm in enumerate(TMs):
                r = make_runs(setup_stretch_fn, ti, tm, atr_len, atr_stop, engine)(fill='stop')
                grid[a, b] = lab.trade_metrics(r)['sharpe']
        res = lab.run_gates(run, grid, split=split)
        g = {x['gate']: x for x in res['gates']}
        print(f"[{label}] verdict={res['verdict']}  reason={res['reason']}")
        print(f"  base: expR={res['base']['expR']:+.5f} sharpe={res['base']['sharpe']:+.2f} "
              f"win={res['base']['win']*100:.1f}% n={res['base']['trades']}")
        d1 = g['delai+1 (L26)'] if 'delai+1 (L26)' in g else g.get('delay1 (L26)')
        print(f"  Gate1 delay1: {'PASS' if d1['pass'] else 'FAIL'}  natif exp={d1['opt_expR']:+.5f} Sh={d1['opt_sharpe']:+.2f}"
              f"  -> real exp={d1['real_expR']:+.5f} Sh={d1['real_sharpe']:+.2f}")
        t2 = g['twosided (L25)']
        print(f"  Gate2 twosided: {'PASS' if t2['pass'] else 'FAIL'}  long={t2['exp_long']:+.5f}(n{t2['n_long']})"
              f" short={t2['exp_short']:+.5f}(n{t2['n_short']}) dom={t2['dom_share_pos_pct']:.0f}%({t2['dominant']})")
        d3 = g['dsr']
        print(f"  Gate3 DSR: {'PASS' if d3['pass'] else 'FAIL'}  SR_obs={d3['SR_obs']:.3f} E[max]={d3['E_max_SR']:.3f} z={d3['DSR_z']:.2f}")
        o4 = g['oos (L31)']
        print(f"  Gate4 OOS: {'PASS' if o4['pass'] else 'FAIL'}  train={o4['train_expR']:+.5f}(n{o4['n_train']})"
              f" -> test={o4['test_expR']:+.5f}(n{o4['n_test']})")

import strat_s037_gsv as s037
run_full("S037_gsv", lambda df: (pd.Series(True, index=df.index), s037.gsv_stretch(df)),
         s037.TI_REP, s037.TM_REP, s037.ATR_LEN, s037.ATR_STOP,
         TIs=[1, 2, 4, 6, 10], TMs=[1, 5, 10, 40])

import strat_s061_orb as s061
run_full("S061_orb", lambda df: (pd.Series(True, index=df.index), s061.crabel_stretch(df, s061.STRETCH_LEN, s061.STRETCH_MULT)),
         s061.TI_REP, s061.TM_REP, s061.ATR_LEN, s061.ATR_STOP,
         TIs=[1, 2, 3, 4, 6, 8, 10], TMs=[1, 3, 5, 10, 20, 40])

import strat_s096_wide_range as s096
def s096_ss(df):
    for t, d2 in uni.items():
        if d2 is df:
            return s096.wide_setup(df, s096.N_REP, s096.LB_REP), s096._ST[t]
    raise KeyError
run_full("S096_wide_range", s096_ss, s096.AIX, s096.TM, 20, 6.0,
         TIs=[2, 5, 10], TMs=[20, 35, 50])

# ---------------------------------------------------------------------------------
# S056 (NR7) and S062 (ORB weekly) both reuse ftmo_lab.simulate_bracket UNCHANGED
# with target_index=BIG (no real target, ATR-stop+time only) -- same corrected
# engine applies directly.
# ---------------------------------------------------------------------------------
import strat_s027_engulfing as s27
import strat_s056_nr7 as s056
run_full("S056_nr7", lambda df: (s056.nr_setup(df, s056.NR_REP), s27.crabel_stretch(df)),
         s056.BIG, s056.N_REP, s056.ATR_LEN, s056.ATR_STOP,
         TIs=[s056.BIG], TMs=[5, 10, 20, 40])  # NR_Length is the real swept var in its own script; time_index here for DSR proxy

import strat_s062_orb_weekly as s062
uni_w = s062.uni  # weekly-resampled universe (module-level, already built by import)
costs_w = s062.costs
def make_runs_weekly(setup_stretch_fn, target_index, time_index, atr_len, atr_stop, engine):
    def _run(fill='stop'):
        frames = []
        for t, df in uni_w.items():
            setup, stretch = setup_stretch_fn(df)
            tr = engine(df, setup, stretch, target_index=target_index, time_index=time_index,
                        atr_len=atr_len, atr_stop=atr_stop, cost_bps=costs_w[t], fill=fill)
            if len(tr):
                tr['instr'] = t; frames.append(tr)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _run

print(f"\n{'='*70}\nS062_orb_weekly\n{'='*70}")
for label, engine in [("ORIGINAL", lab.simulate_bracket), ("CORRECTED", simulate_bracket_corrected)]:
    setup_stretch_fn = lambda df: (pd.Series(True, index=df.index), s062.crabel_stretch(df, s062.SL_REP, s062.SM_REP))
    run = make_runs_weekly(setup_stretch_fn, s062.NO_TGT, s062.BIG_TIME, s062.ATR_LEN, s062.ATR_STOP, engine)
    TIs_w, TMs_w = [s062.NO_TGT], [26, 52, 78]
    grid = np.full((len(TIs_w), len(TMs_w)), np.nan)
    for a, ti in enumerate(TIs_w):
        for b, tm in enumerate(TMs_w):
            r = make_runs_weekly(setup_stretch_fn, ti, tm, s062.ATR_LEN, s062.ATR_STOP, engine)(fill='stop')
            grid[a, b] = lab.trade_metrics(r)['sharpe']
    res = lab.run_gates(run, grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print(f"[{label}] verdict={res['verdict']}  reason={res['reason']}")
    print(f"  base: expR={res['base']['expR']:+.5f} sharpe={res['base']['sharpe']:+.2f} n={res['base']['trades']}")
    d1 = g.get('delai+1 (L26)', g.get('delay1 (L26)'))
    print(f"  Gate1: {'PASS' if d1['pass'] else 'FAIL'} natif={d1['opt_expR']:+.5f}/{d1['opt_sharpe']:+.2f} -> real={d1['real_expR']:+.5f}/{d1['real_sharpe']:+.2f}")
    t2 = g['twosided (L25)']; print(f"  Gate2: {'PASS' if t2['pass'] else 'FAIL'} long={t2['exp_long']:+.5f} short={t2['exp_short']:+.5f} dom={t2['dom_share_pos_pct']:.0f}%")
    d3 = g['dsr']; print(f"  Gate3: {'PASS' if d3['pass'] else 'FAIL'} z={d3['DSR_z']:.2f}")
    o4 = g['oos (L31)']; print(f"  Gate4: {'PASS' if o4['pass'] else 'FAIL'} train={o4['train_expR']:+.5f} test={o4['test_expR']:+.5f}")

# ---------------------------------------------------------------------------------
# S002 -- own exit engine (ATR-stop OR Stretch-band OR time; no target). Needs its
# own corrected variant (s002_corrected.py), not the generic bracket one.
# ---------------------------------------------------------------------------------
from s002_corrected import simulate_setupexit_corrected
import strat_s002_crabel_nr_setupexit as s002

def make_runs_s002(engine):
    def _run(fill='stop'):
        frames = []
        for t, df in uni.items():
            setup, stretch = s002.crabel_signals(df, look_back=s002.LB_REP)
            tr = engine(df, setup, stretch, time_index=s002.TM_REP, atr_len=s002.ATR_LEN,
                        atr_stop=s002.ATR_STOP, cost_bps=costs[t], fill=fill)
            if len(tr):
                tr['instr'] = t; frames.append(tr)
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    return _run

print(f"\n{'='*70}\nS002_crabel_nr_setupexit\n{'='*70}")
for label, engine in [("ORIGINAL", s002.simulate_setupexit), ("CORRECTED", simulate_setupexit_corrected)]:
    run = make_runs_s002(engine)
    LBs, TMs2 = [10, 20, 35, 50], [3, 5, 10, 20, 40]
    grid = np.full((len(LBs), len(TMs2)), np.nan)
    for a, lb in enumerate(LBs):
        for b, tm in enumerate(TMs2):
            frames = []
            for t, df in uni.items():
                setup, stretch = s002.crabel_signals(df, look_back=lb)
                tr = engine(df, setup, stretch, time_index=tm, atr_len=s002.ATR_LEN,
                            atr_stop=s002.ATR_STOP, cost_bps=costs[t], fill='stop')
                if len(tr): frames.append(tr)
            pool = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            grid[a, b] = lab.trade_metrics(pool)['sharpe']
    res = lab.run_gates(run, grid, split='2015-12-31')
    g = {x['gate']: x for x in res['gates']}
    print(f"[{label}] verdict={res['verdict']}  reason={res['reason']}")
    print(f"  base: expR={res['base']['expR']:+.5f} sharpe={res['base']['sharpe']:+.2f} n={res['base']['trades']}")
    d1 = g.get('delai+1 (L26)', g.get('delay1 (L26)'))
    print(f"  Gate1: {'PASS' if d1['pass'] else 'FAIL'} natif={d1['opt_expR']:+.5f}/{d1['opt_sharpe']:+.2f} -> real={d1['real_expR']:+.5f}/{d1['real_sharpe']:+.2f}")
    t2 = g['twosided (L25)']; print(f"  Gate2: {'PASS' if t2['pass'] else 'FAIL'} long={t2['exp_long']:+.5f} short={t2['exp_short']:+.5f} dom={t2['dom_share_pos_pct']:.0f}%")
    d3 = g['dsr']; print(f"  Gate3: {'PASS' if d3['pass'] else 'FAIL'} z={d3['DSR_z']:.2f}")
    o4 = g['oos (L31)']; print(f"  Gate4: {'PASS' if o4['pass'] else 'FAIL'} train={o4['train_expR']:+.5f} test={o4['test_expR']:+.5f}")
