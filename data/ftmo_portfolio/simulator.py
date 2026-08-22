"""Exact FTMO 2-step simulator on joint M5 paths (CET) — segment engine.

Book legs: XAUUSD (trend), USDJPY (J1), US100 + GER40 (overnight midweek).
Position changes only at scheduled CET times:
  09:00  exit GER40 overnight leg
  15:30  exit US100 overnight leg
  17:35  enter GER40 overnight leg (if tonight flagged)
  22:05  trend rebalance (gold, jpy) + enter US100 overnight leg (if flagged)
=> each day = <=5 constant-position segments; joint equity path per segment is
   one numpy matmul; rule checks (daily limit / floor / breaker / target) exact
   on the M5 grid.

Rules (official 2026-05): daily limit = balance@00:00CET - 5%*initial (equity,
incl. floating, swaps, commissions); static floor 90%*initial; target on
BALANCE all-closed; min 4 trading days (opened) per phase; no time limit.
Accounting: balance vs equity separated; swaps posted nightly to balance
(3x day per class); realized P&L on reductions (avg price); costs = half-RT
bps on |delta notional|; lot quantization vs current price.
Quanto note: USDJPY P&L approximated in USD as notional*ret (documented).
"""
import numpy as np
import pandas as pd
import config as C

LEGS = ["XAUUSD", "USDJPY", "US100", "GER40"]
NL = len(LEGS)
INIT = float(C.ACCOUNT_SIZE)
DAILY_BUDGET = C.MAX_DAILY_LOSS * INIT
FLOOR = INIT * (1 - C.MAX_TOTAL_LOSS)
SCHED = ("09:00", "15:30", "17:35", "22:05")
CSIZE = {"XAUUSD": 100.0, "USDJPY": 100_000.0, "US100": 1.0, "GER40": 1.0}
VSTEP = 0.01


def lot_step(k, price):
    s = LEGS[k]
    return (CSIZE[s] if s == "USDJPY" else CSIZE[s] * price) * VSTEP


def quantize_vec(notional, prices, do=True):
    if not do:
        return notional.copy()
    out = np.zeros(NL)
    for k in range(NL):
        st = lot_step(k, prices[k])
        if st > 0 and np.isfinite(st):
            out[k] = np.round(notional[k] / st) * st
    return out


class Days:
    """Container: per-day segmented M5 prices + cost/swap rows."""
    def __init__(self, segs, dates, swapL, swapS, mult, rt_bps):
        self.segs = segs          # list of list[(label, px_array (T,4))]
        self.dates = dates        # list of Timestamps
        self.swapL = swapL; self.swapS = swapS; self.mult = mult
        self.rt = rt_bps          # np array (4,) round-trip bps
        self.n = len(dates)
        self.orb_R = np.zeros(len(dates))   # ORB E7 R-multiple per day (0 = no trade)


def build_days(m5df: pd.DataFrame, swapL, swapS, mult, rt_bps,
               start="2013-10-01", nan_mask=None) -> Days:
    df = m5df.loc[start:].copy()
    df = df.ffill()
    if nan_mask is not None:                 # audit fix: keep true data holes NaN
        nm = nan_mask.reindex(df.index).fillna(False)
        for c in nm.columns:
            df.loc[nm[c].values, c] = np.nan
    dates, segs = [], []
    hhmm = df.index.strftime("%H:%M")
    df["_seg"] = np.searchsorted([" 09:00", "15:30", "17:35", "22:05"], hhmm,
                                 side="right") if False else 0
    # segment id per bar
    seg_id = np.zeros(len(df), dtype=int)
    for j, t in enumerate(SCHED):
        seg_id += (hhmm >= t).astype(int)
    df["_seg"] = seg_id
    sL = swapL.reindex(columns=LEGS); sS = swapS.reindex(columns=LEGS)
    mu = mult.reindex(columns=LEGS)
    swL, swS, mus = [], [], []
    for d, g in df.groupby(df.index.date):
        if len(g) < 30:
            continue
        day_segs = []
        for sid, gg in g.groupby("_seg"):
            day_segs.append((int(sid), gg[LEGS].to_numpy(float)))
        dates.append(pd.Timestamp(d))
        segs.append(day_segs)
        dd = pd.Timestamp(d)
        swL.append(sL.loc[dd].to_numpy(float) if dd in sL.index else np.zeros(NL))
        swS.append(sS.loc[dd].to_numpy(float) if dd in sS.index else np.zeros(NL))
        mus.append(mu.loc[dd].to_numpy(float) if dd in mu.index else np.ones(NL))
    return Days(segs, dates, np.nan_to_num(np.array(swL)),
                np.nan_to_num(np.array(swS)),
                np.nan_to_num(np.array(mus), nan=1.0),
                rt_bps.reindex(LEGS).to_numpy(float))


# ---------------- core attempt ----------------

def run_attempt(D: Days, i0: int, WT: np.ndarray, ON: np.ndarray, cfg: dict):
    """One phase on a fresh account from day index i0.
    WT: (n_days, 2) unit notional fractions for [XAU, JPY] (signed, vol-normed)
    ON: (n_days,) 1.0 if the evening of day i holds overnight legs
    cfg keys: target, vol_mult, on_w, breaker_frac, taper_buf, glide,
              quantize, max_cal_days
    Returns dict(outcome, days_used, end_bal, last_idx)."""
    bal = INIT
    pos = np.zeros(NL)            # signed $ notional
    avg = np.full(NL, np.nan)     # avg entry price
    target = INIT * (1 + cfg["target"])
    open_days = 0
    zombie_days = 0
    ab_buf = cfg.get("abandon_buf", 0.0) * INIT
    ab_days = cfg.get("abandon_days", 10**9)
    i = i0
    while i < D.n:
        di = i - i0
        if cfg.get("max_cal_days") and (D.dates[i] - D.dates[i0]).days > cfg["max_cal_days"]:
            return dict(outcome="timeout", end=bal + _mtm(pos, avg, _last_px(D, i - 1)),
                        last_idx=i, days_used=di)
        daily_limit = bal - DAILY_BUDGET
        flat_today = False
        opened = False
        _taper0 = float(np.clip(((bal - FLOOR) / INIT) / cfg["taper_buf"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * _taper0
        orb_on = orb_risk > 0 and D.orb_R[i] != 0.0
        for sid, px in D.segs[i]:
            T = px.shape[0]
            # ORB synthetic leg: trade lives 15:30->22:05; post P&L at 22:05 open;
            # count a conservative constant dip (-1.31R) against rules while live
            if orb_on and sid == 4:
                bal += orb_risk * D.orb_R[i]
                opened = True
                orb_on = False
            orb_dip = (1.31 * orb_risk) if (orb_on and sid in (2, 3)) else 0.0
            if not flat_today:
                # position change at segment start
                newpos, _ = _sched_target(sid, i, D, WT, ON, cfg, bal, pos,
                                          avg, px[0], daily_limit, i0=i0)
                if newpos is not None:
                    did_open = bool(((np.abs(newpos) > 1e-9) &
                                     (np.abs(newpos - pos) > 1e-9)).any())
                    if sid == 4 and cfg.get("daily_realize", False):
                        bal = _flatten(pos, avg, px[0], bal, D.rt)
                    bal = _rebalance(pos, avg, newpos, px[0], bal, D.rt)
                    opened = opened or did_open
            # equity path over segment
            with np.errstate(invalid="ignore"):
                ratio = px / avg                      # (T,4)
            pl = np.where(np.isfinite(ratio) & (pos != 0.0), (ratio - 1.0) * pos, 0.0)
            eqp = bal + pl.sum(axis=1) - orb_dip
            # rule checks
            lim = max(daily_limit, FLOOR)
            bad = eqp < lim
            brk = eqp < lim + cfg["breaker_frac"] * DAILY_BUDGET
            hit = eqp >= target * (1 + 2e-4)
            t_bad = np.argmax(bad) if bad.any() else T
            t_brk = np.argmax(brk) if brk.any() else T
            t_hit = np.argmax(hit) if hit.any() else T
            t_first = min(t_bad, t_brk, t_hit)
            if t_first < T:
                if t_first == t_bad and t_bad <= min(t_brk, t_hit):
                    eq_end = eqp[t_bad]
                    return dict(outcome="bust_daily" if eq_end >= FLOOR else "bust_floor",
                                end=eq_end, last_idx=i, days_used=di + 1)
                if t_hit <= t_brk:
                    bal = _flatten(pos, avg, px[t_hit], bal, D.rt)
                    if bal >= target and open_days + (1 if opened else 0) >= C.MIN_TRADING_DAYS:
                        return dict(outcome="pass", end=bal, last_idx=i, days_used=di + 1)
                    # TOKEN-TRADE RULE (v2.1, audit équipe): au-dessus de la cible
                    # mais < 4 jours d'ouverture -> ouvrir/refermer un lot minimal
                    # pour comptabiliser le jour (live: 0.01 lot US100, ~$0.06 RT).
                    if bal >= target and not opened:
                        bal -= 287.0 * (D.rt[2] / 1e4)   # cout RT token 0.01 lot US100
                        opened = True
                        if open_days + 1 >= C.MIN_TRADING_DAYS:
                            return dict(outcome="pass", end=bal, last_idx=i,
                                        days_used=di + 1)
                    flat_today = True   # below target after costs: resume tomorrow
                else:
                    # pessimistic breaker fill: close +- k x bar range against us
                    kslip = cfg.get("breaker_slip_k", 0.0)
                    fill = px[t_brk].copy()
                    if kslip > 0.0 and t_brk > 0:
                        rng = np.abs(px[t_brk] - px[t_brk - 1])
                        fill = fill - np.sign(pos) * kslip * rng
                    bal = _flatten(pos, avg, fill, bal, D.rt)
                    flat_today = True
                    if bal < FLOOR:
                        return dict(outcome="bust_floor", end=bal, last_idx=i,
                                    days_used=di + 1)
                    if bal < daily_limit:
                        return dict(outcome="bust_daily", end=bal, last_idx=i,
                                    days_used=di + 1)
        # ---- end of day ----
        if pos.any():
            side = np.where(pos > 0, D.swapL[i], D.swapS[i])
            bal += float((np.abs(pos) * side / 1e4 * D.mult[i]).sum())
        if opened:
            open_days += 1
        # early pass possible while flat if min days satisfied later
        if not pos.any() and bal >= target and open_days >= C.MIN_TRADING_DAYS:
            return dict(outcome="pass", end=bal, last_idx=i, days_used=di + 1)
        # zombie detection: pinned near floor -> abandon (retry-able)
        eq_eod = bal + _mtm(pos, avg, _last_px(D, i))
        zombie_days = zombie_days + 1 if eq_eod < FLOOR + ab_buf else 0
        if zombie_days >= ab_days:
            return dict(outcome="abandon", end=eq_eod, last_idx=i, days_used=di + 1)
        i += 1
    return dict(outcome="timeout", end=bal + _mtm(pos, avg, _last_px(D, D.n - 1)),
                last_idx=D.n - 1, days_used=D.n - i0)


def _last_px(D, i):
    return D.segs[i][-1][1][-1]


def _mtm(pos, avg, px):
    with np.errstate(invalid="ignore"):
        r = px / avg
    return float(np.where(np.isfinite(r) & (pos != 0), (r - 1) * pos, 0).sum())


def _sched_target(sid, i, D, WT, ON, cfg, bal, pos, avg, px0, daily_limit,
                  i0=None):
    """Desired full position vector at the START of segment sid (None = no-op).
    seg ids: 0=[00:00,09:00) 1=[09:00,15:30) 2=[15:30,17:35) 3=[17:35,22:05) 4=[22:05,..)
    """
    di = i
    eq = bal + _mtm(pos, avg, px0)
    room_floor = (eq - FLOOR) / INIT
    taper = float(np.clip(room_floor / cfg["taper_buf"], 0.0, 1.0))
    prog = (eq / INIT - 1.0) / cfg["target"]
    glide = cfg["glide"] if prog > 0.8 else 1.0
    pace = 1.0
    if cfg.get("pace") and i0 is not None and cfg.get("max_cal_days"):
        frac_t = (D.dates[i] - D.dates[i0]).days / cfg["max_cal_days"]
        behind = frac_t - max(prog, 0.0)
        pace = float(np.clip(1.0 + cfg.get("pace_k", 1.0) * behind, 0.8, 2.0))
    scale = cfg["vol_mult"] * taper * glide * pace
    new = None; did_open = False
    if sid == 1:                      # 09:00 — drop GER40 overnight leg
        if pos[3] != 0.0:
            new = pos.copy(); new[3] = 0.0
    elif sid == 2:                    # 15:30 — drop US100 overnight leg
        if pos[2] != 0.0:
            new = pos.copy(); new[2] = 0.0
    elif sid == 3:                    # 17:35 — enter GER40 if tonight flagged
        if ON[di] > 0:
            new = pos.copy()
            new[3] = cfg.get("on_w_ger", cfg["on_w"]) * scale * eq
            did_open = True
    elif sid == 4:                    # 22:05 — trend rebalance + US100 overnight
        new = pos.copy()
        weekend = (cfg.get("weekend_flat", False)
                   and D.dates[di].dayofweek == 4)        # Friday evening
        new[0] = 0.0 if weekend else WT[di, 0] * cfg.get("w_gold", 1.0) * scale * eq
        new[1] = 0.0 if weekend else WT[di, 1] * cfg.get("w_jpy", 1.0) * scale * eq
        new[2] = (cfg["on_w"] * scale * eq) if ON[di] > 0 else 0.0
        did_open = bool(abs(new[0]) > 0 or abs(new[1]) > 0 or new[2] > 0)
    if new is None:
        return None, False
    # margin cap (measured FTMO rates: indices/gold 2%, FX 1%): scale down if
    # required margin would exceed cap x equity (audit MD 2026-06-10)
    mcap = cfg.get("margin_cap", None)
    if mcap is not None and eq > 0:
        mrate = np.array([0.02, 0.01, 0.02, 0.02])   # XAU, JPY, US100, GER40
        need = float(np.abs(new) @ mrate)
        if need > mcap * eq:
            new = new * (mcap * eq / need)
    new = quantize_vec(new, px0, cfg.get("quantize", True))
    return new, did_open


def _rebalance(pos, avg, newpos, prices, bal, rt):
    for k in range(NL):
        n, o = newpos[k], pos[k]
        if abs(n - o) < 1e-9:
            continue
        bal -= abs(n - o) * (rt[k] / 2.0) / 1e4
        if o != 0.0 and (n == 0.0 or n * o < 0 or abs(n) < abs(o)):
            closed = o - (n if n * o > 0 else 0.0)
            bal += closed * (prices[k] / avg[k] - 1.0)
        if n == 0.0:
            avg[k] = np.nan
        elif o == 0.0 or n * o < 0:
            avg[k] = prices[k]
        elif abs(n) > abs(o):
            w_old = abs(o) / abs(n)
            avg[k] = 1.0 / (w_old / avg[k] + (1.0 - w_old) / prices[k])
        pos[k] = n
    return bal


def _flatten(pos, avg, prices, bal, rt):
    for k in range(NL):
        if pos[k] != 0.0:
            bal += pos[k] * (prices[k] / avg[k] - 1.0)
            bal -= abs(pos[k]) * (rt[k] / 2.0) / 1e4
            pos[k] = 0.0; avg[k] = np.nan
    return bal


# ---------------- two-phase + retries ----------------

def run_funnel(D: Days, i0: int, WT, ON, cfg, wall_days=182, retries=True,
               gap_bd=3, retry_gap_bd=2):
    """Full mission from day i0: P1 (+10%) -> gap -> P2 (+5%), retries allowed
    while wall clock (calendar days) permits. Returns dict with outcome,
    n_attempts, t_pass_days (calendar), fees_paid (count of challenges)."""
    start_date = D.dates[i0]
    i = i0
    attempts = 0
    while True:
        if (D.dates[min(i, D.n - 1)] - start_date).days > wall_days or i >= D.n - 5:
            return dict(funded=False, attempts=attempts, t=np.nan)
        attempts += 1
        c1 = dict(cfg); c1["target"] = C.PHASE1_TARGET
        r1 = run_attempt(D, i, WT, ON, c1)
        if r1["outcome"] == "pass":
            j = min(r1["last_idx"] + gap_bd, D.n - 1)
            if (D.dates[j] - start_date).days > wall_days:
                return dict(funded=False, attempts=attempts, t=np.nan)
            c2 = dict(cfg); c2["target"] = C.PHASE2_TARGET
            c2["vol_mult"] = cfg["vol_mult"] * cfg.get("p2_mult", 0.7)
            r2 = run_attempt(D, j, WT, ON, c2)
            if r2["outcome"] == "pass":
                t = (D.dates[r2["last_idx"]] - start_date).days
                if t <= wall_days:
                    return dict(funded=True, attempts=attempts, t=t)
                return dict(funded=False, attempts=attempts, t=np.nan)
            if not retries:
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r2["last_idx"] + retry_gap_bd, D.n - 1)   # restart from scratch
        else:
            if r1["outcome"] == "timeout":
                return dict(funded=False, attempts=attempts, t=np.nan)
            if not retries:
                return dict(funded=False, attempts=attempts, t=np.nan)
            i = min(r1["last_idx"] + retry_gap_bd, D.n - 1)   # bust OR abandon -> retry
