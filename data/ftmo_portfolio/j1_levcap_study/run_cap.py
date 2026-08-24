"""J1 leverage-cap study — arm runner (pre-registered, PREREGISTRATION.md).

Usage:
  python3 run_cap.py equiv          # baseline clone == v22 engine, all cohorts
  python3 run_cap.py baseline       # instrumented baseline (j1_lev_cap=0)
  python3 run_cap.py LCAP8|LCAP10|LCAP12|COMPRESS

Arms:
  LCAP8/10/12 : cfg["j1_lev_cap"] = 8/10/12   (engine hook, |notional_J1|/eq cap)
  COMPRESS    : WT[:,1] *= 0.5 where rvj in bottom-20th of trailing-504d dist, lag1 (causal)
Outputs: tables/cohorts_<arm>.csv, tables/attempts_<arm>.csv,
         records/<arm>_days.parquet, records/<arm>_events.csv, records/<arm>_margins.parquet
"""
import sys, time, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j1_engine_cap as J

E, C22, V22 = J.E, J.C22, J.V22
TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
REC = HERE / "records"; REC.mkdir(exist_ok=True)

ARM = sys.argv[1]
t0 = time.time()
M, WT, ON = J.load_all()
print(f"[{ARM}] stack loaded n={M['n']} [{time.time()-t0:.0f}s]", flush=True)


def cohort_grid():
    out = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V22.starts(M, lo, hi, C22.COHORT_STEP):
            out.append((win, int(i0)))
    return out


def compress_mult():
    """Causal compression flag: rvj (USDJPY 60d ann.vol) in bottom-20th of its trailing
    504-day distribution, lagged 1 day. Returns a per-M-date multiplier (0.5 / 1.0)."""
    PKG = HERE.parent
    rets = pd.read_parquet(PKG / "cache" / "panel_rets.parquet")["USDJPY"]
    rvj = rets.rolling(60, min_periods=20).std() * np.sqrt(252)
    q20 = rvj.rolling(504, min_periods=252).quantile(0.20)
    flag = (rvj <= q20).shift(1).fillna(False)              # decision uses info through t-1
    mult = pd.Series(np.where(flag, 0.5, 1.0), index=rvj.index)
    dates = pd.DatetimeIndex(M["dates"])
    return mult.reindex(dates).fillna(1.0).to_numpy(float)


# ---------------------------------------------------------------- equiv
if ARM == "equiv":
    cfg = dict(C22.CFG_CHALLENGE)                            # j1_lev_cap absent -> off
    bad = 0; rows = []
    for n, (win, i0) in enumerate(cohort_grid()):
        r_ref = V22.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
        r_new = J.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
        same = (r_ref["funded"] == r_new["funded"]
                and r_ref["attempts"] == r_new["attempts"]
                and (r_ref["t"] == r_new["t"]
                     or (np.isnan(r_ref["t"]) and np.isnan(r_new["t"])))
                and r_ref["micro"] == r_new["micro"])
        if not same:
            bad += 1; print(f"  MISMATCH i0={i0} ref={r_ref} new={r_new}", flush=True)
        rows.append(dict(win=win, start=M["dates"][i0], funded=r_new["funded"],
                         attempts=r_new["attempts"], t=r_new["t"], micro=r_new["micro"]))
    d = pd.DataFrame(rows)
    ref_csv = HERE.parent / "v22" / "tables" / "v22_challenge_91.csv"
    if ref_csv.exists():
        ref = pd.read_csv(ref_csv, parse_dates=["start"])
        m = d.merge(ref, on=["win", "start"], suffixes=("_new", "_v22"))
        mm = ((m.funded_new != m.funded_v22) | (m.attempts_new != m.attempts_v22)
              | ((m.t_new != m.t_v22) & ~(m.t_new.isna() & m.t_v22.isna()))).sum()
        print(f"vs committed CSV: {len(m)} matched rows, {mm} mismatches", flush=True)
        bad += int(mm)
    print(f"EQUIV {'PASS' if bad == 0 else f'FAIL ({bad})'} "
          f"n={len(d)} pooled={d.funded.mean()*100:.2f} [{time.time()-t0:.0f}s]", flush=True)
    sys.exit(0 if bad == 0 else 1)


# ---------------------------------------------------------------- arms
wt = WT.copy()
cfg = dict(C22.CFG_CHALLENGE)
if ARM == "baseline":
    pass
elif ARM == "LCAP8":
    cfg["j1_lev_cap"] = 8.0
elif ARM == "LCAP10":
    cfg["j1_lev_cap"] = 10.0
elif ARM == "LCAP12":
    cfg["j1_lev_cap"] = 12.0
elif ARM == "COMPRESS":
    mult = compress_mult()
    wt[:, 1] = wt[:, 1] * mult
    print(f"[{ARM}] compression mult applied: {100*(mult<1).mean():.1f}% of dates halved", flush=True)
else:
    raise SystemExit(f"unknown arm {ARM}")

rows, att_log, rec, events, margins = [], [], [], [], []
grid = cohort_grid()
for n, (win, i0) in enumerate(grid):
    r = J.run_funnel(M, i0, wt, ON, cfg, wall=C22.WALL, rec=rec, events=events,
                     margins=margins, att_log=att_log, cohort_id=int(i0), win=win)
    rows.append(dict(win=win, start=M["dates"][i0], cohort=int(i0),
                     funded=r["funded"], attempts=r["attempts"], t=r["t"], micro=r["micro"]))
    if n % 150 == 0:
        print(f"[{ARM}] {n}/{len(grid)} [{time.time()-t0:.0f}s]", flush=True)

d = pd.DataFrame(rows)
d.to_csv(TAB / f"cohorts_{ARM}.csv", index=False)
pd.DataFrame(att_log).to_csv(TAB / f"attempts_{ARM}.csv", index=False)
pd.DataFrame(rec).to_parquet(REC / f"{ARM}_days.parquet", index=False)
pd.DataFrame(events).to_csv(REC / f"{ARM}_events.csv", index=False)
pd.DataFrame(margins).to_parquet(REC / f"{ARM}_margins.parquet", index=False)
p_is = d[d.win == "IS"].funded.mean(); p_oos = d[d.win == "OOS"].funded.mean()
print(f"[{ARM}] DONE IS {p_is*100:.1f} OOS {p_oos*100:.1f} pooled {d.funded.mean()*100:.2f} "
      f"att {d.attempts.mean():.2f} med_t {d.loc[d.funded,'t'].median():.0f} "
      f"days={len(rec)} events={len(events)} [{time.time()-t0:.0f}s]", flush=True)
