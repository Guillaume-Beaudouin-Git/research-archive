"""v2.3 J1-study engine — instrumented clone of v22/engine_v22.py (v2.2 semantics).

Observation-only except ONE hook: cfg["j1_band"] (default 0.0 = off) — the pre-registered
variant-B no-trade band on the J1 leg at the 22:05 rebalance, applied BEFORE margin cap and
quantization. With j1_band=0 and untouched WT, run_funnel() must reproduce
engine_v22.run_funnel() exactly (acceptance-tested per cohort).

Recording (all observation, no behavior change):
  - per day-attempt: per-leg pnl decomposition (realized - cost + swap + delta-unrealized),
    per-leg executed $-turnover, J1 (prev, raw-target) pair at s4 pre-band, weekend-gap pnl
    of held legs at day open, EOD bal/eq/pos, margin need & bind at 17:35/22:05 rebalances.
  - bust events: weekday, segment, gap-day flag, per-leg unrealized at breach, per-leg gap pnl.
  - identity: INIT + sum(attributed) == end equity per attempt, tolerance = micro dip on
    s2/s3-bust micro days (documented v2.1 phantom) + 1e-6.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(PKG / "audit_v2_independent" / "cleanroom"))
sys.path.insert(0, str(PKG / "v22"))
import engine as E           # frozen cleanroom (data/signals/accounting)
import engine_v22 as V22     # frozen v2.2 engine (stack loader + equivalence reference)
import config_v22 as C22

INIT, FLOOR, BUDGET = E.INIT, E.FLOOR, E.DAILY_BUDGET
LEG_NAMES = ["gold", "jpy", "on_us", "on_ger"]


def load_all():
    """Frozen v2.2 stack + signals, aligned (v22 helpers: M['dates'] is a list)."""
    M = V22.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_df, ON_df = E.build_signals()
    WT, ON = V22.align(M, WT_df, ON_df)
    return M, WT, ON


# ------------------------------------------------------------- accounting
def _trade_to_attr(pos, avg, bal, target, prices, rt, cost_out, real_out, turn_out):
    """Exact clone of E._trade_to with per-leg cost/realized/turnover accumulation."""
    for k in range(4):
        t, o, p = target[k], pos[k], prices[k]
        if abs(t - o) < 1e-9:
            continue
        if not np.isfinite(p):
            continue
        c = abs(t - o) * (rt[k] / 2.0) / 1e4
        bal -= c
        cost_out[k] += c
        turn_out[k] += abs(t - o)
        if o != 0.0:
            if t == 0.0 or t * o < 0:
                r = o * (p / avg[k] - 1.0)
                bal += r; real_out[k] += r
            elif abs(t) < abs(o):
                r = (o - t) * (p / avg[k] - 1.0)
                bal += r; real_out[k] += r
        if t == 0.0:
            avg[k] = np.nan
        elif o == 0.0 or t * o < 0:
            avg[k] = p
        elif abs(t) > abs(o):
            inv = (abs(o) / abs(t)) / avg[k] + (1 - abs(o) / abs(t)) / p
            avg[k] = 1.0 / inv
        pos[k] = t
    return bal


def _u_vec(pos, avg, prices):
    u = np.zeros(4)
    for k in range(4):
        if pos[k] != 0.0 and np.isfinite(avg[k]) and np.isfinite(prices[k]):
            u[k] = pos[k] * (prices[k] / avg[k] - 1.0)
    return u


# ------------------------------------------------- target with J1-band hook
def _target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg, px0, i0, vm, obs):
    """Clone of E._target_for_segment + j1_band hook + margin observation."""
    eq = bal + E._mtm(pos, avg, px0)
    room = (eq - FLOOR) / INIT
    taper = float(np.clip(room / cfg["taper"], 0.0, 1.0))
    prog = (eq / INIT - 1.0) / cfg["target"]
    glide = cfg.get("glide", 1.0) if prog > 0.8 else 1.0
    pace = 1.0
    if cfg.get("pace") and cfg.get("max_cal"):
        frac_t = (M["dates"][i] - M["dates"][i0]).days / cfg["max_cal"]
        pace = float(np.clip(1.0 + cfg.get("pace_k", 1.0) * (frac_t - max(prog, 0.0)),
                             0.8, 2.0))
    scale = vm * taper * glide * pace
    tgt = None
    opened = False
    if s == 1 and pos[3] != 0.0:                      # 09:00 GER40 off
        tgt = pos.copy(); tgt[3] = 0.0
    elif s == 2 and pos[2] != 0.0:                    # 15:30 US100 off
        tgt = pos.copy(); tgt[2] = 0.0
    elif s == 3 and ON[i] > 0:                        # 17:35 GER40 on
        tgt = pos.copy()
        tgt[3] = cfg["on_w"] * scale * eq
        opened = True
    elif s == 4:                                      # 22:05 rebalance
        tgt = pos.copy()
        tgt[0] = WT[i, 0] * scale * eq
        tgt[1] = WT[i, 1] * scale * eq
        tgt[2] = cfg["on_w"] * scale * eq if ON[i] > 0 else 0.0
        if obs is not None:
            obs["j1_prev"] = float(pos[1])
            obs["j1_tgt_raw"] = float(tgt[1])
        # --- pre-registered J1 leverage cap hook (j1_levcap_study/PREREGISTRATION.md) ---
        # cap |notional_J1| / eq <= Lc ; sign-preserving ; applied AFTER recording the raw
        # target, BEFORE the j1_band hold-logic and BEFORE the proportional margin cap.
        Lc = cfg.get("j1_lev_cap", 0.0)
        if Lc > 0.0 and eq > 0 and tgt[1] != 0.0 and abs(tgt[1]) > Lc * eq:
            tgt[1] = (1.0 if tgt[1] > 0 else -1.0) * Lc * eq
            if obs is not None:
                obs["j1_capped"] = 1.0
        X = cfg.get("j1_band", 0.0)
        if (X > 0.0 and pos[1] != 0.0 and tgt[1] != 0.0 and pos[1] * tgt[1] > 0
                and abs(tgt[1] - pos[1]) <= X * abs(tgt[1])):
            tgt[1] = pos[1]                           # hold: no J1 trade
        opened = bool(abs(tgt[0]) > 0 or abs(tgt[1]) > 0 or tgt[2] > 0)
    if tgt is None:
        return None, False
    mcap = cfg.get("margin_cap")
    if mcap is not None and eq > 0:
        need = float(np.abs(tgt) @ E.MRATE)
        if obs is not None and s in (3, 4) and abs(tgt).sum() > 0:
            obs.setdefault("margin", []).append((s, need / eq, need > mcap * eq))
        if need > mcap * eq:
            tgt = tgt * (mcap * eq / need)
    tgt = E._quantize(tgt, px0) if cfg.get("quantize", True) else tgt
    return tgt, opened


# ------------------------------------------------------------- phase loop
def run_phase(M, i0, WT, ON, cfg, rec=None, events=None, margins=None, meta=None):
    """Instrumented clone of engine_v22.run_phase. rec/events/margins: lists or None."""
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
    backstop_fires = 0
    u_prev = np.zeros(4)
    attr_sum = 0.0                       # sum of all attributed day pnl
    meta = meta or {}
    i = i0

    def day_rec(exit_prices, outcome, d_cost, d_real, d_swap, d_orb, d_micro, d_fix,
                d_turn, gap_pnl, obs, di):
        nonlocal u_prev, attr_sum
        u_now = _u_vec(pos, avg, exit_prices)
        pnl = d_real - d_cost + d_swap + (u_now - u_prev)
        day_total = float(pnl.sum() + d_orb + d_micro + d_fix)
        attr_sum += day_total
        if rec is not None:
            mg = obs.get("margin", [])
            r = dict(meta)
            r.update(date=M["dates"][i], di=di, weekday=int(M["dates"][i].dayofweek),
                     gap_day=bool(i > 0 and (M["dates"][i] - M["dates"][i - 1]).days >= 3),
                     outcome=outcome, bal=bal,
                     eq_eod=bal + float(u_now.sum()),
                     orb=d_orb, micro=d_micro, fix=d_fix,
                     j1_prev=obs.get("j1_prev", np.nan),
                     j1_tgt_raw=obs.get("j1_tgt_raw", np.nan),
                     margin_need_max=max((m[1] for m in mg), default=np.nan),
                     margin_bind_any=any(m[2] for m in mg),
                     gap_pnl_gold=gap_pnl[0], gap_pnl_jpy=gap_pnl[1])
            for k, nm in enumerate(LEG_NAMES):
                r[nm] = float(pnl[k])
                r["cost_" + nm] = float(d_cost[k])
                r["turn_" + nm] = float(d_turn[k])
                r["pos_" + nm] = float(pos[k])
            rec.append(r)
        if margins is not None:
            for s_, nd, bd in obs.get("margin", []):
                margins.append(dict(date=M["dates"][i], seg=s_, need=nd, bind=bd, **meta))
        u_prev = u_now
        return u_now

    def bust_event(exit_prices, kind, seg_id, bar, gap_pnl):
        if events is None:
            return
        u_now = _u_vec(pos, avg, exit_prices)
        ev = dict(meta)
        ev.update(date=M["dates"][i], weekday=int(M["dates"][i].dayofweek),
                  gap_day=bool(i > 0 and (M["dates"][i] - M["dates"][i - 1]).days >= 3),
                  kind=kind, seg=seg_id, bar=int(bar),
                  gap_pnl_gold=gap_pnl[0], gap_pnl_jpy=gap_pnl[1])
        for k, nm in enumerate(LEG_NAMES):
            ev["u_" + nm] = float(u_now[k])
        events.append(ev)

    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            end = bal + E._mtm(pos, avg, M["days"][i - 1][0][-1])
            _check_identity(end, attr_sum, 0.0)
            return dict(out="timeout", end=end, last=i, used=di,
                        micro=micro_fired_days, backstop=backstop_fires)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        # micro-ORB candidacy (v2.2 rev 20:42): "no other trade opened by 21:30"
        # evaluated at posting time via the live `opened` flag
        micro_today = (cfg.get("micro_orb", False)
                       and M["m_risk"][i] > 0 and M["mR"][i] != 0.0)
        micro_risk = M["m_risk"][i] if micro_today else 0.0
        flat_today = False
        opened = False
        d_cost = np.zeros(4); d_real = np.zeros(4); d_swap = np.zeros(4)
        d_turn = np.zeros(4)
        d_orb = 0.0; d_micro = 0.0; d_fix = 0.0
        obs = {}
        # weekend-gap pnl of legs held over the day boundary (observation)
        gap_pnl = np.zeros(2)            # [gold, jpy] — only weekend-held legs
        if i > i0 and np.any(pos[:2]) and i > 0:
            prev_close = M["days"][i - 1][0][-1]
            op = px_day[0]
            for k in (0, 1):
                if pos[k] != 0.0 and np.isfinite(prev_close[k]) and np.isfinite(op[k]):
                    gap_pnl[k] = pos[k] * (op[k] / prev_close[k] - 1.0)
        is_gap_day = bool(i > 0 and (M["dates"][i] - M["dates"][i - 1]).days >= 3)
        if not is_gap_day:
            gap_pnl[:] = 0.0             # keep the metric weekend-specific
        # weekend-gap stress (rule-check only) — v2.2 semantics
        wgap_extra = 0.0
        if wgap_k != 1.0 and i > i0 and np.any(pos) \
                and (M["dates"][i] - M["dates"][i - 1]).days >= 3:
            prev_close = M["days"][i - 1][0][-1]
            op = px_day[0]
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(prev_close[k]) and np.isfinite(op[k]):
                    wgap_extra += (wgap_k - 1.0) * pos[k] * (op[k] / prev_close[k] - 1.0)
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b:
                continue
            seg = px_day[a:b]
            if s == 4:
                if orb_live:
                    gain = orb_risk * M["orb_R"][i]
                    bal += gain; cash += gain; d_orb += gain
                    opened = True
                    orb_live = False
                if micro_today and not opened:      # nothing opened by 21:30
                    gain = micro_risk * M["mR"][i]
                    bal += gain; cash += gain; d_micro += gain
                    opened = True
                    micro_today = False
                    micro_fired_days += 1
                elif micro_today:                   # something opened earlier
                    micro_today = False
            dip = 1.31 * (orb_risk if orb_live else 0.0) \
                + 1.31 * (micro_risk if micro_today else 0.0)
            dip = dip if s in (2, 3) else 0.0
            if not flat_today:
                tgt, did_open = _target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                    pos, avg, seg[0], i0, vm, obs)
                if tgt is not None:
                    b2 = _trade_to_attr(pos, avg, bal, tgt, seg[0], M["rt"],
                                        d_cost, d_real, d_turn)
                    cash += b2 - bal
                    bal = b2
                    opened = opened or did_open
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            eq_chk = eq + wgap_extra
            hb = eq_chk < lim_eff
            hk = eq_chk < brk_line
            ht = eq >= target * (1 + E.EPS_T)
            tb = int(np.argmax(hb)) if hb.any() else len(seg)
            tk = int(np.argmax(hk)) if hk.any() else len(seg)
            th = int(np.argmax(ht)) if ht.any() else len(seg)
            if min(tb, tk, th) < len(seg):
                if tb <= min(tk, th):
                    e = eq_chk[tb]
                    kind = "bust_daily" if e >= FLOOR else "bust_floor"
                    bust_event(seg[tb], kind, s, tb, gap_pnl)
                    day_rec(seg[tb], kind, d_cost, d_real, d_swap, d_orb, d_micro,
                            d_fix, d_turn, gap_pnl, obs, di)
                    _check_identity(e, attr_sum, dip)
                    return dict(out=kind, end=e, last=i, used=di + 1,
                                micro=micro_fired_days, backstop=backstop_fires)
                if th <= tk:
                    b2 = _trade_to_attr(pos, avg, bal, np.zeros(4), seg[th], M["rt"],
                                        d_cost, d_real, d_turn)
                    cash += b2 - bal; bal = b2
                    if bal >= target and open_days + (1 if opened else 0) >= E.MIN_OPEN_DAYS:
                        day_rec(seg[th], "pass", d_cost, d_real, d_swap, d_orb,
                                d_micro, d_fix, d_turn, gap_pnl, obs, di)
                        _check_identity(bal, attr_sum, 0.0)
                        return dict(out="pass", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days, backstop=backstop_fires)
                    flat_today = True
                else:
                    fill = seg[tk].copy()
                    kslip = cfg.get("brk_slip", 0.0)
                    if kslip > 0.0 and tk > 0:
                        fill = fill - np.sign(pos) * kslip * np.abs(seg[tk] - seg[tk - 1])
                    b2 = _trade_to_attr(pos, avg, bal, np.zeros(4), fill, M["rt"],
                                        d_cost, d_real, d_turn)
                    cash += b2 - bal; bal = b2
                    flat_today = True
                    if bal < FLOOR:
                        bust_event(fill, "bust_floor", s, tk, gap_pnl)
                        day_rec(fill, "bust_floor", d_cost, d_real, d_swap, d_orb,
                                d_micro, d_fix, d_turn, gap_pnl, obs, di)
                        _check_identity(bal, attr_sum, 0.0)
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days, backstop=backstop_fires)
                    if bal < limit:
                        bust_event(fill, "bust_daily", s, tk, gap_pnl)
                        day_rec(fill, "bust_daily", d_cost, d_real, d_swap, d_orb,
                                d_micro, d_fix, d_turn, gap_pnl, obs, di)
                        _check_identity(bal, attr_sum, 0.0)
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days, backstop=backstop_fires)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    sw = abs(pos[k]) * side / 1e4 * M["mult"][i, k]
                    bal += sw; cash += sw; d_swap[k] += sw
        if opened:
            open_days += 1
        if not np.any(pos) and bal >= target and open_days >= E.MIN_OPEN_DAYS:
            day_rec(px_day[-1], "pass", d_cost, d_real, d_swap, d_orb, d_micro,
                    d_fix, d_turn, gap_pnl, obs, di)
            _check_identity(bal, attr_sum, 0.0)
            return dict(out="pass", end=bal, last=i, used=di + 1,
                        micro=micro_fired_days, backstop=backstop_fires)
        eq_eod = bal + E._mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            day_rec(px_day[-1], "abandon", d_cost, d_real, d_swap, d_orb, d_micro,
                    d_fix, d_turn, gap_pnl, obs, di)
            _check_identity(eq_eod, attr_sum, 0.0)
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1,
                        micro=micro_fired_days, backstop=backstop_fires)
        if (cfg.get("fix_deadlock") and flat_today and not np.any(pos)
                and bal >= target and open_days < E.MIN_OPEN_DAYS and not opened):
            open_days += 1
            bal -= 1.0; cash -= 1.0; d_fix -= 1.0
            backstop_fires += 1
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                day_rec(px_day[-1], "pass", d_cost, d_real, d_swap, d_orb, d_micro,
                        d_fix, d_turn, gap_pnl, obs, di)
                _check_identity(bal, attr_sum, 0.0)
                return dict(out="pass", end=bal, last=i, used=di + 1,
                            micro=micro_fired_days, backstop=backstop_fires)
        day_rec(px_day[-1], "mid", d_cost, d_real, d_swap, d_orb, d_micro,
                d_fix, d_turn, gap_pnl, obs, di)
        i += 1
    end = bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1])
    return dict(out="timeout", end=end, last=M["n"] - 1, used=M["n"] - i0,
                micro=micro_fired_days, backstop=backstop_fires)


def _check_identity(end, attr_sum, dip_allow):
    resid = abs(INIT + attr_sum - end)
    assert resid <= dip_allow + 1e-6, f"attribution identity broken: resid={resid}"


# ----------------------------------------------------------------- funnel
def run_funnel(M, i0, WT, ON, cfg, wall=91, rec=None, events=None, margins=None,
               att_log=None, cohort_id=None, win=None):
    start = M["dates"][i0]
    i = i0
    attempts = 0
    micro_tot = 0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
        attempts += 1
        meta = dict(cohort=cohort_id, win=win, attempt=attempts, phase=1)
        c1 = dict(cfg, target=E.TARGET1, max_cal=wall)
        r1 = run_phase(M, i, WT, ON, c1, rec, events, margins, meta)
        micro_tot += r1["micro"]
        if att_log is not None:
            att_log.append(dict(meta, out=r1["out"], end=r1["end"], used=r1["used"],
                                micro=r1["micro"], backstop=r1["backstop"],
                                start_date=M["dates"][i]))
        if r1["out"] == "pass":
            j = min(r1["last"] + 3, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            meta = dict(cohort=cohort_id, win=win, attempt=attempts, phase=2)
            c2 = dict(cfg, target=E.TARGET2, max_cal=wall,
                      vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase(M, j, WT, ON, c2, rec, events, margins, meta)
            micro_tot += r2["micro"]
            if att_log is not None:
                att_log.append(dict(meta, out=r2["out"], end=r2["end"], used=r2["used"],
                                    micro=r2["micro"], backstop=r2["backstop"],
                                    start_date=M["dates"][j]))
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
