"""p(campaign) under INDEPENDENCE vs under the DEPENDENCE actually measured.

The campaign model behind "~4.3 challenges per funded" multiplies independent
attempt probabilities. If outcomes group in time, a re-buy launched 2 business days
after a failure lands INSIDE the same stretch of tape that produced the failure, so
the attempts are positively correlated and 1-(1-p)^K overstates the campaign odds.

This measures it directly: sequential re-buys on the REAL tape (retry = resolution
date + 2 business days, the simulator's own rule), versus 1-(1-p)^K with the same
marginal p. The same computation is run on the overlap-matched placebo, which has no
regime: whatever gap survives there is mechanical, not a regime effect.

usage: campaign.py <vm> [K]
"""
from __future__ import annotations

import sys
import time

import numpy as np
import pandas as pd

import cc_lib as C

L = C.L
vm = float(sys.argv[1]) if len(sys.argv) > 1 else 10.0
K = int(sys.argv[2]) if len(sys.argv) > 2 else 6
NPL = int(sys.argv[3]) if len(sys.argv) > 3 else 25

M, WT, ON, starts, sd = C.stack()
dates = M["dates"]
didx = pd.DatetimeIndex(dates)
cfg = dict(L.CFG_LIVE, target=L.E.TARGET2, max_cal=L.LONG_CAP,
           vm=vm * L.CFG_LIVE["p2_mult"])


def next_start(last_i: int) -> int | None:
    """First trading day at or after resolution + 2 business days."""
    d = didx[last_i] + pd.tseries.offsets.BDay(2)
    j = int(np.searchsorted(didx.values, np.datetime64(d), side="left"))
    return j if j < len(didx) else None


def campaign(i0: int):
    """Returns (funded?, n_attempts_used, total_calendar_days, per-attempt flags)."""
    i, flags, t0 = i0, [], didx[i0]
    for a in range(K):
        r = L.V.run_phase(M, i, WT, ON, cfg)
        ok = r["out"] == "pass"
        flags.append(ok)
        if ok:
            return True, a + 1, int((didx[r["last"]] - t0).days), flags
        j = next_start(r["last"])
        if j is None or j >= M["n"] - 5:
            return None, a + 1, int((didx[r["last"]] - t0).days), flags   # censored
        i = j
    return False, K, int((didx[i] - t0).days), flags


def run_all(label):
    rows, seq_flags = [], []
    for i0 in starts:
        f, a, t, fl = campaign(i0)
        rows.append((i0, str(didx[i0].date()), f, a, t))
        seq_flags.append(fl)
    d = pd.DataFrame(rows, columns=["i0", "date", "funded", "attempts", "cal_days"])
    d["label"] = label
    return d, seq_flags


def summarize(d, seq_flags, label):
    ok = d.funded.notna()
    n = int(ok.sum())
    # marginal single-attempt p on the SAME cohort set (attempt 1 only)
    p1 = float(np.mean([fl[0] for fl in seq_flags]))
    # conditional: p(attempt j passes | attempt j-1 failed)
    cond = [fl[j] for fl in seq_flags for j in range(1, len(fl))]
    p_cond = float(np.mean(cond)) if cond else np.nan
    out = dict(label=label, n=n, p1=p1, p_cond_after_fail=p_cond,
               n_cond=len(cond),
               p_camp_measured=float(d.loc[ok, "funded"].astype(bool).mean()),
               p_camp_indep=float(1 - (1 - p1) ** K),
               att_measured=float(d.loc[ok, "attempts"].mean()),
               att_indep=float(sum((1 - p1) ** j for j in range(K))),
               med_days=float(d.loc[ok & d.funded.astype(bool).fillna(False),
                                    "cal_days"].median()))
    out["overstatement_pt"] = 100 * (out["p_camp_indep"] - out["p_camp_measured"])
    return out


t0 = time.time()
d_real, f_real = run_all("real")
s = [summarize(d_real, f_real, "real")]
d_real.to_csv(C.TAB / f"campaign_paths_vm{vm:g}.csv", index=False)
print(f"real done {time.time()-t0:.0f}s  {s[0]}", flush=True)

for k in range(NPL):
    rng = np.random.default_rng(910_000 + k)
    L.set_signs(L.block_signs(M["n"], C.BLOCK_SIGNS, rng))
    dd, ff = run_all(f"placebo{k}")
    L.set_signs(None)
    s.append(summarize(dd, ff, "placebo"))
    if (k + 1) % 5 == 0:
        print(f"placebo {k+1}/{NPL} {time.time()-t0:.0f}s", flush=True)

S = pd.DataFrame(s)
S["K"] = K
S["vm"] = vm
S.to_csv(C.TAB / f"campaign_vm{vm:g}.csv", index=False)
print("\nREAL:")
print(S[S.label == "real"].round(4).to_string(index=False))
print("\nPLACEBO (mean over reps):")
print(S[S.label == "placebo"].drop(columns=["label"]).mean().round(4).to_string())
