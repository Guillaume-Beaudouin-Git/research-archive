"""
ftmo_sim_ensemble.py — FTMO Monte-Carlo for the index-ORB ensemble.

Two features that make this honest:
1. DAY-BLOCK bootstrap: we resample whole trading days (the full cross-instrument
   R vector), so any within-day correlation between setups is preserved. (For ORB
   the cross-instrument correlation happens to be ~0, but the method is correct
   regardless and does not assume independence.)
2. RISK OVERLAYS that are pure risk-management (not signal tuning):
     - daily circuit-breaker: stop trading for the day after a -X% daily loss.
     - optional "coast": cut size once equity is comfortably above start.

Result (risk 0.6%/trade, -3% daily breaker), single attempt:
    TRAIN 2021-22 : 70%      VALID 2023 : 40% (ORB decay year)      OOS 2024-25 : 65%
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def simulate(matrix: pd.DataFrame, risk: float, n_paths: int = 20_000,
             max_days: int = 40, daily_stop: float | None = 0.03,
             coast_at: float | None = None, coast_mult: float = 0.5,
             start=10_000.0, target=11_000.0, total_floor=9_000.0,
             daily_loss=500.0, min_trading_days: int = 4, seed: int = 1) -> dict:
    """Day-block bootstrap of the ensemble's daily R-matrix through the FTMO barriers."""
    vals = matrix.values
    ncol = matrix.shape[1]
    n_hist = len(vals)
    rng = np.random.default_rng(seed)
    eq = np.full(n_paths, start)
    status = np.zeros(n_paths, int)   # 0 live, 1 pass, 2 fail-daily, 3 fail-total
    tdays = np.zeros(n_paths, int)

    for _ in range(max_days):
        row = vals[rng.integers(0, n_hist, n_paths)]   # one historical day per path
        day_start = eq.copy()
        traded = np.zeros(n_paths, bool)
        halted = np.zeros(n_paths, bool)
        for c in range(ncol):                          # apply each setup's trade
            r = row[:, c]
            has = ~np.isnan(r)
            live = (status == 0) & has & (~halted)
            rr = np.where(has, r, 0.0)
            rk = np.full(n_paths, risk)
            if coast_at is not None:
                rk = np.where(eq >= coast_at, risk * coast_mult, rk)
            eq = np.where(live, eq + rk * eq * rr, eq)
            traded |= live
            status = np.where(live & (eq < total_floor), 3, status)
            status = np.where(live & (eq < day_start - daily_loss) & (status == 0), 2, status)
            if daily_stop is not None:
                halted |= eq <= day_start * (1 - daily_stop)
        tdays += traded.astype(int)
        passed = (status == 0) & (eq >= target) & (tdays >= min_trading_days)
        status = np.where(passed, 1, status)
        if (status == 0).sum() == 0:
            break

    return {"pass_rate": float((status == 1).mean()),
            "fail_daily": float((status == 2).mean()),
            "fail_total": float((status == 3).mean()),
            "timeout": float((status == 0).mean())}


def reattempt(p: float, n=(1, 2, 3)):
    return {k: 1 - (1 - p) ** k for k in n}


if __name__ == "__main__":
    from strategy_orb import build_ensemble_matrix
    for lab, lo, hi in [("TRAIN 2021-22", "2021", "2022"),
                        ("VALID 2023", "2023", "2023"),
                        ("OOS 2024-25", "2024", "2025")]:
        M = build_ensemble_matrix(lo=lo, hi=hi)
        m = simulate(M, risk=0.006)
        print(f"{lab}: meanR={M.mean().mean():+.3f}  PASS={m['pass_rate']*100:.0f}%  "
              f"failTotal={m['fail_total']*100:.0f}%  timeout={m['timeout']*100:.0f}%")
    M = build_ensemble_matrix(lo="2024", hi="2025")
    p = simulate(M, risk=0.006)["pass_rate"]
    print("OOS re-attempts:", {k: round(v, 2) for k, v in reattempt(p).items()})
