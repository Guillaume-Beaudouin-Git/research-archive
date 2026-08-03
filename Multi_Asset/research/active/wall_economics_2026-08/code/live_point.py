"""Track 3 — the Pace channel AT THE LIVE OPERATING POINT (read-only from state.json).

Live state 2026-08-03, day 13 of an attempt opened 2026-07-21 (account <ACCOUNT_ID>):
    equity 9473.89 | static_floor 9000.00 | daily_floor 8973.89 | target 11002.20
    vm 14 | taper 1.0 | glide 1.0 | governor.pace 1.1429 | scale 16.0
=> room to the STATIC floor is $473.89 = 4.74% of the initial balance, and the binding
   barrier is the STATIC one (daily_floor 8973.89 sits BELOW static_floor 9000).

The averaged cohort sweep cannot answer "what does Pace cost from HERE", because this
state (behind, near the floor, clock running) is exactly where Pace is largest. So we
restart the walk from the live state and vary ONLY the pace rule.

The governor is reproduced from `ftmo_live/lib/invariants.py` (read, never imported-and-
mutated): scale = vm * taper(eq) * glide(eq) * pace(t, eq), pace = clip(1 + k*(frac_t -
max(prog,0)), 0.8, 2.0). Daily returns are block-bootstrapped from the deployed MONO
book at vm=14, so multiplying by taper*glide*pace reproduces the live scale exactly
(14 * 1.0 * 1.0 * 1.1429 = 16.0, the value state.json carries).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
TAB = HERE.parent / "tables"
TAB.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parents[4]))
sys.path.insert(0, str(HERE))

from Portfolio.admission.barrier import BarrierConfig, _run_phase        # noqa: E402
from Portfolio.admission.marginal import stationary_bootstrap_indices    # noqa: E402

INIT = 10_000.0
FLOOR = 0.90            # static floor, fraction of INIT
DAILY = 0.05            # daily stop, fraction of INIT, off balance@00:00
TARGET = 0.10
TAPER_FRAC, GLIDE_FRAC, VM, PACE_K, PACE_MAX = 0.02, 0.5, 14.0, 1.0, 2.0

LIVE_EQ = 9473.89 / INIT
LIVE_DAY = 13
MEAN_BLOCK = 10.0
N_PATHS = 40_000
TD_PER_CAL = 252.0 / 365.0


def governor(eq: float, day: int, wall: int | None, pace_on: bool) -> float:
    """scale / vm, i.e. the multiplier applied to the book's vm=14 daily return."""
    taper = float(np.clip((eq - FLOOR) / TAPER_FRAC, 0.0, 1.0))
    prog = (eq - 1.0) / TARGET
    glide = GLIDE_FRAC if prog > 0.8 else 1.0
    pace = 1.0
    if pace_on and wall:
        frac_t = day / float(wall)
        pace = float(np.clip(1.0 + PACE_K * (frac_t - max(prog, 0.0)), 0.8, PACE_MAX))
    return taper * glide * pace


def walk(path: np.ndarray, eq0: float, day0: int, wall: int | None, pace_on: bool,
         budget_cal: int) -> tuple[str, int, float]:
    """Forward walk from the live state. Returns (outcome, calendar days used, min pace-free room)."""
    eq = eq0
    n = len(path)
    max_td = int(round((budget_cal - day0) * TD_PER_CAL))
    for k in range(max_td):
        if k >= n:
            return "timeout", budget_cal - day0, eq
        day = day0 + int(round(k / TD_PER_CAL))
        m = governor(eq, day, wall, pace_on)
        day_open = eq
        eq = eq * (1.0 + m * float(path[k]))
        if eq <= day_open - DAILY:              # daily stop, -5% of INIT off the day's open
            return "daily", int(round(k / TD_PER_CAL)) + 1, eq
        if eq <= FLOOR:                         # STATIC floor -10% of INIT
            return "floor", int(round(k / TD_PER_CAL)) + 1, eq
        if eq >= 1.0 + TARGET:
            return "pass", int(round(k / TD_PER_CAL)) + 1, eq
    return "timeout", budget_cal - day0, eq


def sweep(r: np.ndarray, variants: dict, seed: int = 11) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    max_td = int(round(400 * TD_PER_CAL)) + 10
    reps = int(np.ceil(max_td / r.size)) + 1
    acc = {k: {"pass": 0, "daily": 0, "floor": 0, "timeout": 0, "days": [], "pace": []}
           for k in variants}
    for _ in range(N_PATHS):
        idx = np.concatenate(
            [stationary_bootstrap_indices(r.size, MEAN_BLOCK, rng) for _ in range(reps)]
        )[:max_td]
        path = r[idx]                             # SAME path for every variant -> paired
        for k, (wall, pace_on, budget) in variants.items():
            o, d, _ = walk(path, LIVE_EQ, LIVE_DAY, wall, pace_on, budget)
            acc[k][o] += 1
            if o == "pass":
                acc[k]["days"].append(d)
    rows = []
    n = float(N_PATHS)
    for k, a in acc.items():
        wall, pace_on, budget = variants[k]
        rows.append(dict(
            variant=k, wall=wall, pace_on=pace_on, budget_cal=budget,
            p_pass=a["pass"] / n, p_floor=a["floor"] / n, p_daily=a["daily"] / n,
            p_timeout=a["timeout"] / n,
            p_death=(a["floor"] + a["daily"]) / n,
            floor_share_of_deaths=a["floor"] / max(a["floor"] + a["daily"], 1),
            median_days=float(np.median(a["days"])) if a["days"] else np.nan,
            pace_now=governor(LIVE_EQ, LIVE_DAY, wall, pace_on)
                     / float(np.clip((LIVE_EQ - FLOOR) / TAPER_FRAC, 0.0, 1.0)),
        ))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    book = pd.read_csv(OUT / "book_mono_daily.csv", index_col=0)["ret"]
    r = book.to_numpy(float)

    # sanity: the reduced-form walker must agree with barrier._run_phase when the
    # governor is switched off and we start at par (the only regime both cover).
    rng = np.random.default_rng(1)
    cfg = BarrierConfig()
    agree = 0
    for _ in range(400):
        idx = np.concatenate([stationary_bootstrap_indices(r.size, MEAN_BLOCK, rng)
                              for _ in range(2)])[:300]
        p = r[idx]
        a, _, _ = walk(p, 1.0, 0, None, False, 400)
        b, _ = _run_phase(p, 0, cfg.target_p1, cfg, 0, 0)
        agree += (a == b)
    print(f"cross-check vs Portfolio/admission/barrier._run_phase: {agree}/400 identical")

    variants = {
        "pace ON, wall 91 (DEPLOYED)":  (91,  True,  91),
        "pace OFF (decoupled)":          (None, False, 91),
        "pace ON, denominator 182":      (182, True,  91),
        "pace ON, denominator 360":      (360, True,  91),
        # same, with the horizon opened up (no self-imposed abandon before day 400)
        "pace ON wall 91 / horizon 400":  (91,  True,  400),
        "pace OFF / horizon 400":        (None, False, 400),
        "pace ON denom 400 / horizon 400": (400, True, 400),
    }
    tab = sweep(r, variants)
    tab.to_csv(TAB / "live_point.csv", index=False)
    print(f"\n=== FORWARD FROM THE LIVE STATE (eq {LIVE_EQ*INIT:.2f}, day {LIVE_DAY}, "
          f"room to static floor ${(LIVE_EQ-FLOOR)*INIT:.2f}) ===")
    print(tab.to_string(float_format=lambda x: f"{x:.4f}", index=False))

    # marginal effect of the pace multiplier alone, deployed horizon
    a = tab.set_index("variant")[["p_pass", "p_floor", "p_daily", "p_death", "median_days"]]
    d = a.loc["pace ON, wall 91 (DEPLOYED)"] - a.loc["pace OFF (decoupled)"]
    print(f"\nPace channel at the live point (ON - OFF), horizon 91:")
    print(f"  d p(pass)          {d.p_pass*100:+.2f} pt")
    print(f"  d p(STATIC floor)  {d.p_floor*100:+.2f} pt")
    print(f"  d p(daily)         {d.p_daily*100:+.2f} pt")
    d2 = a.loc["pace ON wall 91 / horizon 400"] - a.loc["pace OFF / horizon 400"]
    print(f"Pace channel at the live point (ON - OFF), horizon 400 (FTMO's real rule):")
    print(f"  d p(pass)          {d2.p_pass*100:+.2f} pt")
    print(f"  d p(STATIC floor)  {d2.p_floor*100:+.2f} pt")
    print(f"  d p(daily)         {d2.p_daily*100:+.2f} pt")
