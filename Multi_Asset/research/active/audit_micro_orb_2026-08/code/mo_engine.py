"""Clone INSTRUMENTÉ de engine_v22.run_phase / run_funnel.

Seul ajout : un journal par jour-tentative (qui a marqué le jour, valeur du
compteur, P&L micro, dip micro) + hooks d'ablation. Hooks OFF => les résultats
doivent être IDENTIQUES au moteur committé (test de non-régression obligatoire,
convention v23_j1_study/PREREGISTRATION.md).

Hooks (cfg) :
  micro_pnl_off = True   -> le micro marque le jour mais son P&L et son dip sont nuls
  micro_R        = array -> remplace M["mR"] (re-pricing L59)
  backstop_any   = True  -> le backstop $1 se déclenche dès qu'aucun trade n'est
                            ouvert et open_days < 4 (sans exiger bal >= target)
"""
import numpy as np

import mo_common as K

V = K.V
E = K.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET

COUNTERS = dict(micro_fires=0, backstop_fires=0)


def run_phase(M, i0, WT, ON, cfg, log=None):
    bal = INIT
    cash = 0.0
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    target = INIT * (1 + cfg["target"])
    open_days = 0
    zombie = 0
    vm = cfg["vm"]
    wgap_k = cfg.get("wgap_stress", 1.0)
    micro_fired_days = 0
    mR = cfg.get("micro_R")
    mR = M["mR"] if mR is None else mR
    pnl_off = bool(cfg.get("micro_pnl_off", False))
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            end = bal + E._mtm(pos, avg, M["days"][i - 1][0][-1])
            return dict(out="timeout", end=end, last=i, used=di, micro=micro_fired_days,
                        open_days=open_days)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = E.breaker_line(bal, cfg)
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        micro_today = (cfg.get("micro_orb", False)
                       and M["m_risk"][i] > 0 and mR[i] != 0.0)
        micro_cand = micro_today
        micro_risk = M["m_risk"][i] if micro_today else 0.0
        flat_today = False
        opened = False
        opened_by = None
        micro_pnl = 0.0
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
            if s == 4:
                if orb_live:
                    gain = orb_risk * M["orb_R"][i]
                    bal += gain
                    cash += gain
                    opened = True
                    opened_by = opened_by or "orb"
                    orb_live = False
                if micro_today and not opened:
                    gain = 0.0 if pnl_off else micro_risk * mR[i]
                    bal += gain
                    cash += gain
                    micro_pnl = gain
                    opened = True
                    opened_by = "micro"
                    micro_today = False
                    micro_fired_days += 1
                    COUNTERS["micro_fires"] += 1
                elif micro_today:
                    micro_today = False
            dip = 1.31 * (orb_risk if orb_live else 0.0) \
                + 1.31 * (0.0 if pnl_off else (micro_risk if micro_today else 0.0))
            dip = dip if s in (2, 3) else 0.0
            if not flat_today:
                tgt, did_open = E._target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                      pos, avg, seg[0], i0, vm)
                if tgt is not None:
                    b2 = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
                    cash += b2 - bal
                    bal = b2
                    if did_open and not opened:
                        opened_by = "book_s%d" % s
                    opened = opened or did_open
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            eq_chk = eq + gap_extra
            hb = eq_chk < lim_eff
            hk = eq_chk < brk_line
            if cfg.get("brk_needs_pos") and not np.any(pos):
                hk = hk & False
            ht = eq >= target * (1 + E.EPS_T)
            tb = int(np.argmax(hb)) if hb.any() else len(seg)
            tk = int(np.argmax(hk)) if hk.any() else len(seg)
            th = int(np.argmax(ht)) if ht.any() else len(seg)
            if min(tb, tk, th) < len(seg):
                if tb <= min(tk, th):
                    e = eq_chk[tb]
                    if log is not None:
                        log.append(dict(date=M["dates"][i], di=di, opened=opened,
                                        opened_by=opened_by, micro_cand=micro_cand,
                                        micro_pnl=micro_pnl, micro_risk=micro_risk,
                                        micro_dip=1.31 * micro_risk if micro_today else 0.0,
                                        open_days=open_days, event="bust", seg=s, bal=bal, target=target,
                                        breach_margin=float(lim_eff - e)))
                    return dict(out="bust_daily" if e >= FLOOR else "bust_floor",
                                end=e, last=i, used=di + 1, micro=micro_fired_days,
                                open_days=open_days)
                if th <= tk:
                    b2 = E._flat(pos, avg, bal, seg[th], M["rt"])
                    cash += b2 - bal
                    bal = b2
                    if bal >= target and open_days + (1 if opened else 0) >= E.MIN_OPEN_DAYS:
                        if log is not None:
                            log.append(dict(date=M["dates"][i], di=di, opened=opened,
                                            opened_by=opened_by, micro_cand=micro_cand,
                                            micro_pnl=micro_pnl, micro_risk=micro_risk,
                                            micro_dip=0.0, open_days=open_days,
                                            event="pass_intraday", seg=s, bal=bal, target=target))
                        return dict(out="pass", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days,
                                    open_days=open_days + (1 if opened else 0))
                    flat_today = True
                else:
                    fill = seg[tk].copy()
                    kslip = cfg.get("brk_slip", 0.0)
                    if kslip > 0.0 and tk > 0:
                        fill = fill - np.sign(pos) * kslip * np.abs(seg[tk] - seg[tk - 1])
                    b2 = E._flat(pos, avg, bal, fill, M["rt"])
                    cash += b2 - bal
                    bal = b2
                    flat_today = True
                    if bal < FLOOR:
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days, open_days=open_days)
                    if bal < limit:
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days, open_days=open_days)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    sw = abs(pos[k]) * side / 1e4 * M["mult"][i, k]
                    bal += sw
                    cash += sw
        if opened:
            open_days += 1
        bs = False
        if not np.any(pos) and bal >= target and open_days >= E.MIN_OPEN_DAYS:
            if log is not None:
                log.append(dict(date=M["dates"][i], di=di, opened=opened,
                                opened_by=opened_by, micro_cand=micro_cand,
                                micro_pnl=micro_pnl, micro_risk=micro_risk,
                                micro_dip=0.0, open_days=open_days, event="pass_eod",
                                seg=-1, bal=bal, target=target))
            return dict(out="pass", end=bal, last=i, used=di + 1,
                        micro=micro_fired_days, open_days=open_days)
        eq_eod = bal + E._mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            if log is not None:
                log.append(dict(date=M["dates"][i], di=di, opened=opened,
                                opened_by=opened_by, micro_cand=micro_cand,
                                micro_pnl=micro_pnl, micro_risk=micro_risk,
                                micro_dip=0.0, open_days=open_days, event="abandon",
                                seg=-1, bal=bal, target=target))
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1,
                        micro=micro_fired_days, open_days=open_days)
        bs_cond = (cfg.get("fix_deadlock") and not np.any(pos)
                   and open_days < E.MIN_OPEN_DAYS and not opened)
        if cfg.get("backstop_any"):
            bs_ok = bs_cond
        else:
            bs_ok = bs_cond and flat_today and bal >= target
        if bs_ok:
            open_days += 1
            bal -= 1.0
            cash -= 1.0
            bs = True
            COUNTERS["backstop_fires"] += 1
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                if log is not None:
                    log.append(dict(date=M["dates"][i], di=di, opened=True,
                                    opened_by="backstop", micro_cand=micro_cand,
                                    micro_pnl=0.0, micro_risk=micro_risk,
                                    micro_dip=0.0, open_days=open_days,
                                    event="pass_backstop", seg=-1, bal=bal, target=target))
                return dict(out="pass", end=bal, last=i, used=di + 1,
                            micro=micro_fired_days, open_days=open_days)
        if log is not None:
            log.append(dict(date=M["dates"][i], di=di, opened=opened or bs,
                            opened_by="backstop" if bs else opened_by,
                            micro_cand=micro_cand, micro_pnl=micro_pnl,
                            micro_risk=micro_risk, micro_dip=0.0,
                            open_days=open_days, event="day", seg=-1, bal=bal, target=target))
        i += 1
    end = bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1])
    return dict(out="timeout", end=end, last=M["n"] - 1, used=M["n"] - i0,
                micro=micro_fired_days, open_days=open_days)


def run_funnel(M, i0, WT, ON, cfg, wall=91, log=None):
    start = M["dates"][i0]
    i = i0
    attempts = 0
    micro_tot = 0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
        attempts += 1
        c1 = dict(cfg, target=E.TARGET1, max_cal=wall)
        r1 = run_phase(M, i, WT, ON, c1, log=log)
        micro_tot += r1["micro"]
        if r1["out"] == "pass":
            j = min(r1["last"] + 3, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            c2 = dict(cfg, target=E.TARGET2, max_cal=wall,
                      vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase(M, j, WT, ON, c2, log=log)
            micro_tot += r2["micro"]
            if r2["out"] == "pass":
                t = (M["dates"][r2["last"]] - start).days
                if t <= wall:
                    return dict(funded=True, attempts=attempts, t=t, micro=micro_tot)
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            if r2["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            i = min(r2["last"] + 2, M["n"] - 1)
        else:
            if r1["out"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            i = min(r1["last"] + 2, M["n"] - 1)
