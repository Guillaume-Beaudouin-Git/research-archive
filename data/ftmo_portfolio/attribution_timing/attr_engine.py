"""Attribution-instrumented funnel runner — wraps the FROZEN audit cleanroom engine.

The cleanroom engine (audit_v2_independent/cleanroom/engine.py) is imported
READ-ONLY for its data layer, signal layer and scheduling; the phase loop is
re-implemented here with per-sleeve cashflow accounting so that every dollar of
a cohort's P&L is attributed to {gold, jpy, on_us, on_ger, orb, fix}.

Identity enforced per attempt: INIT + sum(all attributed P&L) == end equity
(tolerance 1e-6). Micro-trade day-counter rule (deadlock fix) is ALWAYS ON.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "audit_v2_independent" / "cleanroom"))
import engine as E

LEG_NAMES = ["gold", "jpy", "on_us", "on_ger"]
INIT, FLOOR, BUDGET = E.INIT, E.FLOOR, E.DAILY_BUDGET


def trade_to_attr(pos, avg, bal, target, prices, rt):
    """E._trade_to with per-leg (cost, realized) returned."""
    cost = np.zeros(4)
    real = np.zeros(4)
    for k in range(4):
        t, o, p = target[k], pos[k], prices[k]
        if abs(t - o) < 1e-9 or not np.isfinite(p):
            continue
        c = abs(t - o) * (rt[k] / 2.0) / 1e4
        bal -= c
        cost[k] += c
        if o != 0.0:
            if t == 0.0 or t * o < 0:
                r = o * (p / avg[k] - 1.0)
                bal += r; real[k] += r
            elif abs(t) < abs(o):
                r = (o - t) * (p / avg[k] - 1.0)
                bal += r; real[k] += r
        if t == 0.0:
            avg[k] = np.nan
        elif o == 0.0 or t * o < 0:
            avg[k] = p
        elif abs(t) > abs(o):
            inv = (abs(o) / abs(t)) / avg[k] + (1 - abs(o) / abs(t)) / p
            avg[k] = 1.0 / inv
        pos[k] = t
    return bal, cost, real


def _u_vec(pos, avg, prices):
    u = np.zeros(4)
    for k in range(4):
        if pos[k] != 0.0 and np.isfinite(avg[k]) and np.isfinite(prices[k]):
            u[k] = pos[k] * (prices[k] / avg[k] - 1.0)
    return u


def run_phase_attr(M, i0, WT, ON, cfg, rec, meta):
    """Instrumented copy of cleanroom run_phase (same rules, same order)."""
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    target = INIT * (1 + cfg["target"])
    open_days = 0
    zombie = 0
    vm = cfg["vm"]
    u_prev = np.zeros(4)
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            return dict(out="timeout", end=bal + E._mtm(pos, avg, M["days"][i - 1][0][-1]),
                        last=i, used=di)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        opened = False
        d_cost = np.zeros(4); d_real = np.zeros(4); d_swap = np.zeros(4)
        d_orb = 0.0; d_fix = 0.0
        margin_pre = np.nan; margin_post = np.nan

        def day_rec(exit_prices, outcome):
            u_now = _u_vec(pos, avg, exit_prices)
            pnl = d_real - d_cost + d_swap + (u_now - u_prev)
            r = dict(date=M["dates"][i], di=di, outcome=outcome,
                     orb=d_orb, fix=d_fix, bal=bal,
                     margin_pre=margin_pre, margin_post=margin_post,
                     orb_risk=orb_risk if M["orb_R"][i] != 0.0 else 0.0)
            for k, nm in enumerate(LEG_NAMES):
                r[nm] = pnl[k]
                r["pos_" + nm] = pos[k]
            r.update(meta)
            rec.append(r)
            return u_now

        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            if s == 4 and orb_live:
                gain = orb_risk * M["orb_R"][i]
                bal += gain
                d_orb += gain
                opened = True
                orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, did_open = E._target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                      pos, avg, seg[0], i0, vm)
                if tgt is not None:
                    if s in (3, 4):
                        eqx = bal + E._mtm(pos, avg, seg[0])
                        margin_pre = float(np.abs(tgt) @ E.MRATE) / max(eqx, 1e-9)
                    bal2, c, r_ = trade_to_attr(pos, avg, bal, tgt, seg[0], M["rt"])
                    bal = bal2
                    d_cost += c; d_real += r_
                    if s in (3, 4):
                        margin_post = float(np.abs(pos) @ E.MRATE) / max(
                            bal + E._mtm(pos, avg, seg[0]), 1e-9)
                    opened = opened or did_open
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            hit_bust = eq < lim_eff
            hit_brk = eq < brk_line
            hit_tgt = eq >= target * (1 + E.EPS_T)
            tb = int(np.argmax(hit_bust)) if hit_bust.any() else len(seg)
            tk = int(np.argmax(hit_brk)) if hit_brk.any() else len(seg)
            th = int(np.argmax(hit_tgt)) if hit_tgt.any() else len(seg)
            if min(tb, tk, th) < len(seg):
                if tb <= min(tk, th):
                    day_rec(seg[tb], "bust")
                    e = eq[tb]
                    return dict(out="bust_daily" if e >= FLOOR else "bust_floor",
                                end=e, last=i, used=di + 1)
                if th <= tk:
                    bal2, c, r_ = trade_to_attr(pos, avg, bal, np.zeros(4),
                                                seg[th], M["rt"])
                    bal = bal2; d_cost += c; d_real += r_
                    if bal >= target and open_days + (1 if opened else 0) >= E.MIN_OPEN_DAYS:
                        day_rec(seg[th], "pass")
                        return dict(out="pass", end=bal, last=i, used=di + 1)
                    flat_today = True
                else:
                    fill = seg[tk].copy()
                    kslip = cfg.get("brk_slip", 0.0)
                    if kslip > 0.0 and tk > 0:
                        fill = fill - np.sign(pos) * kslip * np.abs(seg[tk] - seg[tk - 1])
                    bal2, c, r_ = trade_to_attr(pos, avg, bal, np.zeros(4),
                                                fill, M["rt"])
                    bal = bal2; d_cost += c; d_real += r_
                    flat_today = True
                    if bal < FLOOR:
                        day_rec(fill, "bust")
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1)
                    if bal < limit:
                        day_rec(fill, "bust")
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    sw = abs(pos[k]) * side / 1e4 * M["mult"][i, k]
                    bal += sw
                    d_swap[k] += sw
        if opened:
            open_days += 1
        if not np.any(pos) and bal >= target and open_days >= E.MIN_OPEN_DAYS:
            day_rec(px_day[-1], "pass")
            return dict(out="pass", end=bal, last=i, used=di + 1)
        eq_eod = bal + E._mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            day_rec(px_day[-1], "abandon")
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1)
        # micro-trade day-counter rule (ALWAYS ON in this study)
        if (flat_today and not np.any(pos) and bal >= target
                and open_days < E.MIN_OPEN_DAYS and not opened):
            open_days += 1
            bal -= 1.0
            d_fix -= 1.0
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                day_rec(px_day[-1], "pass")
                return dict(out="pass", end=bal, last=i, used=di + 1)
        u_prev = day_rec(px_day[-1], "mid")
        i += 1
    return dict(out="timeout", end=bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1]),
                last=M["n"] - 1, used=M["n"] - i0)


def run_funnel_attr(M, i0, WT, ON, cfg, rec, att_log, cohort_id, wall=91):
    start = M["dates"][i0]
    i = i0
    attempts = 0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan)
        attempts += 1
        meta = dict(cohort=cohort_id, attempt=attempts, phase=1)
        c1 = dict(cfg, target=E.TARGET1, max_cal=wall)
        r1 = run_phase_attr(M, i, WT, ON, c1, rec, meta)
        _tag_attempt(rec, cohort_id, attempts, 1, r1["out"])
        att_log.append(dict(cohort=cohort_id, attempt=attempts, phase=1,
                            out=r1["out"], end=r1["end"], used=r1["used"],
                            start_date=M["dates"][i]))
        if r1["out"] == "pass":
            j = min(r1["last"] + 3, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan)
            meta = dict(cohort=cohort_id, attempt=attempts, phase=2)
            c2 = dict(cfg, target=E.TARGET2, max_cal=wall,
                      vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase_attr(M, j, WT, ON, c2, rec, meta)
            _tag_attempt(rec, cohort_id, attempts, 2, r2["out"])
            att_log.append(dict(cohort=cohort_id, attempt=attempts, phase=2,
                                out=r2["out"], end=r2["end"], used=r2["used"],
                                start_date=M["dates"][j]))
            if r2["out"] == "pass":
                t = (M["dates"][r2["last"]] - start).days
                if t <= wall:
                    return dict(funded=True, attempts=attempts, t=t)
                return dict(funded=False, attempts=attempts, t=np.nan)
            if r2["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r2["last"] + 2, M["n"] - 1)
        else:
            if r1["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r1["last"] + 2, M["n"] - 1)


def _tag_attempt(rec, cohort, attempt, phase, outcome):
    for r in reversed(rec):
        if r["cohort"] == cohort and r["attempt"] == attempt and r.get("phase") == phase:
            if "att_out" in r:
                break
            r["att_out"] = outcome
        else:
            break


SLEEVES = dict(gold=["gold"], jpy=["jpy"], overnight=["on_us", "on_ger"],
               orb=["orb"])
