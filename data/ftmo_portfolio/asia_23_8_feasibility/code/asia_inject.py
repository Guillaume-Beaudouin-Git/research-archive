"""Sandbox injection of ASIA_23_8 into the AUDITED v2.2 bar engine (read-only reuse).

Strategy: copy v2.2 run_phase / run_funded VERBATIM and insert exactly ONE ASIA block
at the correct causal point — right after the daily-loss line (limit/lim_eff/brk_line)
is fixed from balance@00:00, and BEFORE the 09:00 (segment-0) book loop. The ASIA window
01:00->09:00 CET closes exactly at the book's first segment, and the FTMO daily-loss day
that contains ASIA also contains that book day (server reset 00:00 = 21:00/22:00 UTC,
2h/1h before the 23:00 UTC entry), so ASIA and the book share one daily-loss reference.

ASIA injection per day i:
  a_net  = INIT * asia_lev * M["asia_net"][i]   (close P&L, account $)
  a_low  = INIT * asia_lev * M["asia_low"][i]   (worst intraday excursion, account $)
  - barrier: if bal + a_low < lim_eff -> bust (daily if >= FLOOR else floor)
  - else realize: bal += a_net; cash += a_net; opened=True (counts for min-4-days)
ASIA is swap-free (Q4) -> no swap leg.

VALIDATION: with cfg["asia_on"] absent/False, patched == audited -> reproduces pooled 0.87.
Only `asia_on` adds behaviour; `book_on=False` is achieved by zeroing WT/ON/on_w/orb/micro.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

V22 = Path("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/v22")
sys.path.insert(0, str(V22))
import engine_v22 as V          # noqa: E402
import config_v22 as C22        # noqa: E402
E = V.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import asia_series as ASER       # noqa: E402


# ============================ patched challenge phase ============================
def run_phase(M, i0, WT, ON, cfg, diag=None):
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
    i = i0
    while i < M["n"]:
        di = i - i0
        if cfg.get("max_cal") and (M["dates"][i] - M["dates"][i0]).days > cfg["max_cal"]:
            end = bal + E._mtm(pos, avg, M["days"][i - 1][0][-1])
            V._identity(bal, cash, end, pos, avg, M["days"][i - 1][0][-1], 0.0)
            return dict(out="timeout", end=end, last=i, used=di, micro=micro_fired_days)
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        micro_today = (cfg.get("micro_orb", False)
                       and M["m_risk"][i] > 0 and M["mR"][i] != 0.0)
        micro_risk = M["m_risk"][i] if micro_today else 0.0
        flat_today = False
        opened = False
        # ------------------- ASIA_23_8 injection (01:00-09:00 CET, swap-free) -------------------
        if cfg.get("asia_on") and M["asia_net"][i] != 0.0:
            klev = cfg.get("asia_lev", 1.0)
            a_net = INIT * klev * float(M["asia_net"][i])
            a_low = INIT * klev * float(M["asia_low"][i])
            eq_low = bal + a_low
            if eq_low < lim_eff:
                if diag is not None:
                    diag.append(dict(date=M["dates"][i], seg=-1, kind="bust_asia",
                                     eq=eq_low))
                return dict(out="bust_daily" if eq_low >= FLOOR else "bust_floor",
                            end=eq_low, last=i, used=di + 1, micro=micro_fired_days)
            bal += a_net
            cash += a_net
            opened = True
        # ----------------------------------------------------------------------------------------
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
                if micro_today and not opened:
                    gain = micro_risk * M["mR"][i]
                    bal += gain; cash += gain
                    opened = True
                    micro_today = False
                    micro_fired_days += 1
                    V.COUNTERS["micro_fires"] += 1
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
            hk = eq_chk < brk_line
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
                        V._identity(bal, cash, bal, pos, avg, seg[th], 0.0)
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
            V._identity(bal, cash, bal, pos, avg, px_day[-1], 0.0)
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
            V.COUNTERS["backstop_fires"] += 1
            if bal >= target and open_days >= E.MIN_OPEN_DAYS:
                return dict(out="pass", end=bal, last=i, used=di + 1,
                            micro=micro_fired_days)
        i += 1
    end = bal + E._mtm(pos, avg, M["days"][M["n"] - 1][0][-1])
    return dict(out="timeout", end=end, last=M["n"] - 1, used=M["n"] - i0,
                micro=micro_fired_days)


# ============================== patched funded stage ==============================
DAILY_EQ = []      # appended (date, equity) per funded day when cfg["log_eq"]


def run_funded(M, i0, WT, ON, cfg, horizon=504, wd_every=14):
    bal = INIT
    pos = np.zeros(4)
    avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0
    min_eq = INIT
    i = i0
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET
        lim_eff = max(limit, FLOOR)
        brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]
        cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        if cfg.get("asia_on") and M["asia_net"][i] != 0.0:
            klev = cfg.get("asia_lev", 1.0)
            a_low = INIT * klev * float(M["asia_low"][i])
            min_eq = min(min_eq, bal + a_low)
            if bal + a_low < lim_eff:
                return dict(wd=total_wd, payouts=n_pay, life=days, busted=True,
                            residual=0.0, min_eq=min_eq)
            bal += INIT * klev * float(M["asia_net"][i])
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
            brk = eq < brk_line
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            min_eq = min(min_eq, float(eq.min()))
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True,
                                residual=0.0, min_eq=min(min_eq, float(eq[tb])))
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"])
                flat_today = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_eod = bal + E._mtm(pos, avg, M["days"][i][0][-1])
        min_eq = min(min_eq, eq_eod)
        if cfg.get("log_eq"):
            DAILY_EQ.append((M["dates"][i], eq_eod))
        days += 1
        i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT
            n_pay += 1
            bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res, min_eq=min_eq)


# install the patches (run_funnel resolves the module-global run_phase at call time)
V.run_phase = run_phase
V.run_funded = run_funded


# ============================== stack + signal builders ==============================
def load_asia_stack(spread_bps=1.5, regime_overlay=False, ma100_gate=False):
    """v2.2 market stack + ASIA arrays aligned to book dates (aday D -> book D+1)."""
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    a = ASER.build(spread_bps=spread_bps)
    net = a["net_simple"].copy()
    low = a["low_frac"].copy()
    scale = pd.Series(1.0, index=a.index)
    if ma100_gate:
        eq = (1 + a["net_simple"]).cumprod()
        g = (eq > eq.rolling(100).mean()).astype(float).replace(0.0, 0.4).shift(1).fillna(1.0)
        scale = scale * g
    if regime_overlay:
        drift = a["raw_log"].rolling(252).sum().shift(1)
        scale = scale * (drift > 0).astype(float).fillna(0.0)
    net = net * scale
    low = low * scale
    bd = M["dates_idx"]
    M["asia_net"] = ASER.align_to_book(net, bd)
    M["asia_low"] = ASER.align_to_book(low, bd)
    M["asia_traded"] = ASER.align_to_book((a["pos"] * 0 + 1.0) * scale.clip(upper=1.0), bd)
    return M


def book_off_signals(M):
    """Zero WT/ON so the 4 book legs never trade (ASIA-standalone)."""
    WT = np.zeros((M["n"], 2))
    ON = np.zeros(M["n"])
    return WT, ON
