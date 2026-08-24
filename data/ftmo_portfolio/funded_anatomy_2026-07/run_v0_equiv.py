"""G-SELF-EQUIV: run_funded_anat == LC.run_funded (busted,wd,payouts,life,residual), gate ON,
modes close+low, canonical FUNDED_WINDOWS. STOP if any mismatch."""
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
t0 = time.time()

M = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
PX_JPY = pd.read_parquet(E.CACHE / "panel_px.parquet")["USDJPY"]
mult = (~G.suspend_causal(PX_JPY, 160.0, 155.0, 10).reindex(M["dates_idx"]).fillna(False).to_numpy(bool)).astype(float)
wt = WT.copy(); wt[:, 1] = wt[:, 1] * mult
E.MRATE = np.array([C22.MARGIN_RATES_POLICY[s] for s in E.LEGS])
# recost cost stack (live account)
bL = np.array([C22.swap_bps(s, "long") for s in E.LEGS]); bS = np.array([C22.swap_bps(s, "short") for s in E.LEGS])
M["swL"] = np.tile(bL, (M["n"], 1)); M["swS"] = np.tile(bS, (M["n"], 1))
M["rt"] = M["rt"] + np.array([C22.comm_rt_bps(s) for s in E.LEGS])
print(f"stack ready n={M['n']} [{time.time()-t0:.0f}s]", flush=True)

bad = 0; n = 0
for mode in ["close", "low"]:
    for w, lo, hi in C22.FUNDED_WINDOWS:
        for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP):
            r_ref = LC.run_funded(M, int(i0), wt, ON, C22.CFG_FUNDED,
                                  horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY, mode=mode)
            r_new = FA.run_funded_anat(M, int(i0), wt, ON, C22.CFG_FUNDED,
                                       horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY, mode=mode)
            n += 1
            same = (r_ref["busted"] == r_new["busted"] and abs(r_ref["wd"] - r_new["wd"]) < 1e-6
                    and r_ref["payouts"] == r_new["payouts"] and r_ref["life"] == r_new["life"]
                    and abs(r_ref["residual"] - r_new["residual"]) < 1e-6)
            if not same:
                bad += 1
                if bad <= 5:
                    print(f"  MISMATCH mode={mode} i0={i0}\n   ref={r_ref}\n   new={r_new}", flush=True)
print(f"\nG-SELF-EQUIV {'PASS' if bad==0 else f'FAIL ({bad}/{n})'}  checked {n} runs [{time.time()-t0:.0f}s]")
sys.exit(0 if bad == 0 else 1)
