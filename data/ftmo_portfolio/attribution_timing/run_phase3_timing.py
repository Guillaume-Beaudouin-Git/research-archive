"""Phase 3 — start-timing study. ONE step-1 cohort sweep, then bucket groupings.
Pre-registered buckets: H1 DOW(5) + H2 FOMC-week(2 full)/CPI-week(2 OOS-only)
+ H3 ORB trailing regime(3) + H4 gold state(3) + H5 month(12, descriptive)
= 27 buckets. Deflation bar for any 'best window': z >= sqrt(2 ln 27) = 2.57.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import attr_engine as AE
E = AE.E

TAB = HERE / "tables"
ROOT = Path("<HOME>/Desktop/Algo_claude")
t0 = time.time()
VAL, FEE = 1453.0, 96.0

M = E.load_market()
WT_df, ON_df = E.build_signals()
WT, ON = E.align_signals(M, WT_df, ON_df)
CFG = dict(E.CFG_V2, fix_deadlock=True)

# ---- step-1 sweep (every trading day 2013-10 -> 2026-02-25) ----
f = TAB / "p3_step1_cohorts.csv"
if f.exists():
    d = pd.read_csv(f, parse_dates=["start"])
else:
    sel = np.where((M["dates"] >= "2013-10-01") & (M["dates"] <= "2026-02-25"))[0]
    rows = []
    for i0 in sel:
        r = E.run_funnel(M, int(i0), WT, ON, CFG, wall=91)
        rows.append(dict(start=M["dates"][int(i0)], i0=int(i0),
                         funded=r["funded"], attempts=r["attempts"], t=r["t"]))
    d = pd.DataFrame(rows)
    d.to_csv(f, index=False)
print(f"step-1 cohorts n={len(d)} pooled p={d.funded.mean()*100:.2f}% "
      f"[{time.time()-t0:.0f}s]", flush=True)

# ---- bucket assignments ----
d["wd"] = d.start.dt.dayofweek
d["month"] = d.start.dt.month
d["iso_week"] = d.start.dt.strftime("%G-%V")

fomc = pd.read_csv(ROOT / "data/personal_book/post_fomc_drift/data_cache/fomc_events.csv")
fomc_weeks = set(pd.to_datetime(fomc["date"]).dt.strftime("%G-%V"))
d["fomc_week"] = d.iso_week.isin(fomc_weeks)

ec = pd.read_csv(ROOT / "data/panels/economic_calendar.csv")
cpi_weeks = set(pd.to_datetime(ec.loc[ec.event.str.upper().str.contains("CPI"),
                                      "date"]).dt.strftime("%G-%V"))
d["cpi_week"] = d.iso_week.isin(cpi_weeks)

# H3: trailing 63 nonzero-ORB-day mean of era-costed R, strictly before start
orb = M["orb_R"]
nz_idx = np.where(orb != 0)[0]
nz_val = orb[nz_idx]
csum = np.concatenate([[0.0], np.cumsum(nz_val)])
def trail63(i0):
    k = np.searchsorted(nz_idx, i0)           # trades strictly before i0
    if k < 63:
        return np.nan
    return (csum[k] - csum[k - 63]) / 63
d["orb_trail"] = [trail63(i) for i in d.i0]
d["orb_regime"] = pd.cut(d.orb_trail, [-np.inf, 0.0, 0.08, np.inf],
                         labels=["unfav", "neutral", "fav"])

# H4: gold WT state at start
g0 = WT[d.i0.to_numpy(), 0]
d["gold_state"] = np.where(g0 == 0, "flat", np.where(g0 > 0, "long", "short"))

# ---- block bootstrap machinery ----
rng = np.random.default_rng(31)
y = d.funded.to_numpy(float)
n = len(y)
B = 65                                          # ~13 weeks of step-1 starts
def boot_bucket(mask_series, n_boot=2000):
    mask = mask_series.to_numpy(bool)
    if mask.sum() == 0:
        return np.nan, (np.nan, np.nan)
    means = []
    for _ in range(n_boot):
        ix = []
        while len(ix) < n:
            s = rng.integers(0, n)
            ix.extend(((s + np.arange(B)) % n).tolist())
        ix = np.array(ix[:n])
        mm = mask[ix]
        if mm.sum() == 0:
            continue
        means.append(y[ix][mm].mean())
    means = np.array(means)
    return means.std(), tuple(np.percentile(means, [2.5, 97.5]))

def neff(series):
    x = series.to_numpy(float)
    if len(x) < 30 or x.std() == 0:
        return len(x)
    ac = [pd.Series(x).autocorr(k) for k in range(1, 14)]
    return len(x) / (1 + 2 * sum(max(a, 0) for a in ac if np.isfinite(a)))

p_all = y.mean()
buckets = []
def add_buckets(hyp, col, subset=None):
    dd = d if subset is None else d[subset]
    for val, grp in dd.groupby(col, observed=True):
        sd_b, ci = boot_bucket(
            (d[col] == val) & (subset if subset is not None else True))
        ev = grp.funded.mean() * VAL - grp.attempts.mean() * FEE
        buckets.append(dict(
            hyp=hyp, bucket=f"{col}={val}", n=len(grp),
            n_eff=round(neff(grp.sort_values('start').funded), 0),
            p=grp.funded.mean(), ci_lo=ci[0], ci_hi=ci[1],
            z=(grp.funded.mean() - p_all) / sd_b if sd_b and sd_b > 0 else np.nan,
            ev=ev, med_t=grp.loc[grp.funded, "t"].median(),
            att=grp.attempts.mean(),
            bust_per_cohort=(grp.attempts - grp.funded.astype(int)).mean()))

add_buckets("H1", "wd")
add_buckets("H2", "fomc_week")
add_buckets("H2", "cpi_week", subset=(d.start >= "2020-01-01"))
add_buckets("H3", "orb_regime")
add_buckets("H4", "gold_state")
add_buckets("H5", "month")

bk = pd.DataFrame(buckets)
bk["p"] = bk.p.round(4)
bk.to_csv(TAB / "p3_buckets.csv", index=False)
print(bk.round(3).to_string(index=False))
nb = len(bk)
bar = np.sqrt(2 * np.log(nb))
zmax = bk.z.abs().max()
best = bk.loc[bk.z.abs().idxmax()]
print(f"\nbuckets tested = {nb}; deflation bar sqrt(2 ln {nb}) = {bar:.2f}")
print(f"max |z| = {zmax:.2f} ({best.hyp} {best.bucket}, p={best.p*100:.1f} "
      f"vs uncond {p_all*100:.1f}) -> "
      f"{'SURVIVES' if zmax >= bar else 'DOES NOT SURVIVE'} deflation")
print(f"done {time.time()-t0:.0f}s")
