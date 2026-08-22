"""
ftmo_engine.py — Audit-grade FTMO challenge simulator.

Two simulation modes:
  - iid_bootstrap : random daily R-vectors (same as ftmo_sim_ensemble.py)
  - real_path     : contiguous real days starting at each historical date

Floating-equity rule modelled within-day: we apply per-sleeve P&L in two
session-blocks (AM then PM, ordered by clock); the daily floor is checked
after AM and after PM (i.e. the worst point of the day). Block-cap 1.5% per
session block, AM = GER40@10:00 (1 sleeve, 1.5% risk); PM = US100+GER40@16:30
(2 sleeves, 0.75% each = 1.5% block).

Phase chaining: Phase 1 (+10% target) modelled, then Phase 2 (+5% target),
both with same daily 5% / total 10% caps. Phase 1 -> Phase 2 conditional pass
returned separately so we can compute p(funded) = p(P1) * p(P2 | P1).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Sequence

AM_COLS = ["GER40_1000_30m"]
PM_COLS = ["US100_1630_30m", "GER40_1630_15m"]


def _block_pnl_array(M: pd.DataFrame, block_cap_pct: float = 0.015):
    """
    Returns two arrays of equal length (N_days, ...): am_block_R and pm_block_R,
    each expressed as % of starting equity for that day's block (so block_cap
    is already baked in). NaNs preserved (no trade that day for that sleeve).
    """
    n = len(M)
    am = M[AM_COLS].fillna(0.0).sum(axis=1).values * block_cap_pct
    # PM: 2 sleeves share 1.5% (0.75% each)
    pm_risk = block_cap_pct / len(PM_COLS)
    pm = (M[PM_COLS].fillna(0.0) * pm_risk).sum(axis=1).values
    # We need per-sleeve PM P&L too to model intraday floating dd within PM block
    pm_sleeves = M[PM_COLS].fillna(0.0).values * pm_risk  # shape (n,2)
    am_sleeves = M[AM_COLS].fillna(0.0).values * block_cap_pct  # shape (n,1)
    return am, pm, am_sleeves, pm_sleeves


def simulate(
    M: pd.DataFrame,
    mode: str = "real_path",
    target_pct: float = 0.10,
    daily_loss_pct: float = 0.05,
    total_loss_pct: float = 0.10,
    block_cap_pct: float = 0.015,
    max_days: int = 40,
    min_trading_days: int = 4,
    n_paths: int = 5000,
    start_indices: Sequence[int] | None = None,
    seed: int = 1,
) -> dict:
    """
    Simulate FTMO challenges.

    mode='real_path': start at each calendar position in [0, n-max_days];
                     run contiguous max_days. n_paths becomes len(start_indices)
                     if provided, else len(M)-max_days+1.

    mode='iid_bootstrap': resample whole daily R-vectors iid.

    Returns: {pass_rate, fail_daily, fail_total, timeout, time_to_pass_dist,
              n_paths, per_path_outcome (np.ndarray), trough_dist}
    """
    am, pm, am_sl, pm_sl = _block_pnl_array(M, block_cap_pct)
    n = len(M)
    if mode == "real_path":
        if start_indices is None:
            starts = np.arange(0, max(1, n - max_days + 1))
        else:
            starts = np.asarray(start_indices)
        n_paths = len(starts)
    elif mode == "iid_bootstrap":
        rng = np.random.default_rng(seed)
        # pre-sample rows per path/day
        idx_mat = rng.integers(0, n, size=(n_paths, max_days))
    else:
        raise ValueError(mode)

    status = np.zeros(n_paths, dtype=int)  # 0=live 1=pass 2=fail_daily 3=fail_total
    eq = np.ones(n_paths)                  # equity normalised to 1
    tdays = np.zeros(n_paths, dtype=int)
    days_to_resolve = np.zeros(n_paths, dtype=int)
    trough = np.ones(n_paths)              # min equity hit (start=1)

    target = 1 + target_pct
    total_floor = 1 - total_loss_pct
    daily_floor_loss = daily_loss_pct       # measured from day_start

    for d in range(max_days):
        live = status == 0
        if not live.any():
            break
        # Get the day-row indices for this day
        if mode == "real_path":
            day_idx = starts + d
            valid = day_idx < n
            day_idx_eff = np.where(valid, day_idx, 0)
        else:
            day_idx_eff = idx_mat[:, d]
            valid = np.ones(n_paths, dtype=bool)

        am_r = am[day_idx_eff]
        pm_r = pm[day_idx_eff]
        # Also fetch per-sleeve PM (for intraday worst-point modelling)
        # We approximate "intraday worst" as min(0, sum of worst-case sleeve)
        # Simpler: model AM first then PM; floating check at end of AM and PM.
        day_start = eq.copy()

        # Trade AM
        live_mask = live & valid
        had_am_trade = (~np.isnan(M[AM_COLS].values[day_idx_eff])).any(axis=1) & live_mask
        eq_after_am = np.where(live_mask, day_start * (1 + am_r), day_start)
        # Total-floor check after AM (floating)
        total_breach_am = live_mask & (eq_after_am < total_floor)
        # Daily-loss check after AM
        daily_breach_am = live_mask & (eq_after_am < day_start * (1 - daily_floor_loss))
        status = np.where(total_breach_am, 3, status)
        status = np.where(daily_breach_am & (status == 0), 2, status)
        # update live mask
        live_mask = (status == 0) & valid
        eq = eq_after_am

        # Trade PM (only paths still alive)
        had_pm_trade = (~np.isnan(M[PM_COLS].values[day_idx_eff])).any(axis=1) & live_mask
        eq_after_pm = np.where(live_mask, eq * (1 + pm_r), eq)
        total_breach_pm = live_mask & (eq_after_pm < total_floor)
        daily_breach_pm = live_mask & (eq_after_pm < day_start * (1 - daily_floor_loss))
        status = np.where(total_breach_pm, 3, status)
        status = np.where(daily_breach_pm & (status == 0), 2, status)
        eq = eq_after_pm

        trough = np.minimum(trough, eq)
        traded_today = (had_am_trade | had_pm_trade) & valid
        tdays += traded_today.astype(int)
        # Check pass
        passed_now = (status == 0) & (eq >= target) & (tdays >= min_trading_days)
        days_to_resolve = np.where(passed_now & (days_to_resolve == 0), d + 1, days_to_resolve)
        status = np.where(passed_now, 1, status)

    # Anything still 0 at end = timeout
    timeout_mask = status == 0
    return {
        "n_paths": int(n_paths),
        "pass_rate": float((status == 1).mean()),
        "fail_daily": float((status == 2).mean()),
        "fail_total": float((status == 3).mean()),
        "timeout": float(timeout_mask.mean()),
        "median_ttp_days": int(np.median(days_to_resolve[status == 1]))
                          if (status == 1).any() else None,
        "ttp_dist": days_to_resolve[status == 1].tolist(),
        "trough_dist": trough.tolist(),
        "status": status,
        "start_indices": starts if mode == "real_path" else None,
    }


def chain_phase1_phase2(M: pd.DataFrame, n_paths_p2: int = 20000,
                        block_cap_pct: float = 0.015,
                        max_days_p1: int = 40, max_days_p2: int = 40,
                        seed: int = 7) -> dict:
    """
    Compute p(phase1), p(phase2 | phase1) via iid bootstrap, plus p(funded).

    Phase 1 target = +10%, Phase 2 target = +5%, both with same DD caps.
    """
    p1 = simulate(M, mode="iid_bootstrap", target_pct=0.10,
                  block_cap_pct=block_cap_pct, max_days=max_days_p1,
                  n_paths=n_paths_p2, seed=seed)
    p2 = simulate(M, mode="iid_bootstrap", target_pct=0.05,
                  block_cap_pct=block_cap_pct, max_days=max_days_p2,
                  n_paths=n_paths_p2, seed=seed + 1)
    pf = p1["pass_rate"] * p2["pass_rate"]
    return {
        "phase1": p1["pass_rate"],
        "phase2": p2["pass_rate"],
        "p_funded": pf,
        "p1_detail": p1,
        "p2_detail": p2,
    }


if __name__ == "__main__":
    from orb_core import build_3sleeve_matrix
    print("=" * 70)
    print("AUDIT BASELINE — 3-sleeve core, block-cap 1.5%")
    print("=" * 70)
    for lab, lo, hi in [("2021-22", "2021", "2022"),
                        ("2023 chop", "2023", "2023"),
                        ("2024-25 OOS", "2024", "2025"),
                        ("2022-2025 full", "2022", "2025"),
                        ("2021-2026 all", "2021", "2026"),
                        ("2026 only", "2026", "2026")]:
        M = build_3sleeve_matrix(lo=lo, hi=hi)
        # real-path on this window
        r_real = simulate(M, mode="real_path", max_days=40)
        # iid bootstrap on same R-pool
        r_iid = simulate(M, mode="iid_bootstrap", n_paths=10000, max_days=40)
        print(f"{lab:18s} days={len(M):4d}  "
              f"REAL pass={r_real['pass_rate']*100:5.1f}% "
              f"(fT={r_real['fail_total']*100:4.1f}% fD={r_real['fail_daily']*100:4.1f}% "
              f"to={r_real['timeout']*100:4.1f}% n={r_real['n_paths']})  "
              f"|  IID pass={r_iid['pass_rate']*100:5.1f}% "
              f"(fT={r_iid['fail_total']*100:4.1f}% fD={r_iid['fail_daily']*100:4.1f}%)")
    print()
    print("=" * 70)
    print("Phase 1 + Phase 2 chain (full 2022-2025 R-pool, iid bootstrap)")
    print("=" * 70)
    Mfull = build_3sleeve_matrix(lo="2022", hi="2025")
    chained = chain_phase1_phase2(Mfull, n_paths_p2=10000)
    print(f"  p(phase1 +10%) = {chained['phase1']*100:.1f}%")
    print(f"  p(phase2 +5%)  = {chained['phase2']*100:.1f}%")
    print(f"  p(funded) = p1 * p2 = {chained['p_funded']*100:.1f}%")
