"""
step1_full_vs_2026.py — Full-sample vs 2026 cherry-pick comparison.

Computes for each period:
  - daily Sharpe annualised (HAC lag-6 t-stat on excess returns)
  - per-trade expectancy (mean R)
  - profit factor
  - skew, kurtosis
  - MaxDD on compounded equity
  - worst calendar month
  - n_trades, n_days
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.api as sm
from orb_core import build_3sleeve_matrix, block_capped_pnl, SLEEVE_NAMES


def hac_tstat(returns: np.ndarray, lags: int = 6) -> tuple[float, float]:
    """Mean & HAC t-stat (Newey-West) on a return series vs 0."""
    r = returns[~np.isnan(returns)]
    if len(r) < lags + 2:
        return float("nan"), float("nan")
    X = np.ones((len(r), 1))
    mod = sm.OLS(r, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(mod.params[0]), float(mod.tvalues[0])


def metrics_period(M_full: pd.DataFrame, lo: str, hi: str,
                   block_cap_pct: float = 0.015) -> dict:
    M = M_full.loc[lo:hi]
    pnl = block_capped_pnl(M, block_cap_pct=block_cap_pct)
    # Treat empty days as 0% (no trade) -> include in daily series
    daily = pnl.fillna(0.0).values
    # Per-trade (pooled across sleeves) — for expectancy / PF / skew
    trades = M.values.flatten()
    trades = trades[~np.isnan(trades)]

    # HAC stats on daily
    mean_d, t_d = hac_tstat(daily, lags=6)
    std_d = daily.std(ddof=1)
    sharpe_ann = mean_d / std_d * np.sqrt(252) if std_d > 0 else np.nan

    # Per-trade stats
    mean_R = trades.mean()
    wins = trades[trades > 0]
    losses = trades[trades < 0]
    pf = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.nan
    skew = pd.Series(trades).skew()
    kurt = pd.Series(trades).kurt()
    win_rate = (trades > 0).mean()
    avg_win = wins.mean() if len(wins) else np.nan
    avg_loss = losses.mean() if len(losses) else np.nan

    # MaxDD on cumulative compounded equity
    eq = (1 + pd.Series(daily, index=pnl.index)).cumprod()
    dd = (eq / eq.cummax() - 1).min()

    # Worst month
    m_pnl = pnl.fillna(0.0).resample("ME").apply(lambda x: (1+x).prod()-1)
    worst_month = m_pnl.min() if len(m_pnl) else np.nan

    return {
        "n_days": len(M),
        "n_trades": len(trades),
        "trades_per_day": M.notna().sum(axis=1).mean(),
        "mean_R": mean_R,
        "win_rate": win_rate,
        "avg_win_R": avg_win,
        "avg_loss_R": avg_loss,
        "profit_factor": pf,
        "skew": skew,
        "kurtosis": kurt,
        "daily_mean_pct": mean_d * 100,
        "daily_std_pct": std_d * 100,
        "sharpe_ann": sharpe_ann,
        "t_HAC_lag6": t_d,
        "max_dd": dd,
        "worst_month": worst_month,
        "total_return": (eq.iloc[-1] - 1) if len(eq) else np.nan,
    }


if __name__ == "__main__":
    M = build_3sleeve_matrix(lo="2021", hi="2026")
    periods = [
        ("2021-2022", "2021", "2022"),
        ("2023 chop", "2023", "2023"),
        ("2024-2025", "2024", "2025"),
        ("Full 2022-2025", "2022", "2025"),
        ("All 2021-2026", "2021", "2026"),
        ("2026 ONLY (cherry)", "2026", "2026"),
    ]
    rows = []
    for lab, lo, hi in periods:
        m = metrics_period(M, lo, hi)
        m["period"] = lab
        rows.append(m)
    df = pd.DataFrame(rows).set_index("period")

    print("=" * 90)
    print("STEP 1 — Full-sample vs 2026 cherry-pick (3-sleeve core, block-cap 1.5%)")
    print("=" * 90)
    cols_to_show = ["n_trades", "trades_per_day", "mean_R", "win_rate",
                    "avg_win_R", "avg_loss_R", "profit_factor", "skew", "kurtosis",
                    "daily_mean_pct", "daily_std_pct",
                    "sharpe_ann", "t_HAC_lag6", "max_dd", "worst_month",
                    "total_return"]
    print(df[cols_to_show].round(3).T.to_string())
    print()
    print("Headline check vs report §6.4 (which is 2026 only):")
    r = df.loc["2026 ONLY (cherry)"]
    print(f"  Report says: Trades 308, WR 44%, Expectancy +0.106R, PF 1.20, Skew +2.2, "
          f"Sharpe 1.62, MaxDD -8.2%, Worst day -3.27%, Best day +10.47%, Total +28.9%")
    print(f"  Audit 2026:  Trades {int(r['n_trades'])}, WR {r['win_rate']*100:.0f}%, "
          f"Expectancy {r['mean_R']:+.3f}R, PF {r['profit_factor']:.2f}, "
          f"Skew {r['skew']:+.2f}, Sharpe {r['sharpe_ann']:.2f}, "
          f"MaxDD {r['max_dd']*100:.1f}%, Total {r['total_return']*100:+.1f}%")
    print()
    print("Headline check vs report §6.4 cross-régime claim (\"~+0.05R 2022-25\"):")
    r2 = df.loc["Full 2022-2025"]
    print(f"  Report says: Expectancy ~+0.05R")
    print(f"  Audit:       Expectancy {r2['mean_R']:+.3f}R")
    print()
    print("PROPFIRM_PASS gate: Sharpe > 1.0  ?")
    for lab in ["Full 2022-2025", "All 2021-2026", "2026 ONLY (cherry)"]:
        sr = df.loc[lab, 'sharpe_ann']
        print(f"  {lab:25s} Sharpe={sr:.3f}  {'PASS' if sr > 1.0 else 'FAIL'}")
    df.to_csv("step1_metrics.csv")
    print("\nSaved -> step1_metrics.csv")
