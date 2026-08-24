"""Honor pre-reg §1: baseline anatomy at FUNDED_STEP=6 (spec'd) — run_all_funded used step 12.
Writes busts_baseline_s6.csv / runs_baseline_s6.csv for the canonical step-6 anatomy."""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))
import engine as E
import engine_v22 as V
import config_v22 as C22
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "real_metrics_2026-07"))
sys.path.insert(0, str(HERE.parent / "j1_suspend_study"))
import lowcheck_engine as LC
import gate as G
sys.path.insert(0, str(HERE))
import funded_anat_engine as FA
TAB = HERE / "tables"; LEGS = E.LEGS
t0 = time.time()

M = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals(); WT, ON = V.align(M, WT_df, ON_df)
PX_JPY = pd.read_parquet(E.CACHE / "panel_px.parquet")["USDJPY"]
jpy_zone = G.suspend_causal(PX_JPY, 160.0, 155.0, 10).reindex(M["dates_idx"]).fillna(False).to_numpy(bool)
E.MRATE = np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS])
M["swL"] = np.tile(np.array([C22.swap_bps(s, "long") for s in LEGS]), (M["n"], 1))
M["swS"] = np.tile(np.array([C22.swap_bps(s, "short") for s in LEGS]), (M["n"], 1))
M["rt"] = M["rt"] + np.array([C22.comm_rt_bps(s) for s in LEGS])
wt = WT.copy(); wt[:, 1] = wt[:, 1] * (~jpy_zone).astype(float)

runs, bust_log = [], []
for w, lo, hi in C22.FUNDED_WINDOWS:
    for i0 in V.starts(M, lo, hi, 6):                    # STEP 6 per pre-reg
        r = FA.run_funded_anat(M, int(i0), wt, ON, C22.CFG_FUNDED, horizon=C22.FUNDED_HORIZON,
                               wd_every=C22.FUNDED_WD_EVERY, mode="low", bust_log=bust_log, run_id=int(i0))
        runs.append(dict(win=w, run_id=int(i0), busted=r["busted"], extr=r["wd"] + r["residual"]))
dr = pd.DataFrame(runs); pd.DataFrame(bust_log).to_csv(TAB / "busts_baseline_s6.csv", index=False)
dr.to_csv(TAB / "runs_baseline_s6.csv", index=False)
bl = pd.DataFrame(bust_log)
print(f"step6: {len(dr)} runs, {int(dr.busted.sum())} busts ({100*dr.busted.mean():.1f}%), "
      f"{bl.date.nunique()} unique days -> {sorted(pd.to_datetime(bl.date).dt.strftime('%Y-%m-%d').unique())} "
      f"[{time.time()-t0:.0f}s]")
