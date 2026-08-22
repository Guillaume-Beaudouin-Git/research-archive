"""
iter10_regime_split.py — Regime decomposition + split-by-direction for iter_10
on Databento NQ 2010-2026.

Steps:
  1. Run iter_10 on full Databento 2010-2026.
  2. Decompose by 5 régime buckets (2010-2012, 2013-2015, 2016-2018, 2019-2021,
     2022-2026) AND by 11 specific episodes (eurozone 2011, China bust 2015-16,
     2018 vol, COVID 2020, etc.).
  3. Split by direction (long-only vs short-only).
  4. Annual breakdown.
  5. Lumpy metrics (skew, kurt, win-rate, avg winner/loser ratio).
  6. Stress: cost ×1.5, ×3 — sharpe degradation.

Outputs:
  - iter10_regime.csv, iter10_episodes.csv, iter10_annual.csv
  - iter10_regime_split_output.txt
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from iter10_validation import (
    load_rth_1min, precompute_vwap_rth, build_opening_features,
    build_iter10_signals, run_signals, metrics, sharpe_hac_daily,
    COST_RT_USD, POINT_VALUE_USD,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


REGIMES = [
    ("2010-2012", "2010-06-01", "2013-01-01"),
    ("2013-2015", "2013-01-01", "2016-01-01"),
    ("2016-2018", "2016-01-01", "2019-01-01"),
    ("2019-2021", "2019-01-01", "2022-01-01"),
    ("2022-2026", "2022-01-01", "2027-01-01"),
]

EPISODES = [
    ("2011_eurozone", "2011-05-01", "2011-12-31"),
    ("2012_QE3", "2012-06-01", "2013-06-01"),
    ("2014_taper", "2014-01-01", "2014-12-31"),
    ("2015_China_bust", "2015-06-01", "2016-04-01"),
    ("2017_low_vol", "2017-01-01", "2017-12-31"),
    ("2018_vol_shock", "2018-01-01", "2018-12-31"),
    ("2019_recovery", "2019-01-01", "2019-12-31"),
    ("2020_COVID", "2020-02-15", "2020-09-30"),
    ("2021_postCOVID", "2021-01-01", "2021-12-31"),
    ("2022_bear", "2022-01-01", "2022-12-31"),
    ("2023_AI_rally", "2023-01-01", "2026-01-01"),
]


def summarize_block(name: str, tl: pd.DataFrame, n_days_total: int) -> dict:
    if tl.empty:
        return {"block": name, "n_trades": 0}
    pnls = tl["pnl_usd"].values
    n = len(pnls)
    daily = tl.set_index(pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None))["pnl_usd"]
    daily_g = daily.groupby(level=0).sum()
    if n_days_total > 0:
        all_dates = pd.bdate_range(daily_g.index.min(), daily_g.index.max())
        daily_g = daily_g.reindex(all_dates, fill_value=0.0)
    mean_R_pts = float(np.mean(tl["pnl_pts"].values))
    return {
        "block": name,
        "n_trades": n,
        "win_rate_pct": round(float((pnls > 0).mean()) * 100, 1),
        "mean_pnl_usd": round(float(np.mean(pnls)), 2),
        "mean_pnl_pts": round(mean_R_pts, 3),
        "std_pnl_pts": round(float(np.std(tl["pnl_pts"], ddof=1)), 3),
        "skew_pnl": round(float(stats.skew(pnls)), 3),
        "kurt_pnl": round(float(stats.kurtosis(pnls)), 3),
        "profit_factor": round(float(tl[tl["pnl_usd"] > 0]["pnl_usd"].sum() /
                                       max(1.0, abs(tl[tl["pnl_usd"] <= 0]["pnl_usd"].sum()))), 3),
        "sharpe_daily_ann": round(float(sharpe_hac_daily(daily_g)), 3),
        "total_pnl_usd": round(float(np.sum(pnls)), 2),
        "best_day_usd": round(float(daily_g.max()), 2) if len(daily_g) else 0,
        "worst_day_usd": round(float(daily_g.min()), 2) if len(daily_g) else 0,
    }


def split_long_short(tl: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    return tl[tl["direction"] == 1].copy(), tl[tl["direction"] == -1].copy()


def stress_cost(rth: pd.DataFrame, feats: pd.DataFrame,
                 cost_mults: list[float]) -> pd.DataFrame:
    rows = []
    for cm in cost_mults:
        sigs = build_iter10_signals(feats)
        tl = run_signals(rth, sigs, cost_rt_usd=COST_RT_USD * cm)
        met = metrics(tl)
        met["cost_mult"] = cm
        met["cost_usd"] = COST_RT_USD * cm
        rows.append(met)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    log.info("Loading Databento NQ RTH...")
    df = load_rth_1min(skip_roll=True)
    log.info(f"  {len(df)} bars")

    log.info("Computing VWAP and features...")
    vwap = precompute_vwap_rth(df)
    feats = build_opening_features(df, vwap)
    log.info(f"  {len(feats)} day-features")

    sigs = build_iter10_signals(feats)
    log.info(f"  {len(sigs)} signals after filters")

    log.info("Running base iter_10 on full sample...")
    tl_full = run_signals(df, sigs, cost_rt_usd=COST_RT_USD)
    met_full = metrics(tl_full)
    tl_full.to_parquet(ROOT / "iter10_trades_full.parquet")

    print("\n" + "=" * 90)
    print("FULL SAMPLE 2010-2026 (Databento, cost $19 RT)")
    print("=" * 90)
    for k, v in met_full.items():
        print(f"  {k:25s}: {v}")
    print()

    # === Regime decomposition (5 buckets) ===
    print("=" * 90)
    print("REGIME DECOMPOSITION (5 buckets) — iter_10 by period")
    print("=" * 90)
    rows = []
    summary_long = []
    summary_short = []
    for name, lo, hi in REGIMES:
        tl_reg = tl_full[(tl_full["entry_ts"] >= pd.Timestamp(lo, tz="US/Eastern")) &
                          (tl_full["entry_ts"] < pd.Timestamp(hi, tz="US/Eastern"))]
        s = summarize_block(name, tl_reg, n_days_total=0)
        rows.append(s)
        # Split direction
        long_tl, short_tl = split_long_short(tl_reg)
        sL = summarize_block(name + "_LONG", long_tl, 0)
        sS = summarize_block(name + "_SHORT", short_tl, 0)
        summary_long.append(sL)
        summary_short.append(sS)
    regime_df = pd.DataFrame(rows)
    long_df = pd.DataFrame(summary_long)
    short_df = pd.DataFrame(summary_short)
    print("\nALL trades by regime:")
    print(regime_df.to_string(index=False))
    print("\nLONG trades by regime:")
    print(long_df.to_string(index=False))
    print("\nSHORT trades by regime:")
    print(short_df.to_string(index=False))
    regime_df.to_csv(ROOT / "iter10_regime_all.csv", index=False)
    long_df.to_csv(ROOT / "iter10_regime_long.csv", index=False)
    short_df.to_csv(ROOT / "iter10_regime_short.csv", index=False)

    # === Episodes ===
    print("\n" + "=" * 90)
    print("EPISODE DECOMPOSITION — specific market regimes")
    print("=" * 90)
    ep_rows = []
    for name, lo, hi in EPISODES:
        tl_ep = tl_full[(tl_full["entry_ts"] >= pd.Timestamp(lo, tz="US/Eastern")) &
                         (tl_full["entry_ts"] < pd.Timestamp(hi, tz="US/Eastern"))]
        s = summarize_block(name, tl_ep, 0)
        ep_rows.append(s)
    ep_df = pd.DataFrame(ep_rows)
    print(ep_df.to_string(index=False))
    ep_df.to_csv(ROOT / "iter10_episodes.csv", index=False)

    # === Annual breakdown ===
    print("\n" + "=" * 90)
    print("ANNUAL BREAKDOWN — iter_10 vs do-nothing baseline")
    print("=" * 90)
    years = sorted(set(pd.to_datetime(tl_full["entry_ts"]).dt.year))
    ann_rows = []
    for y in years:
        tl_y = tl_full[pd.to_datetime(tl_full["entry_ts"]).dt.year == y]
        s = summarize_block(str(y), tl_y, 0)
        s["year"] = y
        ann_rows.append(s)
    ann_df = pd.DataFrame(ann_rows)
    print(ann_df.to_string(index=False))
    ann_df.to_csv(ROOT / "iter10_annual.csv", index=False)

    # === Direction split overall ===
    print("\n" + "=" * 90)
    print("DIRECTION SPLIT — full sample 2010-2026")
    print("=" * 90)
    long_full, short_full = split_long_short(tl_full)
    print("\nLONG only:")
    sL = summarize_block("LONG_full", long_full, 0)
    for k, v in sL.items():
        print(f"  {k:25s}: {v}")
    print("\nSHORT only:")
    sS = summarize_block("SHORT_full", short_full, 0)
    for k, v in sS.items():
        print(f"  {k:25s}: {v}")

    # === Stress test (cost) ===
    print("\n" + "=" * 90)
    print("STRESS — cost multipliers (×1, ×1.5, ×3)")
    print("=" * 90)
    stress_df = stress_cost(df, feats, [1.0, 1.5, 3.0])
    print(stress_df[["cost_mult", "cost_usd", "n_trades", "win_rate",
                      "avg_trade_usd", "profit_factor", "sharpe_daily_hac",
                      "max_dd_pct", "total_pnl_usd"]].to_string(index=False))
    stress_df.to_csv(ROOT / "iter10_stress.csv", index=False)

    # === Lumpy metrics summary ===
    print("\n" + "=" * 90)
    print("LUMPY METRICS — for L24 / propfirm conversion analysis")
    print("=" * 90)
    pnls = tl_full["pnl_usd"].values
    skew = stats.skew(pnls)
    kurt = stats.kurtosis(pnls)
    winners = pnls[pnls > 0]
    losers = pnls[pnls <= 0]
    print(f"  hit_rate         : {(pnls > 0).mean()*100:.2f}%")
    print(f"  win/loss ratio   : {winners.mean() / abs(losers.mean()):.2f}")
    print(f"  skew             : {skew:.3f}")
    print(f"  excess kurt      : {kurt:.3f}")
    print(f"  best trade  $    : {pnls.max():.0f}")
    print(f"  worst trade $    : {pnls.min():.0f}")
    print(f"  P90 trade $      : {np.percentile(pnls, 90):.0f}")
    print(f"  P10 trade $      : {np.percentile(pnls, 10):.0f}")
    print(f"  Std trade $      : {pnls.std(ddof=1):.0f}")
    print(f"  Median trade $   : {np.median(pnls):.0f}")
    print()
    print("  Comparison to L24 FTMO-suitable profile (target):")
    print("  - hit_rate         > 55%  → iter_10 = {:.1f}%  → {}".format(
        (pnls > 0).mean()*100, "FAIL" if (pnls > 0).mean() < 0.55 else "OK"))
    print("  - win/loss ratio   ≈ 1    → iter_10 = {:.2f}    → {}".format(
        winners.mean()/abs(losers.mean()), "LUMPY" if winners.mean()/abs(losers.mean()) > 2 else "OK"))
    print("  - skew low         < 1    → iter_10 = {:.2f}   → {}".format(
        skew, "FAIL (lumpy)" if skew > 1.5 else "OK"))
    print("  - kurt low         < 3    → iter_10 = {:.2f}  → {}".format(
        kurt, "FAIL (fat tails)" if kurt > 3 else "OK"))
