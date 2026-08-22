"""
f1_check3_dsr.py — Deflated Sharpe Ratio Bailey-LdP on F1-filtered strategy.

The Sharpe boost is large (×4.2 mean R). Could it survive deflation given the
search budget? We test multiple n_trials scenarios:

  - n_trials_microstructure = 15 features × 4 cutoff variants = 60
  - n_trials_total = 60 (microstructure) + 18 (prior families per CHALLENGE_REPORT) = 78
  - n_trials_pessimistic = 200 (cover sleeves × directions × interactions search)
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from scipy.stats import norm
from orb_core import build_3sleeve_matrix


# Block-cap engine for daily PnL (same as audit step6 personal book)
AM_COLS = ["GER40_1000_30m"]
PM_COLS = ["US100_1630_30m", "GER40_1630_15m"]


def block_capped_pnl(M: pd.DataFrame, block_cap_pct: float = 0.005) -> pd.Series:
    am = M[AM_COLS].fillna(0.0).sum(axis=1) * block_cap_pct
    pm_risk = block_cap_pct / len(PM_COLS)
    pm = (M[PM_COLS].fillna(0.0) * pm_risk).sum(axis=1)
    return (am + pm).fillna(0.0)


def deflated_sharpe(sr_obs: float, t_obs_days: int, n_trials: int,
                    skew: float, kurt: float) -> dict:
    """Bailey-Lopez de Prado (2014) DSR.

    sr_obs : observed annualised Sharpe
    t_obs_days : sample length in days
    n_trials : number of strategies tried (multiple testing)
    skew, kurt : sample skew and excess kurtosis
    """
    # Expected max of N iid standard normals
    gamma = 0.5772
    e = np.e
    EmaxN = ((1 - gamma) * norm.ppf(1 - 1/n_trials)
             + gamma * norm.ppf(1 - 1/(n_trials * e)))
    # Convert annualised SR to daily for variance
    sr_daily = sr_obs / np.sqrt(252)
    var_sr_daily = (1 - skew * sr_daily + (kurt - 1) / 4 * sr_daily ** 2) / (t_obs_days - 1)
    if var_sr_daily <= 0:
        return {"sr_obs": sr_obs, "sr0": float("nan"), "sr_deflated": float("nan"),
                "z": float("nan"), "dsr_p_real": float("nan"), "EmaxN": EmaxN,
                "n_trials": n_trials}
    sr0_daily = np.sqrt(var_sr_daily) * EmaxN
    sr0_ann = sr0_daily * np.sqrt(252)
    denom_ann = np.sqrt(var_sr_daily) * np.sqrt(252)
    z = (sr_obs - sr0_ann) / denom_ann if denom_ann > 0 else float("nan")
    dsr = float(norm.cdf(z)) if not np.isnan(z) else float("nan")
    return {"sr_obs": sr_obs, "sr0_threshold_ann": sr0_ann,
            "sr_deflated": sr_obs - sr0_ann,
            "z": z, "dsr_p_real": dsr, "EmaxN": EmaxN,
            "var_sr_daily": var_sr_daily,
            "n_trials": n_trials}


def trades_to_M_matrix(trades_df: pd.DataFrame) -> pd.DataFrame:
    pivot = trades_df.pivot_table(values="r_realised", index=trades_df.index,
                                    columns="sleeve", aggfunc="first")
    cols = ["GER40_1000_30m", "US100_1630_30m", "GER40_1630_15m"]
    for c in cols:
        if c not in pivot.columns:
            pivot[c] = np.nan
    return pivot[cols]


if __name__ == "__main__":
    df = pd.read_parquet("trade_dataset.parquet")
    M_baseline = build_3sleeve_matrix(lo="2022", hi="2025")
    threshold = df["time_to_break_5min"].quantile(0.5)
    keep = df["time_to_break_5min"] <= threshold
    df_F1 = df[keep]
    M_F1 = trades_to_M_matrix(df_F1).reindex(M_baseline.index)

    # Compute daily PnL series
    pnl_base = block_capped_pnl(M_baseline, block_cap_pct=0.005)
    pnl_F1 = block_capped_pnl(M_F1, block_cap_pct=0.005)

    # Stats
    def stats(pnl, label):
        n = len(pnl)
        mean_d = pnl.mean()
        std_d = pnl.std(ddof=1)
        sr_ann = mean_d / std_d * np.sqrt(252) if std_d > 0 else 0
        skew = pnl.skew()
        kurt = pnl.kurt()  # pandas excess kurtosis
        return {"label": label, "n_days": n, "mean_d": mean_d, "std_d": std_d,
                "sr_ann": sr_ann, "skew": skew, "kurt": kurt}

    base_stats = stats(pnl_base, "BASELINE")
    f1_stats = stats(pnl_F1, "F1")

    print("=" * 90)
    print("CHECK 3 — DSR Bailey-LdP on F1 filtered strategy")
    print("=" * 90)
    print(f"\nBASELINE (no filter): n={base_stats['n_days']} days, "
          f"Sharpe_ann={base_stats['sr_ann']:.3f}, skew={base_stats['skew']:.2f}, "
          f"kurt={base_stats['kurt']:.2f}")
    print(f"F1 (ttb ≤ med):      n={f1_stats['n_days']} days, "
          f"Sharpe_ann={f1_stats['sr_ann']:.3f}, skew={f1_stats['skew']:.2f}, "
          f"kurt={f1_stats['kurt']:.2f}")
    print()

    print("=" * 90)
    print("DSR scenarios (varying n_trials to reflect search budget)")
    print("=" * 90)
    scenarios = [
        ("Just-F1 (1 trial)", 1),
        ("Microstructure-only", 15 * 4),
        ("Microstructure + 18 prior families", 15 * 4 + 18),
        ("Pessimistic (cover sleeves × directions × interactions)", 200),
        ("Very pessimistic", 500),
    ]
    print(f"\n{'Scenario':<55} {'n_trials':>9} {'SR0 thr':>9} {'SR_def':>8} {'z':>6} {'P(real)':>8}")
    for desc, n_trials in scenarios:
        d = deflated_sharpe(f1_stats["sr_ann"], f1_stats["n_days"], n_trials,
                             f1_stats["skew"], f1_stats["kurt"])
        print(f"{desc:<55} {n_trials:>9} {d['sr0_threshold_ann']:>9.3f} "
              f"{d['sr_deflated']:>8.3f} {d['z']:>6.2f} {d['dsr_p_real']:>8.3f}")
    print()

    # Same for baseline for comparison
    print("--- Baseline DSR (no filter) ---")
    for desc, n_trials in [("Baseline 18 families", 18),
                            ("Baseline 78 (incl micro)", 78)]:
        d = deflated_sharpe(base_stats["sr_ann"], base_stats["n_days"], n_trials,
                             base_stats["skew"], base_stats["kurt"])
        print(f"{desc:<55} {n_trials:>9} {d['sr0_threshold_ann']:>9.3f} "
              f"{d['sr_deflated']:>8.3f} {d['z']:>6.2f} {d['dsr_p_real']:>8.3f}")
    print()

    # Verdict
    d_real = deflated_sharpe(f1_stats["sr_ann"], f1_stats["n_days"], 78,
                              f1_stats["skew"], f1_stats["kurt"])
    print("=" * 90)
    print("CHECK 3 — VERDICT")
    print("=" * 90)
    print(f"\nF1 raw Sharpe_ann = {f1_stats['sr_ann']:.3f}")
    print(f"F1 deflated (n_trials=78) = {d_real['sr_deflated']:.3f}")
    print(f"F1 deflated (n_trials=200) = {deflated_sharpe(f1_stats['sr_ann'], f1_stats['n_days'], 200, f1_stats['skew'], f1_stats['kurt'])['sr_deflated']:.3f}")
    print(f"F1 deflated (n_trials=500) = {deflated_sharpe(f1_stats['sr_ann'], f1_stats['n_days'], 500, f1_stats['skew'], f1_stats['kurt'])['sr_deflated']:.3f}")
    if d_real["sr_deflated"] >= 1.0:
        print(f"\n✓ F1 SURVIVES DSR at n_trials=78 (deflated SR ≥ 1.0, PROPFIRM gate)")
    else:
        print(f"\n⚠ F1 DEFLATED < 1.0 at n_trials=78 — propfirm gate not cleared")
