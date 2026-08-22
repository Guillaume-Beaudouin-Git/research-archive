"""
placebo_matched.py — Stronger placebo: random matched to K5 exact mean+std.

Goal: clarify how much of K5's 100% comes from ORB SIGNAL STRUCTURE vs just
having positive mean + low std.

Tests under SAME floor_taper:
  (1) K5_actual         : real ORB R
  (2) K5_shuffled       : SAME K5 R values, reordered randomly (preserves dist + sample mean/std,
                           breaks autocorrelation / regime-conditional structure)
  (3) Random_matched    : iid Gaussian with EXACTLY K5's sample mean and std
                           (= floor_taper performance if all you need is K5's central moments)
  (4) Random_matched_high_mean : iid Gaussian with K5's mean × 2 (test floor_taper sensitivity
                                  to higher signal)

If K5_shuffled ≈ K5_actual → time structure doesn't matter, only distribution.
If Random_matched ≈ K5_actual → ORB doesn't add structure either, only mean/std.
If both ≈ K5_actual → floor_taper's 100% is just from "positive-mean, low-std" path,
  not from ORB specifically. ORB adds nothing beyond its central moments.
"""
from __future__ import annotations
from pathlib import Path
import sys
import logging
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from orb_baseline import build_orb_trades, build_daily_R_series, SLEEVES, load_instrument
from nq_sim_v3 import simulate_2step_v3
from oof_framework import build_fold_boundaries, WF_FOLD_END_DATES
from lever_b_conditional_oof import compute_vol_tag, compute_event_flag
from combined_pushpass import SPECS, build_daily_R_for_spec

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def eval_p_funded(daily_R: pd.Series, mgmt: dict,
                    start_indices: np.ndarray | None = None,
                    block_cap: float = 0.005) -> dict:
    bcp1 = mgmt.get("block_cap_p1", block_cap)
    bcp2 = mgmt.get("block_cap_p2", block_cap)
    kw = {k: v for k, v in mgmt.items() if k not in ("block_cap_p1", "block_cap_p2")}
    si = start_indices.tolist() if start_indices is not None else None
    out = simulate_2step_v3(daily_R, block_cap_p1=bcp1, block_cap_p2=bcp2,
                              start_indices=si, **kw)
    return {
        "n_total": out["n_total"],
        "n_resolved": out["n_resolved"],
        "n_funded": out["n_funded"],
        "p_funded_pct": out["p_funded_pct"],
        "censored_pct": out["censored_pct"],
    }


if __name__ == "__main__":
    print("=" * 110)
    print("PLACEBO MATCHED — random with K5's EXACT mean/std, vs shuffled K5")
    print("=" * 110)

    log.info("Building K5 daily R series...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    bd_idx = pd.bdate_range(daily_close.index.min(), daily_close.index.max())
    event_flag = compute_event_flag(bd_idx)
    vol_tag_aligned = vol_tag.reindex(bd_idx).ffill().fillna("mid")
    K5_R, _ = build_daily_R_for_spec(SPECS["K5_V2E7_floor_vol"], vol_tag_aligned, event_flag)
    K5_clean = K5_R.dropna()
    K5_mean = float(K5_clean.mean())
    K5_std = float(K5_clean.std())
    log.info(f"  K5 daily R: n_trade_days={len(K5_clean)}, mean={K5_mean:.4f}, std={K5_std:.4f}")

    floor_mgmt = {"floor_proximity_taper": True, "taper_min_factor": 0.25}
    no_floor_mgmt = {}
    boundaries = build_fold_boundaries(K5_R, WF_FOLD_END_DATES)
    test_starts = np.arange(boundaries[0][1], boundaries[-1][2])

    # Build placebo variants
    placebos = {}

    # (1) Actual K5
    placebos["1_K5_actual"] = K5_R

    # (2) Shuffled K5 (per seed): preserve daily mask, shuffle the R values
    rng = np.random.default_rng(42)
    K5_values = K5_clean.values.copy()
    shuffled = K5_values.copy()
    rng.shuffle(shuffled)
    shuffled_series = pd.Series(np.nan, index=K5_R.index)
    shuffled_series.loc[K5_clean.index] = shuffled
    placebos["2_K5_shuffled"] = shuffled_series

    # (3) Random matched to K5: iid Gaussian with K5's exact sample mean/std
    matched = pd.Series(np.nan, index=K5_R.index)
    matched.loc[K5_clean.index] = rng.normal(K5_mean, K5_std, size=len(K5_clean))
    placebos["3_random_matched"] = matched

    # (4) Random with 2× K5 mean (test floor_taper sensitivity)
    matched_high = pd.Series(np.nan, index=K5_R.index)
    matched_high.loc[K5_clean.index] = rng.normal(K5_mean * 2, K5_std, size=len(K5_clean))
    placebos["4_random_2x_mean"] = matched_high

    # (5) Random with K5/2 mean (lower signal)
    matched_low = pd.Series(np.nan, index=K5_R.index)
    matched_low.loc[K5_clean.index] = rng.normal(K5_mean * 0.5, K5_std, size=len(K5_clean))
    placebos["5_random_half_mean"] = matched_low

    # (6) Random with 0 mean (pure noise)
    matched_zero = pd.Series(np.nan, index=K5_R.index)
    matched_zero.loc[K5_clean.index] = rng.normal(0.0, K5_std, size=len(K5_clean))
    placebos["6_random_zero_mean"] = matched_zero

    print()
    print(f"{'config':25s}  {'mean_R':>8s}  {'std_R':>8s}  {'floor_OOF':>10s}  "
           f"{'nofloor_OOF':>12s}  {'floor_n_resolved':>16s}  {'floor_funded':>12s}")
    print("-" * 110)
    rows = []
    for name, dR in placebos.items():
        clean = dR.dropna()
        m = float(clean.mean())
        s = float(clean.std())
        # With floor
        flr = eval_p_funded(dR, floor_mgmt, start_indices=test_starts)
        # Without floor
        nfl = eval_p_funded(dR, no_floor_mgmt, start_indices=test_starts)
        rows.append({
            "config": name,
            "mean_R": round(m, 4),
            "std_R": round(s, 4),
            "floor_OOF_pct": round(flr["p_funded_pct"], 2) if not pd.isna(flr["p_funded_pct"]) else float("nan"),
            "nofloor_OOF_pct": round(nfl["p_funded_pct"], 2) if not pd.isna(nfl["p_funded_pct"]) else float("nan"),
            "floor_n_resolved": flr["n_resolved"],
            "floor_n_funded": flr["n_funded"],
            "floor_censored": round(flr["censored_pct"], 1),
        })
        print(f"{name:25s}  {m:>+8.4f}  {s:>8.4f}  "
               f"{flr['p_funded_pct']:>9.2f}%  {nfl['p_funded_pct']:>11.2f}%  "
               f"{flr['n_resolved']:>16d}  {flr['n_funded']:>12d}")
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "placebo_matched.csv", index=False)

    print()
    print("=" * 110)
    print("INTERPRETATION")
    print("=" * 110)
    actual = df[df["config"] == "1_K5_actual"].iloc[0]
    shuffled = df[df["config"] == "2_K5_shuffled"].iloc[0]
    matched = df[df["config"] == "3_random_matched"].iloc[0]
    zero = df[df["config"] == "6_random_zero_mean"].iloc[0]

    print(f"\n  K5 actual                : floor OOF = {actual['floor_OOF_pct']:.2f}% (mean = {actual['mean_R']:+.4f})")
    print(f"  K5 shuffled              : floor OOF = {shuffled['floor_OOF_pct']:.2f}%")
    print(f"  Random matched (same mean): floor OOF = {matched['floor_OOF_pct']:.2f}% (sample mean = {matched['mean_R']:+.4f})")
    print(f"  Random zero mean          : floor OOF = {zero['floor_OOF_pct']:.2f}%")

    delta_shuffle = actual['floor_OOF_pct'] - shuffled['floor_OOF_pct']
    delta_matched = actual['floor_OOF_pct'] - matched['floor_OOF_pct']

    print()
    print(f"  Δ K5_actual vs shuffled       : {delta_shuffle:+.2f}pp  (effect of TIME STRUCTURE)")
    print(f"  Δ K5_actual vs matched random : {delta_matched:+.2f}pp  (effect of ORB-specific STRUCTURE)")

    if abs(delta_matched) < 5:
        print("\n  → Random matched ≈ K5 : ORB SIGNAL adds NOTHING beyond its central moments.")
        print("    Floor_taper's 100% = function of mean/std, not of ORB-specific structure.")
    elif delta_matched > 5:
        print("\n  → K5 actual > Random matched : ORB has SOME structural advantage beyond mean/std.")
    else:
        print("\n  → K5 actual < Random matched : random is paradoxically better, ORB structure hurts!")
