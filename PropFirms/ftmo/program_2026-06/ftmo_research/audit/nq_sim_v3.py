"""
nq_sim_v3.py — Extended FTMO 2-step simulator with challenge-management rules.

Adds 3 new mechanisms on top of nq_sim.simulate_2step_uncapped:

  1. De-risk after fraction-of-target reached.
     Param `derisk_at_target_frac`: once cum profit ≥ this × target,
       multiply per-trade risk by `derisk_size_factor`.
     E.g. derisk_at_target_frac=0.8, derisk_size_factor=0.0 → stop trading
       once 80% of target is locked.

  2. Reduce risk linearly when approaching floor.
     Param `floor_proximity_taper`: bool. If True, scale risk by
       (eq - floor) / (eq_peak - floor) clipped to [0.25, 1.0].
     Reduces sizing when equity is close to floor.

  3. Phase-specific block_cap_pct.
     `block_cap_p1`, `block_cap_p2` independent. Default both = 0.005.

Same input format as nq_sim. Same output format. Adds optional fields to
each path's RunResult for diagnostics.
"""
from __future__ import annotations
from typing import Optional
import numpy as np
import pandas as pd


def _run_attempt_v3(daily_R: np.ndarray, dates_idx: np.ndarray,
                      start_idx: int, target_pct: float,
                      daily_loss_pct: float = 0.05,
                      total_loss_pct: float = 0.10,
                      block_cap_pct: float = 0.005,
                      min_trading_days: int = 4,
                      # v3 extensions:
                      derisk_at_target_frac: Optional[float] = None,
                      derisk_size_factor: float = 0.0,
                      floor_proximity_taper: bool = False,
                      taper_min_factor: float = 0.25) -> tuple[str, float, int, int]:
    """Same as _run_attempt with optional challenge-mgmt rules."""
    n = len(daily_R)
    eq = 1.0
    eq_peak = 1.0
    tdays = 0
    target = 1 + target_pct
    total_floor = 1 - total_loss_pct
    daily_floor = 1 - daily_loss_pct
    derisked = False

    for d in range(n - start_idx):
        j = start_idx + d
        if j >= n:
            return "CENSORED", eq, d, tdays
        day_start = eq
        r = daily_R[j]
        if np.isnan(r):
            continue

        # Compute current risk multiplier
        risk_mult = 1.0
        if derisk_at_target_frac is not None:
            if not derisked and (eq - 1.0) >= derisk_at_target_frac * target_pct:
                derisked = True
            if derisked:
                risk_mult *= derisk_size_factor
        if floor_proximity_taper:
            # Distance from current eq to floor relative to peak
            if eq_peak > total_floor:
                room = (eq - total_floor) / (eq_peak - total_floor)
                proximity_factor = max(taper_min_factor, min(1.0, room))
                risk_mult *= proximity_factor

        effective_bcp = block_cap_pct * risk_mult
        if effective_bcp <= 0:
            # Trade off: equity stays flat, but trading days don't tick if we
            # treat this as "no trade today" semantics. Keep tdays only when
            # we have an actual move.
            continue

        eq_new = eq * (1 + effective_bcp * r)
        # Total floor (static)
        if eq_new < total_floor:
            return "BUST_TOTAL", eq_new, d + 1, tdays
        # Daily floor
        if eq_new < day_start * daily_floor:
            return "BUST_DAILY", eq_new, d + 1, tdays
        eq = eq_new
        if eq > eq_peak:
            eq_peak = eq
        tdays += 1
        if eq >= target and tdays >= min_trading_days:
            return "PASS", eq, d + 1, tdays
    return "CENSORED", eq, n - start_idx, tdays


def simulate_2step_v3(daily_R: pd.Series,
                       block_cap_p1: float = 0.005,
                       block_cap_p2: float = 0.005,
                       p1_target: float = 0.10,
                       p2_target: float = 0.05,
                       start_indices: list[int] | None = None,
                       # v3 mgmt params:
                       derisk_at_target_frac: Optional[float] = None,
                       derisk_size_factor: float = 0.0,
                       floor_proximity_taper: bool = False,
                       taper_min_factor: float = 0.25) -> dict:
    R = daily_R.values
    dates = daily_R.index.values
    n = len(R)
    if start_indices is None:
        starts = np.arange(n)
    else:
        starts = np.asarray(start_indices)

    outcomes = []
    p1_resolutions = []
    p2_outcomes = []

    for s in starts:
        out_p1, eq_p1, ttp_p1, _ = _run_attempt_v3(
            R, dates, int(s), p1_target,
            block_cap_pct=block_cap_p1,
            derisk_at_target_frac=derisk_at_target_frac,
            derisk_size_factor=derisk_size_factor,
            floor_proximity_taper=floor_proximity_taper,
            taper_min_factor=taper_min_factor,
        )
        if out_p1 == "PASS":
            p2_start = int(s) + ttp_p1
            if p2_start >= n:
                outcomes.append("PASS_P1_CENSORED_P2")
                p1_resolutions.append(ttp_p1)
                p2_outcomes.append("CENSORED")
            else:
                out_p2, eq_p2, ttp_p2, _ = _run_attempt_v3(
                    R, dates, p2_start, p2_target,
                    block_cap_pct=block_cap_p2,
                    derisk_at_target_frac=derisk_at_target_frac,
                    derisk_size_factor=derisk_size_factor,
                    floor_proximity_taper=floor_proximity_taper,
                    taper_min_factor=taper_min_factor,
                )
                p2_outcomes.append(out_p2)
                p1_resolutions.append(ttp_p1)
                if out_p2 == "PASS":
                    outcomes.append("FUNDED")
                elif out_p2 == "CENSORED":
                    outcomes.append("PASS_P1_CENSORED_P2")
                else:
                    outcomes.append(f"PASS_P1_{out_p2}_P2")
        else:
            outcomes.append(out_p1)
            p1_resolutions.append(ttp_p1)
            p2_outcomes.append("NOT_REACHED")

    outcomes_arr = np.array(outcomes)
    censored_mask = (outcomes_arr == "CENSORED") | (outcomes_arr == "PASS_P1_CENSORED_P2")
    resolved_mask = ~censored_mask
    n_total = len(outcomes_arr)
    n_resolved = int(resolved_mask.sum())
    n_censored = int(censored_mask.sum())

    if n_resolved > 0:
        n_funded = int((outcomes_arr == "FUNDED").sum())
        n_pass_p1_resolved = int(np.isin(outcomes_arr, ["FUNDED", "PASS_P1_BUST_TOTAL_P2",
                                                          "PASS_P1_BUST_DAILY_P2"]).sum())
        p_phase1 = n_pass_p1_resolved / n_resolved
        p_funded = n_funded / n_resolved
    else:
        p_phase1 = float("nan")
        p_funded = float("nan")
        n_funded = 0

    def _frac_resolved(target_o):
        return float(((outcomes_arr == target_o) & resolved_mask).sum() / n_resolved) if n_resolved else 0.0

    return {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_censored": n_censored,
        "n_funded": n_funded,
        "censored_pct": n_censored / n_total * 100 if n_total else 0,
        "p_phase1": p_phase1,
        "p_funded": p_funded,
        "p_funded_pct": p_funded * 100 if not np.isnan(p_funded) else float("nan"),
        "bust_total_pct_resolved": _frac_resolved("BUST_TOTAL") * 100,
        "bust_daily_pct_resolved": _frac_resolved("BUST_DAILY") * 100,
        "fail_p2_total_pct_resolved": _frac_resolved("PASS_P1_BUST_TOTAL_P2") * 100,
        "fail_p2_daily_pct_resolved": _frac_resolved("PASS_P1_BUST_DAILY_P2") * 100,
    }


if __name__ == "__main__":
    # Sanity test
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from nq_sim import simulate_2step_uncapped

    rng = np.random.default_rng(42)
    n = 1000
    R = rng.normal(0.1, 1.5, n)
    daily_R = pd.Series(R, index=pd.date_range("2010-01-01", periods=n, freq="B"))

    out_v2 = simulate_2step_uncapped(daily_R, block_cap_pct=0.005)
    out_v3 = simulate_2step_v3(daily_R, block_cap_p1=0.005, block_cap_p2=0.005)

    print("v2:", out_v2.get("p_funded_pct"))
    print("v3 (no rules):", out_v3.get("p_funded_pct"))
    print("v3 derisk at 80%:", simulate_2step_v3(
        daily_R, block_cap_p1=0.005, block_cap_p2=0.005,
        derisk_at_target_frac=0.8, derisk_size_factor=0.0).get("p_funded_pct"))
    print("v3 floor proximity taper:", simulate_2step_v3(
        daily_R, block_cap_p1=0.005, block_cap_p2=0.005,
        floor_proximity_taper=True).get("p_funded_pct"))
    print("v3 P2 conservatif 0.003:", simulate_2step_v3(
        daily_R, block_cap_p1=0.005, block_cap_p2=0.003).get("p_funded_pct"))
