"""
step3b_weekly_2026.py — Reproduce the 2026 weekly-challenge 93% figure
+ p(funded) end-to-end with real-path chaining (P1 then P2 on actual subsequent days).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix, block_capped_pnl
from ftmo_engine import simulate, _block_pnl_array

AM_COLS = ["GER40_1000_30m"]
PM_COLS = ["US100_1630_30m", "GER40_1630_15m"]


def weekly_challenges_realpath(M: pd.DataFrame, start_dates: list[str],
                               target_pct: float = 0.10, max_days: int = 40,
                               block_cap_pct: float = 0.015) -> pd.DataFrame:
    """Run one real-path challenge per start_date; return result table."""
    rows = []
    am, pm, _, _ = _block_pnl_array(M, block_cap_pct)
    for sd in start_dates:
        # Find the index of the start_date in M
        try:
            i0 = M.index.get_indexer([pd.Timestamp(sd)], method="nearest")[0]
        except Exception:
            continue
        eq = 1.0
        peak = 1.0
        trough = 1.0
        outcome = "RUNNING"
        days_resolved = max_days
        tdays = 0
        for d in range(max_days):
            j = i0 + d
            if j >= len(M):
                outcome = "RUNNING"
                days_resolved = d
                break
            am_r = am[j]
            pm_r = pm[j]
            day_start = eq
            traded = False
            # AM
            eq_am = eq * (1 + am_r)
            if not np.isnan(M[AM_COLS].iloc[j]).all():
                traded = True
            trough = min(trough, eq_am)
            if eq_am < 0.90:
                outcome, days_resolved = "BUST_TOTAL", d + 1
                eq = eq_am
                break
            if eq_am < day_start * 0.95:
                outcome, days_resolved = "BUST_DAILY", d + 1
                eq = eq_am
                break
            eq = eq_am
            # PM
            eq_pm = eq * (1 + pm_r)
            if not np.isnan(M[PM_COLS].iloc[j]).all().all() if hasattr(M[PM_COLS].iloc[j], 'all') else False:
                traded = True
            if (~np.isnan(M[PM_COLS].iloc[j])).any():
                traded = True
            trough = min(trough, eq_pm)
            if eq_pm < 0.90:
                outcome, days_resolved = "BUST_TOTAL", d + 1
                eq = eq_pm
                break
            if eq_pm < day_start * 0.95:
                outcome, days_resolved = "BUST_DAILY", d + 1
                eq = eq_pm
                break
            eq = eq_pm
            if traded:
                tdays += 1
            peak = max(peak, eq)
            if eq >= 1 + target_pct and tdays >= 4:
                outcome, days_resolved = "PASS", d + 1
                break
        rows.append({
            "start": sd, "outcome": outcome, "days_to_resolve": days_resolved,
            "trading_days": tdays, "peak_eq": peak, "trough_eq": trough,
            "final_eq": eq,
        })
    return pd.DataFrame(rows)


def end_to_end_phase_chain_realpath(M: pd.DataFrame, max_days_p1: int = 40,
                                     max_days_p2: int = 40,
                                     block_cap_pct: float = 0.015) -> dict:
    """
    For each historical start position, run Phase 1; if pass, run Phase 2
    starting immediately after.
    Returns dict with p_funded and intermediate stats.
    """
    am, pm, _, _ = _block_pnl_array(M, block_cap_pct)
    n = len(M)
    n_paths = n - max_days_p1 - max_days_p2 + 1
    if n_paths <= 0:
        return {"p_funded": 0, "n_paths": 0}
    results = []
    for s in range(n_paths):
        # Phase 1
        eq = 1.0
        passed_p1 = False
        tdays_p1 = 0
        for d in range(max_days_p1):
            j = s + d
            day_start = eq
            eq *= (1 + am[j])
            if eq < 0.90 or eq < day_start * 0.95:
                break
            eq *= (1 + pm[j])
            if eq < 0.90 or eq < day_start * 0.95:
                break
            traded = ((~np.isnan(M[AM_COLS].iloc[j])).any() or
                      (~np.isnan(M[PM_COLS].iloc[j])).any())
            if traded:
                tdays_p1 += 1
            if eq >= 1.10 and tdays_p1 >= 4:
                passed_p1 = True
                p1_resolved_at = j + 1
                break
        if not passed_p1:
            results.append({"phase1": False, "phase2": False})
            continue
        # Phase 2: target +5%, starts day after P1 resolution
        eq2 = 1.0
        passed_p2 = False
        tdays_p2 = 0
        for d in range(max_days_p2):
            j = p1_resolved_at + d
            if j >= n:
                break
            day_start = eq2
            eq2 *= (1 + am[j])
            if eq2 < 0.90 or eq2 < day_start * 0.95:
                break
            eq2 *= (1 + pm[j])
            if eq2 < 0.90 or eq2 < day_start * 0.95:
                break
            traded = ((~np.isnan(M[AM_COLS].iloc[j])).any() or
                      (~np.isnan(M[PM_COLS].iloc[j])).any())
            if traded:
                tdays_p2 += 1
            if eq2 >= 1.05 and tdays_p2 >= 4:
                passed_p2 = True
                break
        results.append({"phase1": True, "phase2": passed_p2})
    df = pd.DataFrame(results)
    p1 = df["phase1"].mean()
    p2_cond = df.loc[df["phase1"], "phase2"].mean() if df["phase1"].any() else 0
    p_funded = (df["phase1"] & df["phase2"]).mean()
    return {"p_phase1": p1, "p_phase2_given_phase1": p2_cond,
            "p_funded": p_funded, "n_paths": len(df)}


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    M_2026 = build_3sleeve_matrix(lo="2026", hi="2026")
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")
    print("=" * 80)
    print("Reproduce 2026 weekly-challenge 93% figure (report §3 / CHALLENGE_METRICS_2026.md)")
    print("=" * 80)
    # Mondays Jan 5 -> May 25 2026 (per report)
    mondays = pd.date_range("2026-01-05", "2026-05-25", freq="W-MON")
    res = weekly_challenges_realpath(M_2026, [d.strftime("%Y-%m-%d") for d in mondays])
    print(res.to_string(index=False))
    print()
    print(f"Aggregate: {len(res)} challenges")
    print(res["outcome"].value_counts())
    resolved = res[res["outcome"].isin(["PASS","BUST_TOTAL","BUST_DAILY","TIMEOUT"])]
    if len(resolved):
        pass_rate_resolved = (resolved["outcome"]=="PASS").mean()
        print(f"Pass rate among resolved: {pass_rate_resolved*100:.0f}%")
    print(f"Report claim: 13 PASS / 14 resolved / 1 TIMEOUT / 7 still running / median TTP 19d / 93% of resolved")
    print()

    print("=" * 80)
    print("End-to-end real-path P1->P2 chaining (each start, full 2022-2025)")
    print("=" * 80)
    ch = end_to_end_phase_chain_realpath(M_full)
    print(f"  n_paths = {ch['n_paths']}")
    print(f"  p(Phase 1 +10%) = {ch['p_phase1']*100:.1f}%")
    print(f"  p(Phase 2 +5% | passed P1) = {ch['p_phase2_given_phase1']*100:.1f}%")
    print(f"  p(funded) end-to-end = {ch['p_funded']*100:.1f}%")
    print()
    print("This is the HONEST chained probability of getting funded from a single attempt,")
    print("starting at a random historical date. Replaces the report's 80% (Phase 1 only).")
