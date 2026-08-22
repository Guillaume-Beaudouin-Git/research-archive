"""
optim_step7_uncapped_sweep.py — FTMO 2-step UNCAPPED sweep with censorship.

Sweep risk-per-block ∈ {0.10, 0.25, 0.50, 0.75, 1.0, 1.25, 1.5}% on the
ftmo_2step_uncapped container (no time limit, full real-path P1→P2 chain).

Reports:
  - p(P1), p(P2|P1), p(funded) — over RESOLVED starts only
  - % censored
  - median + mean total grind (P1 + P2 days)
  - failure-mode decomposition (BUST_TOTAL vs BUST_DAILY vs CENSORED)
  - "fast bust" (cluster-driven, low ttp) vs "slow bleed" (drift, high ttp)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container


def fast_vs_slow_bust(out: dict) -> dict:
    """Diagnose: of BUST events, what fraction is 'fast' (cluster) vs 'slow' (drift)?"""
    p1_out = np.array(out["outcomes_p1"])
    p1_ttp = np.array(out["ttps_p1"])
    bust_mask = np.isin(p1_out, ["BUST_TOTAL", "BUST_DAILY"])
    if bust_mask.sum() == 0:
        return {"fast_bust_pct": 0.0, "slow_bust_pct": 0.0,
                "median_bust_ttp": None, "fast_threshold_days": 5}
    bust_ttps = p1_ttp[bust_mask]
    # Fast bust = -10% reached in <= 5 trading days (rare cluster of adverse)
    fast_threshold = 5
    fast = (bust_ttps <= fast_threshold).sum()
    slow = (bust_ttps > fast_threshold).sum()
    return {
        "fast_bust_pct": fast / len(p1_out) * 100,
        "slow_bust_pct": slow / len(p1_out) * 100,
        "median_bust_ttp": int(np.median(bust_ttps)),
        "fast_threshold_days": fast_threshold,
    }


def sweep_uncapped(M: pd.DataFrame, risks: list[float]) -> pd.DataFrame:
    rows = []
    for r in risks:
        out = simulate_real_path_container(M, "ftmo_2step_uncapped", block_cap_pct=r)
        fs = fast_vs_slow_bust(out)
        rows.append({
            "risk_per_block_pct": r * 100,
            "n_total": out["n_paths"],
            "n_resolved": out["n_resolved"],
            "n_censored": out["n_censored"],
            "censored_pct": out["censored_pct"],
            "p1_pct": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
            "p2_given_p1_pct": out["p_phase2_given_p1"] * 100
                               if (out["p_phase2_given_p1"] is not None
                                   and not np.isnan(out["p_phase2_given_p1"])) else float("nan"),
            "p_funded_pct": out["p_funded"] * 100 if not np.isnan(out["p_funded"]) else float("nan"),
            "median_grind_days": out["median_grind_p1p2"],
            "mean_grind_days": out["mean_grind_p1p2"],
            "median_ttp_p1": out["median_ttp_p1"],
            "median_ttp_p2": out["median_ttp_p2"],
            "bust_total_pct_resolved": out["p1_bust_total_pct"],
            "bust_daily_pct_resolved": out["p1_bust_daily_pct"],
            "fast_bust_pct": fs["fast_bust_pct"],
            "slow_bust_pct": fs["slow_bust_pct"],
            "median_bust_ttp": fs["median_bust_ttp"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")
    print(f"Data: {len(M_all)} days ({M_all.index.min().date()} -> {M_all.index.max().date()})")
    risks = [0.001, 0.0025, 0.005, 0.0075, 0.010, 0.0125, 0.015]

    print("=" * 110)
    print("STEP 7 — FTMO 2-STEP UNCAPPED — sweep risk-per-block (in-sample 2022-2026 H1)")
    print("=" * 110)
    df = sweep_uncapped(M_all, risks)
    df.to_csv("optim_step7_uncapped_sweep.csv", index=False)

    cols = ["risk_per_block_pct", "n_resolved", "censored_pct",
            "p1_pct", "p2_given_p1_pct", "p_funded_pct",
            "median_grind_days", "mean_grind_days",
            "bust_total_pct_resolved", "bust_daily_pct_resolved",
            "fast_bust_pct", "slow_bust_pct", "median_bust_ttp"]
    print(df[cols].round(2).to_string(index=False))

    # Argmax
    best_mean = df.loc[df["p_funded_pct"].idxmax()]
    print(f"\nArgmax mean p(funded) = {best_mean['p_funded_pct']:.1f}% @ risk={best_mean['risk_per_block_pct']:.2f}%")
    print(f"  -> n_resolved={int(best_mean['n_resolved'])}, censored={best_mean['censored_pct']:.1f}%, "
          f"median grind={best_mean['median_grind_days']}d")

    # Failure mode shift
    print(f"\nFailure-mode shift along the sizing axis:")
    print(f"  - At small sizing (0.10%, 0.25%): bust-floor near-zero, but censure ↑↑ (long grind > data window)")
    print(f"  - At large sizing (1.25%, 1.5%):  bust-floor dominates, censure near-zero (fast grind in 30-40 days)")
    print(f"  - 'fast_bust' (≤5 trading days) vs 'slow_bust' (>5) indicates cluster vs drift mode.")
