"""v2.3 J1 study — arm runner.

Usage:
  python3 run_arms.py equiv               # acceptance: clone == engine_v22, all cohorts
  python3 run_arms.py baseline            # instrumented baseline (day records)
  python3 run_arms.py A_raw|A_iso|B_raw|B_iso|C_raw|C_iso

Arms (pre-registered, PREREGISTRATION.md):
  A: WT[:,1] *= 0.5          (J1 budget 0.5 -> 0.25)
  B: cfg j1_band = X*        (no-trade band, X* from band_X.json)
  C: WT[:,1]  = 0.0          (J1 OFF)
  *_iso: vm *= FACT (factors.json, frozen v2.1 procedure on v2.2 baseline records)
Outputs per arm: tables/cohorts_<arm>.csv, tables/attempts_<arm>.csv,
records/<arm>_days.parquet, records/<arm>_events.csv, records/<arm>_margins.parquet
"""
import sys, time, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j1_engine as J

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


# ---------------------------------------------------------------- equiv
if ARM == "equiv":
    cfg = dict(C22.CFG_CHALLENGE)
    bad = 0
    rows = []
    for n, (win, i0) in enumerate(cohort_grid()):
        r_ref = V22.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
        r_new = J.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
        same = (r_ref["funded"] == r_new["funded"]
                and r_ref["attempts"] == r_new["attempts"]
                and (r_ref["t"] == r_new["t"]
                     or (np.isnan(r_ref["t"]) and np.isnan(r_new["t"])))
                and r_ref["micro"] == r_new["micro"])
        if not same:
            bad += 1
            print(f"  MISMATCH i0={i0} ref={r_ref} new={r_new}", flush=True)
        rows.append(dict(win=win, start=M["dates"][i0], funded=r_new["funded"],
                         attempts=r_new["attempts"], t=r_new["t"], micro=r_new["micro"]))
        if n % 100 == 0:
            print(f"  {n} cohorts, mismatches={bad} [{time.time()-t0:.0f}s]", flush=True)
    d = pd.DataFrame(rows)
    # cross-check vs the committed v2.2 CONTRACTUAL table (battery anchor #1)
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
if ARM.startswith("A"):
    wt[:, 1] = 0.5 * wt[:, 1]
elif ARM.startswith("C"):
    wt[:, 1] = 0.0
elif ARM.startswith("B"):
    X = json.loads((HERE / "band_X.json").read_text())["X_star"]
    cfg["j1_band"] = float(X)
elif ARM != "baseline":
    raise SystemExit(f"unknown arm {ARM}")

if ARM.endswith("_iso"):
    F = json.loads((HERE / "factors.json").read_text())
    fact = F[f"FACT_{ARM[0]}"]
    cfg["vm"] = cfg["vm"] * float(fact)
    print(f"[{ARM}] iso-leverage vm = {cfg['vm']:.3f} (FACT={fact:.4f})", flush=True)

rows, att_log, rec, events, margins = [], [], [], [], []
grid = cohort_grid()
for n, (win, i0) in enumerate(grid):
    r = J.run_funnel(M, i0, wt, ON, cfg, wall=C22.WALL, rec=rec, events=events,
                     margins=margins, att_log=att_log,
                     cohort_id=int(i0), win=win)
    rows.append(dict(win=win, start=M["dates"][i0], cohort=int(i0),
                     funded=r["funded"], attempts=r["attempts"], t=r["t"],
                     micro=r["micro"]))
    if n % 100 == 0:
        print(f"[{ARM}] {n}/{len(grid)} [{time.time()-t0:.0f}s]", flush=True)

d = pd.DataFrame(rows)
d.to_csv(TAB / f"cohorts_{ARM}.csv", index=False)
pd.DataFrame(att_log).to_csv(TAB / f"attempts_{ARM}.csv", index=False)
pd.DataFrame(rec).to_parquet(REC / f"{ARM}_days.parquet", index=False)
pd.DataFrame(events).to_csv(REC / f"{ARM}_events.csv", index=False)
pd.DataFrame(margins).to_parquet(REC / f"{ARM}_margins.parquet", index=False)
p_is = d[d.win == "IS"].funded.mean()
p_oos = d[d.win == "OOS"].funded.mean()
print(f"[{ARM}] DONE IS {p_is*100:.1f} OOS {p_oos*100:.1f} pooled {d.funded.mean()*100:.2f} "
      f"att {d.attempts.mean():.2f} med_t {d.loc[d.funded,'t'].median():.0f} "
      f"days={len(rec)} events={len(events)} [{time.time()-t0:.0f}s]", flush=True)
