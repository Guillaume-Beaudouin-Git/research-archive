"""Audit of the contradiction: `ftmo_checkup_2026-07` says "Q1 10.7 % vs Q2 34.6 %,
launch in April or October"; `ftmo_attribution_timing_2026-06` says "timing NULL,
start anytime". Both cannot hold.

The two studies are re-derived from the SAME artefact family
(`data/ftmo_portfolio/attribution_timing/tables/attempt_log.csv`, the June v2 4-sleeve
book, cohorts every 7 trading days), and the 1-try seasonality is re-tested against a
CIRCULAR-SHIFT null: the outcome series is rotated against fixed calendar labels, so
the null preserves the cohort autocorrelation EXACTLY and destroys only the calendar
alignment. That is the null the checkup never ran (its own caveat: "block-bootstrap
CIs still TODO").
"""
import numpy as np
import pandas as pd

import cc_lib as C

T = C.Path("<HOME>/Desktop/Algo_claude/data/ftmo_portfolio/"
           "attribution_timing/tables")
a = pd.read_csv(T / "attempt_log.csv", parse_dates=["start_date"])

first = a[a.attempt == 1]
p1 = first[first.phase == 1].set_index("cohort")
p2 = first[first.phase == 2].set_index("cohort")
co = pd.DataFrame({"start": p1.start_date, "p1_pass": p1.out.eq("pass")})
co["p2_pass"] = p2.out.eq("pass").reindex(co.index).fillna(False)
co["funded_1try"] = co.p1_pass & co.p2_pass
co = co.sort_values("start").reset_index(drop=True)
sd = pd.DatetimeIndex(co.start)
y = co.funded_1try.to_numpy(float)
n = len(y)
print(f"cohorts {n}  1-try p(funded) {y.mean():.3f}  "
      f"{sd[0].date()}..{sd[-1].date()}")


def shift_test(y, keys, name):
    ks = np.unique(keys)
    K = np.array([(keys == k).astype(float) for k in ks])
    cnt = K.sum(axis=1)
    means = np.array([(K @ np.roll(y, s)) / cnt for s in range(len(y))])
    dev = means - y.mean()
    stat = np.abs(dev).max(axis=1)
    rng = means.max(axis=1) - means.min(axis=1)
    rows = []
    for j, k in enumerate(ks):
        rows.append(dict(scheme=name, cell=int(k), n=int((keys == k).sum()),
                         p=means[0, j], dev=dev[0, j],
                         p_shift=float((np.abs(dev[:, j]) >= abs(dev[0, j])).mean())))
    d = pd.DataFrame(rows)
    d["p_sidak"] = 1 - (1 - d.p_shift.clip(1e-9, 1)) ** len(ks)
    d["p_omni_maxdev"] = float((stat >= stat[0]).mean())
    d["p_omni_range"] = float((rng >= rng[0]).mean())
    return d


res = []
for nm, keys in (("quarter", sd.quarter.to_numpy()), ("month", sd.month.to_numpy())):
    d = shift_test(y, keys, nm)
    res.append(d)
    print(f"\n--- {nm} (1-try funded, circular-shift null, {n} cohorts) ---")
    print(d.round(4).to_string(index=False))
out = pd.concat(res, ignore_index=True)
out.to_csv(C.TAB / "audit_checkup_seasonality.csv", index=False)

# n_eff of this cohort set: block bootstrap over cohorts
rng = np.random.default_rng(5)
for blk in (1, 8, 12):
    nb = int(np.ceil(n / blk))
    idx = ((np.arange(blk)[None, :] + rng.integers(0, n, size=(6000, nb))[:, :, None])
           % n).reshape(6000, -1)[:, :n]
    v = y[idx].mean(axis=1).var(ddof=1)
    print(f"block {blk:>2}  n_eff = {y.mean()*(1-y.mean())/v:6.1f}")
