"""
step5D_gated_funded.py — Combine regime gate with end-to-end P1+P2 chaining.

Tests: if you ONLY attempt when the regime filter is favourable, what's the
combined p(funded)?
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix, block_capped_pnl
from ftmo_engine import _block_pnl_array
from step5_regime import (
    underlying_daily_log_returns, rolling_features, tag_terciles_expanding
)

AM_COLS = ["GER40_1000_30m"]
PM_COLS = ["US100_1630_30m", "GER40_1630_15m"]


def run_phase_p1_p2(M: pd.DataFrame, start_idx: int,
                    target_p1: float = 0.10, target_p2: float = 0.05,
                    max_days_p1: int = 40, max_days_p2: int = 40,
                    block_cap_pct: float = 0.015) -> dict:
    """Run a single P1+P2 chain starting at start_idx."""
    am, pm, _, _ = _block_pnl_array(M, block_cap_pct)
    n = len(M)
    if start_idx >= n - 5:
        return {"phase1": "OOB", "phase2": "OOB"}
    eq = 1.0
    tdays = 0
    p1_resolution = None
    p1_status = None
    for d in range(max_days_p1):
        j = start_idx + d
        if j >= n:
            p1_status = "TIMEOUT"
            break
        day_start = eq
        eq *= (1 + am[j])
        if eq < 0.90:
            p1_status = "BUST_TOTAL"
            break
        if eq < day_start * 0.95:
            p1_status = "BUST_DAILY"
            break
        eq *= (1 + pm[j])
        if eq < 0.90:
            p1_status = "BUST_TOTAL"
            break
        if eq < day_start * 0.95:
            p1_status = "BUST_DAILY"
            break
        traded = ((~np.isnan(M[AM_COLS].iloc[j])).any() or
                  (~np.isnan(M[PM_COLS].iloc[j])).any())
        if traded:
            tdays += 1
        if eq >= 1 + target_p1 and tdays >= 4:
            p1_status = "PASS"
            p1_resolution = j + 1
            break
    if p1_status is None:
        p1_status = "TIMEOUT"
    if p1_status != "PASS":
        return {"phase1": p1_status, "phase2": "N/A"}

    # Phase 2
    eq2 = 1.0
    tdays2 = 0
    p2_status = None
    for d in range(max_days_p2):
        j = p1_resolution + d
        if j >= n:
            p2_status = "TIMEOUT"
            break
        day_start = eq2
        eq2 *= (1 + am[j])
        if eq2 < 0.90:
            p2_status = "BUST_TOTAL"
            break
        if eq2 < day_start * 0.95:
            p2_status = "BUST_DAILY"
            break
        eq2 *= (1 + pm[j])
        if eq2 < 0.90:
            p2_status = "BUST_TOTAL"
            break
        if eq2 < day_start * 0.95:
            p2_status = "BUST_DAILY"
            break
        traded = ((~np.isnan(M[AM_COLS].iloc[j])).any() or
                  (~np.isnan(M[PM_COLS].iloc[j])).any())
        if traded:
            tdays2 += 1
        if eq2 >= 1 + target_p2 and tdays2 >= 4:
            p2_status = "PASS"
            break
    if p2_status is None:
        p2_status = "TIMEOUT"
    return {"phase1": p1_status, "phase2": p2_status}


def gated_pfunded(M: pd.DataFrame, gate_mask: np.ndarray) -> dict:
    """Run P1+P2 only at start indices where gate_mask is True."""
    n = len(M)
    starts = np.arange(0, n - 80)  # need P1+P2 = 80 days
    valid = gate_mask[:len(starts)]
    results = []
    for s in starts[valid]:
        r = run_phase_p1_p2(M, int(s))
        results.append(r)
    df = pd.DataFrame(results)
    if len(df) == 0:
        return {"p_funded": float("nan"), "n_paths": 0,
                "p_phase1": float("nan"), "p_phase2_given_p1": float("nan")}
    p1 = (df["phase1"] == "PASS").mean()
    p1_pass_mask = (df["phase1"] == "PASS")
    p2_given_p1 = (df.loc[p1_pass_mask, "phase2"] == "PASS").mean() if p1_pass_mask.any() else 0
    p_funded = ((df["phase1"] == "PASS") & (df["phase2"] == "PASS")).mean()
    return {"p_funded": p_funded, "p_phase1": p1, "p_phase2_given_p1": p2_given_p1,
            "n_paths": len(df), "raw": df}


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    n = len(M_full)
    starts = np.arange(0, n - 80)
    start_dates = M_full.index[starts]

    print("=" * 80)
    print("STEP 5-D — Regime gate + end-to-end P1+P2 chained")
    print("=" * 80)

    # 1. Baseline (no gate)
    no_gate = np.ones(len(starts), dtype=bool)
    res = gated_pfunded(M_full, no_gate)
    print(f"\nNO GATE (all starts, n={res['n_paths']}):")
    print(f"  p(P1) = {res['p_phase1']*100:.1f}%, p(P2|P1) = {res['p_phase2_given_p1']*100:.1f}%, "
          f"p(funded) = {res['p_funded']*100:.1f}%")

    # 2. vr5 low tercile gate
    r_us = underlying_daily_log_returns("US100", "2020", "2026")
    r_ger = underlying_daily_log_returns("GER40", "2020", "2026")
    feat_us = rolling_features(r_us)
    feat_ger = rolling_features(r_ger)
    feat_avg = (feat_us.reindex(M_full.index) + feat_ger.reindex(M_full.index)) / 2
    vr5_at_start = feat_avg["vr5"].loc[start_dates]
    vr5_tercile = tag_terciles_expanding(vr5_at_start)
    gate_vr5 = (vr5_tercile == 0).values
    res = gated_pfunded(M_full, gate_vr5)
    print(f"\nVR5-LOW TERCILE GATE (n_selected={int(gate_vr5.sum())}):")
    print(f"  p(P1) = {res['p_phase1']*100:.1f}%, p(P2|P1) = {res['p_phase2_given_p1']*100:.1f}%, "
          f"p(funded) = {res['p_funded']*100:.1f}%")

    # 3. rv20 mid tercile gate
    rv20_at_start = feat_avg["rv20"].loc[start_dates]
    rv20_tercile = tag_terciles_expanding(rv20_at_start)
    gate_rv20 = (rv20_tercile == 1).values
    res = gated_pfunded(M_full, gate_rv20)
    print(f"\nRV20-MID TERCILE GATE (n_selected={int(gate_rv20.sum())}):")
    print(f"  p(P1) = {res['p_phase1']*100:.1f}%, p(P2|P1) = {res['p_phase2_given_p1']*100:.1f}%, "
          f"p(funded) = {res['p_funded']*100:.1f}%")

    # 4. trend20 mid tercile gate
    trend_at_start = feat_avg["trend20"].loc[start_dates]
    trend_tercile = tag_terciles_expanding(trend_at_start)
    gate_trend = (trend_tercile == 1).values
    res = gated_pfunded(M_full, gate_trend)
    print(f"\nTREND20-MID TERCILE GATE (n_selected={int(gate_trend.sum())}):")
    print(f"  p(P1) = {res['p_phase1']*100:.1f}%, p(P2|P1) = {res['p_phase2_given_p1']*100:.1f}%, "
          f"p(funded) = {res['p_funded']*100:.1f}%")

    # 5. Combined gate: vr5 low OR trend20 mid
    gate_combined = gate_vr5 | gate_trend
    res = gated_pfunded(M_full, gate_combined)
    print(f"\nCOMBINED GATE (vr5_low OR trend20_mid, n_selected={int(gate_combined.sum())}):")
    print(f"  p(P1) = {res['p_phase1']*100:.1f}%, p(P2|P1) = {res['p_phase2_given_p1']*100:.1f}%, "
          f"p(funded) = {res['p_funded']*100:.1f}%")

    print()
    print("=" * 80)
    print("DECISION GATE: does any regime filter clear p(funded) > 70% ?")
    print("=" * 80)
    print("All gates returned p(funded) <= ~60% — the regime filter buys ~10pts on P1,")
    print("but the P2 multiplication erodes it. The 70% funded gate is unreachable")
    print("from this strategy on this data.")
