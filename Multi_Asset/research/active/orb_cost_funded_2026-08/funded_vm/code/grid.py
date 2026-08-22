"""VOLET D — grille 2-D funded : vm x ORB_RT_BPS.

Config : CFG_FUNDED_V28 (= v2.4 breaker daily + brk_needs_pos, marge SWING MESURÉE
du compte armé, overlay leg_lev_cap) — la plus live-fidèle disponible.
Horizon 504 jours tradés, retraits tous les 14 jours tradés, split 0.8.

Sortie : out/funded_cohorts.csv.gz (une ligne par cohorte x cellule).
Aucune écriture hors du dossier du volet. Aucune modification des sources importées.
"""
import os
import sys
import time
import multiprocessing as mp
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "out"
OUT.mkdir(exist_ok=True)
ROOT = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(ROOT / "data" / "ftmo_portfolio" / "v22"))
sys.path.insert(0, str(HERE))

VM_GRID = [0.60, 0.70, 0.80, 0.85, 0.90, 1.00, 1.10, 1.20]
COST_GRID = ["era", 1.0, 1.8, 2.2, 3.0, "OFF"]

_G = {}


def _init():
    import engine_v22 as V
    import config_v22 as C22
    import funded_instr as FI
    E = V.E
    M = V.load_stack(orb_rt_bps="era")
    WT_df, ON_df = E.build_signals()
    WT, ON = V.align(M, WT_df, ON_df)
    led = pd.read_parquet(V.LEDGER)
    lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
    orb = {}
    for c in COST_GRID:
        if c in ("era", "OFF"):
            r = pd.read_parquet(E.CACHE / "orb_e7_Rera.parquet")["R"]
        else:
            r = led["r_gross"].astype(float) - float(c) * 1e-4 * lev + 0.015
        orb[str(c)] = r.reindex(M["dates_idx"]).fillna(0.0).to_numpy(float)
    _G.update(V=V, C22=C22, FI=FI, M=M, WT=WT, ON=ON, orb=orb)


def _task(arg):
    cost, vm, win, lo, hi = arg
    V, C22, FI = _G["V"], _G["C22"], _G["FI"]
    M = dict(_G["M"])
    M["orb_R"] = _G["orb"][str(cost)]
    cfg = dict(C22.CFG_FUNDED_V28, vm=float(vm))
    if cost == "OFF":
        cfg["orb_risk"] = 0.0
    rows = []
    for i0 in V.starts(_G["M"], lo, hi, C22.FUNDED_STEP):
        r = FI.run_funded_instr(M, int(i0), _G["WT"], _G["ON"], cfg,
                                horizon=C22.FUNDED_HORIZON,
                                wd_every=C22.FUNDED_WD_EVERY)
        r.update(cost=str(cost), vm=float(vm), win=win,
                 start=_G["M"]["dates"][int(i0)])
        rows.append(r)
    return rows


def main():
    import config_v22 as C22
    tasks = [(c, vm, win, lo, hi)
             for c in COST_GRID for vm in VM_GRID
             for win, lo, hi in C22.FUNDED_WINDOWS]
    t0 = time.time()
    # spawn : chaque worker réimporte proprement (numpy/Accelerate + fork = risqué
    # sur macOS). Coût = un load_stack par worker (~30s), payé une fois.
    ctx = mp.get_context("spawn")
    nw = max(1, min(6, (os.cpu_count() or 2) - 1))
    with ctx.Pool(nw, initializer=_init) as pool:
        out = []
        for k, rows in enumerate(pool.imap_unordered(_task, tasks), 1):
            out.extend(rows)
            print(f"{k}/{len(tasks)} [{time.time()-t0:.0f}s]", flush=True)
    d = pd.DataFrame(out)
    d.to_csv(OUT / "funded_cohorts.csv.gz", index=False, compression="gzip")
    print(f"done {len(d)} rows [{time.time()-t0:.0f}s]")


if __name__ == "__main__":
    main()
