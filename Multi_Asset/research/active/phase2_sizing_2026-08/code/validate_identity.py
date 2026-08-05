"""Three validations, all fail-loud.

A. THE DAY-COUNTER. Three arms on phase 2: the inherited (defective) CFG_LIVE, the
   cleanroom `fix_deadlock` stand-in, and the DEPLOYED v2.2 micro-ORB counter. Counts
   how many `timeout` accounts sit AT OR ABOVE the +5 % target (those are winners
   recorded as deaths), and measures how long the counter itself takes.

B. THE COLLAPSE IDENTITY. With the Pace denominator frozen at 91, `max_cal` reaches
   `run_phase` only at the timeout check, so collapsing one long run onto a horizon H
   must equal re-running the engine at max_cal=H. Checked cohort-by-cohort.

C. THE STRUCTURAL FACT. How many risk events per calendar week does the MONO book
   actually take, and how many sessions does the min-4-trading-days counter need?
"""
import time

import numpy as np
import pandas as pd

import p2_lib as L

E, V = L.E, L.V
t0 = time.time()

M = L.market()
WT, ON = L.book_mono(M)
dates = pd.DatetimeIndex(M["dates_idx"])
print(f"market: n={M['n']} days  {dates[0].date()} -> {dates[-1].date()}")

L.set_pace(91, on=True)
starts = L.cohort_starts(M, runway_td=60, step=7)
print(f"cohorts: {len(starts)}  ({dates[starts[0]].date()} -> {dates[starts[-1]].date()})")

# ---------------------------------------------------------------- A. counter
ARMS = [
    ("inherited CFG_LIVE (NO counter)", dict(micro_orb=False, fix_deadlock=False), "clean"),
    ("cleanroom fix_deadlock only", dict(micro_orb=False, fix_deadlock=True), "clean"),
    ("DEPLOYED spec: micro-ORB + backstop", dict(), "v22"),
]
rows = []
for name, patch, eng in ARMS:
    cfg = dict(L.CFG_LIVE, **patch)
    for H in (7, 14, 35, 70):
        c = dict(cfg, target=E.TARGET2, max_cal=H, vm=14.0 * cfg["p2_mult"])
        run = V.run_phase if eng == "v22" else E.run_phase
        outs, ends = [], []
        for i0 in starts:
            r = run(M, i0, WT, ON, c)
            outs.append(r["out"]); ends.append(r["end"])
        outs, ends = np.array(outs), np.array(ends)
        to = outs == "timeout"
        tgt = E.INIT * 1.05
        rows.append(dict(arm=name, engine=eng, H_cal=H, n=len(outs),
                         p_pass=float((outs == "pass").mean()),
                         p_timeout=float(to.mean()),
                         p_floor=float((outs == "bust_floor").mean()),
                         p_daily=float((outs == "bust_daily").mean()),
                         p_abandon=float((outs == "abandon").mean()),
                         timeouts_at_or_above_target=(float((ends[to] >= tgt).mean())
                                                      if to.any() else np.nan),
                         median_timeout_equity=(float(np.median(ends[to]))
                                                if to.any() else np.nan)))
dd = pd.DataFrame(rows)
dd.to_csv(L.TAB / "counter_defect_phase2.csv", index=False)
print("\n--- A. the min-trading-days counter, PHASE 2 ---")
print(dd.round(4).to_string(index=False))

# ---------------------------------------------------------------- B. identity
bad = 0
for eng in ("v22", "clean"):
    res = L.resolve(M, WT, ON, starts, vm_spec=14.0, engine=eng)
    for H in (7, 14, 21, 35, 49, 70):
        c = dict(L.CFG_LIVE, target=E.TARGET2, max_cal=H, vm=14.0 * 1.2)
        run = V.run_phase if eng == "v22" else E.run_phase
        direct = np.array([run(M, i0, WT, ON, c)["out"] == "pass" for i0 in starts])
        coll = L.horizon_stats(res, H)["pass_flags"]
        n_dis = int((direct != coll).sum())
        bad += n_dis
        print(f"  [{eng}] H={H:3d}  direct {direct.mean():.5f}  collapsed "
              f"{coll.mean():.5f}  disagreements={n_dis}/{len(starts)}")
assert bad == 0, f"COLLAPSE IDENTITY BROKEN: {bad} disagreements"
print("IDENTITY OK (0 disagreements, both engines).")

# ---------------------------------------------------------------- C. structure
on_idx = np.flatnonzero(ON > 0)
per_week = pd.Series(1.0, index=dates[on_idx]).resample("W").sum()
print("\n--- C. structural facts of the MONO book ---")
print(f"  risk-taking sessions (Mon+Tue overnight): {len(on_idx)}/{M['n']} = "
      f"{len(on_idx)/M['n']:.1%} of sessions")
print(f"  per calendar week: mean {per_week.mean():.2f}, median {per_week.median():.0f}")

# sessions needed to bank 4 trading days, per counter
sess = []
for i0 in starts:
    c = 0
    for j in range(i0, min(i0 + 60, M["n"])):
        if ON[j] > 0:
            c += 1
        if c == 4:
            sess.append((j - i0 + 1, int((dates[j] - dates[i0]).days)))
            break
sess = np.array(sess)
print(f"  ON-days-only counter: 4 trading days needs median {np.median(sess[:,0]):.0f} "
      f"sessions = {np.median(sess[:,1]):.0f} CALENDAR days (p90 {np.percentile(sess[:,1],90):.0f})")
sess2 = []
for i0 in starts:
    c = 0
    for j in range(i0, min(i0 + 60, M["n"])):
        if ON[j] > 0 or (M["m_risk"][j] > 0 and M["mR"][j] != 0.0):
            c += 1
        if c == 4:
            sess2.append((j - i0 + 1, int((dates[j] - dates[i0]).days)))
            break
sess2 = np.array(sess2)
print(f"  micro-ORB counter  : 4 trading days needs median {np.median(sess2[:,0]):.0f} "
      f"sessions = {np.median(sess2[:,1]):.0f} CALENDAR days (p90 {np.percentile(sess2[:,1],90):.0f})")
pd.DataFrame(dict(counter=["ON_only", "micro_orb"],
                  med_sessions=[np.median(sess[:, 0]), np.median(sess2[:, 0])],
                  med_cal_days=[np.median(sess[:, 1]), np.median(sess2[:, 1])],
                  p90_cal_days=[np.percentile(sess[:, 1], 90),
                                np.percentile(sess2[:, 1], 90)])
             ).to_csv(L.TAB / "min_trading_days_clock.csv", index=False)
print(f"\nelapsed {time.time() - t0:.1f}s")
