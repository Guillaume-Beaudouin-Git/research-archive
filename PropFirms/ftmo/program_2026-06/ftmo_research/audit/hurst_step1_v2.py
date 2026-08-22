"""
hurst_step1_v2.py — Optimized: compute Hurst/vol-z PER TRADE only, not per bar.

For each trade entry timestamp T, get last 200 5-min closes BEFORE T,
compute Hurst from those returns. Same for vol-z.

This is O(N_trades) = ~4000 instead of O(N_bars) = ~1M.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from functools import lru_cache


DATA_PATH = Path(__file__).resolve().parents[1].parent / "raw" / "NQ_1min_databento_2010-2026.parquet"


@lru_cache(maxsize=1)
def load_nq_5min_rth() -> pd.DataFrame:
    """Load NQ 5-min filtered to is_rth & ~is_roll_day (same as nq_orb_backtest)."""
    df = pd.read_parquet(DATA_PATH)
    df = df[df["is_rth"] & ~df["is_roll_day"]].copy()
    df_5m = df.groupby(df.index.date).apply(
        lambda g: g[["open", "high", "low", "close", "volume"]].resample("5min").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
        ).dropna()
    )
    return df_5m.reset_index(level=0, drop=True).sort_index()


def compute_hurst_vr(returns: np.ndarray, lags: tuple = (2, 4, 8)) -> float:
    """Hurst via Lo-MacKinlay variance ratio at multiple lags. Median H."""
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


def classify(H: float, vol_z: float) -> tuple[str, str]:
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


def per_trade_features(df_trades: pd.DataFrame, df_5m: pd.DataFrame,
                       window: int = 200, rv_window: int = 25,
                       vol_lookback_bars: int = 6000):
    """For each trade, compute H + vol_z from trailing bars BEFORE the trade's date."""
    # Compute returns once
    close = df_5m["close"].values
    log_ret = np.zeros(len(close))
    log_ret[1:] = np.log(close[1:] / close[:-1])
    # We need: for each trade date, the index in df_5m of the LAST bar of the prior trading day
    # (= the last 5-min RTH close before the OR period of trade day)
    # Trade index = the date the trade occurred (Timestamp normalized to date)
    df_5m_dates = pd.Series(df_5m.index.date, index=df_5m.index)
    # For each trade, find the largest df_5m timestamp whose .date() < trade.date()
    # (= last RTH close of the previous trading day)
    H_arr = []
    vol_z_arr = []
    h_reg_arr = []
    v_reg_arr = []
    RV25_arr = []

    # Pre-compute global mean/std for vol_z normalisation
    # Use a global mean/std of RV25 (cleaner than per-bar 6m rolling here)
    # Actually for paper fidelity, use a 6-month-equivalent ~6000 bars trailing
    # Approximation: use trailing N bars of bar-index for each trade.

    for trade_date, _ in df_trades.iterrows():
        td = pd.Timestamp(trade_date).date()
        # Find last bar with date < td
        mask = df_5m_dates < td
        if not mask.any():
            H_arr.append(np.nan); vol_z_arr.append(np.nan)
            h_reg_arr.append("unknown"); v_reg_arr.append("unknown")
            RV25_arr.append(np.nan)
            continue
        # Index of last bar with date < td
        last_idx = np.where(mask.values)[0][-1]
        if last_idx < window:
            H_arr.append(np.nan); vol_z_arr.append(np.nan)
            h_reg_arr.append("unknown"); v_reg_arr.append("unknown")
            RV25_arr.append(np.nan)
            continue
        # Trailing window of returns (last `window` returns before last_idx)
        ret_window = log_ret[last_idx - window + 1: last_idx + 1]
        H = compute_hurst_vr(ret_window)
        # RV25: last 25 returns std
        rv_arr = log_ret[max(0, last_idx - rv_window + 1): last_idx + 1]
        RV25 = float(rv_arr.std(ddof=1)) if len(rv_arr) > 1 else np.nan
        # vol_z: compare RV25 to recent baseline (trailing N bars)
        if last_idx >= vol_lookback_bars + rv_window:
            # Compute trailing RV25 series for normalisation
            lookback_start = last_idx - vol_lookback_bars
            # Window of RV25 values: for each end-bar in lookback, compute std of last 25 ret
            # Approximation: use rolling std on log_ret then compute mean/std on the trailing window
            roll_std = pd.Series(log_ret[lookback_start:last_idx]).rolling(rv_window).std(ddof=1).dropna()
            if len(roll_std) > 100:
                mean_n = roll_std.mean()
                std_n = roll_std.std(ddof=1)
                vol_z = (RV25 - mean_n) / std_n if std_n > 0 else np.nan
            else:
                vol_z = np.nan
        else:
            vol_z = np.nan
        H_arr.append(H)
        vol_z_arr.append(vol_z)
        RV25_arr.append(RV25)
        h_reg, v_reg = classify(H, vol_z)
        h_reg_arr.append(h_reg)
        v_reg_arr.append(v_reg)

    return pd.DataFrame({
        "H": H_arr, "vol_z": vol_z_arr, "RV25": RV25_arr,
        "h_regime": h_reg_arr, "v_regime": v_reg_arr,
    }, index=df_trades.index)


def table_by_regime(df: pd.DataFrame, r_col: str = "r_net_v2e7"):
    print(f"\n--- WR / avg R / PnL by H regime (r_col={r_col}) ---")
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
    print(f"\n--- Combined 3×3 mean_R ---")
    pivot = df.pivot_table(index="h_regime", columns="v_regime",
                            values=r_col, aggfunc="mean")
    pivot = pivot.reindex(index=["persistent", "neutral", "anti_persistent"],
                          columns=["vol_high", "vol_mid", "vol_low"])
    print(pivot.round(4).to_string())
    pivot_n = df.pivot_table(index="h_regime", columns="v_regime",
                               values=r_col, aggfunc="count")
    pivot_n = pivot_n.reindex(index=["persistent", "neutral", "anti_persistent"],
                                columns=["vol_high", "vol_mid", "vol_low"])
    print(f"\n--- Combined 3×3 count ---")
    print(pivot_n.to_string())


if __name__ == "__main__":
    print("=" * 95)
    print("HURST STEP 1 v2 — gradient par régime (point-in-time, optimized)")
    print("=" * 95)
    print("\nLoading NQ 5-min RTH...")
    df_5m = load_nq_5min_rth()
    print(f"  {len(df_5m):,} bars, range {df_5m.index.min()} → {df_5m.index.max()}")

    print("\nLoading V2+E7 trades (ORB 30-min + trail_BE@1R)...")
    df_trades = pd.read_parquet("breakout_phase2_trades_ORB_30min.parquet")
    df_trades["r_net_v2e7"] = df_trades["r_net_trail_BE@1R"]
    print(f"  {len(df_trades)} trades")

    print("\nComputing Hurst + vol-z per trade (window=200 5-min bars trailing)...")
    feat = per_trade_features(df_trades, df_5m, window=200, rv_window=25,
                                vol_lookback_bars=6000)
    print(f"  H valid: {feat['H'].notna().sum()}/{len(feat)}")
    print(f"  vol_z valid: {feat['vol_z'].notna().sum()}/{len(feat)}")
    print(f"  H stats: mean={feat['H'].mean():.3f}, std={feat['H'].std():.3f}, "
          f"p10={feat['H'].quantile(0.1):.3f}, p50={feat['H'].quantile(0.5):.3f}, "
          f"p90={feat['H'].quantile(0.9):.3f}")
    print(f"  H regime counts: {feat['h_regime'].value_counts().to_dict()}")
    print(f"  v regime counts: {feat['v_regime'].value_counts().to_dict()}")

    df_full = pd.concat([df_trades, feat], axis=1)
    df_full.to_parquet("hurst_step1_trades_with_features.parquet")

    print("\n" + "=" * 95)
    print("TABLE 3 — Sur les trades V2+E7 (NOS données, ORB 30-min + trail_BE@1R)")
    print("=" * 95)
    table_by_regime(df_full, r_col="r_net_v2e7")

    print("\n--- Same on EOD baseline (sanity) ---")
    table_by_regime(df_full, r_col="r_net_EOD")

    # Save summary
    summary = df_full.groupby(["h_regime", "v_regime"]).agg(
        n=("r_net_v2e7", "count"),
        mean_R=("r_net_v2e7", "mean"),
        WR=("r_net_v2e7", lambda s: (s > 0).mean() * 100),
        cum_R=("r_net_v2e7", "sum"),
    ).round(4)
    summary.to_csv("hurst_step1_summary.csv")
    print(f"\nSaved: hurst_step1_trades_with_features.parquet, hurst_step1_summary.csv")
