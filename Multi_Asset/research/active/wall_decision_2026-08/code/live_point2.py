"""The Pace legs AT THE CURRENT LIVE OPERATING POINT — 2026-08-05.

state (attempt opened 2026-07-21, day 15):
    equity 10,589.83  ->  prog = (1.058983-1)/0.10 = 0.5898
    frac_t = 15/91 = 0.1648
    x = clip(1 + 1.0*(0.1648 - 0.5898), 0.8, 2.0) = clip(0.575) = 0.80   <-- CLIPPED
    scale = vm 14 * taper 1.0 * glide 1.0 * pace 0.80 = 11.2  (vs 16.0 last week)

So the account sits on the **LOW leg, at the clip**: Pace is de-levering it by 20 %.
Last Monday (day 13, equity 9,473.89) it was on the HIGH leg at 1.1429. The averaged
cohort sweep cannot answer "what does each leg do from HERE", which is why this walk
exists — and it is now the FIRST time the low leg has been priced at its own operating
point rather than diluted into an average.

Governor mirrors `ftmo_live/lib/invariants.py` (read, never mutated). Barriers: daily
-5 % of initial off the day's open on intraday EQUITY; STATIC floor -10 % of initial.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "outputs"
TAB = HERE.parent / "tables"
OUT.mkdir(exist_ok=True)
TAB.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE.parents[4]))
sys.path.insert(0, str(HERE))

from Portfolio.admission.marginal import stationary_bootstrap_indices    # noqa: E402
from Portfolio.admission.barrier import BarrierConfig, _run_phase        # noqa: E402

INIT = 10_000.0
FLOOR, DAILY, TARGET = 0.90, 0.05, 0.10
TAPER_FRAC, GLIDE_FRAC, VM, PACE_K = 0.02, 0.5, 14.0, 1.0
PACE_LO, PACE_HI = 0.8, 2.0

LIVE_EQ = 10_589.83 / INIT
LIVE_DAY = 15
MEAN_BLOCK = 10.0
N_PATHS = 40_000
TD_PER_CAL = 252.0 / 365.0


def pace_raw(eq: float, day: int, denom: int) -> float:
    prog = (eq - 1.0) / TARGET
    return float(np.clip(1.0 + PACE_K * (day / float(denom) - max(prog, 0.0)),
                         PACE_LO, PACE_HI))


def governor(eq: float, day: int, denom, mode: str) -> float:
    taper = float(np.clip((eq - FLOOR) / TAPER_FRAC, 0.0, 1.0))
    prog = (eq - 1.0) / TARGET
    glide = GLIDE_FRAC if prog > 0.8 else 1.0
    if mode == "off" or not denom:
        pace = 1.0
    else:
        x = pace_raw(eq, day, denom)
        pace = {"coupled": x, "hi_only": max(x, 1.0), "lo_only": min(x, 1.0)}[mode]
    return taper * glide * pace


def walk(path, eq0, day0, denom, mode, budget_cal):
    eq, n = eq0, len(path)
    max_td = int(round((budget_cal - day0) * TD_PER_CAL))
    for k in range(max_td):
        if k >= n:
            return "timeout", budget_cal - day0
        day = day0 + int(round(k / TD_PER_CAL))
        m = governor(eq, day, denom, mode)
        day_open = eq
        eq = eq * (1.0 + m * float(path[k]))
        if eq <= day_open - DAILY:
            return "daily", int(round(k / TD_PER_CAL)) + 1
        if eq <= FLOOR:
            return "floor", int(round(k / TD_PER_CAL)) + 1
        if eq >= 1.0 + TARGET:
            return "pass", int(round(k / TD_PER_CAL)) + 1
    return "timeout", budget_cal - day0


def sweep(r, variants, seed=11):
    rng = np.random.default_rng(seed)
    max_td = int(round(400 * TD_PER_CAL)) + 10
    reps = int(np.ceil(max_td / r.size)) + 1
    acc = {k: {"pass": 0, "daily": 0, "floor": 0, "timeout": 0, "days": []}
           for k in variants}
    for _ in range(N_PATHS):
        idx = np.concatenate(
            [stationary_bootstrap_indices(r.size, MEAN_BLOCK, rng) for _ in range(reps)]
        )[:max_td]
        path = r[idx]                                  # SAME path for all arms -> paired
        for k, (denom, mode, budget) in variants.items():
            o, d = walk(path, LIVE_EQ, LIVE_DAY, denom, mode, budget)
            acc[k][o] += 1
            if o == "pass":
                acc[k]["days"].append(d)
    rows = []
    for k, a in acc.items():
        denom, mode, budget = variants[k]
        n = float(N_PATHS)
        rows.append(dict(variant=k, denom=denom, mode=mode, budget_cal=budget,
                         p_pass=a["pass"] / n, p_floor=a["floor"] / n,
                         p_daily=a["daily"] / n, p_timeout=a["timeout"] / n,
                         p_death=(a["floor"] + a["daily"]) / n,
                         median_days=float(np.median(a["days"])) if a["days"] else np.nan,
                         pace_now=(1.0 if mode == "off" or not denom else
                                   {"coupled": lambda x: x,
                                    "hi_only": lambda x: max(x, 1.0),
                                    "lo_only": lambda x: min(x, 1.0)}[mode](
                                       pace_raw(LIVE_EQ, LIVE_DAY, denom)))))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    import track2_placebo as T2                      # reuse the audited book builder
    f = OUT / "book_mono_daily.csv"
    if f.exists():
        book = pd.read_csv(f, index_col=0)["ret"]
    else:
        book = T2.build_book()
        book.to_frame().to_csv(f)
    r = book.to_numpy(float)
    print(f"MONO book n={len(r)} active={float((r!=0).mean()):.3f} "
          f"SR={r.mean()*252/(r.std(ddof=1)*np.sqrt(252)):.3f} "
          f"skew={pd.Series(r[r!=0]).skew():.3f}")
    print(f"live: eq {LIVE_EQ*INIT:,.2f}  day {LIVE_DAY}  prog {(LIVE_EQ-1)/TARGET:.4f}  "
          f"frac_t {LIVE_DAY/91:.4f}  x_raw {1+ (LIVE_DAY/91 - max((LIVE_EQ-1)/TARGET,0)):.4f}"
          f" -> pace {pace_raw(LIVE_EQ, LIVE_DAY, 91):.4f}")

    rng = np.random.default_rng(1)
    cfg = BarrierConfig()
    agree = 0
    for _ in range(400):
        idx = np.concatenate([stationary_bootstrap_indices(r.size, MEAN_BLOCK, rng)
                              for _ in range(2)])[:300]
        p = r[idx]
        a, _ = walk(p, 1.0, 0, None, "off", 400)
        b, _ = _run_phase(p, 0, cfg.target_p1, cfg, 0, 0)
        agree += (a == b)
    print(f"cross-check vs Portfolio/admission/barrier._run_phase: {agree}/400 identical")

    variants = {
        "DEPLOYED  pace ON, denom 91":   (91, "coupled", 91),
        "pace OFF":                      (None, "off", 91),
        "HIGH leg only (denom 91)":      (91, "hi_only", 91),
        "LOW leg only (denom 91)":       (91, "lo_only", 91),
        "pace ON, denom 182":            (182, "coupled", 91),
        # horizon opened (policy A): FTMO imposes no deadline
        "A: horizon 182, denom 91 (A only)":   (91, "coupled", 182),
        "A+B: horizon 182, denom 182":         (182, "coupled", 182),
        "A, pace OFF, horizon 182":            (None, "off", 182),
    }
    t = sweep(r, variants)
    t.to_csv(TAB / "live_point2.csv", index=False)
    pd.set_option("display.width", 220)
    print("\n=== FORWARD FROM THE LIVE STATE (2026-08-05) ===")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    NUM = ["p_pass","p_floor","p_daily","p_death","median_days"]
    a = t.set_index("variant")[NUM]
    for lab, hi, lo in (("LOW leg (deployed - hi_only)", "DEPLOYED  pace ON, denom 91",
                         "HIGH leg only (denom 91)"),
                        ("HIGH leg (deployed - lo_only)", "DEPLOYED  pace ON, denom 91",
                         "LOW leg only (denom 91)"),
                        ("LOW leg main (lo_only - off)", "LOW leg only (denom 91)", "pace OFF"),
                        ("HIGH leg main (hi_only - off)", "HIGH leg only (denom 91)", "pace OFF")):
        d = a.loc[hi] - a.loc[lo]
        print(f"{lab:34s} dp(pass) {d.p_pass*100:+.2f} pt | dp(floor) {d.p_floor*100:+.2f} pt"
              f" | dp(daily) {d.p_daily*100:+.2f} pt")
