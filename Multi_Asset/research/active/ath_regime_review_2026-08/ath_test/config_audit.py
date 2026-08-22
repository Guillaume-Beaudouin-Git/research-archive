"""STEP 0 — audit the config literals of ``regime_overlay_ftmo_2026-07`` before any
p(pass) number is quoted downstream.

Documented suspicion: ``CFG_MONO`` / ``CFG_LIVE`` omit the engine's min-trading-days
backstop, and the same omission elsewhere counted WINNERS as deaths.

Mechanism: ``MIN_OPEN_DAYS = 4`` is a module constant and is always enforced, but the
escape hatch is the ``fix_deadlock`` cfg key (engine.py:363-368). Without it an account
that reaches its target with fewer than 4 open days must keep posting FULL-SIZE risk until
the counter fills, and can die above target.

Nothing outside this folder is written; the engine and the 2026-07 folder are read-only.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("<HOME>/Desktop/Algo_claude")
OVERLAY = REPO / "Multi_Asset/research/active/regime_overlay_ftmo_2026-07"
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"

sys.path.insert(0, str(OVERLAY))
import build_book as B  # noqa: E402  (read-only import of the audited reconstruction)

E = B.E

# The literal used by cohort_funnel.py of the 2026-07 study, reproduced verbatim so the
# diff below is against the real object and not a paraphrase.
CFG_LIVE_2026_07 = dict(
    vm=14.0, p2_mult=1.2, on_w=0.6, orb_risk=0.0,
    breaker=0.30, taper=0.02, glide=0.5, pace=1, pace_k=1.0,
    ab_buf=0.02, ab_days=5, margin_cap=0.60, quantize=True,
    mrate=E.MRATE_SWING, brk_mode="daily", brk_needs_pos=True,
)

DELIBERATE = {
    "orb_risk": "MONO book: ORB is challenge-OFF in production (deliberate)",
    "mrate": "live Swing margin rates, MORE conservative than engine default (deliberate)",
    "brk_mode": "EA v2.4 deployed 2026-07-20 (deliberate)",
    "brk_needs_pos": "EA v2.4 conditions the breaker on OurPositionsExist() (deliberate)",
    "p2_mult": "phase-2 vm multiplier, present in CFG_V2 (n/a)",
    "pace": "pace multiplier (n/a)",
    "pace_k": "pace multiplier (n/a)",
    "quantize": "0.01-lot quantization (n/a)",
    "margin_cap": "60% margin cap (n/a)",
}


def diff_configs() -> pd.DataFrame:
    keys = sorted(set(E.CFG_V2) | set(CFG_LIVE_2026_07) | set(B.CFG_MONO))
    rows = []
    for k in keys:
        v2 = E.CFG_V2.get(k, "<absent>")
        lv = CFG_LIVE_2026_07.get(k, "<absent>")
        mn = B.CFG_MONO.get(k, "<absent>")
        same = str(v2) == str(lv) == str(mn)
        rows.append(dict(key=k, engine_CFG_V2=str(v2), study_CFG_LIVE=str(lv),
                         study_CFG_MONO=str(mn), identical=same,
                         note=DELIBERATE.get(k, "")))
    # the backstop is a cfg KEY absent from all three, plus a module constant
    rows.append(dict(key="fix_deadlock", engine_CFG_V2="<absent>",
                     study_CFG_LIVE="<absent>", study_CFG_MONO="<absent>",
                     identical=True,
                     note="MIN-TRADING-DAYS BACKSTOP — absent everywhere; engine.py:363"))
    rows.append(dict(key="MIN_OPEN_DAYS (module const)", engine_CFG_V2=str(E.MIN_OPEN_DAYS),
                     study_CFG_LIVE="inherited", study_CFG_MONO="inherited",
                     identical=True, note="always enforced, not configurable"))
    return pd.DataFrame(rows)


def where_it_bites(M, WT, ON) -> dict:
    """`fix_deadlock` is inert in the return-stream reconstruction, live in the funnel."""
    a = B.run_book(M, WT, ON, B.CFG_MONO)["ret"].to_numpy()
    b = B.run_book(M, WT, ON, dict(B.CFG_MONO, fix_deadlock=True))["ret"].to_numpy()
    return dict(max_abs_diff_returns=float(np.abs(a - b).max()),
                identical=bool(np.allclose(a, b, atol=0, rtol=0)))


def p2_phase_scan(M, WT, ON, cfg: dict, target: float, wall: int = 91,
                  step: int = 7) -> dict:
    """Run PHASE-2-geometry single phases (+5%) from every cohort start.

    Returns outcome mix plus the signature of the backstop bug: deaths that occurred
    while the account was AT OR ABOVE target.
    """
    starts = E.cohort_starts(M, M["dates"][0], M["dates"][-1], step=step)
    starts = [i for i in starts if i < M["n"] - 120]
    goal = E.INIT * (1.0 + target)
    outs, used, above = [], [], []
    for i0 in starts:
        r = E.run_phase(M, i0, WT, ON, dict(cfg, target=target, max_cal=wall))
        outs.append(r["out"])
        used.append(r["used"])
        above.append(bool(r["out"] != "pass" and r["end"] >= goal))
    s = pd.Series(outs)
    n = len(outs)
    dead = s != "pass"
    return dict(
        n_cohorts=n,
        p_pass=float((s == "pass").mean()),
        p_bust_daily=float((s == "bust_daily").mean()),
        p_bust_floor=float((s == "bust_floor").mean()),
        p_timeout=float((s == "timeout").mean()),
        p_abandon=float((s == "abandon").mean()),
        median_days=float(np.median([u for u, o in zip(used, outs) if o == "pass"]))
        if (s == "pass").any() else float("nan"),
        n_dead=int(dead.sum()),
        n_dead_at_or_above_target=int(np.sum(above)),
        share_dead_at_or_above_target=float(np.sum(above) / max(int(dead.sum()), 1)),
    )


def main() -> None:
    OUT.mkdir(exist_ok=True)
    d = diff_configs()
    d.to_csv(OUT / "config_diff.csv", index=False)
    print("=== STEP 0.1  CONFIG DIFF (engine CFG_V2 vs the 2026-07 study literals) ===")
    print(d.to_string(index=False))

    M = B.build_market()
    dates = pd.DatetimeIndex(M["dates"])
    WT, ON = B.mono_signals(dates)
    print(f"\nmarket: {dates.min().date()} -> {dates.max().date()}  n={M['n']}")

    bite = where_it_bites(M, WT, ON)
    print("\n=== STEP 0.2  DOES THE OMISSION BITE THE RETURN-STREAM RECONSTRUCTION? ===")
    print(json.dumps(bite, indent=2))

    print("\n=== STEP 0.3  IMPACT ON PHASE-2 GEOMETRY (+5%), MEASURED ===")
    rows = {}
    for tag, cfg in (("P2_uncorrected", CFG_LIVE_2026_07),
                     ("P2_fix_deadlock", dict(CFG_LIVE_2026_07, fix_deadlock=True))):
        rows[tag] = p2_phase_scan(M, WT, ON, cfg, target=E.TARGET2)
    # phase-1 geometry for contrast (the target the 2026-07 study actually headlined)
    for tag, cfg in (("P1_uncorrected", CFG_LIVE_2026_07),
                     ("P1_fix_deadlock", dict(CFG_LIVE_2026_07, fix_deadlock=True))):
        rows[tag] = p2_phase_scan(M, WT, ON, cfg, target=E.TARGET1)
    tab = pd.DataFrame(rows).T
    tab.to_csv(OUT / "config_impact.csv")
    print(tab.to_string(float_format=lambda x: f"{x:.4f}"))

    (OUT / "config_audit.json").write_text(json.dumps(
        dict(bite=bite, impact={k: v for k, v in rows.items()}), indent=2))


if __name__ == "__main__":
    main()
