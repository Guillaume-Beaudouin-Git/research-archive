"""Main design: {POLICY,SWING} x {gateOFF,gateON} x {close,low,low_both} challenge sweeps
+ funded stage (for VAL/EV). Raw outputs only; stats in aggregate.py.

E.MRATE swapped per margin (module global consumed by E._target_for_segment). Gate = live
mechanism wt[:,1]*=(1-flag). Moteur canonique non muté."""
import sys, time, json
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
sys.path.insert(0, str(HERE.parent / "j1_suspend_study"))   # gate.py (origin/main #343)
import gate as G
sys.path.insert(0, str(HERE))
import lowcheck_engine as LC

TAB = HERE / "tables"; REC = HERE / "records"
TAB.mkdir(exist_ok=True); REC.mkdir(exist_ok=True)
LEGS = E.LEGS
t0 = time.time()


def log(m):
    print(f"{m}  [{time.time()-t0:.0f}s]", flush=True)


M = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
DATES = M["dates_idx"]
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
log(f"stack n={M['n']} {DATES.min().date()}..{DATES.max().date()}")

# gate mult (causal, live mechanism) — panel_px USDJPY, 160/155/10
PX_JPY = pd.read_parquet(E.CACHE / "panel_px.parquet")["USDJPY"]
susp = G.suspend_causal(PX_JPY, t_off=160.0, t_on=155.0, n=10)
mask = susp.reindex(DATES).fillna(False).to_numpy(bool)
mult = (~mask).astype(float)
log(f"gate: days_off={int(mask.sum())} frac={mask.mean():.4f}")

MARGINS = {"policy": np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS]),
           "swing": np.array([C22.MARGIN_RATES_SWING[s] for s in LEGS])}
GATES = {"OFF": None, "ON": mult}
MODES = ["close", "low", "low_both", "low_dom"]
GRID = [(w, int(i0)) for w, lo, hi in C22.WINDOWS for i0 in V.starts(M, lo, hi, C22.COHORT_STEP)]
log(f"cohorts={len(GRID)} IS={sum(1 for w,_ in GRID if w=='IS')} OOS={sum(1 for w,_ in GRID if w=='OOS')}")

# recost cost stack (measured swaps @REF_PX + commissions) = what the LIVE account pays.
# POLICY cells use the DEFAULT stack (anchor 87.01/+0.65); SWING cells use RECOST (anchor 71.4).
SW_DEFAULT = dict(swL=M["swL"].copy(), swS=M["swS"].copy(), rt=M["rt"].copy())
bL = np.array([C22.swap_bps(s, "long") for s in LEGS])
bS = np.array([C22.swap_bps(s, "short") for s in LEGS])
comm = np.array([C22.comm_rt_bps(s) for s in LEGS])
SW_RECOST = dict(swL=np.tile(bL, (M["n"], 1)), swS=np.tile(bS, (M["n"], 1)),
                 rt=SW_DEFAULT["rt"] + comm)
log(f"recost: swapL_bps={np.round(bL,3).tolist()} comm_rt_bps={np.round(comm,3).tolist()}")

MRATE_SAVE = E.MRATE.copy()
meta = {"gate_days_off": int(mask.sum()), "cohorts": len(GRID),
        "cost_stack": {"policy": "default", "swing": "recost(measured swaps+comm)"}, "arms": {}}

# ---------------- CHALLENGE sweeps ----------------
for mname, rates in MARGINS.items():
    E.MRATE = rates
    stk = SW_RECOST if mname == "swing" else SW_DEFAULT
    M["swL"], M["swS"], M["rt"] = stk["swL"], stk["swS"], stk["rt"]
    for gname, gm in GATES.items():
        wt = WT.copy()
        if gm is not None:
            wt[:, 1] = wt[:, 1] * gm
        for mode in MODES:
            rows, events = [], []
            for w, i0 in GRID:
                cfg = dict(C22.CFG_CHALLENGE)
                r = LC.run_funnel(M, i0, wt, ON, cfg, wall=C22.WALL, mode=mode,
                                  cohort_id=int(i0), win=w,
                                  events=events if mode != "close" else None)
                rows.append(dict(win=w, start=M["dates"][i0], cohort=int(i0),
                                 funded=r["funded"], attempts=r["attempts"],
                                 camp_days=r["camp_days"], t=r["t"], micro=r["micro"]))
            d = pd.DataFrame(rows)
            tag = f"{mname}_{gname}_{mode}"
            d.to_csv(TAB / f"cohorts_{tag}.csv", index=False)
            if events:
                pd.DataFrame(events).to_csv(REC / f"events_{tag}.csv", index=False)
            meta["arms"][tag] = dict(pooled=float(d.funded.mean()),
                                     p_IS=float(d[d.win == "IS"].funded.mean()),
                                     p_OOS=float(d[d.win == "OOS"].funded.mean()),
                                     attempts=float(d.attempts.mean()),
                                     med_t=float(d.loc[d.funded, "t"].median()) if d.funded.any() else float("nan"))
            log(f"[{tag:22s}] pooled {100*d.funded.mean():5.2f} IS {100*d[d.win=='IS'].funded.mean():5.2f} "
                f"OOS {100*d[d.win=='OOS'].funded.mean():5.2f} att {d.attempts.mean():.2f}")
E.MRATE = MRATE_SAVE

# ---------------- FUNDED stage (vm1 margin-insensitive; RECOST stack -> VAL~1381) ------
E.MRATE = MARGINS["policy"]
M["swL"], M["swS"], M["rt"] = SW_RECOST["swL"], SW_RECOST["swS"], SW_RECOST["rt"]
fund_rows = []
for gname, gm in GATES.items():
    wt = WT.copy()
    if gm is not None:
        wt[:, 1] = wt[:, 1] * gm
    for mode in ["close", "low", "low_dom"]:
        for w, lo, hi in C22.FUNDED_WINDOWS:
            for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP):
                r = LC.run_funded(M, int(i0), wt, ON, C22.CFG_FUNDED,
                                  horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY, mode=mode)
                fund_rows.append(dict(gate=gname, mode=mode, win=w, start=M["dates"][int(i0)],
                                      extr=r["wd"] + r["residual"], busted=r["busted"],
                                      payouts=r["payouts"], life=r["life"]))
    log(f"funded[{gname}] done")
E.MRATE = MRATE_SAVE
pd.DataFrame(fund_rows).to_csv(TAB / "funded_all.csv", index=False)

(TAB / "meta_design.json").write_text(json.dumps(meta, indent=2, default=str))
log("DONE")
