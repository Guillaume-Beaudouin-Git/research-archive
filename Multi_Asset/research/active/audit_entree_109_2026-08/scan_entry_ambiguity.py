"""
Chantier A/C -- full scan of the ENTRY dual-breakout ambiguity ("both sides -> assume
loser" for the ORB-stop family; "skip" for the channel-breakout family) across every
strategy in the 109-corpus that structurally can trigger it: a REAL pending buy-stop
AND sell-stop on the SAME daily bar (as opposed to the 98 strategies that pick a
single, already-determined signal direction and cannot double-trigger).

READ-ONLY on the archived corpus: only imports ftmo_lab.py and strat_*.py modules
(their own __main__ blocks are not executed; we call their run_point()/run() at their
own representative parameter point, exactly as their own scripts do). Writes only to
this study's own directory.
"""
import sys, os
import numpy as np, pandas as pd

CODE_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/code"
sys.path.insert(0, CODE_DIR)
os.environ["OHLC_DIR"] = os.path.join(os.path.dirname(CODE_DIR), "ohlc")
STUDY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/audit_entree_109_2026-08"
import ftmo_lab as lab

rows = []
trade_frames = {}

def summarize(name, tr, n_opportunities=None):
    n = len(tr)
    if n == 0:
        rows.append(dict(strategy=name, n_trades=0, n_both=0, frac_both_of_trades=np.nan,
                          n_opportunities=n_opportunities, frac_both_of_opportunities=np.nan))
        return
    n_both = int((tr['reason'] == 'both').sum()) if 'reason' in tr.columns else 0
    frac_o = (n_both / n_opportunities) if n_opportunities else np.nan
    rows.append(dict(strategy=name, n_trades=n, n_both=n_both, frac_both_of_trades=n_both / n,
                      n_opportunities=n_opportunities, frac_both_of_opportunities=frac_o))
    print(f"{name}: n_trades={n} n_both={n_both} frac_of_trades={n_both/n*100:.2f}%")
    trade_frames[name] = tr

# ---------------------------------------------------------------------------------
# Family "assume loser" (-2R), reason=='both' rows ARE counted as trades already.
# ---------------------------------------------------------------------------------
import strat_s001_crabel_nr_orb as s001
uni = s001.uni if hasattr(s001, 'uni') else lab.load_universe()
if not hasattr(s001, 'uni'):
    uni = lab.load_universe()
costs = {t: lab.round_turn_cost_bps(t, df) for t, df in uni.items()}

def run_generic(setup_stretch_fn, target_index, time_index, atr_len, atr_stop):
    frames = []
    for t, df in uni.items():
        setup, stretch = setup_stretch_fn(df)
        tr = lab.simulate_bracket(df, setup, stretch, target_index=target_index, time_index=time_index,
                                   atr_len=atr_len, atr_stop=atr_stop, cost_bps=costs[t])
        if len(tr):
            tr['instr'] = t
            frames.append(tr)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

tr1 = run_generic(s001.crabel_signals, target_index=3.0, time_index=10, atr_len=s001.ATR_LEN, atr_stop=s001.ATR_STOP)
summarize("S001_crabel_nr_orb", tr1)

import strat_s002_crabel_nr_setupexit as s002
tr2_frames = []
for t, df in uni.items():
    setup, stretch = s002.crabel_signals(df, look_back=s002.LB_REP)
    tr = s002.simulate_setupexit(df, setup, stretch, time_index=s002.TM_REP,
                                  atr_len=s002.ATR_LEN, atr_stop=s002.ATR_STOP, cost_bps=costs[t])
    if len(tr):
        tr['instr'] = t; tr2_frames.append(tr)
tr2 = pd.concat(tr2_frames, ignore_index=True) if tr2_frames else pd.DataFrame()
summarize("S002_crabel_nr_setupexit", tr2)

import strat_s037_gsv as s037
tr37 = s037.run_point(s037.TI_REP, s037.TM_REP)
summarize("S037_gsv", tr37)

import strat_s055_narrow_range as s055
tr55 = s055.run_point(s055.N_REP, s055.LB_REP)
summarize("S055_narrow_range", tr55)

import strat_s056_nr7 as s056
tr56 = s056.run_point(s056.NR_REP, s056.N_REP)
summarize("S056_nr7", tr56)

import strat_s061_orb as s061
tr61 = s061.run_point(s061.TI_REP, s061.TM_REP)
summarize("S061_orb", tr61)

import strat_s062_orb_weekly as s062
tr62 = s062.run_point(s062.SL_REP, s062.SM_REP)
summarize("S062_orb_weekly", tr62)

import strat_s096_wide_range as s096
tr96 = s096.run_point()
summarize("S096_wide_range", tr96)

# ---------------------------------------------------------------------------------
# Family "skip" (S020/S021/S022): the ambiguous bar produces NO trade at all, so it
# never appears in the trades table. We measure it directly on the up/dn channel
# arithmetic (identical to their own code) at the canonical channel_len=20.
# ---------------------------------------------------------------------------------
CL = 20
skip_rows = []
for t, df in uni.items():
    h, l = df['high'].values, df['low'].values
    up = pd.Series(df['high']).rolling(CL).max().shift(1).values
    dn = pd.Series(df['low']).rolling(CL).min().shift(1).values
    valid = np.isfinite(up) & np.isfinite(dn)
    long_hit = valid & (h >= up)
    short_hit = valid & (l <= dn)
    both = long_hit & short_hit
    n_opp = int((long_hit | short_hit).sum())
    n_both = int(both.sum())
    skip_rows.append(dict(instr=t, n_signal_bars=n_opp, n_both_skipped=n_both,
                           frac_both_of_signals=(n_both / n_opp if n_opp else np.nan)))
skip_df = pd.DataFrame(skip_rows)
skip_df.to_csv(os.path.join(STUDY_DIR, "donchian_skip_ambiguity_by_instrument.csv"), index=False)
tot_opp = skip_df['n_signal_bars'].sum(); tot_both = skip_df['n_both_skipped'].sum()
print(f"S020/S021/S022 (channel_len=20, shared entry): n_signal_bars={tot_opp} "
      f"n_both_skipped={tot_both} frac={tot_both/tot_opp*100:.2f}%")
rows.append(dict(strategy="S020_S021_S022_donchian_skip", n_trades=tot_opp - tot_both,
                  n_both=tot_both, frac_both_of_trades=tot_both / (tot_opp - tot_both),
                  n_opportunities=tot_opp, frac_both_of_opportunities=tot_both / tot_opp))

summary = pd.DataFrame(rows)
summary.to_csv(os.path.join(STUDY_DIR, "entry_ambiguity_summary.csv"), index=False)
print("\n=== SUMMARY ===")
print(summary.to_string())

# Save the per-strategy trade tables (with 'both' rows flagged) for the resolver step
for name, tr in trade_frames.items():
    tr.to_parquet(os.path.join(STUDY_DIR, f"trades_{name}.parquet"))
print("\nSaved trades_*.parquet + entry_ambiguity_summary.csv + donchian_skip_ambiguity_by_instrument.csv")
