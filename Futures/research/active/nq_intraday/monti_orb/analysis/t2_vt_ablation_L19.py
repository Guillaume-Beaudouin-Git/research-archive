"""
T2 — Vol-targeting ablation (L24 protocol).

Tests whether ATR-based position sizing improves Sharpe vs fixed 1-contract baseline.
Since Sharpe is scale-invariant, A_rescaled = A_raw (trivially same Sharpe).

Three configurations at same realized-σ reference:
  A_raw     : 1 NQ contract fixed → σ_A, Sharpe_A
  A_rescaled: not separately run (Sharpe is scale-invariant → Sharpe = Sharpe_A)
  B         : vol-targeted; target_$ calibrated so median(contracts_B) = 1

Decision rule (L19/L24):
  Sharpe(B) - Sharpe(A) > 0.1 WITH bootstrap paired t-stat > 1.5
    → vol-targeting adds real timing edge
  Otherwise:
    → only leverage rescaling, no alpha gain
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parents[6]))

from data.cache import load_nq_1min, get_cached_or_fetch_fred
from Futures.research.active.nq_intraday.monti_orb.signal import monti_orb_signal
from Futures.research.active.nq_intraday.monti_orb.backtest import (
    build_atr, daily_returns, sharpe_hac, POINT_VALUE,
)


def _bootstrap_sharpe_diff(dn_a: "np.ndarray", dn_b: "np.ndarray",
                            n_boot: int = 10_000, seed: int = 42) -> tuple[float, float]:
    """Paired block bootstrap for Sharpe(B) - Sharpe(A)."""
    rng   = np.random.default_rng(seed)
    n     = min(len(dn_a), len(dn_b))
    a, b  = dn_a[:n], dn_b[:n]
    block = 5
    diffs = []
    for _ in range(n_boot):
        starts = rng.integers(0, max(1, n - block + 1), size=max(1, n // block))
        idx    = np.concatenate([np.arange(s, min(s + block, n)) for s in starts])[:n]
        sa_b   = a[idx]; sb_b = b[idx]
        def sr(x: np.ndarray) -> float:
            m = x.mean(); s = x.std(ddof=1)
            return m / s * np.sqrt(252) if s > 1e-9 else 0.0
        diffs.append(sr(sb_b) - sr(sa_b))
    arr = np.array(diffs)
    t_stat = arr.mean() / (arr.std(ddof=1) + 1e-12)
    return float(arr.mean()), float(t_stat)


def run(trades=None) -> dict:
    print("=" * 60)
    print("T2 — Vol-targeting ablation (L24)")
    print("=" * 60)

    df = load_nq_1min()
    if trades is None:
        trades = monti_orb_signal(df)

    rf = get_cached_or_fetch_fred("DTB3", "2022-12-26", "2025-12-11")
    atr = build_atr(df, window=20)

    # ── A_raw: 1 contract fixed ──────────────────────────────────────────────
    tl_a, dn_a = daily_returns(
        trades, sizing="fixed", n_contracts_fixed=1, rf_series=rf["dtb3"]
    )
    sr_a = sharpe_hac(dn_a)

    # ── B: vol-targeted, calibrate target_$ so median(contracts) ≈ 1 ────────
    # target_dollar_risk = median(ATR) × POINT_VALUE × 1  (1 contract median)
    atr_idx = atr.copy()
    atr_idx.index = atr_idx.index.normalize()
    active = trades[~trades["exit_reason"].isin(["no_signal", "insufficient_orb"])]
    atr_on_trade_days = atr_idx.reindex(active.index, method="ffill").dropna()
    atr_median = float(atr_on_trade_days.median()) if len(atr_on_trade_days) > 0 else 50.0
    target_dollar_risk = atr_median * POINT_VALUE  # USD risk such that median → 1 contract

    tl_b, dn_b = daily_returns(
        trades, sizing="vol_targeted",
        target_dollar_risk=target_dollar_risk,
        atr_series=atr,
        rf_series=rf["dtb3"],
    )
    sr_b = sharpe_hac(dn_b)

    delta_sr = float(sr_b - sr_a) if (sr_b is not None and sr_a is not None) else np.nan

    # Align daily series on common dates
    common = dn_a.index.intersection(dn_b.index)
    mean_diff, t_stat = _bootstrap_sharpe_diff(
        dn_a.reindex(common).fillna(0.0).values,
        dn_b.reindex(common).fillna(0.0).values,
    )

    # Contract distribution for B
    if not tl_b.empty:
        c_dist = tl_b["contracts"].value_counts().sort_index().to_dict()
        c_mean = float(tl_b["contracts"].mean())
    else:
        c_dist, c_mean = {}, 1.0

    print(f"\nATR median (on trade days): {atr_median:.1f} pts")
    print(f"Target $ risk calibrated:  ${target_dollar_risk:,.0f}")
    print(f"Mean contracts_B:          {c_mean:.2f}")
    print(f"Contract distribution B:   {c_dist}")
    print(f"\nSharpe_A (fixed 1 ctr):   {sr_a:.4f}")
    print(f"Sharpe_B (vol-targeted):  {sr_b:.4f}")
    print(f"Δ Sharpe (B – A):         {delta_sr:+.4f}")
    print(f"Bootstrap Δ mean:          {mean_diff:+.4f}")
    print(f"Bootstrap t-stat:          {t_stat:.3f}  (threshold: 1.5)")

    vt_adds_value = (delta_sr > 0.1) and (t_stat > 1.5)
    if vt_adds_value:
        print("\n[T2] Vol-targeting ADDS REAL EDGE: Δ>0.1 and t>1.5")
    else:
        print("\n[T2] Vol-targeting does NOT improve Sharpe beyond leverage rescaling")
        if delta_sr <= 0:
            print("      (direction wrong: vol-targeting HURTS performance)")

    result = {
        "test":               "T2",
        "atr_median_pts":     round(atr_median, 2),
        "target_dollar_risk": round(target_dollar_risk, 2),
        "contracts_mean_B":   round(c_mean, 3),
        "sharpe_A":           round(float(sr_a), 4) if sr_a is not None else None,
        "sharpe_B":           round(float(sr_b), 4) if sr_b is not None else None,
        "delta_sharpe":       round(float(delta_sr), 4) if not np.isnan(delta_sr) else None,
        "bootstrap_t":        round(float(t_stat), 3),
        "vt_adds_value":      bool(vt_adds_value),
    }
    return result


if __name__ == "__main__":
    run()
