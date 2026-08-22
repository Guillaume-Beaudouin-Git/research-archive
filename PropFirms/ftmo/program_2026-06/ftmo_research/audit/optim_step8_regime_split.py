"""
optim_step8_regime_split.py — Decompose p(funded) by regime traversed.

For each sizing, split p(funded) according to whether the actual grind period
[start, start + grind_days] overlaps with the 2023 chop window or not.

Test the hypothesis:
  - Down-sizing protects against fast-cluster bust (transient adverse cluster)
  - Down-sizing AMPLIFIES exposure to drift bust (sustained mu<0 in chop)
  -> "Cluster vs drift" tradeoff that the cap was hiding.

Definition of chop window: 2023-01-01 to 2023-12-31 (the only large chop in the data).
A start "overlaps chop" if the grind interval [start, start + max_grind_observed] crosses 2023.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container


CHOP_START = pd.Timestamp("2023-01-01")
CHOP_END = pd.Timestamp("2023-12-31")


def regime_split(M: pd.DataFrame, container: str, risk: float) -> dict:
    """
    Decompose p(funded) by whether the grind overlaps the 2023 chop window.

    For each start:
      - Determine the grind end position (start + total_grind_days where
        total_grind = p1_ttp + p2_ttp). For CENSORED, use the bound where
        end_of_data was reached.
      - 'chop_overlap' = [start, end] intersects [CHOP_START, CHOP_END]
    """
    out = simulate_real_path_container(M, container, block_cap_pct=risk)
    starts = out["starts"]
    p1_ttp = np.array(out["ttps_p1"])
    p2_ttp = np.array(out["ttps_p2"])
    p1_outcomes = np.array(out["outcomes_p1"])
    p2_outcomes = np.array(out["outcomes_p2"])
    resolved_mask = out["resolved_mask"]

    # For each start, compute total grind days
    # If not PASS in P1: grind = p1_ttp (i.e. time until bust)
    # If PASS in P1 but not PASS in P2: grind = p1_ttp + p2_ttp
    # If both PASS: grind = p1_ttp + p2_ttp (full funded path)
    total_grind = np.where(p1_outcomes == "PASS", p1_ttp + np.where(p2_ttp > 0, p2_ttp, 0), p1_ttp)

    # End date of grind in M's calendar
    start_pos = starts
    end_pos = np.minimum(start_pos + total_grind, len(M) - 1)
    start_dates = M.index[start_pos]
    end_dates = M.index[end_pos]

    # chop overlap = interval [start, end] intersects [CHOP_START, CHOP_END]
    chop_overlap = (start_dates <= CHOP_END) & (end_dates >= CHOP_START)
    if hasattr(chop_overlap, "values"):
        chop_overlap = chop_overlap.values
    chop_overlap = np.asarray(chop_overlap)

    # Filter resolved
    funded_mask = (p1_outcomes == "PASS") & (p2_outcomes == "PASS")

    res = {}
    for tag, mask in [("ALL_RESOLVED", resolved_mask),
                       ("CHOP_OVERLAP", chop_overlap & resolved_mask),
                       ("TRENDING_ONLY", ~chop_overlap & resolved_mask)]:
        n = int(mask.sum())
        if n == 0:
            res[tag] = {"n": 0, "p_funded": float("nan"), "p1": float("nan"),
                         "p2_given_p1": float("nan"),
                         "bust_total_pct": float("nan"),
                         "fast_bust_pct": float("nan"),
                         "slow_bust_pct": float("nan")}
            continue
        funded_n = int((funded_mask & mask).sum())
        p1_pass = int(((p1_outcomes == "PASS") & mask).sum())
        bust_total = int(((p1_outcomes == "BUST_TOTAL") & mask).sum())
        # Fast vs slow bust restricted to this subset
        bust_mask_subset = np.isin(p1_outcomes, ["BUST_TOTAL", "BUST_DAILY"]) & mask
        bust_ttps = p1_ttp[bust_mask_subset]
        fast_bust = int((bust_ttps <= 5).sum())
        slow_bust = int((bust_ttps > 5).sum())
        res[tag] = {
            "n": n,
            "p_funded": funded_n / n * 100,
            "p1": p1_pass / n * 100,
            "p2_given_p1": ((funded_n / p1_pass) * 100) if p1_pass else float("nan"),
            "bust_total_pct": (bust_total / n * 100) if isinstance(bust_total, int) else float("nan"),
            "fast_bust_pct": (fast_bust / n * 100),
            "slow_bust_pct": (slow_bust / n * 100),
            "median_grind": int(np.median(total_grind[mask])) if mask.any() else None,
        }
    return res


if __name__ == "__main__":
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")
    print(f"Data: {len(M_all)} days; chop window = {CHOP_START.date()} to {CHOP_END.date()}")

    risks = [0.0025, 0.005, 0.0075, 0.010, 0.0125, 0.015]
    print("=" * 110)
    print("STEP 8 — REGIME DECOMPOSITION (chop-overlap vs trending-only)")
    print("=" * 110)
    rows = []
    for r in risks:
        res = regime_split(M_all, "ftmo_2step_uncapped", r)
        for tag, d in res.items():
            rows.append({
                "risk_pct": r * 100,
                "regime": tag,
                "n": d["n"],
                "p1_pct": round(d["p1"], 1),
                "p2_given_p1_pct": round(d["p2_given_p1"], 1) if not np.isnan(d["p2_given_p1"]) else None,
                "p_funded_pct": round(d["p_funded"], 1),
                "bust_total_pct": round(d.get("bust_total_pct", float("nan")), 1) if (isinstance(d.get("bust_total_pct"), (int, float, np.floating)) and not np.isnan(d["bust_total_pct"])) else None,
                "fast_bust_pct": round(d["fast_bust_pct"], 1),
                "slow_bust_pct": round(d["slow_bust_pct"], 1),
                "median_grind": d.get("median_grind"),
            })
    df = pd.DataFrame(rows)
    df.to_csv("optim_step8_regime_split.csv", index=False)
    # Pretty pivot
    print("\np_funded by regime:")
    piv = df.pivot(index="risk_pct", columns="regime", values="p_funded_pct")
    print(piv.to_string())
    print("\nfast_bust by regime (cluster mode):")
    piv = df.pivot(index="risk_pct", columns="regime", values="fast_bust_pct")
    print(piv.to_string())
    print("\nslow_bust by regime (drift mode):")
    piv = df.pivot(index="risk_pct", columns="regime", values="slow_bust_pct")
    print(piv.to_string())
    print("\nmedian grind by regime:")
    piv = df.pivot(index="risk_pct", columns="regime", values="median_grind")
    print(piv.to_string())
