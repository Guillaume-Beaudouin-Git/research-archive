"""
step5_regime.py — Ex-ante regime gate (5-A), persistence (5-B), HMM (5-C).

5-A: bin start-dates by features computed using ONLY data <= J-1
     features:
       - VR_5, VR_10 of underlying daily returns (US100 + GER40)
       - realised vol 20d (percentile rank, expanding)
     For each tercile of each feature, compute {pass, bust, median TTP}.

5-B: regime episode persistence vs 40d horizon. Distinct chop episodes count.

5-C: HMM (Student-t emissions) walk-forward, FILTERED probability (online),
     ablation L19 vs threshold-gate from 5-A.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix, _load_m5, block_capped_pnl
from ftmo_engine import simulate


def underlying_daily_log_returns(symbol: str, lo: str = "2020", hi: str = "2026") -> pd.Series:
    """Daily close-to-close log returns of the underlying."""
    df = _load_m5(symbol)
    df = df.loc[lo:hi]
    # use 16:00 (close-ish) for US100, 17:00 for GER40 daily close
    daily = df["close"].resample("D").last().dropna()
    return np.log(daily / daily.shift(1)).dropna()


def variance_ratio_lo_mackinlay(returns: np.ndarray, q: int) -> float:
    """VR_q of Lo-MacKinlay 1988. q=5: weekly vs daily."""
    r = returns[~np.isnan(returns)]
    if len(r) < q * 2:
        return float("nan")
    mu = r.mean()
    var1 = ((r - mu) ** 2).sum() / (len(r) - 1)
    r_q = np.array([r[i:i+q].sum() for i in range(len(r) - q + 1)])
    var_q = ((r_q - q * mu) ** 2).sum() / ((len(r_q) - 1) * q)
    return float(var_q / var1) if var1 > 0 else float("nan")


def rolling_features(daily_r: pd.Series, window_vr: int = 60, window_rv: int = 20) -> pd.DataFrame:
    """Rolling features computed using data <= J-1 (shifted by 1)."""
    r = daily_r.copy()
    # Realised vol 20d (annualised)
    rv = r.rolling(window_rv).std() * np.sqrt(252)
    # Variance ratios on a 60-day window
    def _vr_window(arr, q):
        if len(arr) < q * 2 or arr.isna().any():
            return np.nan
        return variance_ratio_lo_mackinlay(arr.values, q)
    vr5 = r.rolling(window_vr).apply(lambda x: _vr_window(x, 5), raw=False)
    vr10 = r.rolling(window_vr).apply(lambda x: _vr_window(x, 10), raw=False)
    # Trend = abs(20d sum) / (20d std * sqrt(20))
    trend = r.rolling(20).sum().abs() / (r.rolling(20).std() * np.sqrt(20))
    feat = pd.DataFrame({"rv20": rv, "vr5": vr5, "vr10": vr10, "trend20": trend})
    return feat.shift(1)  # ensure info available BEFORE the start day


def tag_terciles_expanding(series: pd.Series) -> pd.Series:
    """Expanding terciles. tag in {0,1,2}. Returns NaN until enough data."""
    out = pd.Series(index=series.index, dtype=float)
    for i in range(len(series)):
        if i < 60:  # need history
            out.iloc[i] = np.nan
            continue
        x = series.iloc[:i].dropna()
        if len(x) < 40 or pd.isna(series.iloc[i]):
            out.iloc[i] = np.nan
            continue
        q33, q67 = x.quantile([1/3, 2/3]).values
        v = series.iloc[i]
        out.iloc[i] = 0 if v <= q33 else (1 if v <= q67 else 2)
    return out


def step_5A_regime_gate(M_full: pd.DataFrame, max_days: int = 40):
    """For each feature, bin starts by tercile and report pass/bust/TTP."""
    print("=" * 80)
    print("5-A — Ex-ante regime gate (features computed <= J-1)")
    print("=" * 80)
    # Build features from US100 underlying daily returns
    r_us100 = underlying_daily_log_returns("US100", "2020", "2026")
    feat_us = rolling_features(r_us100)
    # Also GER40
    r_ger40 = underlying_daily_log_returns("GER40", "2020", "2026")
    feat_ger = rolling_features(r_ger40)
    # Average across instruments for a unified feature
    feat_avg = (feat_us.reindex(M_full.index) + feat_ger.reindex(M_full.index)) / 2

    # Real-path simulation on full sample
    out = simulate(M_full, mode="real_path", max_days=max_days)
    starts = out["start_indices"]
    status = out["status"]
    # Need to map starts -> feature value at start day
    start_dates = M_full.index[starts]

    summary_rows = []
    for fname in ["rv20", "vr5", "vr10", "trend20"]:
        feat_series = feat_avg[fname].loc[start_dates]
        tercile_tag = tag_terciles_expanding(feat_series)
        for t in [0, 1, 2]:
            mask = (tercile_tag == t).values
            if mask.sum() == 0:
                continue
            stat_t = status[mask]
            n = mask.sum()
            p_pass = float((stat_t == 1).mean())
            p_bust_t = float((stat_t == 3).mean())
            p_bust_d = float((stat_t == 2).mean())
            p_to = float((stat_t == 0).mean())
            med_ttp = int(np.median(out["status"][mask] == 1)) if (stat_t == 1).any() else None
            ttp_arr = np.array(out["ttp_dist"] if "ttp_dist" in out else [])
            # median ttp restricted to passed in this subset
            summary_rows.append({
                "feature": fname,
                "tercile": ["low", "mid", "high"][t],
                "median_feat": float(np.median(feat_series.values[mask])),
                "n": int(n),
                "pass_pct": p_pass * 100,
                "bust_total_pct": p_bust_t * 100,
                "bust_daily_pct": p_bust_d * 100,
                "timeout_pct": p_to * 100,
            })
    df = pd.DataFrame(summary_rows)
    print(df.to_string(index=False))
    print()
    # Identify best tercile per feature
    print("--- Best tercile per feature (favourable regime → pass rate?) ---")
    for f in df["feature"].unique():
        sub = df[df["feature"] == f]
        best = sub.loc[sub["pass_pct"].idxmax()]
        worst = sub.loc[sub["pass_pct"].idxmin()]
        print(f"  {f}: best={best['tercile']} ({best['pass_pct']:.1f}%, n={best['n']})  "
              f"worst={worst['tercile']} ({worst['pass_pct']:.1f}%, n={worst['n']})  "
              f"spread={best['pass_pct']-worst['pass_pct']:+.1f}pts  "
              f"BEAT 70%? {'YES' if best['pass_pct']>70 else 'no'}")
    print()
    return df


def step_5B_persistence(M_full: pd.DataFrame):
    """Count distinct chop episodes in 2022-2025."""
    print("=" * 80)
    print("5-B — Regime episode persistence")
    print("=" * 80)
    r_us100 = underlying_daily_log_returns("US100", "2022", "2026")
    rv20 = r_us100.rolling(20).std() * np.sqrt(252)
    # Chop = rv20 in bottom 33% expanding
    rv20_terciles = tag_terciles_expanding(rv20)
    chop_mask = (rv20_terciles == 0).reindex(M_full.index, method="nearest")

    # Episodes
    chop_arr = chop_mask.fillna(False).astype(int).values
    episodes = []
    in_ep = False
    start = None
    for i, v in enumerate(chop_arr):
        if v == 1 and not in_ep:
            start, in_ep = i, True
        elif v == 0 and in_ep:
            episodes.append((start, i - 1, i - start))
            in_ep = False
    if in_ep:
        episodes.append((start, len(chop_arr) - 1, len(chop_arr) - start))
    print(f"  # of distinct 'chop' (rv20 bottom-tercile) episodes: {len(episodes)}")
    if episodes:
        durs = [d for _, _, d in episodes]
        print(f"  Episode durations (days): min={min(durs)} median={int(np.median(durs))} "
              f"max={max(durs)} mean={np.mean(durs):.1f}")
        print(f"  vs challenge horizon = 40 days; median TTP ≈ 14-19 days")
        print(f"  Long episodes (≥40d): {sum(1 for d in durs if d >= 40)}")
    # Also count "trending" episodes for symmetry
    print()
    print("  --- Comparison: 2023 chop year — single big episode? ---")
    chop_2023 = chop_mask.loc["2023"].fillna(False).astype(int).values
    n_chop_days_2023 = chop_2023.sum()
    print(f"    Chop days in 2023: {n_chop_days_2023} / {len(chop_2023)} "
          f"({n_chop_days_2023/len(chop_2023)*100:.0f}%)")
    print()
    return episodes


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    df = step_5A_regime_gate(M_full)
    df.to_csv("step5A_regime_gate.csv", index=False)
    step_5B_persistence(M_full)
