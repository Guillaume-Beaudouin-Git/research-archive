"""
T4 — Correlation and orthogonality vs iter_10.

Loads iter_10 signals by re-running the iter_10 signal logic.
Computes:
  - Pearson + Spearman correlation on daily P&L series (overlap period)
  - Trade overlap count (same day)
  - 50/50 equal-weight blend Sharpe vs max individual Sharpe
  - ERC (equal risk contribution) Sharpe if |corr| in (0.3, 0.7)

Verdict:
  |corr| > 0.70  → same edge → keep higher-Sharpe, archive other
  0.30 < |corr| ≤ 0.70 → partial overlap → combine with ERC
  |corr| ≤ 0.30  → orthogonal → candidate for combined Strategy D
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    daily_returns, sharpe_hac,
)


def _load_iter10_daily(df: pd.DataFrame, rf: pd.Series) -> pd.Series:
    """Re-generate iter_10 daily P&L using the exact iter_10 signal logic."""
    repo = Path(__file__).parents[6]
    sys.path.insert(0, str(repo))

    from Futures.research.active.nq_intraday.engine import NQBacktestEngine
    from Futures.research.active.nq_intraday.iter_05 import (
        build_opening_features, signals_from_features,
    )

    # iter_10 parameters (iter_10_refined.py: filter rng≥30 applied BEFORE signals_from_features)
    STRATEGY_GAP  = 0.012
    STRATEGY_STOP = 400.0
    RNG_MIN       = 30.0

    feats = build_opening_features(df)
    feats_filtered = feats[feats["rng"] >= RNG_MIN].copy()
    sigs  = signals_from_features(
        feats_filtered,
        gap_thresh=STRATEGY_GAP,
        dollar_stop=STRATEGY_STOP,
    )

    engine = NQBacktestEngine(df)
    tl, _  = engine.run(sigs)

    if tl.empty:
        return pd.Series(dtype=float)

    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.tz_localize(None).dt.normalize()
    daily_raw  = tl.groupby("date")["pnl_usd"].sum()

    all_days   = pd.bdate_range(daily_raw.index.min(), daily_raw.index.max())
    daily_full = daily_raw.reindex(pd.DatetimeIndex(all_days).normalize(), fill_value=0.0)
    daily_full.index = pd.to_datetime(daily_full.index).normalize()

    rf_pct = rf.copy()
    rf_pct.index = pd.to_datetime(rf_pct.index).normalize()
    if rf_pct.index.tz is not None:
        rf_pct.index = rf_pct.index.tz_localize(None)
    rf_aligned = rf_pct.reindex(daily_full.index, method="ffill").fillna(0.0)
    rf_daily   = (rf_aligned / 100.0 / 252.0) * 50_000.0
    return daily_full - rf_daily


def run(trades=None) -> dict:
    print("=" * 60)
    print("T4 — Comparison vs iter_10")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")

    tl_m, dn_m = daily_returns(
        trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"]
    )
    sr_m = sharpe_hac(dn_m)

    print("Loading iter_10 trades…")
    dn_c = _load_iter10_daily(df, rf["dtb3"])
    sr_c = sharpe_hac(dn_c)

    # Align to common trading days
    common = dn_m.index.intersection(dn_c.index)
    dm     = dn_m.reindex(common).fillna(0.0)
    dc     = dn_c.reindex(common).fillna(0.0)

    # Trade day overlap (both strategies traded on same day)
    trade_days_m = set(tl_m.index) if not tl_m.empty else set()
    active_c     = dc[dc != 0.0].index
    overlap_days = trade_days_m.intersection(set(active_c))
    overlap_pct  = len(overlap_days) / max(len(trade_days_m), 1)

    # Correlations
    pearson_r,  pearson_p  = stats.pearsonr(dm.values,  dc.values)
    spearman_r, spearman_p = stats.spearmanr(dm.values, dc.values)

    # 50/50 blend
    blend_50 = 0.5 * dm + 0.5 * dc
    sr_blend = sharpe_hac(blend_50)

    # ERC blend (equal risk contribution = inverse-vol weighting)
    std_m = float(dm.std(ddof=1))
    std_c = float(dc.std(ddof=1))
    if std_m > 0 and std_c > 0:
        w_m = (1 / std_m) / (1 / std_m + 1 / std_c)
        w_c = 1 - w_m
        blend_erc = w_m * dm + w_c * dc
        sr_erc = sharpe_hac(blend_erc)
    else:
        w_m, w_c, sr_erc = 0.5, 0.5, None

    print(f"\nMonti ORB  — Sharpe: {sr_m:.4f} | N trade days: {len(trade_days_m)}")
    print(f"iter_10    — Sharpe: {sr_c:.4f} | N trade days: {len(active_c)}")
    print(f"\nOverlap:   {len(overlap_days)} days ({overlap_pct:.1%} of Monti trade days)")
    print(f"\nCorrelation (daily P&L on common {len(common)} days):")
    print(f"  Pearson  r = {pearson_r:+.4f}  (p={pearson_p:.4f})")
    print(f"  Spearman r = {spearman_r:+.4f}  (p={spearman_p:.4f})")
    print(f"\nBlend Sharpes:")
    print(f"  50/50   → {sr_blend:.4f}  (max individual: {max(sr_m, sr_c):.4f})")
    print(f"  ERC ({w_m:.2f}/{w_c:.2f}) → {sr_erc:.4f}  " if sr_erc else "  ERC → N/A")

    # Verdict
    abs_r = abs(pearson_r)
    if abs_r > 0.70:
        verdict = "SAME_EDGE"
        keep    = "KEEP_ITER10" if sr_c >= sr_m else "KEEP_MONTI"
        print(f"\n[T4] |corr|={abs_r:.2f} > 0.70 → SAME EDGE → {keep}")
    elif abs_r > 0.30:
        verdict = "PARTIAL_OVERLAP"
        print(f"\n[T4] 0.30 < |corr|={abs_r:.2f} ≤ 0.70 → PARTIAL OVERLAP → test ERC combination")
        if sr_erc and sr_erc > max(sr_m, sr_c):
            print(f"     ERC blend ({sr_erc:.3f}) > max individual → COMBINE")
        else:
            print(f"     ERC blend does not improve → prefer higher-Sharpe individual")
    else:
        verdict = "ORTHOGONAL"
        print(f"\n[T4] |corr|={abs_r:.2f} ≤ 0.30 → ORTHOGONAL → candidate Strategy D")

    result = {
        "test":          "T4",
        "sr_monti":      round(float(sr_m), 4),
        "sr_iter10":     round(float(sr_c), 4),
        "pearson_r":     round(float(pearson_r), 4),
        "spearman_r":    round(float(spearman_r), 4),
        "overlap_pct":   round(float(overlap_pct), 4),
        "sr_blend_50":   round(float(sr_blend), 4) if np.isfinite(sr_blend) else None,
        "sr_blend_erc":  round(float(sr_erc), 4) if sr_erc and np.isfinite(sr_erc) else None,
        "erc_weights":   {"monti": round(w_m, 3), "iter10": round(w_c, 3)},
        "verdict":       verdict,
    }
    return result


if __name__ == "__main__":
    run()
