"""Instrumented clone of lowcheck_engine.run_funded (observation-only). Identical control flow
and returns; adds ONLY bust-event + withdrawal-schedule logging (bal_start, kind, dom_leg, gap_day,
timing). Validated bit-for-bit vs LC.run_funded by the self-EQUIV gate (run_v0_equiv.py). The AUDITED
lowcheck_engine.py is NOT modified. NB: Volet-2 overlays (gold/jpy vol-gate, vm sizing) are applied
UPSTREAM (weight suspension on WT, cfg["vm"]) by the caller — this clone contains NO gate logic,
which is exactly why self-EQUIV holds."""
import sys
from pathlib import Path
import numpy as np

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))
import engine as E
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "real_metrics_2026-07"))
import lowcheck_engine as LC          # audited; reused (load_stack_lohi etc.)

INIT, FLOOR, BUDGET = E.INIT, E.FLOOR, E.DAILY_BUDGET
LEGS = E.LEGS


def run_funded_anat(M, i0, WT, ON, cfg, horizon=504, wd_every=14, mode="low",
                    bust_log=None, wd_log=None, run_id=None):
    """Clone of LC.run_funded + observation logs. Returns identical dict."""
    bal = INIT; pos = np.zeros(4); avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    i = i0
    while i < M["n"] and days < horizon:
        bal_start = bal                                  # day-anchor (obs)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        lo_day, hi_day = M["lodays"][i], M["hidays"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        gap_day = bool(i > 0 and (M["dates"][i] - M["dates"][i - 1]).days >= 3)
        flat_today = False
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]; seg_lo = lo_day[a:b]; seg_hi = hi_day[a:b]
            if s == 4 and orb_live:
                bal += orb_risk * M["orb_R"][i]; orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg,
                                               seg[0], i0, cfg["vm"])
                if tgt is not None:
                    bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            if mode == "close":
                eq_adv = eq
            else:
                percol = np.zeros((len(seg), 4))
                for k in range(4):
                    if pos[k] != 0.0 and np.isfinite(avg[k]):
                        adv_col = seg_lo[:, k] if pos[k] > 0 else seg_hi[:, k]
                        adv_col = np.where(np.isfinite(adv_col), adv_col, seg[:, k])
                        percol[:, k] = pos[k] * (adv_col - seg[:, k]) / avg[k]
                eq_adv = eq + (percol.min(axis=1) if mode == "low_dom" else percol.sum(axis=1))
            bad = eq_adv < lim_eff
            brk = (eq_adv if mode == "low_both" else eq) < brk_line
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    if bust_log is not None:
                        e = float(eq_adv[tb])
                        u = {}
                        for k in range(4):
                            adv = (seg_lo[tb, k] if pos[k] > 0 else seg_hi[tb, k])
                            u[LEGS[k]] = float(pos[k] * (adv / avg[k] - 1.0)) if (
                                pos[k] != 0 and np.isfinite(avg[k]) and np.isfinite(adv)) else 0.0
                        dom = min(u, key=u.get)
                        bust_log.append(dict(
                            run_id=run_id, date=M["dates"][i], mode=mode,
                            kind="daily" if bal_start >= FLOOR + BUDGET else "max_loss",
                            e=e, bal_start=float(bal_start), daily_loss=float(bal_start - e),
                            at_open=bool(s == 0 and tb == 0), seg=int(s), bar=int(tb),
                            gap_day=gap_day, life=days, n_pay=n_pay, wd_banked=float(total_wd),
                            dom_leg=dom, **{f"u_{n}": u[n] for n in LEGS}))
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True, residual=0.0)
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"]); flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        days += 1; i += 1
        if days % wd_every == 0 and bal > INIT:
            amt = bal - INIT
            total_wd += amt; n_pay += 1
            if wd_log is not None:
                wd_log.append(dict(run_id=run_id, date=M["dates"][min(i, M["n"] - 1)],
                                   day=days, amount=float(amt), pay_idx=n_pay))
            bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res)
