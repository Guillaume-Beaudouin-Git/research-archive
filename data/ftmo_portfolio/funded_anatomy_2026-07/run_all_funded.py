"""One consolidated funded compute (load stack ONCE). Config book actuel = gate J1 ON, low-check bid,
recost stack, vm1. Canonical FUNDED_WINDOWS step 12.
  baseline  -> bust_log + wd_log + runs  (Volet 1 anatomy + Volet 3 cash-flow + overlay baseline)
  overlays  -> gold vol-gate / jpy vol-gate / vm{0.85,0.7,0.5}  (Volet 2)  [funded-only]
Regime signal (causal): 20d realized vol > rolling-504 p80 (shift 1). Weight-suspension, EA untouched."""
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
sys.path.insert(0, str(HERE.parent / "real_metrics_2026-07"))
sys.path.insert(0, str(HERE.parent / "j1_suspend_study"))
import lowcheck_engine as LC
import gate as G
sys.path.insert(0, str(HERE))
import funded_anat_engine as FA
TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
LEGS = E.LEGS
t0 = time.time()


def log(m):
    print(f"{m}  [{time.time()-t0:.0f}s]", flush=True)


M = LC.load_stack_lohi(orb_rt_bps=C22.ORB_RT_BPS)
DATES = M["dates_idx"]
WT_df, ON_df = E.build_signals()
WT, ON = V.align(M, WT_df, ON_df)
# gate J1 (zone) — live mechanism
PX_JPY = pd.read_parquet(E.CACHE / "panel_px.parquet")["USDJPY"]
jpy_zone = G.suspend_causal(PX_JPY, 160.0, 155.0, 10).reindex(DATES).fillna(False).to_numpy(bool)
# recost cost stack + policy margin (funded vm1)
E.MRATE = np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS])
M["swL"] = np.tile(np.array([C22.swap_bps(s, "long") for s in LEGS]), (M["n"], 1))
M["swS"] = np.tile(np.array([C22.swap_bps(s, "short") for s in LEGS]), (M["n"], 1))
M["rt"] = M["rt"] + np.array([C22.comm_rt_bps(s) for s in LEGS])

# causal vol-regime masks (20d realized vol > rolling-504 p80, shift 1)
rets = pd.read_parquet(E.CACHE / "panel_rets.parquet")


def vol_regime(sym):
    rv = rets[sym].rolling(20).std()
    thr = rv.rolling(504, min_periods=120).quantile(0.80)
    flag = (rv > thr).shift(1).reindex(DATES).fillna(False).to_numpy(bool)
    return flag


gold_hi = vol_regime("XAUUSD")
jpy_hi = vol_regime("USDJPY")
log(f"stack n={M['n']}  gate_zone_days={jpy_zone.sum()}  goldHiVol_days={gold_hi.sum()}  jpyHiVol_days={jpy_hi.sum()}")

# base weights with J1 zone-gate ON (current book)
WT_base = WT.copy(); WT_base[:, 1] = WT_base[:, 1] * (~jpy_zone).astype(float)


def wt_for(config):
    w = WT_base.copy()
    if config == "gold_gate":
        w[:, 0] = w[:, 0] * (~gold_hi).astype(float)
    elif config == "jpy_gate":
        w[:, 1] = w[:, 1] * (~jpy_hi).astype(float)
    return w


CONFIGS = [("baseline", 1.0), ("gold_gate", 1.0), ("jpy_gate", 1.0),
           ("vm085", 0.85), ("vm070", 0.70), ("vm050", 0.50)]
STARTS = [(w, int(i0)) for w, lo, hi in C22.FUNDED_WINDOWS for i0 in V.starts(M, lo, hi, C22.FUNDED_STEP)]
log(f"funded starts={len(STARTS)} (step {C22.FUNDED_STEP})")

meta = {}
for config, vm in CONFIGS:
    wt = wt_for(config)
    cfg = dict(C22.CFG_FUNDED)
    if vm != 1.0:
        cfg["vm"] = vm
    is_base = (config == "baseline")
    bust_log, wd_log, runs = [], ([] if is_base else None), []
    for w, i0 in STARTS:
        r = FA.run_funded_anat(M, i0, wt, ON, cfg, horizon=C22.FUNDED_HORIZON,
                               wd_every=C22.FUNDED_WD_EVERY, mode="low",
                               bust_log=bust_log, wd_log=wd_log, run_id=i0)
        runs.append(dict(win=w, start=M["dates"][i0], run_id=i0, busted=r["busted"],
                         wd=r["wd"], residual=r["residual"], life=r["life"], payouts=r["payouts"],
                         extr=r["wd"] + r["residual"]))
    dr = pd.DataFrame(runs)
    dr.to_csv(TAB / f"runs_{config}.csv", index=False)
    pd.DataFrame(bust_log).to_csv(TAB / f"busts_{config}.csv", index=False)
    if is_base:
        pd.DataFrame(wd_log).to_csv(TAB / "wd_sched_baseline.csv", index=False)
    extr = (dr[dr.win == "IS"].extr.mean() + dr[dr.win == "OOS"].extr.mean()) / 2
    VAL = 96.0 + 0.8 * extr
    meta[config] = dict(n=len(dr), bust_rate=float(dr.busted.mean()),
                        n_bust=int(dr.busted.sum()),
                        unique_bust_days=int(pd.DataFrame(bust_log).date.nunique()) if bust_log else 0,
                        E_extr=float(extr), VAL=float(VAL),
                        EV=float(0.697 * VAL - 3.29 * 96.0))   # challenge p/att from real_metrics swing_ON_low
    log(f"[{config:9s}] bust {100*dr.busted.mean():4.1f}% ({int(dr.busted.sum())}) uniqDays "
        f"{meta[config]['unique_bust_days']:3d}  E[extr] ${extr:,.0f}  VAL ${VAL:,.0f}  EV ${meta[config]['EV']:+,.0f}")

(TAB / "meta_funded.json").write_text(json.dumps(meta, indent=2))
log("DONE")
