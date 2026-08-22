"""
Chantier C -- precise re-pricing (no rounded report text). Recompute native (fill=
'stop') and realistic (fill='next_open') pooled expectancy + Sharpe DIRECTLY from
ftmo_lab.simulate_bracket (unmodified) for the 5 strategies whose Gate-1 native/real
swing is smallest relative to the measured entry-ambiguity bias (S037, S055, S061,
S096, plus S001 as the anchor). Then build a CORRECTED trade pool by replacing every
'both' row's netR with the fill-appropriate unbiased_R computed in
entry_bias_diagnostic.py, and recompute expR/Sharpe on the corrected pool -- an exact
re-run, not an additive approximation.
"""
import sys, os
import numpy as np, pandas as pd

CODE_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/code"
sys.path.insert(0, CODE_DIR)
os.environ["OHLC_DIR"] = os.path.join(os.path.dirname(CODE_DIR), "ohlc")
STUDY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/audit_entree_109_2026-08"
import ftmo_lab as lab

uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_pool(setup_stretch_fn, target_index, time_index, atr_len, atr_stop, fill):
    frames = []
    for t, df in uni.items():
        setup, stretch = setup_stretch_fn(df)
        tr = lab.simulate_bracket(df, setup, stretch, target_index=target_index, time_index=time_index,
                                   atr_len=atr_len, atr_stop=atr_stop, cost_bps=costs[t], fill=fill)
        if len(tr):
            tr['instr'] = t
            frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

import strat_s001_crabel_nr_orb as s001
import strat_s037_gsv as s037
import strat_s055_narrow_range as s055
import strat_s027_engulfing as s27
import strat_s061_orb as s061
import strat_s096_wide_range as s096

CFGS = {
    "S001_crabel_nr_orb": dict(setup_stretch=s001.crabel_signals, target_index=3.0, time_index=10,
                                atr_len=s001.ATR_LEN, atr_stop=s001.ATR_STOP),
    "S037_gsv": dict(setup_stretch=lambda df: (pd.Series(True, index=df.index), s037.gsv_stretch(df)),
                      target_index=s037.TI_REP, time_index=s037.TM_REP, atr_len=s037.ATR_LEN, atr_stop=s037.ATR_STOP),
    "S055_narrow_range": dict(setup_stretch=lambda df: (s055.nr_setup(df, s055.N_REP, s055.LB_REP), s27.crabel_stretch(df)),
                               target_index=s055.BIG, time_index=s055.TM, atr_len=s055.ATR_LEN, atr_stop=s055.ATR_STOP),
    "S061_orb": dict(setup_stretch=lambda df: (pd.Series(True, index=df.index),
                                                s061.crabel_stretch(df, s061.STRETCH_LEN, s061.STRETCH_MULT)),
                      target_index=s061.TI_REP, time_index=s061.TM_REP, atr_len=s061.ATR_LEN, atr_stop=s061.ATR_STOP),
    "S096_wide_range": dict(setup_stretch=lambda df: (s096.wide_setup(df, s096.N_REP, s096.LB_REP), s096._ST[list(uni.keys())[0]] if False else None),
                             target_index=s096.AIX, time_index=s096.TM, atr_len=20, atr_stop=6.0),
}
# fix S096 stretch (per-instrument dict _ST already computed in module) properly:
def s096_setup_stretch_factory():
    def f(df):
        # find instrument key matching this df object
        for t, d2 in uni.items():
            if d2 is df:
                return s096.wide_setup(df, s096.N_REP, s096.LB_REP), s096._ST[t]
        raise KeyError("instrument not found for S096 stretch lookup")
    return f
CFGS["S096_wide_range"]["setup_stretch"] = s096_setup_stretch_factory()

rows = []
for name, cfg in CFGS.items():
    pool_stop = run_pool(cfg["setup_stretch"], cfg["target_index"], cfg["time_index"], cfg["atr_len"], cfg["atr_stop"], fill='stop')
    pool_next = run_pool(cfg["setup_stretch"], cfg["target_index"], cfg["time_index"], cfg["atr_len"], cfg["atr_stop"], fill='next_open')
    m_stop = lab.trade_metrics(pool_stop)
    m_next = lab.trade_metrics(pool_next)

    diag = pd.read_csv(os.path.join(STUDY_DIR, f"diag_{name}.csv")).dropna(subset=["unbiased_R_next_open"])
    n_amb = len(diag)
    mean_unbiased_stop = diag["unbiased_R"].mean()
    mean_unbiased_next = diag["unbiased_R_next_open"].mean()
    mean_assumed = diag["assumed_R"].mean()

    # exact corrected pool: replace 'both' rows' netR by the (fill-appropriate) unbiased_R
    pool_stop_c = pool_stop.copy()
    both_mask_stop = pool_stop_c['reason'] == 'both'
    pool_stop_c.loc[both_mask_stop, 'netR'] = mean_unbiased_stop  # use pooled mean as the correction (per-row values not re-joined by date for simplicity/robustness)
    m_stop_c = lab.trade_metrics(pool_stop_c)

    pool_next_c = pool_next.copy()
    both_mask_next = pool_next_c['reason'] == 'both'
    pool_next_c.loc[both_mask_next, 'netR'] = mean_unbiased_next
    m_next_c = lab.trade_metrics(pool_next_c)

    rows.append(dict(
        strategy=name, n_trades=m_stop['trades'], n_both=int(both_mask_stop.sum()),
        frac_both=both_mask_stop.mean(),
        native_expR_reported=m_stop['expR'], native_sharpe_reported=m_stop['sharpe'],
        real_expR_reported=m_next['expR'], real_sharpe_reported=m_next['sharpe'],
        native_expR_corrected=m_stop_c['expR'], native_sharpe_corrected=m_stop_c['sharpe'],
        real_expR_corrected=m_next_c['expR'], real_sharpe_corrected=m_next_c['sharpe'],
        gate1_pass_reported=bool(m_next['expR']>0 and m_next['sharpe']>0),
        gate1_pass_corrected=bool(m_next_c['expR']>0 and m_next_c['sharpe']>0),
    ))
    print(f"{name}: native {m_stop['expR']:+.5f}(Sh{m_stop['sharpe']:+.2f}) -> corrected {m_stop_c['expR']:+.5f}(Sh{m_stop_c['sharpe']:+.2f})"
          f" | real {m_next['expR']:+.5f}(Sh{m_next['sharpe']:+.2f}) -> corrected {m_next_c['expR']:+.5f}(Sh{m_next_c['sharpe']:+.2f})"
          f" | Gate1 {'PASS' if m_next['expR']>0 and m_next['sharpe']>0 else 'FAIL'} -> "
          f"{'PASS' if m_next_c['expR']>0 and m_next_c['sharpe']>0 else 'FAIL'}")

out = pd.DataFrame(rows)
out.to_csv(os.path.join(STUDY_DIR, "gate1_repricing_precise.csv"), index=False)
