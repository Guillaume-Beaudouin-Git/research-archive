"""
killer4_drift_decomp.py — Explicit decomposition: reversion P&L vs relative drift P&L.

Test: BTC/ETH "reversion" — is it real or just harvested relative drift over the
Park window? Decompose P&L into:
  - reversion component (returns to mean)
  - drift component (BTC over/underperforms ETH structurally)
"""
import numpy as np
import pandas as pd
from pathlib import Path
from validation_D import load_1h_aligned, split_window, kalman_dynamic_beta, OUT

WINDOWS = [
    ("FULL 2018-2026", "2018-01-01", "2026-06-01"),
    ("PRE-Park 2018-2021", "2018-01-01", "2021-12-31"),
    ("PARK Jan2022-Oct2024", "2022-01-01", "2024-10-31"),
    ("POST-Park Nov2024+", "2024-11-01", "2026-06-01"),
]


def decompose_drift(sub: pd.DataFrame):
    """For each window, compute:
       - cumulative log(BTC) - β × log(ETH) trajectory (= spread)
       - mean spread
       - net change in spread over window (= drift, persistent component)
       - oscillation amplitude (std of spread - drift)
    """
    logA = np.log(sub["BTC"].values)
    logB = np.log(sub["ETH"].values)
    # Use Kalman dynamic beta for fair comparison with backtest
    alphas, betas, spreads = kalman_dynamic_beta(logA, logB)
    # Also use static OLS beta (paper convention often)
    X = np.vstack([np.ones(len(logB)), logB]).T
    coef, *_ = np.linalg.lstsq(X, logA, rcond=None)
    spread_static = logA - X @ coef
    # Drift: linear trend over the window
    t = np.arange(len(spread_static))
    slope = np.polyfit(t, spread_static, 1)[0]
    drift_total = slope * len(spread_static)
    # Total displacement: spread end - spread start
    delta_spread = spread_static[-1] - spread_static[0]
    # Mean absolute deviation around mean = oscillation strength
    osc_amp = np.std(spread_static)
    # Relative BTC vs ETH return over window
    ret_A = (np.exp(logA[-1] - logA[0]) - 1) * 100
    ret_B = (np.exp(logB[-1] - logB[0]) - 1) * 100
    # Ratio test: spread positive drift = BTC outperformed in log terms
    return {
        "n": len(sub),
        "ret_BTC_pct": ret_A,
        "ret_ETH_pct": ret_B,
        "ret_diff_pct": ret_A - ret_B,
        "spread_start": spread_static[0],
        "spread_end": spread_static[-1],
        "spread_delta": delta_spread,
        "spread_drift_linear": drift_total,
        "spread_osc_amp": osc_amp,
        "static_beta": coef[1],
        "kalman_beta_start": betas[0],
        "kalman_beta_end": betas[-1],
        "kalman_beta_change": betas[-1] - betas[0],
    }


if __name__ == "__main__":
    print("=" * 95)
    print("KILLER 4 — Décomposition réversion vs drift relatif BTC/ETH")
    print("=" * 95)
    df_1h = load_1h_aligned()
    rows = []
    for label, lo, hi in WINDOWS:
        sub = split_window(df_1h, lo, hi)
        if len(sub) < 1000:
            continue
        res = decompose_drift(sub)
        res["label"] = label
        rows.append(res)
        print(f"\n--- {label} (n={res['n']}) ---")
        print(f"  BTC return: {res['ret_BTC_pct']:+.1f}%, ETH return: {res['ret_ETH_pct']:+.1f}%")
        print(f"  Relative diff (BTC - ETH): {res['ret_diff_pct']:+.1f}pts")
        print(f"  Static OLS beta: {res['static_beta']:.3f}")
        print(f"  Kalman beta: {res['kalman_beta_start']:.3f} → {res['kalman_beta_end']:.3f} "
              f"(Δ = {res['kalman_beta_change']:+.3f})")
        print(f"  Spread (static OLS) start: {res['spread_start']:+.4f}, end: {res['spread_end']:+.4f}")
        print(f"  Spread total delta: {res['spread_delta']:+.4f}")
        print(f"  Spread linear drift: {res['spread_drift_linear']:+.4f}")
        print(f"  Spread oscillation amplitude (std): {res['spread_osc_amp']:.4f}")
        # Verdict
        drift_vs_osc = abs(res['spread_drift_linear']) / max(res['spread_osc_amp'], 1e-6)
        if drift_vs_osc > 1.0:
            print(f"  → drift/osc ratio = {drift_vs_osc:.2f} > 1.0 → DRIFT DOMINANT (= harvested beta, not reversion)")
        else:
            print(f"  → drift/osc ratio = {drift_vs_osc:.2f} ≤ 1.0 → reversion dominant")

    df_out = pd.DataFrame(rows)
    df_out.to_csv(OUT / "killer4_drift_decomp.csv", index=False)
    print()
    print("=" * 95)
    print("Verdict Killer 4")
    print("=" * 95)
    print("\nIf the Park window has dominant drift (BTC overperformed/underperformed ETH"
          " structurally),\nthen the '2.23 Sharpe' was actually a beta harvest in market-neutral costume,"
          "\nnot real mean reversion. Look at the ret_diff_pct + spread_delta over the Park window.")
