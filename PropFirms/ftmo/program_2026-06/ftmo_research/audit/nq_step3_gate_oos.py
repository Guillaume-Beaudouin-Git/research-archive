"""
nq_step3_gate_oos.py — OOS test of rv20_mid gate on NQ 2010-2026.

The rv20_mid gate (volatility 20d mid tercile) gave +16pt in-sample on 2022-2025.
Does it survive OOS on the full 16-year sample with multiple regime types?

L19 ablation: same risk, same exec model, no-gate vs gated.

Test on clean EXEC_NEXT_OPEN with CFD cost (= the live FTMO scenario).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from nq_orb_backtest import extract_trades, load_nq_5min, COST_POINTS_CFD
from nq_sim import simulate_2step_uncapped


def compute_rv20_terciles(daily_R: pd.Series, all_dates: pd.DatetimeIndex) -> pd.Series:
    """
    Compute rv20 (realised vol 20-day rolling std of underlying daily returns)
    EX-ANTE: tercile assignment uses only history up to day t-1 (expanding).

    Note: we use daily R as proxy for underlying daily returns. A more rigorous
    measure would use NQ underlying daily returns but the relative tercile
    structure should be similar for this OOS test.
    """
    # Use the daily R series itself as the underlying activity proxy
    daily_R_filled = daily_R.fillna(0.0)
    rv20 = daily_R_filled.rolling(20).std() * np.sqrt(252)  # annualised
    rv20 = rv20.shift(1)  # ex-ante
    # Expanding terciles
    tercile = pd.Series(index=rv20.index, dtype=float)
    for i in range(len(rv20)):
        if i < 60 or pd.isna(rv20.iloc[i]):
            tercile.iloc[i] = np.nan
            continue
        hist = rv20.iloc[:i].dropna()
        if len(hist) < 40:
            tercile.iloc[i] = np.nan
            continue
        q33, q67 = hist.quantile([1/3, 2/3]).values
        v = rv20.iloc[i]
        tercile.iloc[i] = 0 if v <= q33 else (1 if v <= q67 else 2)
    return tercile


def gated_simulate(daily_R: pd.Series, gate_mask: np.ndarray,
                   risk: float = 0.0075) -> dict:
    """Run sim only at start positions where gate_mask is True."""
    starts = np.where(gate_mask)[0]
    if len(starts) == 0:
        return {"p_funded_pct": float("nan"), "n_total": 0, "n_resolved": 0}
    return simulate_2step_uncapped(daily_R, block_cap_pct=risk, start_indices=starts)


if __name__ == "__main__":
    print("=" * 100)
    print("STEP 3 — rv20_mid gate OOS test on NQ 2010-2026 (EXEC_NEXT_OPEN, CFD cost)")
    print("=" * 100)
    df_trades = extract_trades(or_bars=6, exec_model="EXEC_NEXT_OPEN", cost_pts=COST_POINTS_CFD)
    df_5m = load_nq_5min()
    all_dates = pd.DatetimeIndex(sorted(set(pd.Timestamp(d) for d in df_5m.index.date)))
    daily_R = pd.Series(index=all_dates, dtype=float)
    daily_R.loc[df_trades.index] = df_trades["r_realised"].values
    daily_R = daily_R.sort_index()
    print(f"  {len(daily_R)} session days, {df_trades['r_realised'].notna().sum()} trades")

    # Compute rv20 terciles ex-ante
    terciles = compute_rv20_terciles(daily_R, all_dates)
    print(f"  rv20 tercile distribution (excluding NaN warmup):")
    print(f"  {terciles.value_counts().sort_index().to_dict()}")
    print()

    risks = [0.005, 0.0075, 0.010, 0.0125]

    print("=" * 100)
    print("L19 ABLATION — baseline (no gate) vs gate=rv20_mid (tercile=1)")
    print("=" * 100)
    rows = []
    for r in risks:
        # No gate (baseline)
        out_base = simulate_2step_uncapped(daily_R, block_cap_pct=r)
        # rv20_mid gate
        gate_mid = (terciles == 1).values
        out_mid = gated_simulate(daily_R, gate_mid, risk=r)
        # rv20_low gate (alternative)
        gate_low = (terciles == 0).values
        out_low = gated_simulate(daily_R, gate_low, risk=r)
        # rv20_high gate (alternative)
        gate_high = (terciles == 2).values
        out_high = gated_simulate(daily_R, gate_high, risk=r)
        rows.append({
            "risk_pct": r * 100,
            "BASE_p_funded": out_base["p_funded_pct"],
            "BASE_n_resolved": out_base["n_resolved"],
            "MID_p_funded": out_mid.get("p_funded_pct", float("nan")),
            "MID_n_resolved": out_mid.get("n_resolved", 0),
            "MID_delta_pt": out_mid.get("p_funded_pct", float("nan")) - out_base["p_funded_pct"],
            "LOW_p_funded": out_low.get("p_funded_pct", float("nan")),
            "LOW_delta_pt": out_low.get("p_funded_pct", float("nan")) - out_base["p_funded_pct"],
            "HIGH_p_funded": out_high.get("p_funded_pct", float("nan")),
            "HIGH_delta_pt": out_high.get("p_funded_pct", float("nan")) - out_base["p_funded_pct"],
        })
    df_res = pd.DataFrame(rows)
    df_res.to_csv("nq_step3_gate_oos.csv", index=False)
    print(df_res.round(2).to_string(index=False))
    print()

    # Also test in-sample 2022-2025 only as control
    print("=" * 100)
    print("CONTROL — same gate on 2022-2025 subset (the original in-sample window)")
    print("=" * 100)
    sub_dates = all_dates[(all_dates >= pd.Timestamp("2022-01-01")) & (all_dates <= pd.Timestamp("2025-12-31"))]
    sub_daily_R = daily_R.loc["2022-01-01":"2025-12-31"]
    sub_terciles = terciles.loc["2022-01-01":"2025-12-31"]
    for r in risks:
        out_base = simulate_2step_uncapped(sub_daily_R, block_cap_pct=r)
        out_mid = gated_simulate(sub_daily_R, (sub_terciles == 1).values, risk=r)
        print(f"  risk={r*100:.2f}%: baseline={out_base['p_funded_pct']:.1f}%, "
              f"rv20_mid={out_mid.get('p_funded_pct', float('nan')):.1f}%, "
              f"Δ={out_mid.get('p_funded_pct', float('nan')) - out_base['p_funded_pct']:+.1f}pt")
