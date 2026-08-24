"""vm-sweep — RÉUTILISE le sim audité (engine_v22 + cleanroom) ET les helpers de mesure
de l'étude v2.2.2 (run_swing_fit). SEUL le grid vm change + ajouts: walls sprint 30/45,
décomposition bust (diag), single-sleeve. Lecture seule, AUCUN contact prod (EA/FLAT/live).

Pré-enregistré: v222_vm_sweep/PREREGISTRATION.md (committé aab58ae AVANT ce run).
Gates STOP: policy 87.01 ±0.5 ET swing 71.43 ±0.5 doivent reproduire.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parent                                   # data/ftmo_portfolio
sys.path.insert(0, str(PKG / "v222_swing_fit"))
sys.path.insert(0, str(PKG / "v22"))
import config_v22 as C22                            # noqa: E402
import engine_v22 as V                              # noqa: E402
import run_swing_fit as SWF                         # noqa: E402  (harnais de mesure audité)

E = V.E
LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
TAB = HERE / "tables"
TAB.mkdir(parents=True, exist_ok=True)
SWF.TAB = TAB                                        # rediriger les CSV des helpers ici

SWING = np.array([C22.MARGIN_RATES_SWING[s] for s in LEGS])
POLICY = np.array([C22.MARGIN_RATES_POLICY[s] for s in LEGS])
VAL_SWC = SWF.VAL_SWC                                # 1438
VAL_COMM = SWF.VAL_COMM                              # 1381
FEE = C22.FEE                                        # 96
VM_GRID = [10.0, 14.0, 18.0, 22.0, 26.0, 30.0, 1e6]
SPRINT_WALLS = (30, 45)
TRIPLE_DOW = {2, 4}                                  # XAU/JPY mer (2), US100/GER40 ven (4)
t0 = time.time()


def log(m):
    print(f"{m}  [{time.time()-t0:.0f}s]", flush=True)


def vmname(vm):
    return "vm_inf" if vm >= 1e5 else f"vm{int(vm)}"


def walls_extra(name, M, WT, ON, cfg, walls=SPRINT_WALLS):
    """Walls sprint (30/45j) — p, t_med, EV, attempts. Réutilise SWF.sweep_funnel."""
    E.MRATE = SWING.copy()
    out = {}
    for w in walls:
        d = SWF.sweep_funnel(M, WT, ON, dict(cfg), w)
        out[f"p{w}"] = round(d.funded.mean() * 100, 2)
        out[f"tmed{w}"] = float(d[d.funded].t.median()) if d.funded.any() else float("nan")
        out[f"ev{w}"] = round(float((d.funded * VAL_SWC - d.attempts * FEE).mean()), 1)
        out[f"att{w}"] = round(d.attempts.mean(), 2)
    return out


def date_features(M):
    idx = pd.DatetimeIndex(M["dates"])
    prev = idx.to_series().diff().dt.days.fillna(0).to_numpy()
    return {pd.Timestamp(d): (int(prev[k]), int(idx[k].dayofweek))
            for k, d in enumerate(idx)}


def bust_decomp(name, M, WT, ON, cfg, feat):
    """Passe diag sur le funnel 91j: split daily/floor (via ATTEMPTS) + first_bar/gap/
    triple (via diag). Réutilise SWF.ATTEMPTS + SWF._wrap_run_phase + attempt_breakdown."""
    E.MRATE = SWING.copy()
    diag = []
    SWF.ATTEMPTS.clear()
    orig = V.run_phase
    V.run_phase = SWF._wrap_run_phase(orig)
    try:
        for win, lo, hi in C22.WINDOWS:
            for i0 in V.starts(M, lo, hi, C22.COHORT_STEP):
                V.run_funnel(M, int(i0), WT, ON, dict(cfg), wall=91, diag=diag)
    finally:
        V.run_phase = orig
    bd = SWF.attempt_breakdown()                     # par-tentative daily/floor/abandon/to
    db = pd.DataFrame(diag)
    n = len(db)
    res = dict(arm=name, n_attempts=bd["n_attempts"], n_bust_events=n,
               att_bust_daily=round(bd["bust_daily"] * 100, 2),
               att_bust_floor=round(bd["bust_floor"] * 100, 2),
               att_abandon=round(bd["abandon"] * 100, 2),
               att_timeout=round(bd["timeout"] * 100, 2))
    if n:
        gd = db.date.map(lambda d: feat[pd.Timestamp(d)][0]).to_numpy()
        dow = db.date.map(lambda d: feat[pd.Timestamp(d)][1]).to_numpy()
        fb = db["first_bar"].to_numpy(bool)
        is_gap = gd >= 3
        res.update(
            share_first_bar=round(float(fb.mean()) * 100, 2),
            share_gap_monday=round(float(is_gap.mean()) * 100, 2),
            share_first_bar_AND_gap=round(float((fb & is_gap).mean()) * 100, 2),
            share_first_bar_intraweek=round(float((fb & ~is_gap).mean()) * 100, 2),
            share_triple_dow=round(float(np.isin(dow, list(TRIPLE_DOW)).mean()) * 100, 2),
            fb_among_busts_on_gap=round(float(is_gap[fb].mean()) * 100, 2) if fb.any()
            else float("nan"),
        )
    db.to_csv(TAB / f"bust_diag_{name}.csv", index=False)
    return res


def main():
    M, M_swc, WT, ON = SWF.build()
    log("stack chargé (M base + M_swc re-cost)")

    # ---- GATES (reproduction baseline, STOP sinon) ------------------------
    E.MRATE = POLICY.copy()
    p_pol = SWF.sweep_funnel(M, WT, ON, dict(C22.CFG_CHALLENGE), 91).funded.mean() * 100
    E.MRATE = SWING.copy()
    p_swg = SWF.sweep_funnel(M_swc, WT, ON, dict(C22.CFG_CHALLENGE), 91).funded.mean() * 100
    log(f"GATE policy {p_pol:.2f} (need 87.01) | swing {p_swg:.2f} (need 71.43)")
    assert abs(p_pol - 87.01) <= 0.5, f"GATE FAIL policy {p_pol:.2f} -> STOP"
    assert abs(p_swg - 71.43) <= 0.5, f"GATE FAIL swing {p_swg:.2f} -> STOP"
    log("GATES PASS")

    # ---- SWEEP vm ---------------------------------------------------------
    rows, d91s = [], {}
    for vm in VM_GRID:
        name = vmname(vm)
        cfg = dict(C22.CFG_CHALLENGE, vm=vm)
        row, d91 = SWF.run_arm(name, M_swc, WT, ON, cfg)
        row.update(walls_extra(name, M_swc, WT, ON, cfg))
        rows.append(row)
        d91s[name] = d91
    # cross-checks pré-enregistrés
    p_vm10 = next(r["p91"] for r in rows if r["arm"] == "vm10")
    p_vm14 = next(r["p91"] for r in rows if r["arm"] == "vm14")
    log(f"cross-check vm10 {p_vm10} (need 70.13 ±0.7) | vm14 {p_vm14} (= swing gate)")
    assert abs(p_vm10 - 70.13) <= 0.7, f"CROSS-CHECK FAIL vm10 {p_vm10}"
    res = pd.DataFrame(rows)
    res.to_csv(TAB / "vm_sweep_summary.csv", index=False)

    # ---- deltas appariés vs vm14 -----------------------------------------
    tor = []
    for name in d91s:
        if name == "vm14":
            continue
        tor.append(dict(arm=name, **SWF.paired(d91s["vm14"], d91s[name])))
    tor = pd.DataFrame(tor)
    tor.to_csv(TAB / "paired_vs_vm14.csv", index=False)
    log("paired vs vm14:\n" + tor.to_string(index=False))

    # ---- points (a/b/c) ---------------------------------------------------
    a_ev = res.loc[res.ev91.idxmax()]
    b_fast = res.loc[res.tmed91.idxmin()] if "tmed91" in res else None
    # tmed91 vient de run_arm sous le nom t_med
    b_fast = res.loc[res.t_med.idxmin()]
    neg = res[res.ev91 < 0]
    pt_c = ("aucun EV<0 dans la grille" if neg.empty
            else f"{neg.iloc[0]['arm']} (EV {neg.iloc[0]['ev91']})")
    log(f"(a) argmax EV = {a_ev['arm']} EV {a_ev['ev91']} p91 {a_ev['p91']}")
    log(f"(b) argmin t_med = {b_fast['arm']} t_med {b_fast['t_med']} "
        f"EV {b_fast['ev91']} p91 {b_fast['p91']}")
    log(f"(c) EV<0: {pt_c}")
    # sprint = argmax p45
    sprint = res.loc[res.p45.idxmax()]
    log(f"SPRINT (argmax p45) = {sprint['arm']} p45 {sprint['p45']} "
        f"p30 {sprint['p30']} bust/att {sprint['att_bust_daily']+sprint['att_bust_floor']:.1f} "
        f"EV91 {sprint['ev91']}")

    # ---- décomposition bust (Q4): arm le plus agressif + vm30 + stress ----
    feat = date_features(M_swc)
    bdrows = []
    bdrows.append(bust_decomp("vm_inf", M_swc, WT, ON, dict(C22.CFG_CHALLENGE, vm=1e6), feat))
    bdrows.append(bust_decomp("vm30", M_swc, WT, ON, dict(C22.CFG_CHALLENGE, vm=30.0), feat))
    # stress gap x1.5 sur l'arm le plus agressif (étiqueté, NON canonique)
    bdrows.append(bust_decomp("vm_inf_wgap1.5", M_swc, WT, ON,
                              dict(C22.CFG_CHALLENGE, vm=1e6, wgap_stress=1.5), feat))
    bdf = pd.DataFrame(bdrows)
    bdf.to_csv(TAB / "bust_decomposition.csv", index=False)
    log("bust decomposition:\n" + bdf.to_string(index=False))

    # ---- single-sleeve vs diversifié (Q5) --------------------------------
    WT0 = np.zeros_like(WT)
    ON0 = np.zeros_like(ON)
    WT_gold = WT.copy(); WT_gold[:, 1] = 0.0
    WT_j1 = WT.copy(); WT_j1[:, 0] = 0.0
    sleeves = [
        ("sleeve_overnight_vm14", WT0, ON),
        ("sleeve_gold_vm14", WT_gold, ON0),
        ("sleeve_j1_vm14", WT_j1, ON0),
    ]
    srows, sleeve_inputs = [], {}
    for nm, wt, on in sleeves:
        r, _ = SWF.run_arm(nm, M_swc, wt, on, dict(C22.CFG_CHALLENGE))
        srows.append(r)
        sleeve_inputs[nm] = (wt, on)
    best = max(srows, key=lambda r: r["p91"])
    wt_b, on_b = sleeve_inputs[best["arm"]]
    full_name = best["arm"].replace("_vm14", "_full_inf")
    r_full, _ = SWF.run_arm(full_name, M_swc, wt_b, on_b, dict(C22.CFG_CHALLENGE, vm=1e6))
    srows.append(r_full)
    sdf = pd.DataFrame(srows)
    sdf.to_csv(TAB / "single_sleeve.csv", index=False)
    log(f"best standalone sleeve @vm14 = {best['arm']} p91 {best['p91']} EV {best['ev91']}")
    log(f"best sleeve FULL (vm_inf) = {full_name} p91 {r_full['p91']} EV {r_full['ev91']} "
        f"| diversifié vm14 p91 {p_vm14} EV {a_ev['ev91'] if a_ev['arm']=='vm14' else res[res.arm=='vm14'].ev91.iloc[0]}")

    # ---- summary.json -----------------------------------------------------
    keepcols = ["arm", "vm", "p91", "p91_ci95", "attempts", "t_med",
                "pass_attempt_P1_noclock", "att_bust_daily", "att_bust_floor",
                "att_abandon", "ev91", "ev91_val1381", "p182", "p270",
                "p30", "p45", "tmed45", "mg_bind", "mg_clip_depth", "mg_p50", "mg_p99"]
    summary = dict(
        baseline="1947163e8e92b27221cfbd9d08325e6d121796cf",
        prereg_commit="aab58ae",
        hypothesis="marge SWING officielle 1:30/1:15/1:9 — À CONFIRMER serveur",
        gates=dict(policy=round(p_pol, 2), swing=round(p_swg, 2),
                   vm10_crosscheck=p_vm10),
        VAL_swc=VAL_SWC, VAL_comm=VAL_COMM, fee=FEE,
        sweep=res[keepcols].to_dict(orient="records"),
        point_a_max_ev=dict(arm=str(a_ev["arm"]), ev91=float(a_ev["ev91"]),
                            p91=float(a_ev["p91"]), attempts=float(a_ev["attempts"]),
                            t_med=float(a_ev["t_med"])),
        point_b_min_tmed=dict(arm=str(b_fast["arm"]), t_med=float(b_fast["t_med"]),
                              ev91=float(b_fast["ev91"]), p91=float(b_fast["p91"]),
                              attempts=float(b_fast["attempts"])),
        point_c_ev_negative=pt_c,
        sprint=dict(arm=str(sprint["arm"]), p45=float(sprint["p45"]),
                    p30=float(sprint["p30"]), ev91=float(sprint["ev91"]),
                    bust_att=float(sprint["att_bust_daily"] + sprint["att_bust_floor"])),
        bust_decomposition=bdrows,
        single_sleeve=sdf[["arm", "p91", "attempts", "t_med", "att_bust_daily",
                           "att_bust_floor", "ev91", "mg_bind"]].to_dict(orient="records"),
        best_standalone=str(best["arm"]),
    )
    (HERE / "summary.json").write_text(json.dumps(summary, indent=1, default=str))
    log("summary.json écrit — DONE")


if __name__ == "__main__":
    main()
