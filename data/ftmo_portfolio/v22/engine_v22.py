"""v2.2 contractual engine — cleanroom semantics + MICRO-ORB + weekend-gap stress.

Imports the frozen audit cleanroom module READ-ONLY (data layer, signals, schedule,
accounting helpers). Phase loop re-derived here because v2.2 adds: micro-ORB posting,
weekend-only gap stress, cash-conservation identity accumulator, coverage counters.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

PKG = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PKG / "audit_v2_independent" / "cleanroom"))
import engine as E
import config_v22 as C22

LEDGER = Path("<HOME>/Desktop/Algo_claude/PropFirms/ftmo/"
              "program_2026-06/ftmo_research/audit/nq_v2_trades.parquet")
INIT, FLOOR, BUDGET = E.INIT, E.FLOOR, E.DAILY_BUDGET

COUNTERS = dict(micro_fires=0, backstop_fires=0, deadlock_days=0)


def load_stack(swap_mul=1.0, spread_mul=1.0, orb_rt_bps="era"):
    """Frozen stack + micro-ORB arrays + parameterized funded-ORB cost."""
    M = E.load_market(swap_mul=swap_mul, spread_mul=spread_mul)
    led = pd.read_parquet(LEDGER)
    lev = (led["entry"] / (led["entry"] - led["stop_eff"]).abs()).astype(float)
    if orb_rt_bps == "era":
        orb_R = pd.read_parquet(E.CACHE / "orb_e7_Rera.parquet")["R"]
    else:
        orb_R = led["r_gross"].astype(float) - float(orb_rt_bps) * 1e-4 * lev + 0.015
    M["orb_R"] = orb_R.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    # micro-ORB: same per-trade R; risk$ = 0.01 lot x or_range pts x $1/pt/lot
    M["mR"] = M["orb_R"].copy()
    m_risk = (0.01 * led["or_range"].astype(float))
    M["m_risk"] = m_risk.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    # anti (placebo) micro/full R: flip PRE-cost
    c_era = _implied_era_cost(led, lev)
    r_anti = (-led["r_gross"].astype(float) - c_era * 1e-4 * lev)
    M["orb_R_anti"] = r_anti.reindex(M["dates"]).fillna(0.0).to_numpy(float)
    # hot-loop optimization: plain list of Timestamps (author-engine style);
    # keep the DatetimeIndex for alignment under "dates_idx"
    M["dates_idx"] = M["dates"]
    M["dates"] = list(M["dates"])
    return M


def starts(M, lo, hi, step):
    idx = M["dates_idx"]
    sel = np.where((idx >= lo) & (idx <= hi))[0]
    return sel[::step]


def align(M, WT_df, ON_df):
    WTa = WT_df.reindex(M["dates_idx"]).fillna(0.0).to_numpy(float)
    ONa = ON_df.reindex(M["dates_idx"]).fillna(0.0).to_numpy(float)
    return WTa, ONa


def _implied_era_cost(led, lev):
    r15 = pd.read_parquet(E.CACHE / "orb_e7_R15.parquet")["R"]
    rera = pd.read_parquet(E.CACHE / "orb_e7_Rera.parquet")["R"]
    return pd.Series(1.5 - (rera.values - r15.values) * 1e4 / lev.values,
                     index=led.index)


def run_phase(M, i0, WT, ON, cfg, diag=None):
    bal = INIT
    cash = 0.0                                   # identity accumulator
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    target = INIT * (1 + cfg["target"])
    open_days = 0
    zombie = 0
    vm = cfg["vm"]
    wgap_k = cfg.get("wgap_stress", 1.0)
    micro_fired_days = 0
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            end = bal + E._mtm(pos, avg, M["days"][i - 1][0][-1])
            _identity(bal, cash, end, pos, avg, M["days"][i - 1][0][-1], 0.0)
            return dict(out="timeout", end=end, last=i, used=di,
                        micro=micro_fired_days)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)          # limite dure de BUST (inchangée)
        brk_line = E.breaker_line(bal, cfg)  # v2.4 (A) : dépend de cfg["brk_mode"]
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        # micro-ORB candidacy: signal exists; the "no other trade opened by
        # 21:30" condition is evaluated at posting time via the live `opened`
        # flag (state after the 17:35 segment = state at 21:30)
        micro_today = (cfg.get("micro_orb", False)
                       and M["m_risk"][i] > 0 and M["mR"][i] != 0.0)
        micro_risk = M["m_risk"][i] if micro_today else 0.0
        flat_today = False
        opened = False
        # weekend-gap stress (rule-check equity only), Monday-after-weekend
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
                    bal += gain; cash += gain
                    opened = True
                    orb_live = False
                if micro_today and not opened:      # nothing opened by 21:30
                    gain = micro_risk * M["mR"][i]
                    bal += gain; cash += gain
                    opened = True
                    micro_today = False
                    micro_fired_days += 1
                    COUNTERS["micro_fires"] += 1
                elif micro_today:                   # something opened earlier
                    micro_today = False
            dip = 1.31 * (orb_risk if orb_live else 0.0) \
                + 1.31 * (micro_risk if micro_today else 0.0)
            dip = dip if s in (2, 3) else 0.0
            if not flat_today:
                tgt, did_open = E._target_for_segment(s, i, M, WT, ON, cfg, bal,
                                                      pos, avg, seg[0], i0, vm)
                if tgt is not None:
                    b2 = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
                    cash += b2 - bal
                    bal = b2
                    opened = opened or did_open
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            eq_chk = eq + gap_extra
            hb = eq_chk < lim_eff
            # v2.4 : l'EA conditionne le breaker à OurPositionsExist() (cf. cleanroom)
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
                    if diag is not None:
                        diag.append(dict(date=M["dates"][i], seg=s, bar=tb, kind="bust",
                                         first_bar=(s == 0 and tb == 0)))
                    return dict(out="bust_daily" if e >= FLOOR else "bust_floor",
                                end=e, last=i, used=di + 1, micro=micro_fired_days)
                if th <= tk:
                    b2 = E._flat(pos, avg, bal, seg[th], M["rt"])
                    cash += b2 - bal; bal = b2
                    if bal >= target and open_days + (1 if opened else 0) >= E.MIN_OPEN_DAYS:
                        _identity(bal, cash, bal, pos, avg, seg[th], 0.0)
                        return dict(out="pass", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days)
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
                        return dict(out="bust_floor", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days)
                    if bal < limit:
                        return dict(out="bust_daily", end=bal, last=i, used=di + 1,
                                    micro=micro_fired_days)
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    sw = abs(pos[k]) * side / 1e4 * M["mult"][i, k]
                    bal += sw; cash += sw
        if opened:
            open_days += 1
        if not np.any(pos) and bal >= target and open_days >= E.MIN_OPEN_DAYS:
            _identity(bal, cash, bal, pos, avg, px_day[-1], 0.0)
            return dict(out="pass", end=bal, last=i, used=di + 1, micro=micro_fired_days)
        eq_eod = bal + E._mtm(pos, avg, px_day[-1])
        zombie = zombie + 1 if eq_eod < FLOOR + cfg.get("ab_buf", 0.0) * INIT else 0
        if zombie >= cfg.get("ab_days", 10 ** 9):
            return dict(out="abandon", end=eq_eod, last=i, used=di + 1,
                        micro=micro_fired_days)
        if (cfg.get("fix_deadlock") and flat_today and not np.any(pos)
                and bal >= target and open_days < E.MIN_OPEN_DAYS and not opened):
            open_days += 1
            bal -= 1.0; cash -= 1.0
            COUNTERS["backstop_fires"] += 1
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                return dict(out="pass", end=bal, last=i, used=di + 1,
                            micro=micro_fired_days)
        i += 1
    end = bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1])
    return dict(out="timeout", end=end, last=M["n"] - 1, used=M["n"] - i0,
                micro=micro_fired_days)


def _identity(bal, cash, end, pos, avg, px, dip):
    assert abs(bal - (INIT + cash)) < 1e-6, f"cash identity broken: {bal} vs {INIT+cash}"


def run_funnel(M, i0, WT, ON, cfg, wall=91, diag=None):
    start = M["dates"][i0]
    i = i0
    attempts = 0
    micro_tot = 0
    while True:
        if (M["dates"][min(i, M["n"] - 1)] - start).days > wall or i >= M["n"] - 5:
            return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
        attempts += 1
        c1 = dict(cfg, target=E.TARGET1, max_cal=wall)
        r1 = run_phase(M, i, WT, ON, c1, diag=diag)
        micro_tot += r1["micro"]
        if r1["out"] == "pass":
            j = min(r1["last"] + 3, M["n"] - 1)
            if (M["dates"][j] - start).days > wall:
                return dict(funded=False, attempts=attempts, t=np.nan, micro=micro_tot)
            c2 = dict(cfg, target=E.TARGET2, max_cal=wall,
                      vm=cfg["vm"] * cfg.get("p2_mult", 1.0))
            r2 = run_phase(M, j, WT, ON, c2, diag=diag)
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


def run_funded(M, i0, WT, ON, cfg, horizon=504, wd_every=14):
    """Funded stage (unchanged v2.1 dynamics): no clock, no target, withdrawals."""
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    i = i0
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)          # limite dure de BUST (inchangée)
        brk_line = E.breaker_line(bal, cfg)  # v2.4 (A) : dépend de cfg["brk_mode"]
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
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
                                               avg, seg[0], i0, cfg["vm"])
                if tgt is not None:
                    bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]
                    pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            bad = eq < lim_eff
            # v2.4 : l'EA conditionne le breaker à OurPositionsExist() (cf. cleanroom)
            brk = eq < brk_line
            if cfg.get("brk_needs_pos") and not np.any(pos):
                brk = brk & False
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    return dict(wd=total_wd, payouts=n_pay, life=days,
                                busted=True, residual=0.0)
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"])
                flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        days += 1
        i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT
            n_pay += 1
            bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res)
