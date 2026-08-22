"""
hurst_step1_v3.py — Fully vectorized version.

Pre-compute global rolling RV25 std + mean/std-of-RV25 once,
then per-trade lookup is O(1).

Hurst computed only at unique trade timestamps.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path


DATA_PATH = Path(__file__).resolve().parents[1].parent / "raw" / "NQ_1min_databento_2010-2026.parquet"


def load_nq_5min_rth_cached() -> pd.DataFrame:
    """Cache the RTH 5-min resample to parquet (fast: global resample, no per-day groupby)."""
    cache = Path(__file__).parent / "_nq_5min_rth_cached.parquet"
    if cache.exists():
        return pd.read_parquet(cache)
    print("  Computing RTH 5-min resample (first time, single global resample)...")
    df = pd.read_parquet(DATA_PATH)
    df = df[df["is_rth"] & ~df["is_roll_day"]].copy()
    # Single global resample — pandas handles this in vectorized C
    df_5m = df[["open", "high", "low", "close", "volume"]].resample("5min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    ).dropna()
    df_5m.to_parquet(cache)
    print(f"  Cached {len(df_5m):,} bars to {cache}")
    return df_5m


def compute_hurst_vr(returns: np.ndarray, lags: tuple = (2, 4, 8)) -> float:
    if len(returns) < max(lags) * 4:
        return np.nan
    var1 = returns.var(ddof=1)
    if var1 <= 0:
        return np.nan
    H_estimates = []
    for q in lags:
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
    return float(np.median(H_estimates)) if H_estimates else np.nan


def classify(H, vol_z):
    if pd.isna(H):
        h = "unknown"
    elif H >= 0.55:
        h = "persistent"
    elif H < 0.45:
        h = "anti_persistent"
    else:
        h = "neutral"
    if pd.isna(vol_z):
        v = "unknown"
    elif vol_z >= 0.5:
        v = "vol_high"
    elif vol_z < -0.5:
        v = "vol_low"
    else:
        v = "vol_mid"
    return h, v


if __name__ == "__main__":
    print("=" * 95)
    print("HURST STEP 1 v3 — fully vectorized")
    print("=" * 95)

    df_5m = load_nq_5min_rth_cached()
    print(f"  {len(df_5m):,} bars RTH 5-min, range {df_5m.index.min()} → {df_5m.index.max()}")

    # ---- Pre-compute global features ----
    close = df_5m["close"].values
    log_ret = np.zeros(len(close))
    log_ret[1:] = np.log(close[1:] / close[:-1])

    # Rolling RV25 (NumPy vectorized — pandas rolling is fine if applied once)
    print("\nComputing global rolling RV25...")
    rv25 = pd.Series(log_ret).rolling(25).std(ddof=1).values  # std of last 25 returns

    # Vol-z: rolling mean/std of RV25 over 6000 bars
    print("Computing rolling mean/std of RV25 over 6000 bars...")
    rv25_s = pd.Series(rv25)
    rv25_mean_6m = rv25_s.rolling(6000).mean().shift(1).values
    rv25_std_6m = rv25_s.rolling(6000).std(ddof=1).shift(1).values
    vol_z_arr = (rv25 - rv25_mean_6m) / np.where(rv25_std_6m > 0, rv25_std_6m, np.nan)

    # ---- Load trades ----
    print("\nLoading V2+E7 trades...")
    df_trades = pd.read_parquet("breakout_phase2_trades_ORB_30min.parquet")
    df_trades["r_net_v2e7"] = df_trades["r_net_trail_BE@1R"]
    print(f"  {len(df_trades)} trades")

    # ---- For each trade, find the last bar of the prior trading day ----
    print("\nMapping trade dates to last-prior-bar indices...")
    df_5m_dates = pd.Series(df_5m.index.date, index=df_5m.index)
    # Map: for each unique trade date, get the bar idx of last bar with date < trade_date
    # Use searchsorted on the date index
    unique_dates_sorted = np.array(sorted(set(df_5m_dates.values)))
    # For each trade date, the "prior trading day" is the previous unique date in the dataset
    # before the trade date. Then the "last bar of prior trading day" is the last bar of that date.

    # Pre-compute per-date last-bar-index
    last_bar_idx_by_date = {}
    for d, grp in df_5m_dates.groupby(df_5m_dates.values):
        last_bar_idx_by_date[d] = grp.index[-1]  # last timestamp of that date
    # Mapping last timestamp → integer index in df_5m
    ts_to_idx = {ts: i for i, ts in enumerate(df_5m.index)}

    # For each trade, find prior trading date
    trade_dates = df_trades.index.date
    H_arr = []
    vol_z_pertrade = []
    h_reg_arr = []
    v_reg_arr = []
    RV25_arr = []
    for td in trade_dates:
        # Find prior trading date
        pos = np.searchsorted(unique_dates_sorted, td) - 1
        if pos < 0:
            H_arr.append(np.nan); vol_z_pertrade.append(np.nan)
            h_reg_arr.append("unknown"); v_reg_arr.append("unknown")
            RV25_arr.append(np.nan)
            continue
        prior_date = unique_dates_sorted[pos]
        ts = last_bar_idx_by_date.get(prior_date)
        if ts is None:
            H_arr.append(np.nan); vol_z_pertrade.append(np.nan)
            h_reg_arr.append("unknown"); v_reg_arr.append("unknown")
            RV25_arr.append(np.nan)
            continue
        idx = ts_to_idx[ts]
        # Hurst over last 200 returns ending at idx (inclusive)
        if idx < 200:
            H = np.nan
        else:
            H = compute_hurst_vr(log_ret[idx - 199: idx + 1])
        vol_z = vol_z_arr[idx] if idx < len(vol_z_arr) else np.nan
        RV25 = rv25[idx] if idx < len(rv25) else np.nan
        H_arr.append(H)
        vol_z_pertrade.append(vol_z)
        RV25_arr.append(RV25)
        h, v = classify(H, vol_z)
        h_reg_arr.append(h)
        v_reg_arr.append(v)

    feat = pd.DataFrame({
        "H": H_arr, "vol_z": vol_z_pertrade, "RV25": RV25_arr,
        "h_regime": h_reg_arr, "v_regime": v_reg_arr,
    }, index=df_trades.index)

    print(f"\n  H valid: {feat['H'].notna().sum()}/{len(feat)}")
    print(f"  vol_z valid: {feat['vol_z'].notna().sum()}/{len(feat)}")
    print(f"  H stats: mean={feat['H'].mean():.3f}, std={feat['H'].std():.3f}, "
          f"p10={feat['H'].quantile(0.1):.3f}, p50={feat['H'].quantile(0.5):.3f}, "
          f"p90={feat['H'].quantile(0.9):.3f}")
    print(f"  vol_z stats: mean={feat['vol_z'].mean():.3f}, std={feat['vol_z'].std():.3f}, "
          f"p10={feat['vol_z'].quantile(0.1):.3f}, p50={feat['vol_z'].quantile(0.5):.3f}, "
          f"p90={feat['vol_z'].quantile(0.9):.3f}")
    print(f"  H regime counts: {feat['h_regime'].value_counts().to_dict()}")
    print(f"  v regime counts: {feat['v_regime'].value_counts().to_dict()}")

    df_full = pd.concat([df_trades, feat], axis=1)
    df_full.to_parquet("hurst_step1_trades_with_features.parquet")

    # ---- Table 3 ----
    print("\n" + "=" * 95)
    print("TABLE 3 — Gradient WR/R par régime sur V2+E7 (ORB 30-min + trail_BE@1R)")
    print("=" * 95)
    for r_col_label, r_col in [("V2+E7", "r_net_v2e7"), ("EOD baseline (sanity)", "r_net_EOD")]:
        print(f"\n--- {r_col_label} (col={r_col}) ---")
        print(f"  By H regime:")
        print(f"    {'h_regime':>16} {'n':>5} {'mean_R':>8} {'WR%':>6} {'cum_R':>8} {'t-stat':>7}")
        for reg in ["persistent", "neutral", "anti_persistent"]:
            sub = df_full[df_full["h_regime"] == reg]
            if len(sub) == 0:
                continue
            m = sub[r_col].mean()
            s = sub[r_col].std()
            n = len(sub)
            t = m / (s / np.sqrt(n)) if s > 0 else np.nan
            wr = (sub[r_col] > 0).mean() * 100
            cum = sub[r_col].sum()
            print(f"    {reg:>16} {n:>5d} {m:>+8.4f} {wr:>5.1f}% {cum:>+8.2f} {t:>+7.2f}")
        print(f"  By vol_z regime:")
        print(f"    {'v_regime':>10} {'n':>5} {'mean_R':>8} {'WR%':>6} {'cum_R':>8} {'t-stat':>7}")
        for reg in ["vol_high", "vol_mid", "vol_low"]:
            sub = df_full[df_full["v_regime"] == reg]
            if len(sub) == 0:
                continue
            m = sub[r_col].mean()
            s = sub[r_col].std()
            n = len(sub)
            t = m / (s / np.sqrt(n)) if s > 0 else np.nan
            wr = (sub[r_col] > 0).mean() * 100
            cum = sub[r_col].sum()
            print(f"    {reg:>10} {n:>5d} {m:>+8.4f} {wr:>5.1f}% {cum:>+8.2f} {t:>+7.2f}")
        print(f"  Combined 3×3 mean_R:")
        pivot = df_full.pivot_table(index="h_regime", columns="v_regime",
                                      values=r_col, aggfunc="mean")
        pivot = pivot.reindex(index=["persistent", "neutral", "anti_persistent"],
                                columns=["vol_high", "vol_mid", "vol_low"])
        print(pivot.round(4).to_string())
        pivot_n = df_full.pivot_table(index="h_regime", columns="v_regime",
                                        values=r_col, aggfunc="count")
        pivot_n = pivot_n.reindex(index=["persistent", "neutral", "anti_persistent"],
                                    columns=["vol_high", "vol_mid", "vol_low"])
        print(f"  Combined 3×3 count:")
        print(pivot_n.to_string())

    summary = df_full.groupby(["h_regime", "v_regime"]).agg(
        n=("r_net_v2e7", "count"),
        mean_R=("r_net_v2e7", "mean"),
        WR=("r_net_v2e7", lambda s: (s > 0).mean() * 100),
        cum_R=("r_net_v2e7", "sum"),
    ).round(4)
    summary.to_csv("hurst_step1_summary.csv")
    print(f"\nSaved: hurst_step1_trades_with_features.parquet, hurst_step1_summary.csv")
