"""HARNESS DEFECT CHECK — the inherited `CFG_LIVE` drops the min-trading-days backstop.

FTMO requires >= 4 trading days (`PropFirms/ftmo/rules.md:27`). The cleanroom engine
enforces it (`MIN_OPEN_DAYS = 4`) and FLATTENS + LATCHES `flat_today` the moment equity
touches the target (`engine.py:322-325`). An account that reaches +10 % before it has
opened 4 trading days is therefore frozen flat: it can never open another trade, so the
counter never advances, and the attempt is recorded as a **timeout**.

The deployed spec closes exactly this hole with the MICRO-ORB day counter
(`config_v22.CFG_CHALLENGE: micro_orb=True, fix_deadlock=True`; CLAUDE.md records the
micro-ORB counter's failure rate as 0.00 %). The cleanroom's `fix_deadlock` is its
stand-in (a $1 token trade to tick the counter).

`wall_economics_2026-08/code/wall_lib.py:38-43` sets neither flag. This script measures
what that costs and cross-validates the fix against the INDEPENDENT v2.2 engine, which
implements the real micro-ORB.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

MAIN = Path("<HOME>/Desktop/Algo_claude")
sys.path.insert(0, str(MAIN / "data/ftmo_portfolio/v22"))

import pace_lib as P                     # noqa: E402  (patches the cleanroom engine)
import config_v22 as C22                 # noqa: E402
import engine_v22 as V22                 # noqa: E402

E = P.E
TAB = Path(__file__).resolve().parent.parent / "tables"


def cleanroom_phase(starts, cfg, wall):
    P.E._target_for_segment = P._ORIG      # pristine: no pace patch
    rows = []
    for i0 in starts:
        r = E.run_phase(P._M, i0, P._WT, P._ON,
                        dict(cfg, target=E.TARGET1, max_cal=wall))
        rows.append(dict(out=r["out"], end=r["end"], used=r.get("used", np.nan)))
    return pd.DataFrame(rows)


def v22_phase(M22, WT, ON, starts, cfg, wall):
    rows = []
    for i0 in starts:
        r = V22.run_phase(M22, i0, WT, ON, dict(cfg, target=0.10, max_cal=wall))
        rows.append(dict(out=r["out"], end=r["end"], used=r.get("used", np.nan)))
    return pd.DataFrame(rows)


def summarise(d, label):
    to = d[d.out == "timeout"]
    return dict(
        arm=label, n=len(d),
        p_pass=(d.out == "pass").mean(),
        p_timeout=(d.out == "timeout").mean(),
        p_floor=(d.out == "bust_floor").mean(),
        p_daily=(d.out == "bust_daily").mean(),
        p_abandon=(d.out == "abandon").mean(),
        timeouts_at_or_above_target=float((to.end >= 11_000).mean()) if len(to) else np.nan,
        median_timeout_equity=float(to.end.median()) if len(to) else np.nan,
    )


if __name__ == "__main__":
    M, WT, ON = P.init()
    starts = P.cohort_starts(M, 275, 7)
    print(f"cohorts {len(starts)}   {M['dates'][0].date()} -> {M['dates'][-1].date()}")

    rows = []
    for wall in (91, 182):
        rows.append(summarise(cleanroom_phase(starts, P.CFG_LIVE, wall),
                              f"cleanroom CFG_LIVE (first pass)  wall {wall}"))
        rows.append(summarise(cleanroom_phase(starts, dict(P.CFG_LIVE, fix_deadlock=True),
                                              wall),
                              f"cleanroom + fix_deadlock          wall {wall}"))

    # --- independent cross-check: the v2.2 engine with the REAL micro-ORB counter ---
    M22 = V22.load_stack(orb_rt_bps=C22.ORB_RT_BPS)
    WT22, ON22 = E.build_signals()
    WT22, ON22 = E.align_signals(M22, WT22, ON22)
    WT22 = np.zeros_like(WT22)                 # MONO
    ON22 = np.zeros(len(ON22))
    d22 = pd.DatetimeIndex(M22["dates"])
    ON22[np.isin(d22.dayofweek, [0, 1])] = 1.0
    s22 = [i for i in starts if i < M22["n"] - 275]
    CFG22 = dict(P.CFG_LIVE, micro_orb=True, fix_deadlock=True)
    CFG22_NO = dict(P.CFG_LIVE, micro_orb=False, fix_deadlock=False)
    for wall in (91, 182):
        rows.append(summarise(v22_phase(M22, WT22, ON22, s22, CFG22_NO, wall),
                              f"v2.2 engine, micro-ORB OFF        wall {wall}"))
        rows.append(summarise(v22_phase(M22, WT22, ON22, s22, CFG22, wall),
                              f"v2.2 engine, micro-ORB ON (spec)  wall {wall}"))

    t = pd.DataFrame(rows)
    t.to_csv(TAB / "deadlock_defect.csv", index=False)
    pd.set_option("display.width", 220)
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
