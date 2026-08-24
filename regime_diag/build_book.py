"""Build the date-stamped event sources (per PRE_REGISTRATION §1,§3).
Cleanroom engine imported read-only from main dir; outputs cached to _cache.

 1. challenge_busts.parquet : every funnel bust (date, cause daily/floor, gap-bar,
    cohort_start) from a dense vm=14 sweep  [Q1 mechanics].
 2. book_daily.parquet      : the book's natural daily return series at vm=1, computed
    daily-RE-ANCHORED (bal=INIT each morning) => constant-exposure, no account-rule
    intraday stop / bust / reset => undistorted strategy return. daily_ret, worst_intraday
    (barrier-touch), real-dated  [Q1/Q2 power object].
 3. funded_mc.parquet       : funded-with-stops over dense cohorts -> per-cohort bust date
    + worst-DD day date  [Q2 mechanics confirmation, sparse].

Tail regime-profile is sizing-invariant (vm scales all days equally), so the constant-
exposure series characterises both books; books differ only in which horizon binds.
"""
import sys, time, pickle
from pathlib import Path
import numpy as np, pandas as pd

CLEAN = "<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/audit_v2_independent/cleanroom"
sys.path.insert(0, CLEAN)
import engine as E

HERE = Path(__file__).resolve().parent
CACHE = HERE / "_cache"; CACHE.mkdir(exist_ok=True)
t0 = time.time()
with open(CACHE / "M.pkl", "rb") as f:
    d = pickle.load(f); M, WT, ON = d["M"], d["WT"], d["ON"]
idx = M["dates"]; INIT = E.INIT; DB = E.DAILY_BUDGET; FLOOR = E.FLOOR
print(f"loaded M n={M['n']} {idx[0].date()}..{idx[-1].date()}")

# ----------------------------------------------------------------- 1. CHALLENGE
def build_challenge(step=2):
    starts = E.cohort_starts(M, idx[0], idx[-1], step=step)
    ev, coh = [], []
    for i0 in starts:
        diag = []
        r = E.run_funnel(M, int(i0), WT, ON, E.CFG_V2, diag=diag)
        coh.append(dict(start=idx[int(i0)], funded=r["funded"], attempts=r["attempts"], t=r["t"]))
        for dd in diag:
            if dd["kind"] != "bust":
                continue
            ev.append(dict(date=pd.Timestamp(dd["date"]),
                           cause="daily" if dd["eq"] >= FLOOR else "floor",
                           gap_bar=bool(dd["day_first_bar"]), eq=float(dd["eq"]),
                           cohort_start=idx[int(i0)]))
    EV = pd.DataFrame(ev); CO = pd.DataFrame(coh)
    EV.to_parquet(CACHE / "challenge_busts.parquet"); CO.to_parquet(CACHE / "challenge_cohorts.parquet")
    print(f"[challenge] cohorts={len(CO)} p_funded={CO.funded.mean():.3f} bust_events={len(EV)} "
          f"distinct_days={EV.date.dt.normalize().nunique()} cause={EV.cause.value_counts().to_dict()} "
          f"gap_frac={EV.gap_bar.mean():.2f} [{time.time()-t0:.0f}s]")
    return EV

# --------------------------------------------------- 2. BOOK daily (constant exposure)
FUNDED_CFG = dict(vm=1.0, on_w=0.35, orb_risk=0.0025, breaker=0.30, taper=0.02,
                  glide=1.0, pace=0, margin_cap=0.60, quantize=True, target=10.0)
def book_daily(cfg):
    pos = np.zeros(4); avg = np.full(4, np.nan); rows = []
    for i in range(M["n"]):
        bal = INIT                                  # daily re-anchor => constant exposure
        px_day, bounds = M["days"][i]; cuts = [0] + bounds + [len(px_day)]
        eq_open = bal + E._mtm(pos, avg, px_day[0])
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0
        orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        min_eq = eq_open
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
                    col = seg[:, k]; pl += np.where(np.isfinite(col), (col/avg[k]-1.0)*pos[k], 0.0)
            eq = bal + pl - dip; min_eq = min(min_eq, float(eq.min()))
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_close = bal + E._mtm(pos, avg, px_day[-1])
        rows.append(dict(date=idx[i], daily_ret=(eq_close - eq_open) / INIT,
                         worst_intraday=(min_eq - eq_open) / INIT))
    return pd.DataFrame(rows).set_index("date")

# --------------------------------------------------- 3. FUNDED mechanics (with stops)
def funded_cohort(i0, cfg, horizon=504, wd_every=14):
    bal = INIT; pos = np.zeros(4); avg = np.full(4, np.nan); days = 0; i = i0
    peak = INIT; worst_dd = 0.0; worst_dd_date = None; bust_date = None
    while i < M["n"] and days < horizon:
        limit = bal - DB; lim_eff = max(limit, FLOOR); brk = lim_eff + cfg["breaker"] * DB
        px_day, bounds = M["days"][i]; cuts = [0] + bounds + [len(px_day)]
        taper0 = float(np.clip((bal - FLOOR) / INIT / cfg["taper"], 0.0, 1.0))
        orb_risk = cfg.get("orb_risk", 0.0) * INIT * taper0; orb_live = orb_risk > 0 and M["orb_R"][i] != 0.0
        flat = False
        for s in range(5):
            a, b = cuts[s], cuts[s + 1]
            if a >= b: continue
            seg = px_day[a:b]
            if s == 4 and orb_live: bal += orb_risk * M["orb_R"][i]; orb_live = False
            dip = 1.31 * orb_risk if (orb_live and s in (2, 3)) else 0.0
            if not flat:
                tgt, _ = E._target_for_segment(s, i, M, WT, ON, cfg, bal, pos, avg, seg[0], i0, cfg["vm"])
                if tgt is not None: bal = E._trade_to(pos, avg, bal, tgt, seg[0], M["rt"])
            pl = np.zeros(len(seg))
            for k in range(4):
                if pos[k] != 0.0 and np.isfinite(avg[k]):
                    col = seg[:, k]; pl += np.where(np.isfinite(col), (col/avg[k]-1.0)*pos[k], 0.0)
            eq = bal + pl - dip; bad = eq < lim_eff; bk = eq < brk
            tb = int(np.argmax(bad)) if bad.any() else len(seg)
            tk = int(np.argmax(bk)) if bk.any() else len(seg)
            if min(tb, tk) < len(seg):
                if tb <= tk:
                    return dict(busted=True, bust_date=idx[i], life=days, worst_dd=1.0, worst_dd_date=idx[i])
                bal = E._flat(pos, avg, bal, seg[tk], M["rt"]); flat = True
        if np.any(pos):
            for k in range(4):
                if pos[k] != 0.0:
                    side = M["swL"][i, k] if pos[k] > 0 else M["swS"][i, k]
                    bal += abs(pos[k]) * side / 1e4 * M["mult"][i, k]
        eq_eod = bal + E._mtm(pos, avg, px_day[-1]); peak = max(peak, eq_eod)
        ddv = 1 - eq_eod / peak
        if ddv > worst_dd: worst_dd = ddv; worst_dd_date = idx[i]
        days += 1; i += 1
        if days % wd_every == 0 and bal > INIT: bal = INIT; peak = INIT
    return dict(busted=False, bust_date=bust_date, life=days, worst_dd=worst_dd, worst_dd_date=worst_dd_date)

def build_funded_mc(step=4):
    st = E.cohort_starts(M, idx[0], pd.Timestamp("2024-06-30"), step=step)
    rows = [dict(cohort_start=idx[int(i0)], **funded_cohort(int(i0), FUNDED_CFG)) for i0 in st]
    df = pd.DataFrame(rows); df.to_parquet(CACHE / "funded_mc.parquet")
    print(f"[funded_mc] cohorts={len(df)} bust_rate={df.busted.mean()*100:.1f}% "
          f"bust_dates={df.bust_date.notna().sum()} med_worstDD={df.worst_dd.median()*100:.1f}% "
          f"[{time.time()-t0:.0f}s]")
    return df

EV = build_challenge(step=2)
BD = book_daily(FUNDED_CFG); BD.to_parquet(CACHE / "book_daily.parquet")
ann_vol = BD.daily_ret.std() * np.sqrt(252)
print(f"[book] rows={len(BD)} ret mean={BD.daily_ret.mean()*1e4:.2f}bps/d ann_vol={ann_vol*100:.1f}% "
      f"min={BD.daily_ret.min()*100:.2f}% max={BD.daily_ret.max()*100:.2f}% "
      f"barrier_touch(<-5%)={int((BD.worst_intraday<-0.05).sum())}")
eq = (1 + BD.daily_ret).cumprod(); dd = 1 - eq / eq.cummax()
print(f"[book] equity x{eq.iloc[-1]:.2f} maxDD={dd.max()*100:.1f}% p90DD={dd.quantile(.9)*100:.1f}% "
      f"n_dd_episodes(>5%)={int(((dd>0.05)&(dd.shift(1)<=0.05)).sum())}")
FMC = build_funded_mc(step=4)
print(f"DONE {time.time()-t0:.0f}s")
