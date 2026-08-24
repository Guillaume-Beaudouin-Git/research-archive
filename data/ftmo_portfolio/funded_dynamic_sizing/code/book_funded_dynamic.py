"""Funded dynamic-sizing engine: v2.2 run_funded reused read-only, ONE patch =
per-day dynamic vm on realized cushion + cushion-retaining withdrawal + diagnostics.

Engine imported from the MAIN working dir (cleanroom + caches are gitignored, local there).
Trading/leg logic UNCHANGED (E._target_for_segment, _trade_to, _flat). Validation:
cfg(vm=1, alpha=0, c_keep=0, withdraw-all) must reproduce V.run_funded to the cent.

cushion_eff drives dyn_vm = clip(1 + alpha*cushion_eff, 0, vm_cap):
  target = max(0,(bal-INIT)/INIT)  (realized, on BALANCE not floating equity)
  asym OFF: cushion_eff = target
  asym ON : ratchet up <= ramp/day, instant-down on a down day (anti gain->lever->drawdown trap)
"""
import sys
from pathlib import Path
import numpy as np

MAIN = "<HOME>/Desktop/Algo_claude"
sys.path.insert(0, f"{MAIN}/data/ftmo_portfolio/v22")
import engine_v22 as V          # noqa: E402
import config_v22 as C22        # noqa: E402
E = V.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET

DIAG = dict(worst_day=[], bust_days_since_peak=[])     # filled when cfg['diag']


def run_funded_dyn(M, i0, WT, ON, cfg, horizon=504, wd_every=14):
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    min_eq = INIT
    alpha = cfg.get("alpha", 0.0)
    asym = cfg.get("asym", False)
    vm_cap = cfg.get("vm_cap", 3.0)
    ramp = cfg.get("ramp", 0.02)
    c_keep = cfg.get("c_keep", 0.0)
    keep_bal = INIT * (1.0 + c_keep)
    base = cfg.get("vm", 1.0)
    cushion_eff = 0.0
    last_down = False
    cycle_high = bal
    days_since_peak = 0
    diag = cfg.get("diag", False)
    vm_realized = []
    i = i0
    while i < M["n"] and days < horizon:
        bal_sod = bal
        # ---- dynamic vm from realized cushion ----
        target = max(0.0, (bal - INIT) / INIT)
        if asym:
            cushion_eff = target if last_down else min(target, cushion_eff + ramp)
        else:
            cushion_eff = target
        dyn_vm = float(np.clip(base * (1.0 + alpha * cushion_eff), 0.0, vm_cap))
        vm_realized.append(dyn_vm)
        # ---- v2.2 funded day (leg logic unchanged; cfg['vm'] -> dyn_vm) ----
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        day_worst = 0.0
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            if s == 4 and orb_live:
                bal += orb_risk * M["orb_R"][i]
                orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos,
                                               avg, seg[0], i0, dyn_vm)
                if tgt is not None:
                    bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            day_worst = min(day_worst, float(eq.min()) - bal_sod)
            min_eq = min(min_eq, float(eq.min()))
            bad = eq < lim_eff
            brk = eq < brk_line
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    e = float(eq[tb])
                    if diag:
                        DIAG["bust_days_since_peak"].append(days_since_peak)
                    return dict(busted=True, kind="daily" if e >= FLOOR else "floor",
                                wd=total_wd, payouts=n_pay, life=days,
                                residual=0.0, min_eq=min(min_eq, e),
                                vm_mean=float(np.mean(vm_realized)))
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"])
                flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        if diag:
            DIAG["worst_day"].append(day_worst)
        # end-of-day bookkeeping
        bal_eod = bal + E._mtm(pos, avg, px_day[-1])
        last_down = bal_eod < bal_sod - 1e-9
        if bal_eod > cycle_high:
            cycle_high = bal_eod
            days_since_peak = 0
        else:
            days_since_peak += 1
        days += 1
        i += 1
        if days % wd_every == 0 and bal > keep_bal:
            total_wd += bal - keep_bal
            n_pay += 1
            bal = keep_bal
            cycle_high = bal
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(busted=False, kind="survive", wd=total_wd, payouts=n_pay, life=days,
                residual=res, min_eq=min_eq, vm_mean=float(np.mean(vm_realized)))
