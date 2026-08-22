"""
hurst_step1_gradient.py — Étape 1 du test Hurst sizing.

Calcule Hurst + vol-z point-in-time à chaque entrée ORB V2+E7, puis tabule
WR / avg R / PnL par régime Hurst (et vol-z) — réplique Table 3 du papier
Ntingana sur NOS trades.

⚠ Point-in-time strict: trailing 200 5-min bars BEFORE entry seulement.

V2+E7 reconstruction:
  - ORB 30-min sur NQ (signal_orb avec or_bars=6)
  - Exit trail_BE@1R (move stop à breakeven après +1R)
  - Cost 1 bp RT (= NQ futures equivalent; conservative pour CFD)

Hurst estimation: variance-ratio Lo-MacKinlay multi-lag.
  H ≈ 0.5 + log(VR(q)) / (2 × log(q)) where VR(q) = Var(r_q) / (q × Var(r_1))
  Use median of H estimates at lags q ∈ {2, 4, 8}.

Régimes Hurst:
  persistent H ≥ 0.55
  neutral 0.45 ≤ H < 0.55
  anti-persistent H < 0.45

Vol-z (paper eq. 4-5):
  RV_25 = stddev(returns_25_bars_trailing)
  mean_6m, std_6m = rolling mean/std of RV_25 over ~6 months (= ~6000 5-min bars)
  vol_z = (RV_25 - mean_6m) / std_6m

Vol-z bins (paper):
  vol_low  z < -0.5
  vol_mid  -0.5 ≤ z < +0.5
  vol_high z ≥ +0.5
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache


DATA_PATH = Path(__file__).resolve().parents[1].parent / "raw" / "NQ_1min_databento_2010-2026.parquet"


@lru_cache(maxsize=1)
def load_nq_5min_full() -> pd.DataFrame:
    """Load NQ 1-min, resample to 5-min. Skip roll days. Single global resample (fast)."""
    df = pd.read_parquet(DATA_PATH)
    df = df[~df["is_roll_day"]].copy()
    # Single resample on the full series (much faster than per-day groupby+resample)
    df_5m = df[["open", "high", "low", "close", "volume"]].resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    return df_5m


def compute_hurst_vr(returns: np.ndarray, lags: tuple = (2, 4, 8)) -> float:
    """Estimate Hurst via Lo-MacKinlay variance ratio at multiple lags. Median H."""
    if len(returns) < max(lags) * 4:
        return np.nan
    var1 = returns.var(ddof=1)
    if var1 <= 0:
        return np.nan
    H_estimates = []
    for q in lags:
        # q-period returns (non-overlapping for cleanest estimator)
        n_q = len(returns) // q
        if n_q < 5:
            continue
        r_q = returns[:n_q * q].reshape(n_q, q).sum(axis=1)
        var_q = r_q.var(ddof=1) / q
        VR = var_q / var1
        if VR <= 0:
            continue
        H = 0.5 + np.log(VR) / (2 * np.log(q))
        H_estimates.append(H)
    if not H_estimates:
        return np.nan
    return float(np.median(H_estimates))


def compute_per_bar_hurst_vol(df_5m: pd.DataFrame,
                                window: int = 200, rv_window: int = 25,
                                vol_zscore_lookback: int = 6000) -> pd.DataFrame:
    """
    Compute H and vol-z at each 5-min bar (point-in-time, info ≤ bar t).
    Returns: DataFrame indexed by timestamp with columns H, vol_z, RV25.
    """
    # Log returns of close
    close = df_5m["close"].values
    log_ret = np.zeros(len(close))
    log_ret[1:] = np.log(close[1:] / close[:-1])

    H_arr = np.full(len(close), np.nan)
    rv25_arr = np.full(len(close), np.nan)

    # Rolling Hurst (point-in-time: trailing window only)
    for i in range(window, len(close)):
        H_arr[i] = compute_hurst_vr(log_ret[i - window:i])

    # Rolling RV (point-in-time)
    s = pd.Series(log_ret)
    rv25 = s.rolling(rv_window).std() * np.sqrt(rv_window)  # not annualised; ratio matters
    rv25_arr = rv25.shift(1).values  # info ≤ bar t-1 → strict point-in-time

    # vol_z: rolling 6m mean/std of RV25, shifted
    rv25_s = pd.Series(rv25_arr)
    mean_6m = rv25_s.rolling(vol_zscore_lookback).mean().shift(1)
    std_6m = rv25_s.rolling(vol_zscore_lookback).std().shift(1)
    vol_z = ((rv25_s - mean_6m) / std_6m).values

    out = pd.DataFrame({
        "H": H_arr,
        "RV25": rv25_arr,
        "vol_z": vol_z,
    }, index=df_5m.index)
    return out


def classify_regime(H: float, vol_z: float) -> tuple[str, str]:
    """Return (H_regime, vol_regime)."""
    if pd.isna(H):
        h_reg = "unknown"
    elif H >= 0.55:
        h_reg = "persistent"
    elif H < 0.45:
        h_reg = "anti_persistent"
    else:
        h_reg = "neutral"
    if pd.isna(vol_z):
        v_reg = "unknown"
    elif vol_z >= 0.5:
        v_reg = "vol_high"
    elif vol_z < -0.5:
        v_reg = "vol_low"
    else:
        v_reg = "vol_mid"
    return h_reg, v_reg


def reconstruct_v2_e7_trades() -> pd.DataFrame:
    """Load existing ORB 30-min trades with trail_BE@1R exit (= V2+E7 approx)."""
    df = pd.read_parquet("breakout_phase2_trades_ORB_30min.parquet")
    df["r_net_v2e7"] = df["r_net_trail_BE@1R"]
    return df[["signal", "direction", "level", "or_range",
                "r_net_v2e7", "r_net_EOD", "regime", "regime_tag"]]


def map_features_to_trades(df_trades: pd.DataFrame, features: pd.DataFrame,
                            df_5m: pd.DataFrame) -> pd.DataFrame:
    """
    For each trade (entered at OR_bars + iu after RTH open), get the H/vol_z
    AT THE BAR BEFORE entry (= point-in-time).

    Approximation: use last 5-min bar of pre-RTH (just before US cash open)
    as the lookup timestamp. This avoids look-ahead.
    """
    # Build a per-day map: date -> entry_bar_timestamp
    df_5m_dt = df_5m.copy()
    df_5m_dt["date"] = df_5m_dt.index.date
    # For each trade date, find the bar just BEFORE 13:30 UTC (US cash open in DST)
    # = the last bar that's <= 13:25 UTC = the very last pre-RTH bar
    # We use this as the "info ≤ entry" timestamp for Hurst lookup
    rows = []
    by_date = df_5m_dt.groupby("date")
    for date, row in df_trades.iterrows():
        date_str = pd.Timestamp(date).date()
        try:
            day_bars = by_date.get_group(date_str)
        except KeyError:
            rows.append({"H": np.nan, "vol_z": np.nan, "RV25": np.nan,
                          "h_regime": "unknown", "v_regime": "unknown"})
            continue
        # Pre-RTH bar: last bar with hour < 13 or (hour == 13 and minute < 30)
        h, m = day_bars.index.hour, day_bars.index.minute
        pre_rth = day_bars[(h < 13) | ((h == 13) & (m < 30))]
        if len(pre_rth) == 0:
            # No pre-RTH bar (early start or only RTH). Try minus 1 day.
            ts_target = None
        else:
            ts_target = pre_rth.index[-1]
        if ts_target is not None and ts_target in features.index:
            H = features.loc[ts_target, "H"]
            vol_z = features.loc[ts_target, "vol_z"]
            RV25 = features.loc[ts_target, "RV25"]
        else:
            H = vol_z = RV25 = np.nan
        h_reg, v_reg = classify_regime(H, vol_z)
        rows.append({"H": H, "vol_z": vol_z, "RV25": RV25,
                      "h_regime": h_reg, "v_regime": v_reg})
    feat_df = pd.DataFrame(rows, index=df_trades.index)
    return pd.concat([df_trades, feat_df], axis=1)


def table_by_regime(df: pd.DataFrame, r_col: str = "r_net_v2e7"):
    """Replicate Table 3 of paper: WR / avg R / PnL / n by H_regime."""
    print(f"\n--- WR / avg R / PnL by H regime ---")
    print(f"{'h_regime':>16} {'n':>5} {'mean_R':>8} {'WR%':>6} {'cum_R':>8} {'t-stat':>7}")
    for reg in ["persistent", "neutral", "anti_persistent"]:
        sub = df[df["h_regime"] == reg]
        if len(sub) == 0:
            continue
        m = sub[r_col].mean()
        s = sub[r_col].std()
        n = len(sub)
        t = m / (s / np.sqrt(n)) if s > 0 else np.nan
        wr = (sub[r_col] > 0).mean() * 100
        cum = sub[r_col].sum()
        print(f"{reg:>16} {n:>5d} {m:>+8.4f} {wr:>5.1f}% {cum:>+8.2f} {t:>+7.2f}")
    print(f"\n--- WR / avg R / PnL by vol_z regime ---")
    print(f"{'v_regime':>10} {'n':>5} {'mean_R':>8} {'WR%':>6} {'cum_R':>8} {'t-stat':>7}")
    for reg in ["vol_high", "vol_mid", "vol_low"]:
        sub = df[df["v_regime"] == reg]
        if len(sub) == 0:
            continue
        m = sub[r_col].mean()
        s = sub[r_col].std()
        n = len(sub)
        t = m / (s / np.sqrt(n)) if s > 0 else np.nan
        wr = (sub[r_col] > 0).mean() * 100
        cum = sub[r_col].sum()
        print(f"{reg:>10} {n:>5d} {m:>+8.4f} {wr:>5.1f}% {cum:>+8.2f} {t:>+7.2f}")
    print(f"\n--- Combined 3×3 mean_R table ---")
    pivot = df.pivot_table(index="h_regime", columns="v_regime",
                            values=r_col, aggfunc="mean")
    # Order: persistent / neutral / anti_persistent rows, vol_high / mid / low cols
    pivot = pivot.reindex(index=["persistent", "neutral", "anti_persistent"],
                            columns=["vol_high", "vol_mid", "vol_low"])
    print(pivot.round(4).to_string())
    pivot_n = df.pivot_table(index="h_regime", columns="v_regime",
                               values=r_col, aggfunc="count")
    pivot_n = pivot_n.reindex(index=["persistent", "neutral", "anti_persistent"],
                                columns=["vol_high", "vol_mid", "vol_low"])
    print(f"\n--- Combined 3×3 count table ---")
    print(pivot_n.to_string())


if __name__ == "__main__":
    print("=" * 95)
    print("HURST STEP 1 — gradient WR/R par régime Hurst (point-in-time) sur V2+E7")
    print("=" * 95)
    print("\nLoading NQ 5-min (all bars including overnight)...")
    df_5m = load_nq_5min_full()
    print(f"  {len(df_5m):,} 5-min bars, range {df_5m.index.min()} → {df_5m.index.max()}")

    print("\nComputing per-bar Hurst (window=200, lags=(2,4,8))...")
    features = compute_per_bar_hurst_vol(df_5m, window=200, rv_window=25,
                                           vol_zscore_lookback=6000)
    n_valid_H = features["H"].notna().sum()
    n_valid_vz = features["vol_z"].notna().sum()
    print(f"  H valid: {n_valid_H:,} ({n_valid_H/len(features)*100:.1f}%)")
    print(f"  vol_z valid: {n_valid_vz:,} ({n_valid_vz/len(features)*100:.1f}%)")
    print(f"  H mean: {features['H'].mean():.3f}, std: {features['H'].std():.3f}")
    print(f"  H p10/p50/p90: {features['H'].quantile([0.1, 0.5, 0.9]).values.round(3)}")
    features.to_parquet("hurst_features_per_bar.parquet")

    print("\nReconstructing V2+E7 trade log (ORB 30-min + trail_BE@1R, NQ 16y)...")
    df_trades = reconstruct_v2_e7_trades()
    print(f"  {len(df_trades)} trades")
    print(f"  Mean R V2+E7 (trail_BE@1R): {df_trades['r_net_v2e7'].mean():+.4f}")
    print(f"  Mean R EOD baseline: {df_trades['r_net_EOD'].mean():+.4f}")

    print("\nMapping features to trades (pre-RTH bar timestamp = info ≤ entry)...")
    df_with_feat = map_features_to_trades(df_trades, features, df_5m)
    df_with_feat.to_parquet("hurst_step1_trades_with_features.parquet")
    print(f"  Trades with H valid: {df_with_feat['H'].notna().sum()}/{len(df_with_feat)}")
    print(f"  Trades with vol_z valid: {df_with_feat['vol_z'].notna().sum()}/{len(df_with_feat)}")
    print(f"  Trades classified into H regime: ")
    print(df_with_feat["h_regime"].value_counts().to_dict())
    print(f"  Trades classified into vol regime: ")
    print(df_with_feat["v_regime"].value_counts().to_dict())

    # ---- Table 3 replication ----
    print("\n" + "=" * 95)
    print("TABLE 3 REPLICATION — gradient WR/R par régime sur les trades V2+E7")
    print("=" * 95)
    table_by_regime(df_with_feat, r_col="r_net_v2e7")
    # also on EOD baseline
    print("\n--- Same table for EOD baseline (sanity check) ---")
    table_by_regime(df_with_feat, r_col="r_net_EOD")

    # Save aggregate
    summary = df_with_feat.groupby(["h_regime", "v_regime"]).agg(
        n=("r_net_v2e7", "count"),
        mean_R=("r_net_v2e7", "mean"),
        WR=("r_net_v2e7", lambda s: (s > 0).mean() * 100),
        cum_R=("r_net_v2e7", "sum"),
    ).round(4)
    summary.to_csv("hurst_step1_summary.csv")
    print(f"\nSaved: hurst_features_per_bar.parquet, hurst_step1_trades_with_features.parquet, hurst_step1_summary.csv")
