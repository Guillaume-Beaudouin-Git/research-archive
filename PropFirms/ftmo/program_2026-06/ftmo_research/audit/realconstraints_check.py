"""
realconstraints_check.py — Verify K5 / V2+E7 / placebo under REAL FTMO 2026 rules.

FTMO Challenge 2-Step 2026 confirmed rules (web verified):
  - Profit target: 10% P1, 5% P2
  - Daily loss limit: 5%
  - Total loss limit: 10%
  - Min trading days: 4
  - NO time limit (removed July 2023)
  - NO consistency rule on 2-Step (Best Day Rule is 1-Step only)
  - 30-day inactivity contact (not hard fail)

Check 1: K5 + V2+E7 under these exact rules → confirm prior numbers hold
         because nq_sim_v3 already models these constraints.
         Add: enforce min trading days strictly (already done).
         Add: include CENSORED-as-FAIL alternative (worst case) for honesty.

Check 2: Placebo strategies under SAME floor_taper + vol_high sizing:
  (a) K5 ORB        : real V2+E7 daily R
  (b) Random        : iid Gaussian daily R with same mean/std as K5
                       + 0 on non-trading days (matches K5 trade frequency)
  (c) Long-bias     : NQ daily close-to-close return, scaled to similar vol
  (d) Long-bias-no-cost: same as (c) but cost = 0 (theoretical max)

Check 3: V2+E7 STANDALONE (no floor_taper, no vol_high) regime decomp.
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
from lever_b_conditional_oof import (compute_vol_tag, compute_event_flag,
                                       vol_regime_sizing, event_sizing,
                                       VOL_CONFIGS)
from combined_pushpass import SPECS, build_daily_R_for_spec

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

COST_BPS = 2.0


# ---------------------------------------------------------------------------
# Stricter "censored = fail" view of p_funded
# ---------------------------------------------------------------------------

def eval_p_funded_strict(daily_R: pd.Series, mgmt: dict,
                          start_indices: np.ndarray | None = None,
                          block_cap_default: float = 0.005) -> dict:
    """Run sim ; report both 'standard' (excludes censored) and 'strict' (censored=FAIL)."""
    bcp1 = mgmt.get("block_cap_p1", block_cap_default)
    bcp2 = mgmt.get("block_cap_p2", block_cap_default)
    kw = {k: v for k, v in mgmt.items() if k not in ("block_cap_p1", "block_cap_p2")}
    si = start_indices.tolist() if start_indices is not None else None
    out = simulate_2step_v3(daily_R, block_cap_p1=bcp1, block_cap_p2=bcp2,
                              start_indices=si, **kw)
    n_total = out["n_total"]
    n_funded = out["n_funded"]
    n_resolved = out["n_resolved"]
    p_funded_standard = (n_funded / n_resolved * 100) if n_resolved > 0 else float("nan")
    p_funded_strict = (n_funded / n_total * 100) if n_total > 0 else float("nan")
    return {
        "n_total": n_total,
        "n_resolved": n_resolved,
        "n_funded": n_funded,
        "p_funded_standard_pct": round(p_funded_standard, 2)
            if not pd.isna(p_funded_standard) else float("nan"),
        "p_funded_strict_pct": round(p_funded_strict, 2)
            if not pd.isna(p_funded_strict) else float("nan"),
        "censored_pct": round(out["censored_pct"], 1),
    }


# ---------------------------------------------------------------------------
# Placebo daily R generators
# ---------------------------------------------------------------------------

def build_placebo_random(ref_dR: pd.Series, seed: int = 42) -> pd.Series:
    """Random daily R with same mean/std and SAME trade-frequency mask as ref_dR.

    On no-trade days (R=NaN in ref), placebo also has NaN (so simulator skips).
    On trade days, R ~ N(mean_ref, std_ref).
    """
    rng = np.random.default_rng(seed)
    out = pd.Series(np.nan, index=ref_dR.index)
    trade_mask = ref_dR.notna()
    n_trades = int(trade_mask.sum())
    if n_trades == 0:
        return out
    mean = ref_dR.dropna().mean()
    std = ref_dR.dropna().std()
    samples = rng.normal(mean, std, size=n_trades)
    out.loc[trade_mask] = samples
    return out


def build_placebo_long_bias(nq_df: pd.DataFrame, cost_bps: float = 2.0,
                              or_typical_bps: float = 50.0) -> pd.Series:
    """Long-bias: long every day at OR close, exit at RTH close.

    Daily R = (close - or_close) / (or_range_typical) — net of cost in bps.
    or_typical_bps ≈ 50 bps (median ORB range in v3 data).
    """
    df = nq_df.copy()
    h, m = df.index.hour, df.index.minute
    sess = df[((h > 9) | ((h == 9) & (m >= 30))) & (h < 16)].copy()
    sess["day"] = sess.index.normalize()
    rows = []
    for day, g in sess.groupby("day"):
        if len(g) < 50:
            continue
        # Entry = OR close (= close of 30-min after open = bar at 09:59 ET)
        # OR is first 30 1-min bars
        entry_px = float(g.iloc[29]["close"]) if len(g) > 30 else float(g.iloc[0]["close"])
        close_px = float(g.iloc[-1]["close"])
        cost_px = entry_px * (cost_bps / 10000.0)
        # Convert price move to R, where R = or_typical_bps × entry_px / 10000
        risk = entry_px * (or_typical_bps / 10000.0)
        r_realised = ((close_px - entry_px) - cost_px) / risk
        rows.append({"date": pd.Timestamp(day), "r_realised": r_realised})
    if not rows:
        return pd.Series(dtype=float)
    tl = pd.DataFrame(rows).set_index("date")
    all_dates = pd.bdate_range(tl.index.min(), tl.index.max())
    return tl["r_realised"].reindex(all_dates)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("=" * 110)
    print("REAL CONSTRAINTS CHECK + PLACEBO TEST")
    print("=" * 110)
    print("FTMO 2026 rules: P1+10% / P2+5%, DD daily 5% total 10%, min 4 trading days, NO time limit, NO consistency rule (2-Step)")
    print()

    # Build conditioning vars
    log.info("Building conditioning variables...")
    nq = load_instrument(SLEEVES["NQ"])
    daily_close = nq["close"].resample("B").last().dropna()
    vol_tag = compute_vol_tag(daily_close)
    bd_idx = pd.bdate_range(daily_close.index.min(), daily_close.index.max())
    event_flag = compute_event_flag(bd_idx)
    vol_tag_aligned = vol_tag.reindex(bd_idx).ffill().fillna("mid")

    # Build K5 (V2+E7+floor+vol_high) and V2+E7 (Lever A alone) daily R series
    K_SPECS = {
        "K1_V2E7_lever_a": SPECS["K1_V2_E7"],
        "K2_V2E7_floor": SPECS["K2_V2E7_floor"],
        "K5_V2E7_floor_vol_high": SPECS["K5_V2E7_floor_vol"],
    }
    daily_R_per_K = {}
    mgmt_per_K = {}
    for name, spec in K_SPECS.items():
        log.info(f"  Building {name}...")
        dR, _ = build_daily_R_for_spec(spec, vol_tag_aligned, event_flag)
        daily_R_per_K[name] = dR
        mgmt_per_K[name] = spec["mgmt"]

    K5_R = daily_R_per_K["K5_V2E7_floor_vol_high"]
    K5_mgmt = mgmt_per_K["K5_V2E7_floor_vol_high"]

    # ============================================================
    # CHECK 1 — K5 + Lever A under REAL FTMO rules (already correct)
    # ============================================================
    print("=" * 110)
    print("CHECK 1 — K5 + V2+E7 under FTMO 2026 (NO time limit, simulator already matches)")
    print("=" * 110)
    print("Reporting both 'standard' (excludes censored) AND 'strict' (censored=FAIL = worst case).")
    print()

    boundaries = build_fold_boundaries(K5_R, WF_FOLD_END_DATES)
    test_start_first = boundaries[0][1]
    test_end_last = boundaries[-1][2]
    test_starts_all = np.arange(test_start_first, test_end_last)

    rows = []
    for name in K_SPECS:
        dR = daily_R_per_K[name]
        mgmt = mgmt_per_K[name]
        is_res = eval_p_funded_strict(dR, mgmt)
        oof_res = eval_p_funded_strict(dR, mgmt, start_indices=test_starts_all)
        rows.append({
            "config": name,
            "in_sample_p_funded_pct": is_res["p_funded_standard_pct"],
            "in_sample_strict_pct": is_res["p_funded_strict_pct"],
            "in_sample_censored_pct": is_res["censored_pct"],
            "oof_p_funded_pct": oof_res["p_funded_standard_pct"],
            "oof_strict_pct": oof_res["p_funded_strict_pct"],
            "oof_censored_pct": oof_res["censored_pct"],
            "oof_n_total": oof_res["n_total"],
            "oof_n_resolved": oof_res["n_resolved"],
            "oof_n_funded": oof_res["n_funded"],
        })
    check1_df = pd.DataFrame(rows)
    print(check1_df.to_string(index=False))
    check1_df.to_csv(ROOT / "realconstraints_check1.csv", index=False)
    print()

    # ============================================================
    # CHECK 2 — Placebo under floor_taper + vol_high
    # ============================================================
    print("=" * 110)
    print("CHECK 2 — PLACEBO: floor_taper+vol_high with ORB / random / long-bias entries")
    print("=" * 110)
    print("If random/long-bias ≈ ORB → the ORB SIGNAL contributes nothing; gains are 100% bêta+floor.")
    print()

    placebo_R_per = {}

    # (a) K5 = ORB
    placebo_R_per["a_K5_ORB"] = K5_R

    # (b) Random: same mean/std as K5 daily R, on same trade-day mask, vol_high scaling applied
    base_V2E7_R = daily_R_per_K["K1_V2E7_lever_a"]  # unscaled by vol
    random_R_raw = build_placebo_random(base_V2E7_R, seed=42)
    # Apply same vol_high scaling that K5 uses
    vol_sizing = VOL_CONFIGS["B04_vol_high_only"]
    random_R = vol_regime_sizing(random_R_raw, vol_tag_aligned.reindex(random_R_raw.index),
                                   vol_sizing)
    placebo_R_per["b_random_iid"] = random_R

    # (c) Long-bias: NQ open→close return
    log.info("Building long-bias placebo (NQ open→close, no signal)...")
    long_bias_R = build_placebo_long_bias(nq, cost_bps=COST_BPS)
    # Scale by vol_high too (for apples-to-apples)
    long_bias_R_scaled = vol_regime_sizing(long_bias_R, vol_tag_aligned.reindex(long_bias_R.index),
                                             vol_sizing)
    placebo_R_per["c_long_bias_open_close"] = long_bias_R_scaled

    # (d) Long-bias no cost (theoretical max from pure NQ drift)
    long_bias_R0 = build_placebo_long_bias(nq, cost_bps=0.0)
    long_bias_R0_scaled = vol_regime_sizing(long_bias_R0, vol_tag_aligned.reindex(long_bias_R0.index),
                                              vol_sizing)
    placebo_R_per["d_long_bias_no_cost"] = long_bias_R0_scaled

    # Also: (e) random WITHOUT floor_taper to show what randomness gives alone
    rows = []
    floor_mgmt = {"floor_proximity_taper": True, "taper_min_factor": 0.25}
    no_floor_mgmt = {}

    for name, dR in placebo_R_per.items():
        # With floor_taper
        is_floor = eval_p_funded_strict(dR, floor_mgmt)
        # Test fold OOF
        try:
            bds = build_fold_boundaries(dR, WF_FOLD_END_DATES)
            test_starts = np.arange(bds[0][1], bds[-1][2])
        except Exception:
            test_starts = None
        oof_floor = eval_p_funded_strict(dR, floor_mgmt, start_indices=test_starts) if test_starts is not None else {}
        # Without floor_taper for reference
        oof_nofloor = eval_p_funded_strict(dR, no_floor_mgmt, start_indices=test_starts) if test_starts is not None else {}
        # Per-day stats
        dR_clean = dR.dropna()
        rows.append({
            "config": name,
            "n_days": len(dR),
            "n_trade_days": int(dR_clean.shape[0]) if not dR_clean.empty else 0,
            "mean_R": round(float(dR_clean.mean()), 4) if not dR_clean.empty else float("nan"),
            "std_R": round(float(dR_clean.std()), 4) if not dR_clean.empty else float("nan"),
            "floor_in_sample_pct": is_floor.get("p_funded_standard_pct"),
            "floor_OOF_pct": oof_floor.get("p_funded_standard_pct"),
            "floor_OOF_strict_pct": oof_floor.get("p_funded_strict_pct"),
            "floor_OOF_censored_pct": oof_floor.get("censored_pct"),
            "no_floor_OOF_pct": oof_nofloor.get("p_funded_standard_pct"),
            "no_floor_OOF_strict_pct": oof_nofloor.get("p_funded_strict_pct"),
        })
    check2_df = pd.DataFrame(rows)
    print(check2_df.to_string(index=False))
    check2_df.to_csv(ROOT / "realconstraints_check2_placebo.csv", index=False)
    print()

    # ============================================================
    # CHECK 3 — V2+E7 standalone regime decomp (no floor_taper, no vol_high)
    # ============================================================
    print("=" * 110)
    print("CHECK 3 — V2+E7 (Lever A SEUL) regime decomposition")
    print("=" * 110)

    V2E7_R = daily_R_per_K["K1_V2E7_lever_a"]
    no_mgmt = {}
    REGIMES = [
        ("2010-2012", "2010-06-01", "2013-01-01"),
        ("2013-2015", "2013-01-01", "2016-01-01"),
        ("2016-2018", "2016-01-01", "2019-01-01"),
        ("2019-2021", "2019-01-01", "2022-01-01"),
        ("2022-2023", "2022-01-01", "2024-01-01"),
        ("2024-2026", "2024-01-01", "2027-01-01"),
    ]
    rows = []
    for name, lo, hi in REGIMES:
        mask = (V2E7_R.index >= pd.Timestamp(lo)) & (V2E7_R.index < pd.Timestamp(hi))
        idx = np.where(mask)[0]
        if len(idx) == 0:
            rows.append({"block": name, "n_days": 0})
            continue
        res = eval_p_funded_strict(V2E7_R, no_mgmt, start_indices=idx)
        rows.append({
            "block": name,
            "n_days": len(idx),
            "n_resolved": res["n_resolved"],
            "n_funded": res["n_funded"],
            "p_funded_pct": res["p_funded_standard_pct"],
            "p_funded_strict_pct": res["p_funded_strict_pct"],
            "censored_pct": res["censored_pct"],
        })
    check3_reg_df = pd.DataFrame(rows)
    print("\nV2+E7 alone (no floor, no vol scaling) — regime buckets:")
    print(check3_reg_df.to_string(index=False))
    check3_reg_df.to_csv(ROOT / "realconstraints_check3_regime.csv", index=False)
    print()

    # Vol regime conditional for V2+E7 alone
    vol_aligned = vol_tag_aligned.reindex(V2E7_R.index)
    rows = []
    for r_name in ["low", "mid", "high"]:
        idx = np.where(vol_aligned == r_name)[0]
        if len(idx) < 30:
            continue
        res = eval_p_funded_strict(V2E7_R, no_mgmt, start_indices=idx)
        rows.append({
            "vol_regime": r_name,
            "n_starts": len(idx),
            "n_resolved": res["n_resolved"],
            "n_funded": res["n_funded"],
            "p_funded_pct": res["p_funded_standard_pct"],
            "p_funded_strict_pct": res["p_funded_strict_pct"],
            "censored_pct": res["censored_pct"],
        })
    check3_vol_df = pd.DataFrame(rows)
    print("V2+E7 alone — vol regime tercile (NOWCAST):")
    print(check3_vol_df.to_string(index=False))
    check3_vol_df.to_csv(ROOT / "realconstraints_check3_vol.csv", index=False)
    print()

    # Identify current regime
    last_idx = V2E7_R.dropna().index[-1] if not V2E7_R.dropna().empty else V2E7_R.index[-1]
    rv_last = vol_aligned.loc[last_idx] if last_idx in vol_aligned.index else "unknown"
    print(f"  Current regime: **{rv_last}**")
    cur_row = check3_vol_df[check3_vol_df["vol_regime"] == rv_last]
    if len(cur_row) > 0:
        print(f"  V2+E7 alone today (régime={rv_last}): p_funded = {cur_row.iloc[0]['p_funded_pct']:.1f}% "
               f"(strict = {cur_row.iloc[0]['p_funded_strict_pct']:.1f}%)")
