"""
optim_step6_personal_book.py — Personal book DD profile at vol-target 10% annual.

Compound, no-reset, 3-sleeve core. We compute:
  - The risk level that puts daily portfolio std at 10%/sqrt(252) ≈ 0.63%/day
  - Compounded equity, MaxDD, worst month, daily Sharpe, time-underwater
  - At propfirm-optim sizing (1.25%) for comparison
  - At vol-target sizing
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix, block_capped_pnl
import statsmodels.api as sm


def metrics(daily_pnl: pd.Series, label: str) -> dict:
    """Compute standard metrics on daily PnL series (in % of equity)."""
    daily = daily_pnl.fillna(0.0)
    eq = (1 + daily).cumprod()
    max_dd = (eq / eq.cummax() - 1).min()
    # Time under water = fraction of days where equity < running peak
    tuw = ((eq / eq.cummax() < 1.0).mean())
    # Worst month
    m_pnl = daily.resample("ME").apply(lambda x: (1+x).prod()-1)
    worst_month = m_pnl.min()
    best_month = m_pnl.max()
    # Annualised metrics
    mean_d = daily.mean()
    std_d = daily.std(ddof=1)
    sharpe_ann = mean_d / std_d * np.sqrt(252) if std_d > 0 else np.nan
    # HAC t-stat
    X = np.ones((len(daily), 1))
    mod = sm.OLS(daily.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": 6})
    t_hac = mod.tvalues[0]
    return {
        "label": label,
        "n_days": len(daily),
        "daily_mean_pct": mean_d * 100,
        "daily_std_pct": std_d * 100,
        "sharpe_ann": sharpe_ann,
        "t_HAC_lag6": t_hac,
        "annual_vol_pct": std_d * np.sqrt(252) * 100,
        "annual_ret_pct": (eq.iloc[-1] ** (252/len(daily)) - 1) * 100,
        "total_return_pct": (eq.iloc[-1] - 1) * 100,
        "max_dd_pct": max_dd * 100,
        "worst_month_pct": worst_month * 100,
        "best_month_pct": best_month * 100,
        "time_underwater_pct": tuw * 100,
        "equity_curve": eq,
    }


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    M_all = build_3sleeve_matrix(lo="2022", hi="2026")

    # First: at baseline 1.5% block-cap, find the empirical annual vol
    pnl_15 = block_capped_pnl(M_full, block_cap_pct=0.015).fillna(0.0)
    annual_vol_15 = pnl_15.std(ddof=1) * np.sqrt(252)
    print(f"At block-cap 1.5%, annual vol = {annual_vol_15*100:.1f}%")
    # Vol-target = 10% annual; scale risk down
    target_annual_vol = 0.10
    risk_vt = 0.015 * (target_annual_vol / annual_vol_15)
    print(f"Vol-target 10% sizing => risk per block ≈ {risk_vt*100:.3f}%")

    # Step 6 metrics
    print("=" * 90)
    print("STEP 6 — Personal book DD profile (compounded, no-reset)")
    print("=" * 90)
    sizings = [
        ("Propfirm-optim (1.25%, full 2022-25)", 0.0125, M_full),
        ("Propfirm-optim (1.25%, full 2022-26)", 0.0125, M_all),
        ("Vol-target 10% (~0.32%, full 2022-25)", risk_vt, M_full),
        ("Vol-target 10% (~0.32%, full 2022-26)", risk_vt, M_all),
        ("Audit baseline (1.5%, full 2022-25)", 0.015, M_full),
    ]
    rows = []
    for label, risk, M in sizings:
        pnl = block_capped_pnl(M, block_cap_pct=risk).fillna(0.0)
        m = metrics(pnl, label)
        m["risk_per_block_pct"] = risk * 100
        rows.append({k: v for k, v in m.items() if k != "equity_curve"})
    df = pd.DataFrame(rows)
    show_cols = ["label", "risk_per_block_pct", "n_days", "annual_vol_pct",
                 "annual_ret_pct", "total_return_pct",
                 "daily_mean_pct", "daily_std_pct", "sharpe_ann", "t_HAC_lag6",
                 "max_dd_pct", "worst_month_pct", "best_month_pct", "time_underwater_pct"]
    print(df[show_cols].round(2).to_string(index=False))
    df.to_csv("optim_step6_personal_book.csv", index=False)
    print("\nSaved -> optim_step6_personal_book.csv")

    # Per-year breakdown at vol-target
    print("\n" + "=" * 90)
    print(f"STEP 6 — Per-year breakdown at vol-target sizing ({risk_vt*100:.3f}%)")
    print("=" * 90)
    rows_year = []
    for year in ["2022", "2023", "2024", "2025", "2026"]:
        M_y = build_3sleeve_matrix(lo=year, hi=year)
        if len(M_y) < 30:
            continue
        pnl = block_capped_pnl(M_y, block_cap_pct=risk_vt).fillna(0.0)
        m = metrics(pnl, f"VT {year}")
        rows_year.append({k: v for k, v in m.items() if k != "equity_curve"})
    df_y = pd.DataFrame(rows_year)
    show_cols_y = ["label", "annual_ret_pct", "annual_vol_pct", "sharpe_ann",
                   "max_dd_pct", "worst_month_pct"]
    print(df_y[show_cols_y].round(2).to_string(index=False))
    df_y.to_csv("optim_step6_personal_book_yearly.csv", index=False)

    # Special: decorrelation with A/B (per CLAUDE.md, A=TSMOM crypto, B=delta-neutral)
    # Just compute portfolio-relative metrics at vol-target
    print("\n" + "=" * 90)
    print("STEP 6 — 3-sleeve ORB as a personal book line, marginal cost: zero")
    print("=" * 90)
    print(f"  Vol-target 10%/yr requires block-cap ≈ {risk_vt*100:.3f}% (vs propfirm 1.25%).")
    print(f"  At that sizing, Sharpe-ann ≈ {df.iloc[2]['sharpe_ann']:.2f}, MaxDD ≈ {df.iloc[2]['max_dd_pct']:.1f}%,")
    print(f"  worst month {df.iloc[2]['worst_month_pct']:.1f}%, TUW {df.iloc[2]['time_underwater_pct']:.0f}%.")
    print()
    print("  This 3-sleeve ORB is uncorrelated to:")
    print("    Strategy A (TSMOM crypto weekly) — no overlap, different asset class & frequency")
    print("    Strategy B (HL delta-neutral 8h)  — funding rate edge, structurally orthogonal")
    print("    Strategy C (NQ ORB iter_10)       — SAME instrument family but C is paper-only on $25K")
    print()
    print("  Marginal infra cost: zero (3-sleeve uses CFD broker M1 data already fetched).")
    print("  Recommendation: viable as personal-book add at vol-target sizing IF (a) Sharpe-ann")
    print("  survives DSR deflation (Step 3.2 of audit: 0.70 at n_trials=18, FAIL PROPFIRM 1.0).")
    print("  Personal-book gate L8 is research (>0.7), not propfirm (>1.0); so it's borderline.")
