"""Low-check evaluation overlay — instrumented clone of engine_v22 (v2.2 semantics).

Canonical engine NOT mutated. This module reproduces engine_v22.run_phase/run_funnel/run_funded
EXACTLY when mode="close", and swaps ONLY the breach-detection path to an adverse intra-bar
equity when mode!="close":
  - FTMO daily/max-loss FLOOR (hb) : adverse intra-bar (low for long / high for short) = CONTINUOUS
    liquidation (matches the 02-03/07 real breaches: FTMO monitor beat the discrete M5 breaker).
  - EA breaker (hk) : bar CLOSE = discrete-M5 (the EA can only act on M5 grid, breach postmortem).
  - target (ht), accounting, swaps, trades, pass : bar CLOSE (unchanged).
Modes: "close" (=canonical), "low" (floor adverse, breaker discrete — PRIMARY realistic),
       "low_both" (floor+breaker adverse — pre-registered literal, gives breaker foresight).

Adverse level uses a RANGE-OFFSET anchored to the canonical close:
  adv = sim_close + (duka_extreme_bidask - duka_close)   → immunises the US100 source seam;
identical to duka_extreme where duka_close==sim_close (XAU/JPY/GER40, median|Δ|=0).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))
import engine as E              # frozen cleanroom (data/signals/accounting)
import engine_v22 as V          # frozen v2.2 engine (reference)
import config_v22 as C22
HERE = Path(__file__).resolve().parent
LEGS = E.LEGS                   # [XAUUSD, USDJPY, US100, GER40]
INIT, FLOOR, BUDGET = E.INIT, E.FLOOR, E.DAILY_BUDGET


# ============================================================ data layer
def load_stack_lohi(orb_rt_bps="era", start="2013-10-01"):
    """Clone of E.load_market + V.load_stack, ALSO carrying per-day lo/hi adverse arrays
    (bid/ask, range-offset anchored to canonical close). px_day is bit-identical to E."""
    CACHE, AOUT = E.CACHE, E.AOUT
    m5 = pd.read_parquet(CACHE / "sim_m5_repaired.parquet").loc[start:].ffill()
    # GER40 hole mask (identical to E.load_market)
    raw_g = pd.read_parquet(CACHE / "sim_m5.parquet")["GER40"]
    w = raw_g.loc["2018":"2021"].dropna()
    per_day = w.groupby(w.index.date).size()
    holes = {d.date() for d in pd.bdate_range("2018-01-01", "2021-12-31")
             if per_day.get(d.date(), 0) < 50}
    day_of = pd.Series(m5.index.date, index=m5.index)
    ger_hole = day_of.isin(holes).values
    m5.loc[ger_hole, "GER40"] = np.nan

    # adverse lo/hi range-offset, applied to sim close, reindexed to m5 grid
    lohi = pd.read_parquet(HERE / "data/lohi_m5_paris.parquet").reindex(m5.index)
    lo = pd.DataFrame(index=m5.index, columns=LEGS, dtype=float)
    hi = pd.DataFrame(index=m5.index, columns=LEGS, dtype=float)
    for leg in LEGS:
        off_lo = (lohi[f"{leg}_lo_bid"] - lohi[f"{leg}_close"]).fillna(0.0)
        off_hi = (lohi[f"{leg}_hi_ask"] - lohi[f"{leg}_close"]).fillna(0.0)
        lo[leg] = m5[leg] + off_lo.clip(upper=0.0)          # low never above close
        hi[leg] = m5[leg] + off_hi.clip(lower=0.0)          # high never below close
    lo.loc[ger_hole, "GER40"] = np.nan
    hi.loc[ger_hole, "GER40"] = np.nan
    # where close present but lo/hi nan (no duka bar): lo=hi=close (no phantom range)
    lo = lo.where(np.isfinite(lo), m5[LEGS].values)
    hi = hi.where(np.isfinite(hi), m5[LEGS].values)

    sL = pd.read_parquet(CACHE / "panel_swapL.parquet")[LEGS]
    sS = pd.read_parquet(CACHE / "panel_swapS.parquet")[LEGS]
    mu = pd.read_parquet(CACHE / "panel_mult.parquet")[LEGS]
    rt = pd.read_csv(AOUT / "phase0_rt_cost_bps.csv", index_col=0).iloc[:, 0]
    rt = rt.reindex(LEGS).to_numpy(float)

    # vectorized contiguous-day grouping (m5 sorted) — identical groups to E.load_market
    m5v = m5[LEGS].to_numpy(float)
    lov = lo[LEGS].to_numpy(float)
    hiv = hi[LEGS].to_numpy(float)
    minutes = (m5.index.hour * 60 + m5.index.minute).to_numpy()
    dnorm = m5.index.normalize().to_numpy()
    chg = np.where(dnorm[1:] != dnorm[:-1])[0] + 1
    st_arr = np.concatenate([[0], chg])
    en_arr = np.concatenate([chg, [len(dnorm)]])
    days, lodays, hidays, dates = [], [], [], []
    for st, en in zip(st_arr, en_arr):
        if en - st < 30:
            continue
        mins = minutes[st:en]
        bounds = [int(np.searchsorted(mins, t, side="left")) for t in E.SCHED_MIN]
        days.append((m5v[st:en], bounds))
        lodays.append(lov[st:en])
        hidays.append(hiv[st:en])
        dates.append(pd.Timestamp(dnorm[st]))
    dates = pd.DatetimeIndex(dates)
    swL = sL.reindex(dates).fillna(0.0).to_numpy(float)
    swS = sS.reindex(dates).fillna(0.0).to_numpy(float)
    mlt = mu.reindex(dates).fillna(1.0).to_numpy(float)
    orbser = pd.read_parquet(CACHE / "orb_e7_Rera.parquet")["R"]
    orb_R = orbser.reindex(dates).fillna(0.0).to_numpy(float)
    M = dict(days=days, lodays=lodays, hidays=hidays, dates=dates,
             swL=swL, swS=swS, mult=mlt, rt=rt, orb_R=orb_R, n=len(dates))
    # V.load_stack additions (micro-ORB + funded-ORB cost)
    led = pd.read_parquet(V.LEDGER)
    lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
    M["orb_R"] = (pd.read_parquet(CACHE / "orb_e7_Rera.parquet")["R"]
                  .reindex(dates).fillna(0.0).to_numpy(float))
    M["mR"] = M["orb_R"].copy()
    M["m_risk"] = ((0.01 * led["or_range"].astype(float))
                   .reindex(dates).fillna(0.0).to_numpy(float))
    M["dates_idx"] = dates
    M["dates"] = list(dates)
    return M


# ============================================================ phase loop
def run_phase(M, i0, WT, ON, cfg, mode="close", diag=None, events=None):
    """Clone of V.run_phase; breach detection uses adverse intra-bar per `mode`."""
    bal = INIT; cash = 0.0
    pos = np.zeros(4); avg = np.full(4, np.nan)
    target = INIT * (1 + cfg["target"])
    open_days = 0; zombie = 0
    vm = cfg["vm"]; wgap_k = cfg.get("wgap_stress", 1.0)
    micro_fired_days = 0
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            end = bal + E._mtm(pos, avg, M["days"][i - 1][0][-1])
            return dict(out="timeout", end=end, last=i, used=di, micro=micro_fired_days)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        lo_day, hi_day = M["lodays"][i], M["hidays"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        micro_today = (cfg.get("micro_orb", False)
                       and M["m_risk"][i] > 0 and M["mR"][i] != 0.0)
        micro_risk = M["m_risk"][i] if micro_today else 0.0
        flat_today = False; opened = False
        gap_extra = 0.0
        if wgap_k != 1.0 and i > i0 and np.any(pos) \
                and (M["dates"][i] - M["dates"][i - 1]).days >= 3:
            prev_close = M["days"][i - 1][0][-1]
            op = px_day[0]
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(prev_close[k]) and np.isfinite(op[k]):
                    gap_extra += (wgap_k - 1.0) * pos[k] * (op[k] / prev_close[k] - 1.0)
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            seg_lo = lo_day[a:b]; seg_hi = hi_day[a:b]
            if s == 4:
                if orb_live:
                    gain = orb_risk * M["orb_R"][i]
                    bal += gain; cash += gain; opened = True; orb_live = False
                if micro_today and not opened:
                    gain = micro_risk * M["mR"][i]
                    bal += gain; cash += gain; opened = True
                    micro_today = False; micro_fired_days += 1
                elif micro_today:
                    micro_today = False
            dip = 1.31 * (orb_risk if orb_live else 0.0) \
                + 1.31 * (micro_risk if micro_today else 0.0)
            dip = dip if s in (2, 3) else 0.0
            if not flat_today:
                tgt, did_open = E._target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                      pos, avg, seg[0], i0, vm)
                if tgt is not None:
                    b2 = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
                    cash += b2 - bal; bal = b2
                    opened = opened or did_open
            # close-path equity (target, breaker[close], accounting)
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            # adverse-path equity (FTMO floor detection, continuous).
            # percol[:,k] = extra adverse of leg k vs its close (<=0); sum=all-legs
            # (conservative), min=single dominant leg (lower bound, legs hedge in risk-off)
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
            eq_chk = eq_adv + gap_extra                       # FLOOR breach on adverse
            eq_brk = (eq_adv if mode == "low_both" else eq) + gap_extra
            hb = eq_chk < lim_eff
            hk = eq_brk < brk_line
            ht = eq >= target * (1 + E.EPS_T)
            tb = int(np.argmax(hb)) if hb.any() else len(seg)
            tk = int(np.argmax(hk)) if hk.any() else len(seg)
            th = int(np.argmax(ht)) if ht.any() else len(seg)
            if min(tb, tk, th) < len(seg):
                if tb <= min(tk, th):
                    e = eq_chk[tb]
                    if events is not None:
                        u = {LEGS[k]: (float(pos[k] * ((seg_lo[tb, k] if pos[k] > 0
                             else seg_hi[tb, k]) / avg[k] - 1.0)) if pos[k] != 0
                             and np.isfinite(avg[k]) else 0.0) for k in range(4)}
                        events.append(dict(date=M["dates"][i], seg=s, bar=tb, mode=mode,
                                           kind="bust_daily" if e >= FLOOR else "bust_floor",
                                           eq=float(e), **{f"u_{n}": u[n] for n in LEGS}))
                    return dict(out="bust_daily" if e >= FLOOR else "bust_floor",
                                end=e, last=i, used=di + 1, micro=micro_fired_days)
                if th <= tk:
                    b2 = E._flat(pos, avg, bal, seg[th], M["rt"])
                    cash += b2 - bal; bal = b2
                    if bal >= target and open_days + (1 if opened else 0) >= E.MIN_OPEN_DAYS:
                        return dict(out="pass", end=bal, last=i, used=di + 1, micro=micro_fired_days)
                    flat_today = True
                else:
                    fill = seg[tk].copy()
                    kslip = cfg.get("brk_slip", 0.0)
                    if kslip > 0.0 and tk > 0:
                        fill = fill - np.sign(pos) * kslip * np.abs(seg[tk] - seg[tk - 1])
                    b2 = E._flat(pos, avg, bal, fill, M["rt"])
                    cash += b2 - bal; bal = b2
                    flat_today = True
                    if bal < FLOOR:
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1, micro=micro_fired_days)
                    if bal < limit:
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1, micro=micro_fired_days)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    sw = abs(pos[k]) * side / 1e4 * M["mult"][i, k]
                    bal += sw; cash += sw
        if opened:
            open_days += 1
        if not np.any(pos) and bal >= target and open_days >= E.MIN_OPEN_DAYS:
            return dict(out="pass", end=bal, last=i, used=di + 1, micro=micro_fired_days)
        eq_eod = bal + E._mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1, micro=micro_fired_days)
        if (cfg.get("fix_deadlock") and flat_today and not np.any(pos)
                and bal >= target and open_days < E.MIN_OPEN_DAYS and not opened):
            open_days += 1; bal -= 1.0; cash -= 1.0
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                return dict(out="pass", end=bal, last=i, used=di + 1, micro=micro_fired_days)
        i += 1
    end = bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1])
    return dict(out="timeout", end=end, last=M["n"] - 1, used=M["n"] - i0, micro=micro_fired_days)


def run_funnel(M, i0, WT, ON, cfg, wall=91, mode="close", att_log=None, cohort_id=None,
               win=None, events=None):
    start = M["dates"][i0]; i = i0; attempts = 0; micro_tot = 0

    def cd(ii):
        return int((M["dates"][min(ii, M["n"] - 1)] - start).days)
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot, camp_days=cd(i))
        attempts += 1
        c1 = dict(cfg, target=E.TARGET1, max_cal=wall)
        r1 = run_phase(M, i, WT, ON, c1, mode=mode, events=events)
        micro_tot += r1["micro"]
        if att_log is not None:
            att_log.append(dict(cohort=cohort_id, win=win, attempt=attempts, phase=1,
                                out=r1["out"], used=r1["used"], start_date=M["dates"][i]))
        if r1["out"] == "pass":
            j = min(r1["last"] + 3, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot, camp_days=cd(j))
            c2 = dict(cfg, target=E.TARGET2, max_cal=wall, vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase(M, j, WT, ON, c2, mode=mode, events=events)
            micro_tot += r2["micro"]
            if att_log is not None:
                att_log.append(dict(cohort=cohort_id, win=win, attempt=attempts, phase=2,
                                    out=r2["out"], used=r2["used"], start_date=M["dates"][j]))
            if r2["out"] == "pass":
                t = (M["dates"][r2["last"]] - start).days
                if t <= wall:
                    return dict(funded=True, attempts=attempts, t=t, micro=micro_tot, camp_days=t)
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot, camp_days=cd(r2["last"]))
            if r2["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot, camp_days=cd(r2["last"]))
            i = min(r2["last"] + 2, M["n"] - 1)
        else:
            if r1["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot, camp_days=cd(r1["last"]))
            i = min(r1["last"] + 2, M["n"] - 1)


def run_funded(M, i0, WT, ON, cfg, horizon=504, wd_every=14, mode="close", events=None):
    """Funded stage clone; FTMO floor detection on adverse per mode."""
    bal = INIT; pos = np.zeros(4); avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    i = i0
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        lo_day, hi_day = M["lodays"][i], M["hidays"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
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
                    if events is not None:
                        u = {LEGS[k]: (float(pos[k] * ((seg_lo[tb, k] if pos[k] > 0
                             else seg_hi[tb, k]) / avg[k] - 1.0)) if pos[k] != 0
                             and np.isfinite(avg[k]) else 0.0) for k in range(4)}
                        events.append(dict(date=M["dates"][i], mode=mode, life=days,
                                           wd_banked=total_wd, **{f"u_{n}": u[n] for n in LEGS}))
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True, residual=0.0)
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"]); flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        days += 1; i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT; n_pay += 1; bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res)
