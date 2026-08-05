"""Provenance of V = $2,529: which book, which window, gross or net of the 80% split?

Runs the funded stage under the FULL 4-sleeve book (what RECOST v2.2.1 ran) and under
the DEPLOYED MONO book (gold w=0, J1 off), side by side, so the $2,529 can be located
and the correct number for the deployed book substituted.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
V22 = MAIN / "data/ftmo_portfolio/v22"
HERE = Path(__file__).resolve().parent
TAB = HERE.parent / "tables"

sys.path.insert(0, str(V22))
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/audit_v2_independent/cleanroom"))

import engine as E                      # noqa: E402
import config_v22 as C22                # noqa: E402
import engine_v22 as V                  # noqa: E402

E.CACHE = MAIN / "data/ftmo_portfolio/cache"
E.AOUT = MAIN / "data/ftmo_portfolio/outputs"
SPLIT = 0.80


def panel(M, WT, ON, cfg, step=12):
    rows = []
    for win, lo, hi in C22.FUNDED_WINDOWS:
        for i0 in V.starts(M, lo, hi, step):
            r = dict(V.run_funded(M, int(i0), WT, ON, cfg,
                                  horizon=C22.FUNDED_HORIZON,
                                  wd_every=C22.FUNDED_WD_EVERY))
            r["win"] = win
            rows.append(r)
    d = pd.DataFrame(rows)
    d["extr"] = d["wd"] + d["residual"]
    return d


def row(d, book, cfgname):
    o = {}
    for w in ("IS", "OOS"):
        s = d[d.win == w]["extr"]
        o[f"{w}_gross"] = s.mean()
        o[f"{w}_net80"] = SPLIT * s.mean()
    p = d["extr"]
    return dict(book=book, cfg=cfgname, **o,
                POOLED_gross=p.mean(), POOLED_net80=SPLIT * p.mean(),
                bust=float(d["busted"].mean()), n=len(d))


if __name__ == "__main__":
    M = V.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT_full, ON = E.build_signals()
    WT_full, ON = E.align_signals(M, WT_full, ON)
    WT_mono = np.zeros_like(WT_full)

    rows = []
    for bookname, WT in (("FULL 4-sleeve (gold+J1 on)", WT_full),
                         ("DEPLOYED MONO (gold w=0, J1 off)", WT_mono)):
        for cfgname, cfg in (("CFG_FUNDED (RECOST v2.2.1)", C22.CFG_FUNDED),
                             ("CFG_FUNDED_V24_SWING (live-faithful)",
                              C22.CFG_FUNDED_V24_SWING)):
            rows.append(row(panel(M, WT, ON, cfg), bookname, cfgname))

    t = pd.DataFrame(rows)
    t.to_csv(TAB / "v_provenance.csv", index=False)
    pd.set_option("display.width", 250)
    print(t.to_string(float_format=lambda x: f"{x:,.0f}", index=False))
    print("\nRECOST_v2.2.1.md reports: funded IS $683 / OOS $2,529, VAL $1,381 "
          "(= FEE + 0.8 x extr_pooled).")
