"""J1 suspension study — run all arms in one process (PREREGISTRATION.md).

  equiv  : baseline clone == engine_v22.run_funnel (EQUIV gate, must reproduce pooled ~87)
  baseline / FULLOFF / GATE160 / GATE158

Injection = multiplier on WT[:,1] upstream of the funnel — the EXACT live mechanism
(weights["USDJPY"]=0 -> ea_w_usdjpy=0 -> EA flattens J1 at 22:05). Hooks in j1_engine stay inert.
Outputs: tables/cohorts_<arm>.csv, tables/attempts_<arm>.csv, records/<arm>_{days.parquet,events.csv,margins.parquet}.
"""
import sys, time, json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import j1_engine as J
import gate as G

E, C22, V22 = J.E, J.C22, J.V22
TAB = HERE / "tables"; TAB.mkdir(exist_ok=True)
REC = HERE / "records"; REC.mkdir(exist_ok=True)

t0 = time.time()
M, WT, ON = J.load_all()
DATES = pd.DatetimeIndex(M["dates"])
print(f"stack loaded n={M['n']} dates {DATES.min().date()}..{DATES.max().date()} "
      f"[{time.time()-t0:.0f}s]", flush=True)

# USDJPY close aligned to M dates — the engine's OWN panel (== what build_signals reads)
PX_JPY = pd.read_parquet(HERE.parent / "cache" / "panel_px.parquet")["USDJPY"]


def gate_mask(t_off, t_on, n):
    """Causal per-M-date boolean suspend mask + multiplier (0 suspend, 1 keep)."""
    susp = G.suspend_causal(PX_JPY, t_off=t_off, t_on=t_on, n=n)
    m = susp.reindex(DATES).fillna(False).to_numpy(bool)
    return m, (~m).astype(float)


def cohort_grid():
    out = []
    for win, lo, hi in C22.WINDOWS:
        for i0 in V22.starts(M, lo, hi, C22.COHORT_STEP):
            out.append((win, int(i0)))
    return out


GRID = cohort_grid()
print(f"cohorts={len(GRID)}  IS={sum(1 for w,_ in GRID if w=='IS')}  "
      f"OOS={sum(1 for w,_ in GRID if w=='OOS')}", flush=True)

# ---------------------------------------------------------------- EQUIV gate
bad = 0
peq = []
for win, i0 in GRID:
    cfg = dict(C22.CFG_CHALLENGE)
    rr = V22.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
    rn = J.run_funnel(M, i0, WT, ON, cfg, wall=C22.WALL)
    same = (rr["funded"] == rn["funded"] and rr["attempts"] == rn["attempts"]
            and (rr["t"] == rn["t"] or (np.isnan(rr["t"]) and np.isnan(rn["t"]))))
    if not same:
        bad += 1
        if bad <= 5:
            print(f"  MISMATCH i0={i0} ref={rr} new={rn}", flush=True)
    peq.append(rn["funded"])
print(f"EQUIV {'PASS' if bad==0 else f'FAIL ({bad})'} "
      f"pooled={100*np.mean(peq):.2f} [{time.time()-t0:.0f}s]", flush=True)
if bad:
    sys.exit(1)

# ---------------------------------------------------------------- arms
# spec: None=baseline ; ("full",)=FULLOFF ; (t_off,t_on,n)=gate
ARMS = {
    "baseline": None,
    "FULLOFF": ("full",),
    "GATE160": (160.0, 155.0, 10),
    "GATE158": (158.0, 155.0, 10),   # sensitivity on T_off only
}

meta = {}
for name, spec in ARMS.items():
    wt = WT.copy()
    mask = None
    if spec is None:
        pass
    elif spec == ("full",):
        wt[:, 1] = 0.0
    else:
        mask, mult = gate_mask(*spec)
        wt[:, 1] = wt[:, 1] * mult
    rows, att_log, rec, events, margins = [], [], [], [], []
    for win, i0 in GRID:
        cfg = dict(C22.CFG_CHALLENGE)
        r = J.run_funnel(M, i0, wt, ON, cfg, wall=C22.WALL, rec=rec, events=events,
                         margins=margins, att_log=att_log, cohort_id=int(i0), win=win)
        rows.append(dict(win=win, start=M["dates"][i0], cohort=int(i0), funded=r["funded"],
                         attempts=r["attempts"], t=r["t"], micro=r["micro"]))
    d = pd.DataFrame(rows)
    d.to_csv(TAB / f"cohorts_{name}.csv", index=False)
    pd.DataFrame(att_log).to_csv(TAB / f"attempts_{name}.csv", index=False)
    pd.DataFrame(rec).to_parquet(REC / f"{name}_days.parquet", index=False)
    pd.DataFrame(events).to_csv(REC / f"{name}_events.csv", index=False)
    pd.DataFrame(margins).to_parquet(REC / f"{name}_margins.parquet", index=False)
    m = dict(pooled=float(d.funded.mean()),
             p_IS=float(d[d.win == "IS"].funded.mean()),
             p_OOS=float(d[d.win == "OOS"].funded.mean()),
             attempts=float(d.attempts.mean()),
             med_t=float(d.loc[d.funded, "t"].median()) if d.funded.any() else float("nan"))
    if mask is not None:
        m["days_off"] = int(mask.sum())
        m["frac_dates_off"] = float(mask.mean())
        # cohorts whose 91-day window overlaps any suspended day
        off_dates = set(DATES[mask])
        touched = 0
        for win, i0 in GRID:
            s = DATES[i0]
            e = s + pd.Timedelta(days=C22.WALL)
            if any(s <= od <= e for od in off_dates):
                touched += 1
        m["cohorts_touched"] = touched
        m["cohorts_total"] = len(GRID)
    meta[name] = m
    extra = (f" days_off={m.get('days_off','-')} touched={m.get('cohorts_touched','-')}"
             if mask is not None else "")
    print(f"[{name}] pooled {100*m['pooled']:.2f} IS {100*m['p_IS']:.2f} OOS {100*m['p_OOS']:.2f} "
          f"att {m['attempts']:.2f}{extra} [{time.time()-t0:.0f}s]", flush=True)

(TAB / "meta.json").write_text(json.dumps(meta, indent=2, default=str))
print("DONE", flush=True)
