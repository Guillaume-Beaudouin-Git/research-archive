"""Funded-container harness: a VERBATIM copy of the audited asia_inject.run_funded
(gold-dosing branch) with the ASIA block swapped for a BREAKOUT block (M['brk_net'],
M['brk_low']). engine_v22 (V) + config_v22 (C22) imported read-only from main dir.
Also: the canonical FUNDED_WINDOWS driver + a constant-exposure book daily series (Q1).

Injection placement = canonical (day-start block, barrier bal+brk_low<lim_eff), matching
asia/basket. PRIMARY. A conservative combined-low variant (book intraday-min + brk_low) is
provided for the robustness check (the breakout is intraday-concurrent with the book)."""
import sys
from pathlib import Path
import numpy as np, pandas as pd

V22 = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/v22"
sys.path.insert(0, V22)
import engine_v22 as V          # noqa
import config_v22 as C22        # noqa
E = V.E
INIT, FLOOR, BUDGET = V.INIT, V.FLOOR, V.BUDGET


def run_funded(M, i0, WT, ON, cfg, horizon=504, wd_every=14):
    """asia_inject.run_funded, brk swap. cfg['brk_on'], cfg['brk_lev'], cfg.get('brk_combined')."""
    bal = INIT; pos = np.zeros(4); avg = np.full(4, np.nan)
    total_wd, n_pay, days = 0.0, 0, 0; min_eq = INIT; i = i0
    combined = cfg.get("brk_combined", False)
    while i < M["n"] and days < horizon:
        limit = bal - BUDGET; lim_eff = max(limit, FLOOR); brk_line = lim_eff + cfg["breaker"] * BUDGET
        px_day, bounds = M["days"][i]; cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat_today = False
        a_net = a_low = 0.0
        brk_today = cfg.get("brk_on") and M["brk_net"][i] != 0.0
        if brk_today:
            klev = cfg.get("brk_lev", 1.0)
            a_net = INIT * klev * float(M["brk_net"][i]); a_low = INIT * klev * float(M["brk_low"][i])
            if not combined:                       # PRIMARY: canonical day-start block (asia pattern)
                min_eq = min(min_eq, bal + a_low)
                if bal + a_low < lim_eff:
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True, residual=0.0, min_eq=min_eq)
                bal += a_net
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b: continue
            seg = px_day[a:b]
            if s == 4 and orb_live: bal += orb_risk * M["orb_R"][i]; orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat_today:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg, seg[0], i0, cfg["vm"])
                if tgt is not None: bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]; pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip
            # conservative variant: book intraday low + breakout low co-occur
            eq_chk = eq + (a_low if (combined and brk_today) else 0.0)
            bad = eq_chk < lim_eff; brk = eq < brk_line
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(brk)) if brk.any() else len(seg)
            min_eq = min(min_eq, float(eq_chk.min()))
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    return dict(wd=total_wd, payouts=n_pay, life=days, busted=True,
                                residual=0.0, min_eq=min(min_eq, float(eq_chk[tb])))
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"]); flat_today = True
        if combined and brk_today: bal += a_net    # realize breakout net at EOD in combined variant
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_eod = bal + E._mtm(pos, avg, M["days"][i][0][-1]); min_eq = min(min_eq, eq_eod)
        days += 1; i += 1
        if days % wd_every == 0 and bal > INIT:
            total_wd += bal - INIT; n_pay += 1; bal = INIT
    px_last = M["days"][min(i, M["n"] - 1)][0][-1]
    res = max(bal + E._mtm(pos, avg, px_last) - INIT, 0.0)
    return dict(wd=total_wd, payouts=n_pay, life=days, busted=False, residual=res, min_eq=min_eq)


def load_stack():
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    M["brk_net"] = np.zeros(M["n"]); M["brk_low"] = np.zeros(M["n"])
    return M


def set_brk(M, series, lev_scale):
    """Align breakout (net, low) [DatetimeIndex of UTC dates] to book dates_idx (same-day),
    pre-scaled by lev_scale (= vol-target factor). Dose applied separately via cfg['brk_lev']."""
    bd = M["dates_idx"]
    net = (series["net"] * lev_scale).reindex(bd).fillna(0.0).to_numpy(float)
    low = (series["low"] * lev_scale).reindex(bd).fillna(0.0).to_numpy(float)
    M["brk_net"] = net; M["brk_low"] = low
    return float((series["net"].reindex(bd).notna()).mean())   # coverage frac


FEE = C22.FEE
def funded_run(M, WT, ON, brk_on, brk_lev, fstarts, combined=False):
    cfg = dict(C22.CFG_FUNDED, brk_on=brk_on, brk_lev=brk_lev, brk_combined=combined)
    lives, wds, mineqs = [], [], []
    for i0 in fstarts:
        r = run_funded(M, int(i0), WT, ON, cfg, horizon=C22.FUNDED_HORIZON, wd_every=C22.FUNDED_WD_EVERY)
        lives.append(r["life"]); wds.append(0.0 if r["busted"] else 0.8 * (r["wd"] + r["residual"]))
        mineqs.append(r.get("min_eq", np.nan))
    lives = np.array(lives)
    return dict(survive252=float((lives >= 252).mean()), fundedV=round(float(np.mean(wds)) + FEE, 0),
                min_eq_med=float(np.nanmedian(mineqs)), n=len(fstarts))


def fstarts(M):
    return np.concatenate([V.starts(M, lo, hi, C22.FUNDED_STEP) for _, lo, hi in C22.FUNDED_WINDOWS])


def book_daily_series(M, WT, ON, cfg=None):
    """Constant-exposure (daily re-anchored vm=1) realized book daily return + intraday-low,
    incl. ORB. No account-rule stop/withdrawal — the book's natural daily series (for Q1)."""
    cfg = cfg or dict(C22.CFG_FUNDED)
    pos = np.zeros(4); avg = np.full(4, np.nan); rows = []
    for i in range(M["n"]):
        bal = INIT
        px_day, bounds = M["days"][i]; cuts = [0] + bounds + [len(px_day)]
        eq_open = bal + E._mtm(pos, avg, px_day[0]); min_eq = eq_open
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b: continue
            seg = px_day[a:b]
            if s == 4 and orb_live: bal += orb_risk * M["orb_R"][i]; orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg, seg[0], 0, cfg["vm"])
            if tgt is not None: bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]; pl += np.where(np.isfinite(col), (col / avg[k] - 1.0) * pos[k], 0.0)
            eq = bal + pl - dip; min_eq = min(min_eq, float(eq.min()))
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_close = bal + E._mtm(pos, avg, px_day[-1])
        rows.append(dict(date=M["dates_idx"][i], book_ret=(eq_close - eq_open) / INIT,
                         book_low=(min_eq - eq_open) / INIT))
    return pd.DataFrame(rows).set_index("date")
