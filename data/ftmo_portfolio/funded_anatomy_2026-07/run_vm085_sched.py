"""Quick: vm0.85 funded pass WITH withdrawal + bust logging (for the V2->V3 cash-flow variant).
Same setup as run_all_funded baseline but cfg vm=0.85."""
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
cfg = dict(C22.CFG_FUNDED); cfg["vm"] = 0.85

runs, wd_log, bust_log = [], [], []
for w, lo, hi in C22.FUNDED_WINDOWS:
    for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP):
        r = FA.run_funded_anat(M, int(i0), wt, ON, cfg, horizon=C22.FUNDED_HORIZON,
                               wd_every=C22.FUNDED_WD_EVERY, mode="low",
                               bust_log=bust_log, wd_log=wd_log, run_id=int(i0))
        runs.append(dict(win=w, run_id=int(i0), busted=r["busted"], wd=r["wd"],
                         residual=r["residual"], life=r["life"], payouts=r["payouts"],
                         extr=r["wd"] + r["residual"]))
pd.DataFrame(runs).to_csv(TAB / "runs_vm085.csv", index=False)          # overwrite w/ same schema
pd.DataFrame(wd_log).to_csv(TAB / "wd_sched_vm085.csv", index=False)
pd.DataFrame(bust_log).to_csv(TAB / "busts_vm085.csv", index=False)
print(f"vm085 sched: bust {sum(r['busted'] for r in runs)}/{len(runs)}, "
      f"wd events {len(wd_log)} [{time.time()-t0:.0f}s]")
