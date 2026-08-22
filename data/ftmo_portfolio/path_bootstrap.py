"""CB-A — Path-level stationary block bootstrap (weeks) -> distribution of p.

Resamples WHOLE WEEKS (preserves weekday structure: ON flags, 3x swap days,
weekend gaps) in geometric blocks (mean 13 weeks = regime-scale), rebuilds a
synthetic Days view (no data copy; day objects travel with their signals),
runs the challenge funnel on each synthetic history -> one p per history.
Caveat (documented): signals inside WT/orb_R keep their ORIGINAL look-back
context; block joins break long-memory coherence at seams (standard limitation
of outcome-level path bootstrap).
Usage: python3 path_bootstrap.py <n_paths> <seed>
Appends results to outputs/pathboot_p.csv
"""
import sys
import numpy as np
import pandas as pd
import config as C
import simulator as S
import run_phase3 as R
import audit_stack as A

CFG = dict(R.BASE, taper_buf=0.02, abandon_buf=0.02, abandon_days=5,
           max_cal_days=91, p2_mult=1.2, vol_mult=14.0, on_w=0.6, orb_risk=0.0025)
PATH_WEEKS = 120          # ~2.3y per synthetic history
MEAN_BLOCK = 13           # weeks


def build_weeks(D):
    iso = pd.DatetimeIndex(D.dates).isocalendar()
    keys = list(zip(iso.year, iso.week))
    weeks, cur, ck = [], [], keys[0]
    for i, k in enumerate(keys):
        if k != ck:
            weeks.append(cur); cur = []; ck = k
        cur.append(i)
    weeks.append(cur)
    return [w for w in weeks if len(w) >= 3]


class SynthDays:
    def __init__(self, D, day_idx):
        self.segs = [D.segs[i] for i in day_idx]
        self.swapL = D.swapL[day_idx]
        self.swapS = D.swapS[day_idx]
        self.mult = D.mult[day_idx]
        self.rt = D.rt
        self.orb_R = D.orb_R[day_idx]
        self.n = len(day_idx)
        # synthetic calendar: consecutive weeks, weekday preserved per day
        base = pd.Timestamp("2030-01-07")          # a Monday
        dates, w = [], -1
        last_wd = 9
        for j, i in enumerate(day_idx):
            wd = pd.Timestamp(D.dates[i]).dayofweek
            if wd <= last_wd - 1 and j > 0 and wd < last_wd:
                pass
            if wd < last_wd:
                w += 1
            last_wd = wd
            dates.append(base + pd.Timedelta(weeks=w, days=wd))
        self.dates = dates


def synth_path(D, weeks, rng):
    out = []
    while len(out) < PATH_WEEKS:
        s = rng.integers(0, len(weeks))
        L = 1 + rng.geometric(1.0 / MEAN_BLOCK)
        for k in range(s, min(s + L, len(weeks))):
            out.append(weeks[k])
            if len(out) >= PATH_WEEKS:
                break
    day_idx = [i for w in out for i in w]
    return day_idx


def main(n_paths, seed):
    D = A.load_audited()
    WT0, ON0 = R.align(D)
    weeks = build_weeks(D)
    rng = np.random.default_rng(seed)
    rows = []
    for p in range(n_paths):
        idx = synth_path(D, weeks, rng)
        SD = SynthDays(D, idx)
        WT = WT0[idx]; ON = ON0[idx]
        starts = np.arange(5, SD.n - 70, 15)
        res = [S.run_funnel(SD, int(i0), WT, ON, CFG, wall_days=91, retries=True)
               for i0 in starts]
        df = pd.DataFrame(res)
        rows.append(dict(seed=seed, path=p, p=df.funded.mean(), n=len(df)))
        print(f"path {p}: p={df.funded.mean():.3f}", flush=True)
    f = C.OUT / "pathboot_p.csv"
    pd.DataFrame(rows).to_csv(f, mode="a", header=not f.exists(), index=False)


if __name__ == "__main__":
    main(int(sys.argv[1]), int(sys.argv[2]))
