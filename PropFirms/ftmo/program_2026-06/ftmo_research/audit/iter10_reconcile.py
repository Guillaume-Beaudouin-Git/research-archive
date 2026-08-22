"""
iter10_reconcile.py — Side-by-side reconciliation Databento vs Kaggle.

Goal: validate that my iter_10 reproduction MATCHES the reported backtest
(Sharpe 1.5212, N=346, WF 78%) on the EXACT same window 2022-12-26 → 2025-12-11.

If it matches → spec is correct, extension to 2010-2026 is meaningful.
If it doesn't → debug data/spec divergence before any extension.

Comparisons:
  1. Period & N day-candidates (raw, before any filter)
  2. Per-day OR features (open, close, rng, direction, vwap_at_sig, gap_pct)
     compared between Databento and Kaggle for the overlap window.
  3. Filter retention rate.
  4. Trade-level metrics (N, win_rate, total_pnl, Sharpe, MaxDD).
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import datetime
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parents[2]))  # for data.cache

from iter10_validation import (
    load_rth_1min as load_databento_rth, precompute_vwap_rth,
    build_opening_features, build_iter10_signals, run_signals, metrics,
    walk_forward,
    T_OR_START, T_OR_END, T_TIME_STOP, COST_RT_USD,
)

from data.cache import load_nq_1min as load_kaggle  # 2022-12-26 → 2025-12-11

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def kaggle_rth(df: pd.DataFrame) -> pd.DataFrame:
    """Restrict Kaggle data to RTH 09:30-15:59 ET (matches engine.py)."""
    t = df.index.time
    s = datetime.time(9, 30)
    e = datetime.time(15, 59)
    return df[(t >= s) & (t <= e)].copy()


def features_from_kaggle(rth: pd.DataFrame) -> pd.DataFrame:
    """Build per-day features using Kaggle's precomputed vwap_rth column."""
    rth = rth.copy()
    df2 = rth
    t = rth.index.time
    df2["_day"] = rth.index.normalize()
    df2["_is_open"] = (t >= T_OR_START) & (t <= T_OR_END)
    op = df2[df2["_is_open"]]
    g = op.groupby("_day", sort=True)
    out = pd.DataFrame(index=g.size().index.rename("date"))
    out["n_bars"] = g.size()
    out["open_price"] = g["open"].first()
    out["close_price"] = g["close"].last()
    out["sig_ts"] = g.apply(lambda x: x.index[-1], include_groups=False)
    out["vwap_at_sig"] = g["vwap_rth"].last()
    out = out[out["n_bars"] >= 2].copy()
    out["rng"] = (out["close_price"] - out["open_price"]).abs()
    out = out[out["rng"] >= 1.0].copy()
    out["direction"] = np.where(out["close_price"] > out["open_price"], 1, -1)
    out["vwap_ok"] = ((out["direction"] == 1) & (out["close_price"] > out["vwap_at_sig"])) | \
                     ((out["direction"] == -1) & (out["close_price"] < out["vwap_at_sig"]))

    daily_open = rth["open"].resample("B").first().dropna()
    daily_close = rth["close"].resample("B").last().dropna()
    daily_open.index = pd.DatetimeIndex(daily_open.index).normalize()
    daily_close.index = pd.DatetimeIndex(daily_close.index).normalize()
    prev_close = daily_close.shift(1)
    gap = (daily_open - prev_close) / prev_close
    out["gap_pct"] = gap.reindex(out.index).values

    out["date"] = out.index
    def _exit_time(d, sig):
        return pd.Timestamp(d.year, d.month, d.day,
                             T_TIME_STOP.hour, T_TIME_STOP.minute, 0,
                             tzinfo=sig.tzinfo)
    out["exit_time"] = [_exit_time(d, sig) for d, sig in zip(out["date"], out["sig_ts"])]
    out = out.reset_index(drop=True)
    return out[["date", "sig_ts", "direction", "open_price", "close_price",
                "rng", "vwap_at_sig", "vwap_ok", "gap_pct", "exit_time"]]


if __name__ == "__main__":
    log.info("Loading Kaggle NQ 1-min (2022-12-26 → 2025-12-11)...")
    kg = load_kaggle()
    log.info(f"  {len(kg)} bars, {kg.index.min()} -> {kg.index.max()}")

    # Restrict to RTH (consistent with engine.py)
    kg_rth = kaggle_rth(kg)
    log.info(f"  RTH only: {len(kg_rth)} bars")

    log.info("Loading Databento NQ 1-min, restricted to Kaggle range...")
    db_full = load_databento_rth(skip_roll=True)
    db_rth = db_full[(db_full.index >= kg.index.min()) & (db_full.index <= kg.index.max())].copy()
    log.info(f"  RTH only, Kaggle range: {len(db_rth)} bars")

    print("\n" + "=" * 90)
    print("SECTION 1: Bar-level reconciliation (Databento vs Kaggle, same window)")
    print("=" * 90)

    # Align on common indices (some days may differ due to roll-day filter)
    common_idx = db_rth.index.intersection(kg_rth.index)
    print(f"  Databento RTH bars : {len(db_rth)}")
    print(f"  Kaggle RTH bars    : {len(kg_rth)}")
    print(f"  Common timestamps  : {len(common_idx)}")
    print(f"  Db-only (no Kaggle): {len(db_rth) - len(common_idx)}")
    print(f"  Kaggle-only (no Db): {len(kg_rth) - len(common_idx)}")
    if len(common_idx) > 0:
        diff_close = (db_rth.loc[common_idx, "close"] - kg_rth.loc[common_idx, "close"]).abs()
        diff_vol = (db_rth.loc[common_idx, "volume"] - kg_rth.loc[common_idx, "volume"]).abs()
        print(f"  Max diff(close) on common: {diff_close.max():.4f}")
        print(f"  Mean diff(close) on common: {diff_close.mean():.4f}")
        print(f"  Pct identical close: {(diff_close < 0.01).mean()*100:.2f}%")
        print(f"  Max diff(volume) on common: {diff_vol.max():.0f}")
        print(f"  Pct identical volume: {(diff_vol == 0).mean()*100:.2f}%")

    # === SECTION 2: Compute features both ways ===
    print("\n" + "=" * 90)
    print("SECTION 2: Per-day feature comparison (open, close, rng, VWAP, gap)")
    print("=" * 90)
    log.info("Computing my VWAP on Databento bars...")
    db_vwap = precompute_vwap_rth(db_rth)
    log.info("Computing my VWAP on Kaggle bars too (using same formula)...")
    kg_vwap = precompute_vwap_rth(kg_rth)

    log.info("Build features Databento (my vwap)...")
    feats_db = build_opening_features(db_rth, db_vwap)
    log.info(f"  {len(feats_db)} day-features")
    log.info("Build features Kaggle (precomputed vwap_rth column)...")
    feats_kg = features_from_kaggle(kg_rth)
    log.info(f"  {len(feats_kg)} day-features")
    log.info("Build features Kaggle (my own vwap computation on Kaggle bars)...")
    feats_kg_myvwap = build_opening_features(kg_rth, kg_vwap)
    log.info(f"  {len(feats_kg_myvwap)} day-features")

    # Align on date
    fdb = feats_db.set_index(feats_db["date"].dt.normalize())
    fkg = feats_kg.set_index(feats_kg["date"].dt.normalize())
    fkv = feats_kg_myvwap.set_index(feats_kg_myvwap["date"].dt.normalize())
    common = fdb.index.intersection(fkg.index)
    print(f"  Day-features Databento : {len(feats_db)}")
    print(f"  Day-features Kaggle    : {len(feats_kg)}")
    print(f"  Day-features Kaggle-my : {len(feats_kg_myvwap)}")
    print(f"  Common dates           : {len(common)}")
    if len(common) > 0:
        d = fdb.loc[common]
        k = fkg.loc[common]
        km = fkv.loc[common]
        for col in ["open_price", "close_price", "rng", "vwap_at_sig", "gap_pct"]:
            diff = (d[col] - k[col]).abs()
            print(f"  {col:18s}: Db vs Kg-precomputed_vwap — max diff={diff.max():.4f}, "
                  f"mean diff={diff.mean():.4f}, frac identical={(diff < 0.01).mean()*100:.1f}%")
        for col in ["open_price", "close_price", "rng", "vwap_at_sig", "gap_pct"]:
            diff = (d[col] - km[col]).abs()
            print(f"  {col:18s}: Db vs Kg-myvwap          — max diff={diff.max():.4f}, "
                  f"mean diff={diff.mean():.4f}, frac identical={(diff < 0.01).mean()*100:.1f}%")
        # Compare my VWAP on Kaggle bars vs precomputed vwap_rth
        diff_vwap = (km["vwap_at_sig"] - k["vwap_at_sig"]).abs()
        print(f"  VWAP my-formula vs Kaggle-precomputed (same Kaggle bars): "
              f"max diff={diff_vwap.max():.4f}, mean diff={diff_vwap.mean():.4f}, "
              f"frac identical={(diff_vwap < 0.01).mean()*100:.1f}%")
        # vwap_ok agreement
        agree = (d["vwap_ok"] == k["vwap_ok"]).mean() * 100
        agree_m = (d["vwap_ok"] == km["vwap_ok"]).mean() * 100
        print(f"  vwap_ok agreement Db vs Kg-precomputed: {agree:.1f}%")
        print(f"  vwap_ok agreement Db vs Kg-myvwap:      {agree_m:.1f}%")

    # === SECTION 3: Trade-level reconciliation ===
    print("\n" + "=" * 90)
    print("SECTION 3: Trade-level reconciliation")
    print("=" * 90)

    # 3a — Run on Databento with my VWAP (current pipeline)
    sigs_db = build_iter10_signals(feats_db)
    tl_db = run_signals(db_rth, sigs_db, cost_rt_usd=COST_RT_USD)
    met_db = metrics(tl_db)
    print(f"\n  [A] Databento data + my VWAP + my signals:")
    print(f"     n_signals: {len(sigs_db)}, n_trades: {met_db.get('n_trades')}")
    for k in ["n_trades", "win_rate", "avg_trade_usd", "profit_factor",
              "sharpe_daily_hac", "max_dd_pct", "total_pnl_usd"]:
        print(f"     {k:25s}: {met_db.get(k)}")

    # 3b — Run on Kaggle with precomputed vwap_rth
    sigs_kg = build_iter10_signals(feats_kg)
    tl_kg = run_signals(kg_rth, sigs_kg, cost_rt_usd=COST_RT_USD)
    met_kg = metrics(tl_kg)
    print(f"\n  [B] Kaggle data + Kaggle's vwap_rth column + my signals:")
    print(f"     n_signals: {len(sigs_kg)}, n_trades: {met_kg.get('n_trades')}")
    for k in ["n_trades", "win_rate", "avg_trade_usd", "profit_factor",
              "sharpe_daily_hac", "max_dd_pct", "total_pnl_usd"]:
        print(f"     {k:25s}: {met_kg.get(k)}")

    # 3c — Run on Kaggle with MY VWAP formula
    sigs_kg_my = build_iter10_signals(feats_kg_myvwap)
    tl_kg_my = run_signals(kg_rth, sigs_kg_my, cost_rt_usd=COST_RT_USD)
    met_kg_my = metrics(tl_kg_my)
    print(f"\n  [C] Kaggle data + MY VWAP formula + my signals:")
    print(f"     n_signals: {len(sigs_kg_my)}, n_trades: {met_kg_my.get('n_trades')}")
    for k in ["n_trades", "win_rate", "avg_trade_usd", "profit_factor",
              "sharpe_daily_hac", "max_dd_pct", "total_pnl_usd"]:
        print(f"     {k:25s}: {met_kg_my.get(k)}")

    print("\n  REPORTED iter_10 (from results.json):")
    print("     n_trades: 346, win_rate: 0.278, avg_trade: $131.53, "
          "PF: 1.432, Sharpe: 1.521, MaxDD: -13.4%, total_pnl: $45,510")

    # === SECTION 4: WF reconciliation ===
    print("\n" + "=" * 90)
    print("SECTION 4: Walk-Forward reconciliation (12m train / 3m test extended)")
    print("=" * 90)
    # iter_10 used wf_extended: 9 windows. Try 12m train / 3m test on Kaggle
    wf_kg = walk_forward(kg_rth, feats_kg, train_months=12, test_months=3,
                          cost_rt_usd=COST_RT_USD)
    print(f"  [B] Kaggle 12m/3m WF: n={wf_kg.get('n_windows', 0)}, "
          f"pct_pos={wf_kg.get('wf_pct_positive', float('nan'))}%")
    wf_db_kg = walk_forward(db_rth, feats_db, train_months=12, test_months=3,
                             cost_rt_usd=COST_RT_USD)
    print(f"  [A] Databento 12m/3m WF: n={wf_db_kg.get('n_windows', 0)}, "
          f"pct_pos={wf_db_kg.get('wf_pct_positive', float('nan'))}%")
    print("\n  REPORTED iter_10 WF: 100% in-sample / 77.78% extended (9 windows)")
