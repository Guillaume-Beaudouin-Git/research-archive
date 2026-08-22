"""
nq_v2_pfunded_sweep.py — p_funded sweep under bps-constant cost + rv20 gate OOS retest.

Uses the trades from nq_v2_trades.parquet (with all cost-variant R columns precomputed).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from nq_orb_backtest import load_nq_5min
from nq_sim import simulate_2step_uncapped


REGIMES = [
    ("2010-12_recovery",   "2010-06-07", "2012-12-31", "trending"),
    ("2013-14_qe_trend",   "2013-01-01", "2014-12-31", "trending"),
    ("2015-16_china_chop", "2015-01-01", "2016-06-30", "chop"),
    ("2016H2-17_trend",    "2016-07-01", "2017-12-31", "trending"),
    ("2018_vol_shock",     "2018-01-01", "2018-12-31", "vol_shock"),
    ("2019_dovish_pivot",  "2019-01-01", "2019-12-31", "trending"),
    ("2020_covid",         "2020-01-01", "2020-12-31", "vol_shock"),
    ("2021_recovery",      "2021-01-01", "2021-12-31", "trending"),
    ("2022_bear",          "2022-01-01", "2022-12-31", "trending"),
    ("2023_chop",          "2023-01-01", "2023-12-31", "chop"),
    ("2024-26_bull",       "2024-01-01", "2026-05-29", "trending"),
]


def build_daily_R(df_trades: pd.DataFrame, r_col: str, all_dates: pd.DatetimeIndex) -> pd.Series:
    out = pd.Series(index=all_dates, dtype=float)
    out.loc[df_trades.index] = df_trades[r_col].values
    return out


def compute_rv20_terciles(daily_R: pd.Series) -> pd.Series:
    daily_R_filled = daily_R.fillna(0.0)
    rv20 = daily_R_filled.rolling(20).std() * np.sqrt(252)
    rv20 = rv20.shift(1)
    tercile = pd.Series(index=rv20.index, dtype=float)
    for i in range(len(rv20)):
        if i < 60 or pd.isna(rv20.iloc[i]):
            continue
        hist = rv20.iloc[:i].dropna()
        if len(hist) < 40:
            continue
        q33, q67 = hist.quantile([1/3, 2/3]).values
        v = rv20.iloc[i]
        tercile.iloc[i] = 0 if v <= q33 else (1 if v <= q67 else 2)
    return tercile


if __name__ == "__main__":
    df_trades = pd.read_parquet("nq_v2_trades.parquet")
    df_5m = load_nq_5min()
    all_dates = pd.DatetimeIndex(sorted(set(pd.Timestamp(d) for d in df_5m.index.date)))
    print(f"Trades: {len(df_trades)}, sessions: {len(all_dates)}")
    print()

    cost_models = [
        ("3pts_fixed_v1bug", "r_3 pts FIXED (buggy v1)"),
        ("1bps_aggressive", "r_1 bps RT (aggressive)"),
        ("2bps_median", "r_2 bps RT (median)"),
        ("3bps_conservative", "r_3 bps RT (conservative)"),
        ("futures_1pt_realistic", "r_Futures 1 pt (realistic)"),
        ("gross", "r_gross"),
    ]
    risks = [0.005, 0.0075, 0.010, 0.0125]

    # === A. Headline p_funded by (cost model × sizing) ===
    print("=" * 100)
    print("A. HEADLINE p_funded by (cost model × sizing) — full 2010-2026")
    print("=" * 100)
    headline_rows = []
    for cost_label, col in cost_models:
        daily_R = build_daily_R(df_trades, col, all_dates)
        for r in risks:
            out = simulate_2step_uncapped(daily_R, block_cap_pct=r)
            headline_rows.append({
                "cost_model": cost_label, "risk_pct": r * 100,
                "p_funded_pct": out["p_funded_pct"],
                "p_phase1": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
                "censored_pct": out["censored_pct"],
                "median_grind_p1": out["median_grind_p1"],
                "mean_R": df_trades[col].mean(),
            })
    headline = pd.DataFrame(headline_rows)
    headline.to_csv("nq_v2_headline_pfunded.csv", index=False)
    # Pivot
    piv = headline.pivot_table(index="cost_model", columns="risk_pct", values="p_funded_pct")
    cm_order = ["gross", "1bps_aggressive", "2bps_median", "3bps_conservative",
                 "futures_1pt_realistic", "3pts_fixed_v1bug"]
    piv = piv.reindex([c for c in cm_order if c in piv.index])
    print("p_funded_pct by (cost model × risk%):")
    print(piv.round(1).to_string())
    print()

    # === B. p_funded by REGIME under 2 bps cost (realistic median) ===
    print("=" * 100)
    print("B. p_funded by REGIME under realistic costs (risk=0.75%)")
    print("=" * 100)
    rows_regime = []
    risk = 0.0075
    for cost_label, col in [("gross", "r_gross"),
                             ("2bps_median", "r_2 bps RT (median)"),
                             ("3bps_conservative", "r_3 bps RT (conservative)"),
                             ("futures_1pt_realistic", "r_Futures 1 pt (realistic)")]:
        daily_R = build_daily_R(df_trades, col, all_dates)
        for regime_name, lo, hi, tag in REGIMES:
            sub = daily_R.loc[lo:hi]
            if len(sub) < 30:
                continue
            out = simulate_2step_uncapped(sub, block_cap_pct=risk)
            rows_regime.append({
                "cost_model": cost_label, "regime": regime_name, "tag": tag,
                "p_funded_pct": out["p_funded_pct"],
                "p_phase1_pct": out["p_phase1"] * 100 if not np.isnan(out["p_phase1"]) else float("nan"),
                "censored_pct": out["censored_pct"],
                "mean_R_regime": df_trades.loc[lo:hi, col].mean(),
            })
    rg = pd.DataFrame(rows_regime)
    rg.to_csv("nq_v2_pfunded_by_regime.csv", index=False)
    # Pivot p_funded
    pv = rg.pivot_table(index=["tag", "regime"], columns="cost_model", values="p_funded_pct")
    cm_order_b = ["gross", "2bps_median", "3bps_conservative", "futures_1pt_realistic"]
    pv = pv[[c for c in cm_order_b if c in pv.columns]]
    print(pv.round(1).to_string())
    print()
    # Aggregate by tag
    print("\np_funded weighted-mean by tag (= average over regimes in that tag):")
    tag_agg = rg.groupby(["cost_model", "tag"])["p_funded_pct"].mean().reset_index()
    tag_pv = tag_agg.pivot(index="tag", columns="cost_model", values="p_funded_pct")
    tag_pv = tag_pv[[c for c in cm_order_b if c in tag_pv.columns]]
    print(tag_pv.round(1).to_string())
    print()

    # === C. WF maximin per regime under 2bps and 3bps ===
    print("=" * 100)
    print("C. WF MAXIMIN per regime — sizing sweep × cost models")
    print("=" * 100)
    wf_rows = []
    for cost_label, col in [("gross", "r_gross"),
                             ("2bps_median", "r_2 bps RT (median)"),
                             ("3bps_conservative", "r_3 bps RT (conservative)")]:
        daily_R = build_daily_R(df_trades, col, all_dates)
        for r in risks:
            per_regime = {}
            for regime_name, lo, hi, tag in REGIMES:
                sub = daily_R.loc[lo:hi]
                if len(sub) < 30:
                    continue
                out = simulate_2step_uncapped(sub, block_cap_pct=r)
                per_regime[regime_name] = out["p_funded_pct"]
            finite = [v for v in per_regime.values() if not np.isnan(v)]
            wf_mean = float(np.mean(finite)) if finite else float("nan")
            wf_min = float(np.min(finite)) if finite else float("nan")
            full = simulate_2step_uncapped(daily_R, block_cap_pct=r)
            wf_rows.append({
                "cost_model": cost_label, "risk_pct": r * 100,
                "FULL_p_funded": full["p_funded_pct"],
                "WF_mean": wf_mean, "WF_min": wf_min,
                "n_regimes_zero": sum(1 for v in finite if v == 0.0),
            })
    wf = pd.DataFrame(wf_rows)
    wf.to_csv("nq_v2_wf_maximin.csv", index=False)
    print(wf.round(2).to_string(index=False))
    print()

    # === D. rv20 gate retest under 2 bps cost ===
    print("=" * 100)
    print("D. rv20 gate retest under realistic costs (2bps, 3bps, futures 1pt)")
    print("=" * 100)
    for cost_label, col in [("2bps_median", "r_2 bps RT (median)"),
                             ("3bps_conservative", "r_3 bps RT (conservative)"),
                             ("futures_1pt_realistic", "r_Futures 1 pt (realistic)")]:
        daily_R = build_daily_R(df_trades, col, all_dates)
        terciles = compute_rv20_terciles(daily_R)
        print(f"\n--- cost: {cost_label} ---")
        for r in risks:
            out_base = simulate_2step_uncapped(daily_R, block_cap_pct=r)
            gate_low = (terciles == 0).values
            gate_mid = (terciles == 1).values
            gate_high = (terciles == 2).values
            out_low = simulate_2step_uncapped(daily_R, block_cap_pct=r,
                                                start_indices=np.where(gate_low)[0])
            out_mid = simulate_2step_uncapped(daily_R, block_cap_pct=r,
                                                start_indices=np.where(gate_mid)[0])
            out_high = simulate_2step_uncapped(daily_R, block_cap_pct=r,
                                                 start_indices=np.where(gate_high)[0])
            print(f"  risk={r*100:.2f}% BASE={out_base['p_funded_pct']:5.1f}% "
                  f"LOW={out_low['p_funded_pct']:5.1f}% (Δ{out_low['p_funded_pct']-out_base['p_funded_pct']:+5.1f}) "
                  f"MID={out_mid['p_funded_pct']:5.1f}% (Δ{out_mid['p_funded_pct']-out_base['p_funded_pct']:+5.1f}) "
                  f"HIGH={out_high['p_funded_pct']:5.1f}% (Δ{out_high['p_funded_pct']-out_base['p_funded_pct']:+5.1f})")
