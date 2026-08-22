"""Robustness check: does the S037/S061 verdict reversal survive when the L60-
contaminated instruments (XPTUSD 69%, XPDUSD 61%, XAGUSD 23%, COCOA 17%, COFFEE 10%
degenerate high==low daily bars -- print-settlement, not real trading ranges) are
EXCLUDED from the universe entirely?"""
import sys, os
import numpy as np, pandas as pd

CODE_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/archived/oxfordstrat_109_audit/code"
sys.path.insert(0, CODE_DIR)
os.environ["OHLC_DIR"] = os.path.join(os.path.dirname(CODE_DIR), "ohlc")
STUDY_DIR = "<HOME>/Desktop/Algo_claude/Multi_Asset/research/active/audit_entree_109_2026-08"
sys.path.insert(0, STUDY_DIR)
import ftmo_lab as lab
from corrected_engine import simulate_bracket_corrected

L60_BAD = {"XPTUSD", "XPDUSD", "XAGUSD", "COCOA", "COFFEE"}
uni_full = lab.load_universe()
uni = {t: df for t, df in uni_full.items() if t not in L60_BAD}
print(f"Universe: {len(uni_full)} -> {len(uni)} after excluding L60-contaminated instruments {L60_BAD}")
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
    print(f"\n{'='*70}\n{name} (L60-clean universe, N={len(uni)})\n{'='*70}")
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
        print(f"  base: expR={res['base']['expR']:+.5f} sharpe={res['base']['sharpe']:+.2f} n={res['base']['trades']}")
        d1 = g.get('delai+1 (L26)', g.get('delay1 (L26)'))
        print(f"  Gate1: {'PASS' if d1['pass'] else 'FAIL'} natif={d1['opt_expR']:+.5f}/{d1['opt_sharpe']:+.2f} -> real={d1['real_expR']:+.5f}/{d1['real_sharpe']:+.2f}")
        t2 = g['twosided (L25)']; print(f"  Gate2: {'PASS' if t2['pass'] else 'FAIL'} long={t2['exp_long']:+.5f}(n{t2['n_long']}) short={t2['exp_short']:+.5f}(n{t2['n_short']}) dom={t2['dom_share_pos_pct']:.0f}%")
        d3 = g['dsr']; print(f"  Gate3: {'PASS' if d3['pass'] else 'FAIL'} z={d3['DSR_z']:.2f}")
        o4 = g['oos (L31)']; print(f"  Gate4: {'PASS' if o4['pass'] else 'FAIL'} train={o4['train_expR']:+.5f} test={o4['test_expR']:+.5f}")

import strat_s037_gsv as s037
run_full("S037_gsv", lambda df: (pd.Series(True, index=df.index), s037.gsv_stretch(df)),
         s037.TI_REP, s037.TM_REP, s037.ATR_LEN, s037.ATR_STOP,
         TIs=[1, 2, 4, 6, 10], TMs=[1, 5, 10, 40])

import strat_s061_orb as s061
run_full("S061_orb", lambda df: (pd.Series(True, index=df.index), s061.crabel_stretch(df, s061.STRETCH_LEN, s061.STRETCH_MULT)),
         s061.TI_REP, s061.TM_REP, s061.ATR_LEN, s061.ATR_STOP,
         TIs=[1, 2, 3, 4, 6, 8, 10], TMs=[1, 3, 5, 10, 20, 40])
