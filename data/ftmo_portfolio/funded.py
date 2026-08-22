"""Funded-stage simulator (FTMO Account 2-step, Swing): no target, no clock.
Rules: daily 5% (balance-anchored midnight CET), static floor $9k. Monthly
withdrawal of realized profits (bal - INIT), 80% trader split, fee refunded
at first payout. Horizon-capped; residual positive equity at horizon counted
(marked, realistic). Returns per-cohort economics.
"""
import numpy as np
import pandas as pd
import config as C
import simulator as S

INIT = S.INIT
FLOOR = S.FLOOR
DAILY_BUDGET = S.DAILY_BUDGET


def run_funded(D, i0, WT, ON, cfg, horizon_td=504, wd_every=21):
    bal = INIT
    pos = np.zeros(S.NL)
    avg = np.full(S.NL, np.nan)
    total_wd = 0.0
    n_payouts = 0
    i = i0
    days = 0
    while i < D.n and days < horizon_td:
        daily_limit = bal - DAILY_BUDGET
        flat_today = False
        _taper0 = float(np.clip(((bal - FLOOR) / INIT) / cfg["taper_buf"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * _taper0
        orb_on = orb_risk > 0 and D.orb_R[i] != 0.0
        for sid, px in D.segs[i]:
            T = px.shape[0]
            if orb_on and sid == 4:
                bal += orb_risk * D.orb_R[i]
                orb_on = False
            orb_dip = (1.31 * orb_risk) if (orb_on and sid in (2, 3)) else 0.0
            if not flat_today:
                newpos, _ = S._sched_target(sid, i, D, WT, ON, cfg, bal, pos, avg,
                                            px[0], daily_limit, i0=i0)
                if newpos is not None:
                    bal = S._rebalance(pos, avg, newpos, px[0], bal, D.rt)
            with np.errstate(invalid="ignore"):
                ratio = px / avg
            pl = np.where(np.isfinite(ratio) & (pos != 0.0), (ratio - 1.0) * pos, 0.0)
            eqp = bal + pl.sum(axis=1) - orb_dip
            lim = max(daily_limit, FLOOR)
            bad = eqp < lim
            brk = eqp < lim + cfg["breaker_frac"] * DAILY_BUDGET
            t_bad = np.argmax(bad) if bad.any() else T
            t_brk = np.argmax(brk) if brk.any() else T
            if min(t_bad, t_brk) < T:
                if t_bad <= t_brk:
                    return dict(wd=total_wd, payouts=n_payouts, life=days,
                                busted=True, residual=0.0)
                bal = S._flatten(pos, avg, px[t_brk], bal, D.rt)
                flat_today = True
        if pos.any():
            side = np.where(pos > 0, D.swapL[i], D.swapS[i])
            bal += float((np.abs(pos) * side / 1e4 * D.mult[i]).sum())
        days += 1
        i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT
            n_payouts += 1
            bal = INIT
    res = max(bal + S._mtm(pos, avg, S._last_px(D, min(i, D.n - 1))) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_payouts, life=days, busted=False, residual=res)


def sweep(D, WT, ON, vm, starts, p2_irrelevant=True, horizon_td=504):
    cfg = dict(target=10.0, on_w=0.35, breaker_frac=0.30, orb_risk=0.0025,
               taper_buf=0.02, glide=1.0, quantize=True, pace=0,
               daily_realize=False, weekend_flat=False, max_cal_days=None,
               vol_mult=vm)
    rows = []
    for i0 in starts:
        r = run_funded(D, i0, WT, ON, cfg, horizon_td=horizon_td)
        rows.append(r)
    df = pd.DataFrame(rows)
    return df
