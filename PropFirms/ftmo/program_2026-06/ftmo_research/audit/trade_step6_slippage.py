"""
trade_step6_slippage.py — Stress F1 filter under 2x and 3x slippage.

The audit found slippage 0.10R = -15pt p_funded baseline. Does the F1 filter
improvement survive heavier slippage? If F1 only works when execution is perfect,
it's not viable live.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix
from optim_engine import simulate_real_path_container
from trade_features import extract_all_trades
from trade_step3b_wf import trades_to_M_matrix


def stress_slippage(slip_R: float = 0.0, quantile: float = 0.5,
                     risks: list[float] = None) -> pd.DataFrame:
    """Build trade dataset with slip_R adverse slippage, apply F1, evaluate p_funded."""
    if risks is None:
        risks = [0.005, 0.0075, 0.010, 0.0125]
    df = extract_all_trades(lo="2022", hi="2025", slip_R=slip_R)
    # baseline build_3sleeve_matrix with slip
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025", slip_R=slip_R)

    threshold = df["time_to_break_5min"].quantile(quantile)
    keep = df["time_to_break_5min"] <= threshold
    df_filt = df[keep]
    M_filt = trades_to_M_matrix(df_filt).reindex(M_baseline.index)

    rows = []
    for r in risks:
        out_b = simulate_real_path_container(M_baseline, "ftmo_2step_uncapped", block_cap_pct=r)
        out_f = simulate_real_path_container(M_filt, "ftmo_2step_uncapped", block_cap_pct=r)
        rows.append({
            "slip_R": slip_R, "risk_pct": r * 100,
            "n_trades_baseline": len(df), "n_trades_filtered": len(df_filt),
            "mean_R_baseline": df["r_realised"].mean(),
            "mean_R_filtered": df_filt["r_realised"].mean(),
            "p_funded_baseline_pct": out_b["p_funded"] * 100 if not np.isnan(out_b["p_funded"]) else float("nan"),
            "p_funded_filtered_pct": out_f["p_funded"] * 100 if not np.isnan(out_f["p_funded"]) else float("nan"),
            "delta_pt": (out_f["p_funded"] - out_b["p_funded"]) * 100 if (not np.isnan(out_b["p_funded"]) and not np.isnan(out_f["p_funded"])) else float("nan"),
            "cens_baseline_pct": out_b["censored_pct"],
            "cens_filtered_pct": out_f["censored_pct"],
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("=" * 110)
    print("STEP 6 — Slippage stress on F1 filter (in-sample threshold, 2022-2025)")
    print("=" * 110)
    all_rows = []
    # Note: slip_R is per-R fraction. Baseline backtest = 0.
    # Audit §3.3: slip 0.10R is realistic. So 2× ≈ 0.10R, 3× ≈ 0.15R.
    for slip in [0.00, 0.05, 0.10, 0.15]:
        print(f"\nSlippage slip_R = {slip:.2f} ({'baseline' if slip==0 else f'~{int(slip/0.05)}× audit baseline-spec slip'})")
        df = stress_slippage(slip_R=slip)
        cols = ["risk_pct", "n_trades_baseline", "n_trades_filtered",
                 "mean_R_baseline", "mean_R_filtered",
                 "p_funded_baseline_pct", "p_funded_filtered_pct", "delta_pt"]
        print(df[cols].round(2).to_string(index=False))
        df["slip_R"] = slip
        all_rows.append(df)
    full = pd.concat(all_rows, ignore_index=True)
    full.to_csv("trade_step6_slippage.csv", index=False)
