"""GAP 2 — audit of V, the value of a delivered funded account.

The whole wall decision hinges on V: break-even is $2,912 at wall 91 and $1,995 at
wall 182, and the cited value ($2,529) falls BETWEEN them. So V alone flips the sign.

This script re-derives V from the source (`engine_v22.run_funded`) rather than quoting
`RECOST_v2.2.1.md`, and reports the DISPERSION, not a point.

Everything is imported read-only from the MAIN checkout by absolute path (the caches
are gitignored and do not exist in a worktree).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
V22 = MAIN / "data/ftmo_portfolio/v22"
HERE = Path(__file__).resolve().parent
TAB = HERE.parent / "tables"
TAB.mkdir(exist_ok=True)

sys.path.insert(0, str(V22))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))

import engine as E                      # noqa: E402  cleanroom, tracked library
import config_v22 as C22                # noqa: E402
import engine_v22 as V                  # noqa: E402

E.CACHE = MAIN / "data/ftmo_portfolio/cache"
E.AOUT = MAIN / "data/ftmo_portfolio/outputs"

SPLIT = 0.80          # FTMO trader profit share on the standard (non-Swing-scale) plan
FEE = 107.0           # EUR 99 at ~1.08


def build():
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT, ON = E.build_signals()
    WT, ON = E.align_signals(M, WT, ON)
    # DEPLOYED book is MONO: gold w=0, J1 off.
    WT = np.zeros_like(WT)
    return M, WT, ON


def funded_panel(M, WT, ON, cfg, horizon, wd_every, step=12, windows=None):
    windows = windows or C22.FUNDED_WINDOWS
    rows = []
    for win, lo, hi in windows:
        for i0 in V.starts(M, lo, hi, step):
            r = V.run_funded(M, int(i0), WT, ON, cfg, horizon=horizon, wd_every=wd_every)
            r = dict(r)
            r["win"] = win
            r["start"] = M["dates"][int(i0)]
            rows.append(r)
    d = pd.DataFrame(rows)
    d["extr"] = d["wd"] + d["residual"]
    d["net80"] = SPLIT * d["extr"]
    return d


def describe(d, label):
    g = d["extr"].to_numpy(float)
    n = d["net80"].to_numpy(float)
    rng = np.random.default_rng(7)
    bs = np.array([n[rng.integers(0, n.size, n.size)].mean() for _ in range(4000)])
    return dict(
        label=label, n=len(d),
        gross_mean=g.mean(), gross_median=np.median(g),
        net80_mean=n.mean(), net80_median=np.median(n),
        net80_ci_lo=np.percentile(bs, 2.5), net80_ci_hi=np.percentile(bs, 97.5),
        net80_p10=np.percentile(n, 10), net80_p90=np.percentile(n, 90),
        p_zero=float((g <= 1e-9).mean()),
        bust=float(d["busted"].mean()),
        life_td=float(d["life"].mean()),
        payouts=float(d["payouts"].mean()),
    )


if __name__ == "__main__":
    M, WT, ON = build()
    print(f"market {M['dates'][0].date()} -> {M['dates'][-1].date()}  n={M['n']}")

    CFG = C22.CFG_FUNDED_V24_SWING          # live-faithful: v2.4 breaker + Swing margin
    CFG_LEGACY = C22.CFG_FUNDED             # what RECOST v2.2.1 actually ran

    out = []

    # --- A. reproduce the RECOST number exactly (legacy cfg, ORB ON in funded) ---
    d0 = funded_panel(M, WT, ON, CFG_LEGACY, C22.FUNDED_HORIZON, C22.FUNDED_WD_EVERY)
    for w in ("IS", "OOS"):
        out.append(describe(d0[d0.win == w], f"RECOST-cfg {w} (h504, wd14)"))
    out.append(describe(d0, "RECOST-cfg POOLED (h504, wd14)"))

    # --- B. live-faithful cfg (v2.4 breaker semantics + SWING margin) ---
    d1 = funded_panel(M, WT, ON, CFG, C22.FUNDED_HORIZON, C22.FUNDED_WD_EVERY)
    for w in ("IS", "OOS"):
        out.append(describe(d1[d1.win == w], f"v2.4+Swing {w} (h504, wd14)"))
    out.append(describe(d1, "v2.4+Swing POOLED (h504, wd14)"))

    # --- C. horizon sensitivity: how much of V is the arbitrary 504-day cap? ---
    for h in (126, 252, 504, 756):
        dh = funded_panel(M, WT, ON, CFG, h, C22.FUNDED_WD_EVERY)
        out.append(describe(dh, f"v2.4+Swing POOLED h{h}"))

    # --- D. vm sensitivity (repo studied vm 0.85) ---
    for vm in (0.70, 0.85, 1.0):
        dv = funded_panel(M, WT, ON, dict(CFG, vm=vm), C22.FUNDED_HORIZON,
                          C22.FUNDED_WD_EVERY)
        out.append(describe(dv, f"v2.4+Swing POOLED vm{vm}"))

    t = pd.DataFrame(out)
    t.to_csv(TAB / "v_audit.csv", index=False)
    pd.set_option("display.width", 250)
    print(t.to_string(float_format=lambda x: f"{x:,.2f}", index=False))

    # save the pooled live-faithful panel for the EV/time model
    d1[["win", "start", "extr", "net80", "busted", "life", "payouts"]].to_csv(
        HERE.parent / "outputs" / "funded_panel.csv", index=False)
    print("\nVAL identity check (RECOST): FEE + 0.8 * extr_pooled =",
          f"{C22.FEE + SPLIT * d0['extr'].mean():,.0f}  (RECOST reports 1,381)")
