"""
nq_sim.py — FTMO 2-step uncapped simulator for single-sleeve NQ ORB.

Differs from optim_engine.py (which is 3-sleeve AM+PM):
  - Single sleeve = one trade per day max.
  - block_cap_pct = risk-per-trade.
  - Daily PnL = block_cap_pct * R_realised (no block split).

Container = ftmo_2step_uncapped:
  Phase 1: target +10%, daily -5%, total -10% static, no time limit
  Phase 2: target +5%, daily -5%, total -10% static, no time limit
  Funded = pass P1 then pass P2.
  Censure: if grind hits end-of-data without resolution → exclude.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _run_attempt(daily_R: np.ndarray, dates_idx: np.ndarray,
                 start_idx: int, target_pct: float,
                 daily_loss_pct: float = 0.05, total_loss_pct: float = 0.10,
                 block_cap_pct: float = 0.005,
                 min_trading_days: int = 4) -> tuple[str, float, int, int]:
    """
    Run one challenge attempt from start_idx using daily_R series (one trade per day max).

    daily_R: array of R-multiples (NaN where no trade).
    Returns: outcome, final_eq, days_resolved, trading_days
    """
    n = len(daily_R)
    eq = 1.0
    tdays = 0
    target = 1 + target_pct
    total_floor = 1 - total_loss_pct
    daily_floor = 1 - daily_loss_pct

    for d in range(n - start_idx):
        j = start_idx + d
        if j >= n:
            return "CENSORED", eq, d, tdays
        day_start = eq
        r = daily_R[j]
        if np.isnan(r):
            # No trade today; equity unchanged
            continue
        eq_new = eq * (1 + block_cap_pct * r)
        # Total floor (static)
        if eq_new < total_floor:
            return "BUST_TOTAL", eq_new, d + 1, tdays
        # Daily floor (vs day_start)
        if eq_new < day_start * daily_floor:
            return "BUST_DAILY", eq_new, d + 1, tdays
        eq = eq_new
        tdays += 1
        if eq >= target and tdays >= min_trading_days:
            return "PASS", eq, d + 1, tdays
    return "CENSORED", eq, n - start_idx, tdays


def simulate_2step_uncapped(daily_R: pd.Series, block_cap_pct: float = 0.005,
                              p1_target: float = 0.10, p2_target: float = 0.05,
                              start_indices: list[int] | None = None) -> dict:
    """
    Simulate FTMO 2-step uncapped: run P1 from each start; if PASS, run P2 from day after.
    Returns aggregate stats over resolved starts (excludes CENSORED).
    """
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
        out_p1, eq_p1, ttp_p1, _ = _run_attempt(R, dates, int(s), p1_target,
                                                  block_cap_pct=block_cap_pct)
        if out_p1 == "PASS":
            p2_start = int(s) + ttp_p1
            if p2_start >= n:
                outcomes.append("PASS_P1_CENSORED_P2")
                p1_resolutions.append(ttp_p1)
                p2_outcomes.append("CENSORED")
            else:
                out_p2, eq_p2, ttp_p2, _ = _run_attempt(R, dates, p2_start, p2_target,
                                                         block_cap_pct=block_cap_pct)
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
    # Resolved = neither CENSORED outright nor PASS_P1_CENSORED_P2
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
        p_phase2_given_p1 = (n_funded / n_pass_p1_resolved) if n_pass_p1_resolved else 0.0
    else:
        p_phase1 = float("nan")
        p_funded = float("nan")
        p_phase2_given_p1 = float("nan")
    # Bust breakdown over RESOLVED
    def _frac_resolved(target):
        return float(((outcomes_arr == target) & resolved_mask).sum() / n_resolved) if n_resolved else 0.0
    # Median grind for FUNDED
    funded_idx = np.where(outcomes_arr == "FUNDED")[0]
    funded_grind = []
    for i in funded_idx:
        # Approximation: P1 resolution + P2 approx (not stored explicitly)
        funded_grind.append(p1_resolutions[i])
    return {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_censored": n_censored,
        "censored_pct": n_censored / n_total * 100 if n_total else 0,
        "p_phase1": p_phase1,
        "p_funded": p_funded,
        "p_phase2_given_p1": p_phase2_given_p1,
        "p_funded_pct": p_funded * 100 if not np.isnan(p_funded) else float("nan"),
        "bust_total_pct_resolved": _frac_resolved("BUST_TOTAL") * 100,
        "bust_daily_pct_resolved": _frac_resolved("BUST_DAILY") * 100,
        "fail_p2_total_pct_resolved": _frac_resolved("PASS_P1_BUST_TOTAL_P2") * 100,
        "fail_p2_daily_pct_resolved": _frac_resolved("PASS_P1_BUST_DAILY_P2") * 100,
        "median_grind_p1": int(np.median(funded_grind)) if funded_grind else None,
    }


def trades_to_daily_R(df_trades: pd.DataFrame, all_dates: pd.DatetimeIndex) -> pd.Series:
    """
    Convert trades DataFrame to a daily R series aligned to all_dates.
    Days without a trade get NaN (no PnL change).
    """
    return df_trades["r_realised"].reindex(all_dates)


if __name__ == "__main__":
    # Quick sanity test with simulated data
    print("Sanity check on synthetic data...")
    np.random.seed(42)
    n = 1000
    dates = pd.date_range("2010-01-01", periods=n, freq="B")
    R = np.random.normal(0.1, 1.5, n)  # mean R = 0.10, std = 1.5
    daily_R = pd.Series(R, index=dates)
    out = simulate_2step_uncapped(daily_R, block_cap_pct=0.005)
    print(f"  n_total={out['n_total']}, n_resolved={out['n_resolved']}, censored={out['censored_pct']:.1f}%")
    print(f"  p_phase1={out['p_phase1']*100:.1f}%, p_funded={out['p_funded']*100:.1f}%")
    print(f"  bust_total={out['bust_total_pct_resolved']:.1f}%, "
          f"bust_daily={out['bust_daily_pct_resolved']:.1f}%")
