"""
optim_engine.py — Engine extension for propfirm optimisation.

Adds, on top of audit/ftmo_engine.py:
  - Kill-switch parameters (halt day after -X% intraday, halt attempt after -Y% total)
  - Container variants:
      'ftmo_2phase'    : target +10% then +5%, daily -5%, total -10% static
      '1phase_static'  : target +10%, daily -5%, total -10% static
      '1phase_trail6'  : target +10%, daily -5%, total -6% trailing EOD
      '1phase_daily5'  : target +10%, daily -5%, no static total, full trail to bal
  - End-to-end p(funded) on real-path with the same historical path threading P1->P2.

Reuses _block_pnl_array from ftmo_engine.py.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Sequence
from ftmo_engine import _block_pnl_array, AM_COLS, PM_COLS


def _run_single_attempt(
    M: pd.DataFrame,
    start_idx: int,
    am: np.ndarray,
    pm: np.ndarray,
    target_pct: float,
    daily_loss_pct: float,
    total_loss_floor: float | None,
    trailing_loss_pct: float | None,
    block_cap_pct: float,
    max_days: int | None,
    min_trading_days: int = 4,
    killswitch_daily_pct: float | None = None,
    killswitch_total_pct: float | None = None,
) -> tuple[str, float, int, int]:
    """
    Run one challenge attempt starting at start_idx (REAL PATH).

    If max_days is None: UNCAPPED — run until pass/bust or end of data
    (returns 'CENSORED' if end of data hit before resolution).

    Container parameters:
      target_pct        : profit target (e.g. 0.10 for +10%)
      daily_loss_pct    : intra-day floating max loss vs day_start (e.g. 0.05)
      total_loss_floor  : static equity floor (e.g. 0.90 for -10% static), None => no static floor
      trailing_loss_pct : EOD trailing distance from peak balance (e.g. 0.06 for -6% trailing)
                          None => no trailing
    Kill-switch (per-attempt risk control, NOT a propfirm rule):
      killswitch_daily_pct  : halt remaining day after intraday loss reaches X
                              (so the strategy doesn't keep adding to losers)
      killswitch_total_pct  : halt attempt entirely after equity drops X from start

    Returns:
      ('PASS'|'BUST_TOTAL'|'BUST_DAILY'|'BUST_TRAIL'|'KILLED'|'TIMEOUT'|'CENSORED',
       final_eq, days_to_resolve, trading_days)
    """
    n = len(M)
    eq = 1.0
    peak_eq = 1.0
    tdays = 0
    am_vals = M[AM_COLS].values
    pm_vals = M[PM_COLS].values

    # Effective max_days for the loop
    loop_max = max_days if max_days is not None else (n - start_idx)
    for d in range(loop_max):
        j = start_idx + d
        if j >= n:
            # End-of-data reached
            if max_days is None:
                return "CENSORED", eq, d, tdays
            return "TIMEOUT", eq, d, tdays
        day_start = eq

        # Trailing floor recomputed EOD on peak
        trail_floor = (1.0 - trailing_loss_pct) * peak_eq if trailing_loss_pct else None
        # Use the most restrictive floor active for this challenge
        floor_candidates = [v for v in (total_loss_floor, trail_floor) if v is not None]
        effective_floor = max(floor_candidates) if floor_candidates else None

        # AM block
        eq_am = eq * (1 + am[j])
        if effective_floor is not None and eq_am < effective_floor:
            if trail_floor is not None and (total_loss_floor is None or trail_floor > total_loss_floor):
                return "BUST_TRAIL", eq_am, d + 1, tdays
            return "BUST_TOTAL", eq_am, d + 1, tdays
        if eq_am < day_start * (1 - daily_loss_pct):
            return "BUST_DAILY", eq_am, d + 1, tdays
        # Kill-switch: per-attempt risk halt
        if killswitch_daily_pct is not None and eq_am < day_start * (1 - killswitch_daily_pct):
            eq = eq_am  # halt remaining day; carry equity forward
            traded = (~np.isnan(am_vals[j])).any() or (~np.isnan(pm_vals[j])).any()
            if traded:
                tdays += 1
            peak_eq = max(peak_eq, eq)
            if killswitch_total_pct is not None and eq < (1 - killswitch_total_pct):
                return "KILLED", eq, d + 1, tdays
            continue  # skip PM
        eq = eq_am

        # PM block (only if not killed)
        eq_pm = eq * (1 + pm[j])
        if effective_floor is not None and eq_pm < effective_floor:
            if trail_floor is not None and (total_loss_floor is None or trail_floor > total_loss_floor):
                return "BUST_TRAIL", eq_pm, d + 1, tdays
            return "BUST_TOTAL", eq_pm, d + 1, tdays
        if eq_pm < day_start * (1 - daily_loss_pct):
            return "BUST_DAILY", eq_pm, d + 1, tdays
        eq = eq_pm

        traded = (~np.isnan(am_vals[j])).any() or (~np.isnan(pm_vals[j])).any()
        if traded:
            tdays += 1
        peak_eq = max(peak_eq, eq)

        # Kill-switch total
        if killswitch_total_pct is not None and eq < (1 - killswitch_total_pct):
            return "KILLED", eq, d + 1, tdays

        if eq >= 1 + target_pct and tdays >= min_trading_days:
            return "PASS", eq, d + 1, tdays
    # Exhausted loop: capped -> TIMEOUT; uncapped -> CENSORED
    if max_days is None:
        return "CENSORED", eq, loop_max, tdays
    return "TIMEOUT", eq, max_days, tdays


CONTAINERS = {
    "ftmo_2phase":   {"daily_loss_pct": 0.05, "total_loss_floor": 0.90, "trailing_loss_pct": None,
                       "p1_target": 0.10, "p2_target": 0.05, "max_days_p1": 40, "max_days_p2": 40},
    # FTMO 2-step uncapped: Challenge + Verification, both with no time limit (current FTMO 2026 product).
    # max_days_p1=None and max_days_p2=None => loop until pass/bust or end of data (CENSORED).
    "ftmo_2step_uncapped": {"daily_loss_pct": 0.05, "total_loss_floor": 0.90, "trailing_loss_pct": None,
                              "p1_target": 0.10, "p2_target": 0.05,
                              "max_days_p1": None, "max_days_p2": None},
    "1phase_static": {"daily_loss_pct": 0.05, "total_loss_floor": 0.90, "trailing_loss_pct": None,
                       "p1_target": 0.10, "p2_target": None, "max_days_p1": 40, "max_days_p2": 0},
    "1phase_trail6": {"daily_loss_pct": 0.05, "total_loss_floor": None, "trailing_loss_pct": 0.06,
                       "p1_target": 0.10, "p2_target": None, "max_days_p1": 40, "max_days_p2": 0},
    "1phase_daily5": {"daily_loss_pct": 0.05, "total_loss_floor": None, "trailing_loss_pct": None,
                       "p1_target": 0.10, "p2_target": None, "max_days_p1": 40, "max_days_p2": 0},
}


def simulate_real_path_container(
    M: pd.DataFrame,
    container: str,
    block_cap_pct: float = 0.015,
    killswitch_daily_pct: float | None = None,
    killswitch_total_pct: float | None = None,
    start_indices: Sequence[int] | None = None,
) -> dict:
    """
    Real-path simulation over a container's full rule set.
    For 2-phase: runs P1 at each start; if PASS, runs P2 on subsequent contiguous days.
    For 1-phase: runs P1 only.
    Returns p_funded, p_phase1, p_phase2_given_p1 (if applicable), bust breakdowns, TTP.
    """
    cfg = CONTAINERS[container]
    am, pm, _, _ = _block_pnl_array(M, block_cap_pct)
    n = len(M)
    max_p1 = cfg["max_days_p1"]
    max_p2 = cfg["max_days_p2"]
    uncapped = (max_p1 is None)
    if start_indices is None:
        if uncapped:
            # For uncapped, every position is a potential start; censure is detected per-attempt
            starts = np.arange(0, n)
        else:
            last_valid = n - max_p1 - max_p2
            starts = np.arange(0, max(1, last_valid + 1))
    else:
        starts = np.asarray(start_indices)

    p1_outcomes = []
    p2_outcomes = []
    p1_ttps = []
    p2_ttps = []  # aligned 1:1 with p2_outcomes; -1 sentinel for not-run
    p1_eqs = []
    for s in starts:
        out, eq, ttp, td = _run_single_attempt(
            M, int(s), am, pm,
            target_pct=cfg["p1_target"],
            daily_loss_pct=cfg["daily_loss_pct"],
            total_loss_floor=cfg["total_loss_floor"],
            trailing_loss_pct=cfg["trailing_loss_pct"],
            block_cap_pct=block_cap_pct,
            max_days=max_p1,
            killswitch_daily_pct=killswitch_daily_pct,
            killswitch_total_pct=killswitch_total_pct,
        )
        p1_outcomes.append(out)
        p1_ttps.append(ttp)
        p1_eqs.append(eq)
        if out == "PASS" and cfg["p2_target"] is not None:
            p2_start = int(s) + ttp
            out2, eq2, ttp2, _ = _run_single_attempt(
                M, p2_start, am, pm,
                target_pct=cfg["p2_target"],
                daily_loss_pct=cfg["daily_loss_pct"],
                total_loss_floor=cfg["total_loss_floor"],
                trailing_loss_pct=cfg["trailing_loss_pct"],
                block_cap_pct=block_cap_pct,
                max_days=max_p2,
                killswitch_daily_pct=killswitch_daily_pct,
                killswitch_total_pct=killswitch_total_pct,
            )
            p2_outcomes.append(out2)
            p2_ttps.append(ttp2)
        elif out == "PASS":
            p2_outcomes.append("N/A_1PHASE")
            p2_ttps.append(-1)
        else:
            p2_outcomes.append("NOT_REACHED")
            p2_ttps.append(-1)
    p1_arr = np.array(p1_outcomes)
    p2_arr = np.array(p2_outcomes)

    # Censure handling: a path is CENSORED if (P1 hit end-of-data) OR (P2 hit end-of-data after PASSing P1).
    # Excluded from p_funded denominator.
    censored_p1 = (p1_arr == "CENSORED")
    censored_p2 = (p2_arr == "CENSORED")
    censored_mask = censored_p1 | censored_p2
    resolved_mask = ~censored_mask
    n_total = len(p1_arr)
    n_resolved = int(resolved_mask.sum())
    n_censored = int(censored_mask.sum())

    if n_resolved > 0:
        p_p1_pass = float(((p1_arr == "PASS") & resolved_mask).sum() / n_resolved)
        if cfg["p2_target"] is not None:
            # Conditional: among resolved & P1 PASS, how many P2 PASS?
            p1_pass_resolved = (p1_arr == "PASS") & resolved_mask
            n_pass_p1_resolved = int(p1_pass_resolved.sum())
            n_funded = int(((p1_arr == "PASS") & (p2_arr == "PASS") & resolved_mask).sum())
            p_p2_given = (n_funded / n_pass_p1_resolved) if n_pass_p1_resolved else 0.0
            p_funded = n_funded / n_resolved
        else:
            p_p2_given = None
            p_funded = p_p1_pass
    else:
        p_p1_pass = float("nan")
        p_p2_given = float("nan") if cfg["p2_target"] is not None else None
        p_funded = float("nan")

    # Median grind = p1_ttps + p2_ttps for PASSED attempts (resolved & funded)
    grind_days = []
    for i, (o1, t1, o2, t2) in enumerate(zip(p1_outcomes, p1_ttps, p2_outcomes, p2_ttps)):
        if o1 == "PASS" and o2 == "PASS":
            grind_days.append(t1 + (t2 if t2 > 0 else 0))
    median_grind = int(np.median(grind_days)) if grind_days else None
    mean_grind = float(np.mean(grind_days)) if grind_days else None

    # Breakdown of P1 fail modes (% over n_total, then % over n_resolved)
    def _frac_total(arr, target):
        return float((arr == target).mean())
    def _frac_resolved(arr, target):
        return float(((arr == target) & resolved_mask).sum() / n_resolved) if n_resolved else 0.0
    return {
        "container": container,
        "n_paths": n_total,
        "n_resolved": n_resolved,
        "n_censored": n_censored,
        "censored_pct": (n_censored / n_total * 100) if n_total else 0.0,
        "p_phase1": p_p1_pass,
        "p_phase2_given_p1": p_p2_given,
        "p_funded": p_funded,
        "p1_pass_pct": p_p1_pass * 100 if not np.isnan(p_p1_pass) else float("nan"),
        "p1_bust_total_pct": _frac_resolved(p1_arr, "BUST_TOTAL") * 100,
        "p1_bust_trail_pct": _frac_resolved(p1_arr, "BUST_TRAIL") * 100,
        "p1_bust_daily_pct": _frac_resolved(p1_arr, "BUST_DAILY") * 100,
        "p1_killed_pct": _frac_resolved(p1_arr, "KILLED") * 100,
        "p1_timeout_pct": _frac_resolved(p1_arr, "TIMEOUT") * 100,
        "p1_censored_pct_total": (censored_p1.sum() / n_total * 100) if n_total else 0.0,
        "p2_censored_pct_total": (censored_p2.sum() / n_total * 100) if n_total else 0.0,
        "median_ttp_p1": (int(np.median([t for o,t in zip(p1_outcomes,p1_ttps) if o == "PASS"]))
                          if (p1_arr == "PASS").any() else None),
        "median_ttp_p2": (int(np.median([t for o,t in zip(p2_outcomes,p2_ttps) if o == "PASS" and t > 0]))
                          if (cfg["p2_target"] and ((p2_arr == "PASS").any())
                              and len([t for o,t in zip(p2_outcomes,p2_ttps) if o == "PASS" and t > 0]) > 0)
                          else None),
        "median_grind_p1p2": median_grind,
        "mean_grind_p1p2": mean_grind,
        "outcomes_p1": p1_outcomes,
        "outcomes_p2": p2_outcomes,
        "ttps_p1": p1_ttps,
        "ttps_p2": p2_ttps,
        "starts": starts,
        "resolved_mask": resolved_mask,
    }


def simulate_iid_container(
    M: pd.DataFrame,
    container: str,
    block_cap_pct: float = 0.015,
    killswitch_daily_pct: float | None = None,
    killswitch_total_pct: float | None = None,
    n_paths: int = 10000,
    seed: int = 1,
) -> dict:
    """
    iid bootstrap of daily-row indices, then run container rules on each path.
    Useful for stable estimates when fold sizes are small.
    """
    cfg = CONTAINERS[container]
    rng = np.random.default_rng(seed)
    n = len(M)
    am, pm, _, _ = _block_pnl_array(M, block_cap_pct)

    # Build a synthetic "matrix" of resampled R rows by index
    am_idx = rng.integers(0, n, size=(n_paths, cfg["max_days_p1"] + cfg["max_days_p2"]))
    # We need to call _run_single_attempt but with a resampled history. To keep
    # things simple, build a per-path resampled (am, pm, M) view.
    p1_outcomes = []
    p2_outcomes = []
    p1_ttps = []
    am_vals_orig = M[AM_COLS].values
    pm_vals_orig = M[PM_COLS].values

    for p in range(n_paths):
        idx_seq = am_idx[p]
        # Build a synthetic M of length 80 days
        am_p = am[idx_seq]
        pm_p = pm[idx_seq]
        # M-like for NaN checks: use the underlying rows from the original
        # We can't easily re-use _run_single_attempt without a DataFrame, so
        # inline a slim version here.
        eq = 1.0
        peak_eq = 1.0
        tdays = 0
        p1_done = False
        p1_outcome = None
        p1_eq = 1.0
        p1_ttp = 0
        for d in range(cfg["max_days_p1"]):
            j_orig = idx_seq[d]
            day_start = eq
            trail_floor = (1 - cfg["trailing_loss_pct"]) * peak_eq if cfg["trailing_loss_pct"] else None
            floor_list = [v for v in [cfg["total_loss_floor"], trail_floor] if v is not None]
            effective_floor = max(floor_list) if floor_list else None
            # AM
            eq_am = eq * (1 + am_p[d])
            if effective_floor is not None and eq_am < effective_floor:
                p1_outcome = "BUST_TRAIL" if (trail_floor is not None and (cfg["total_loss_floor"] is None or trail_floor > cfg["total_loss_floor"])) else "BUST_TOTAL"
                p1_eq, p1_ttp = eq_am, d + 1
                break
            if eq_am < day_start * (1 - cfg["daily_loss_pct"]):
                p1_outcome, p1_eq, p1_ttp = "BUST_DAILY", eq_am, d + 1
                break
            if killswitch_daily_pct is not None and eq_am < day_start * (1 - killswitch_daily_pct):
                eq = eq_am
                traded = (~np.isnan(am_vals_orig[j_orig])).any() or (~np.isnan(pm_vals_orig[j_orig])).any()
                if traded:
                    tdays += 1
                peak_eq = max(peak_eq, eq)
                if killswitch_total_pct is not None and eq < (1 - killswitch_total_pct):
                    p1_outcome, p1_eq, p1_ttp = "KILLED", eq, d + 1
                    break
                continue
            eq = eq_am
            # PM
            eq_pm = eq * (1 + pm_p[d])
            if effective_floor is not None and eq_pm < effective_floor:
                p1_outcome = "BUST_TRAIL" if (trail_floor is not None and (cfg["total_loss_floor"] is None or trail_floor > cfg["total_loss_floor"])) else "BUST_TOTAL"
                p1_eq, p1_ttp = eq_pm, d + 1
                break
            if eq_pm < day_start * (1 - cfg["daily_loss_pct"]):
                p1_outcome, p1_eq, p1_ttp = "BUST_DAILY", eq_pm, d + 1
                break
            eq = eq_pm
            traded = (~np.isnan(am_vals_orig[j_orig])).any() or (~np.isnan(pm_vals_orig[j_orig])).any()
            if traded:
                tdays += 1
            peak_eq = max(peak_eq, eq)
            if killswitch_total_pct is not None and eq < (1 - killswitch_total_pct):
                p1_outcome, p1_eq, p1_ttp = "KILLED", eq, d + 1
                break
            if eq >= 1 + cfg["p1_target"] and tdays >= 4:
                p1_outcome, p1_eq, p1_ttp = "PASS", eq, d + 1
                break
        if p1_outcome is None:
            p1_outcome, p1_eq, p1_ttp = "TIMEOUT", eq, cfg["max_days_p1"]
        p1_outcomes.append(p1_outcome)
        p1_ttps.append(p1_ttp)

        if p1_outcome == "PASS" and cfg["p2_target"] is not None:
            # Phase 2 on the next slice of resampled indices
            eq2 = 1.0
            peak2 = 1.0
            tdays2 = 0
            p2_outcome = None
            for d in range(cfg["max_days_p2"]):
                j_orig = idx_seq[cfg["max_days_p1"] + d] if (cfg["max_days_p1"] + d) < len(idx_seq) else idx_seq[d]
                day_start = eq2
                # P2 uses same DD rules; need separate am/pm samples
                # We use the second half of the resampled sequence
                if (cfg["max_days_p1"] + d) >= len(idx_seq):
                    break
                am_v = am[idx_seq[cfg["max_days_p1"] + d]]
                pm_v = pm[idx_seq[cfg["max_days_p1"] + d]]
                trail_floor = (1 - cfg["trailing_loss_pct"]) * peak2 if cfg["trailing_loss_pct"] else None
                floor_list = [v for v in [cfg["total_loss_floor"], trail_floor] if v is not None]
                effective_floor = max(floor_list) if floor_list else None
                eq2_am = eq2 * (1 + am_v)
                if effective_floor is not None and eq2_am < effective_floor:
                    p2_outcome = "BUST_TOTAL"; break
                if eq2_am < day_start * (1 - cfg["daily_loss_pct"]):
                    p2_outcome = "BUST_DAILY"; break
                eq2 = eq2_am
                eq2_pm = eq2 * (1 + pm_v)
                if effective_floor is not None and eq2_pm < effective_floor:
                    p2_outcome = "BUST_TOTAL"; break
                if eq2_pm < day_start * (1 - cfg["daily_loss_pct"]):
                    p2_outcome = "BUST_DAILY"; break
                eq2 = eq2_pm
                traded = (~np.isnan(am_vals_orig[j_orig])).any() or (~np.isnan(pm_vals_orig[j_orig])).any()
                if traded:
                    tdays2 += 1
                peak2 = max(peak2, eq2)
                if eq2 >= 1 + cfg["p2_target"] and tdays2 >= 4:
                    p2_outcome = "PASS"; break
            if p2_outcome is None:
                p2_outcome = "TIMEOUT"
            p2_outcomes.append(p2_outcome)
        elif p1_outcome == "PASS":
            p2_outcomes.append("N/A_1PHASE")
        else:
            p2_outcomes.append("NOT_REACHED")

    p1_arr = np.array(p1_outcomes)
    p2_arr = np.array(p2_outcomes)
    p_p1 = float((p1_arr == "PASS").mean())
    if cfg["p2_target"] is not None:
        n_pass_p1 = (p1_arr == "PASS").sum()
        p_p2 = float((p2_arr == "PASS").sum() / n_pass_p1) if n_pass_p1 else 0.0
        p_funded = float(((p1_arr == "PASS") & (p2_arr == "PASS")).mean())
    else:
        p_p2 = None
        p_funded = p_p1
    return {
        "container": container,
        "n_paths": int(n_paths),
        "p_phase1": p_p1,
        "p_phase2_given_p1": p_p2,
        "p_funded": p_funded,
        "p1_outcomes": p1_outcomes,
        "p2_outcomes": p2_outcomes,
        "p1_ttps": p1_ttps,
    }


if __name__ == "__main__":
    from orb_core import build_3sleeve_matrix
    M = build_3sleeve_matrix(lo="2022", hi="2025")
    print("Sanity check — full 2022-2025, block_cap=1.5%:")
    for c in CONTAINERS:
        # real path
        out_rp = simulate_real_path_container(M, c)
        # iid
        out_iid = simulate_iid_container(M, c, n_paths=5000)
        print(f"  {c:18s} REAL p_funded={out_rp['p_funded']*100:5.1f}% "
              f"(p1={out_rp['p_phase1']*100:.1f}% "
              f"p2|p1={(out_rp['p_phase2_given_p1'] or 1)*100:.1f}%)"
              f"  |  IID p_funded={out_iid['p_funded']*100:5.1f}% "
              f"(p1={out_iid['p_phase1']*100:.1f}%)")
