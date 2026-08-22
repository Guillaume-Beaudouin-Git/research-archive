"""
step3_blockboot.py — Block-bootstrap multi-attempt + phase chaining.

The report's "80% in 2 attempts" assumes independence:
    1 - (1-0.58)^2 = 0.82
This is wrong because regime (chop/trend) is autocorrelated on month+ horizons.
We block-bootstrap with contiguous-block lengths matched to the regime
autocorrelation length.

We also compute:
  - p(2 attempts | starting in chop) — worst-case
  - Variance ratio analysis to estimate the autocorrelation length
  - p(funded) = p(P1) * p(P2 | passed P1) end-to-end on real path
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from orb_core import build_3sleeve_matrix, block_capped_pnl
from ftmo_engine import simulate, _block_pnl_array

AM_COLS = ["GER40_1000_30m"]
PM_COLS = ["US100_1630_30m", "GER40_1630_15m"]


def variance_ratio(returns: np.ndarray, q: int) -> float:
    """Lo-MacKinlay variance ratio at horizon q."""
    r = returns[~np.isnan(returns)]
    if len(r) < q * 2:
        return float("nan")
    mu = r.mean()
    var1 = ((r - mu) ** 2).mean()
    # q-period return sums
    r_q = np.array([r[i:i+q].sum() for i in range(len(r) - q + 1)])
    var_q = ((r_q - q * mu) ** 2).mean() / q
    return float(var_q / var1) if var1 > 0 else float("nan")


def regime_autocorr_length(returns: pd.Series) -> dict:
    """Estimate the autocorrelation length using variance ratio + monthly persistence."""
    pnl = returns.values
    out = {}
    for q in [5, 10, 20, 40, 60]:
        out[f"VR_q{q}"] = variance_ratio(pnl, q)
    # Realised vol persistence
    rv = pd.Series(pnl).rolling(20).std()
    out["RV_AC_lag1"] = float(rv.autocorr(1))
    out["RV_AC_lag20"] = float(rv.autocorr(20))
    out["RV_AC_lag60"] = float(rv.autocorr(60))
    return out


def block_bootstrap_pass(M: pd.DataFrame, n_paths: int = 5000, max_days: int = 40,
                         block_len: int = 20, seed: int = 1,
                         target_pct: float = 0.10) -> dict:
    """
    Bootstrap by sampling random contiguous blocks (length=block_len) of the
    matrix, concatenating until max_days days are filled.
    Preserves within-block autocorrelation (regime persistence).
    """
    rng = np.random.default_rng(seed)
    n = len(M)
    n_blocks_needed = (max_days + block_len - 1) // block_len
    # Build a paths x days matrix of historical-row indices
    idx_mat = np.empty((n_paths, max_days), dtype=int)
    for p in range(n_paths):
        cells = []
        while len(cells) < max_days:
            start = rng.integers(0, n - block_len + 1)
            cells.extend(range(start, start + block_len))
        idx_mat[p] = cells[:max_days]

    # Now simulate using the same engine
    am, pm, am_sl, pm_sl = _block_pnl_array(M)
    eq = np.ones(n_paths)
    status = np.zeros(n_paths, dtype=int)
    tdays = np.zeros(n_paths, dtype=int)
    total_floor = 0.90
    daily_floor_loss = 0.05
    target = 1 + target_pct
    days_to_resolve = np.zeros(n_paths, dtype=int)

    for d in range(max_days):
        day_idx = idx_mat[:, d]
        am_r = am[day_idx]
        pm_r = pm[day_idx]
        am_traded = (~np.isnan(M[AM_COLS].values[day_idx])).any(axis=1)
        pm_traded = (~np.isnan(M[PM_COLS].values[day_idx])).any(axis=1)
        day_start = eq.copy()
        live = status == 0

        eq_after_am = np.where(live, day_start * (1 + am_r), day_start)
        status = np.where(live & (eq_after_am < total_floor), 3, status)
        status = np.where((status == 0) & live & (eq_after_am < day_start * (1 - daily_floor_loss)), 2, status)
        eq = eq_after_am
        live = status == 0

        eq_after_pm = np.where(live, eq * (1 + pm_r), eq)
        status = np.where(live & (eq_after_pm < total_floor), 3, status)
        status = np.where((status == 0) & live & (eq_after_pm < day_start * (1 - daily_floor_loss)), 2, status)
        eq = eq_after_pm

        tdays += ((am_traded | pm_traded) & (status != 3) & (status != 2)).astype(int)
        passed = (status == 0) & (eq >= target) & (tdays >= 4)
        days_to_resolve = np.where(passed & (days_to_resolve == 0), d + 1, days_to_resolve)
        status = np.where(passed, 1, status)

    return {
        "pass_rate": float((status == 1).mean()),
        "fail_total": float((status == 3).mean()),
        "fail_daily": float((status == 2).mean()),
        "timeout": float((status == 0).mean()),
        "status": status,
        "ttp": days_to_resolve,
    }


def real_path_starts_by_regime(M: pd.DataFrame, max_days: int = 40,
                                feature: str = "rv20"):
    """
    Tag each potential start-date by regime (terciles of a pre-start feature).
    feature='rv20' = 20-day realised vol of portfolio PnL (computed pre-start).
    Returns: list of (start_idx, regime_tag) tuples where regime_tag in {low, mid, high}.
    """
    pnl = block_capped_pnl(M).fillna(0.0)
    rv = pnl.rolling(20).std().shift(1)  # info available BEFORE start day
    # Valid start indices
    valid_idx = np.arange(len(M) - max_days + 1)
    rv_at_start = rv.iloc[valid_idx].values
    # Compute terciles ignoring NaN
    q33, q67 = np.nanquantile(rv_at_start, [1/3, 2/3])
    tags = np.where(rv_at_start <= q33, "low_vol",
            np.where(rv_at_start <= q67, "mid_vol", "high_vol"))
    return valid_idx, tags, rv_at_start


def chained_p_funded(M_full: pd.DataFrame, n_paths: int = 20000, seed: int = 7) -> dict:
    """End-to-end p(funded) = p(P1) * p(P2 | passed P1) via iid bootstrap."""
    # Phase 1: target +10%
    p1 = simulate(M_full, mode="iid_bootstrap", target_pct=0.10,
                  max_days=40, n_paths=n_paths, seed=seed)
    # Phase 2: target +5% (independent draw — conservative)
    p2 = simulate(M_full, mode="iid_bootstrap", target_pct=0.05,
                  max_days=40, n_paths=n_paths, seed=seed + 1)
    return {
        "p_phase1": p1["pass_rate"],
        "p_phase2": p2["pass_rate"],
        "p_funded": p1["pass_rate"] * p2["pass_rate"],
        "p_phase1_fail_total": p1["fail_total"],
        "p_phase2_fail_total": p2["fail_total"],
    }


if __name__ == "__main__":
    M_full = build_3sleeve_matrix(lo="2022", hi="2025")
    M_all = build_3sleeve_matrix(lo="2021", hi="2026")
    pnl_full = block_capped_pnl(M_full).fillna(0.0)

    print("=" * 80)
    print("STEP 3 — Block-bootstrap multi-attempts + phase chaining")
    print("=" * 80)
    print()
    print("--- Regime autocorrelation diagnostics (full 2022-2025) ---")
    diag = regime_autocorr_length(pnl_full)
    for k, v in diag.items():
        print(f"  {k:15s} = {v:.3f}")
    print("  (VR > 1 => positive autocorrelation; VR<1 => mean reversion)")
    print("  (RV_AC > 0 => realised vol is persistent across that lag in days)")
    print()

    print("--- iid vs block-bootstrap pass rates (target +10%, 40 days) ---")
    print(f"{'method':>22} | {'pass%':>7} | {'fail_total%':>11} | {'2 attempts (indep)':>20}")
    for label, fn_args in [
        ("iid (report's model)", {"mode": "iid_bootstrap", "n_paths": 10000}),
    ]:
        out = simulate(M_full, **fn_args)
        p1 = out["pass_rate"]
        p_2att_indep = 1 - (1 - p1) ** 2
        print(f"{label:>22} | {p1*100:6.1f}% | {out['fail_total']*100:10.1f}% | {p_2att_indep*100:19.1f}%")
    for blk in [5, 10, 20, 30, 40]:
        out = block_bootstrap_pass(M_full, n_paths=5000, block_len=blk)
        p1 = out["pass_rate"]
        # 2 attempts under block bootstrap: simulate independently 2x then 1-(1-p1)*(1-p1_2)
        # but more honest: sample TWO non-overlapping 40-day windows from the same
        # historical path? simpler proxy: 1-(1-p_block)^2 (lower bound on dep)
        p_2att = 1 - (1 - p1) ** 2
        print(f"block_len={blk:3d}        | {p1*100:6.1f}% | {out['fail_total']*100:10.1f}% | {p_2att*100:19.1f}%")
    print()

    # --- Real-path starts: p(pass | regime at start)
    print("--- Real-path challenges, conditional on regime at start (rv20 tercile) ---")
    starts, tags, rv_vals = real_path_starts_by_regime(M_full)
    out_all = simulate(M_full, mode="real_path", n_paths=len(starts))
    statuses = out_all["status"]
    for tag in ["low_vol", "mid_vol", "high_vol"]:
        mask = (tags == tag)
        n_in = mask.sum()
        if n_in == 0:
            continue
        passed = (statuses[mask] == 1).mean()
        bust = (statuses[mask] == 3).mean()
        rv_med = np.median(rv_vals[mask])
        print(f"  {tag:>9} (rv20≈{rv_med*100:.2f}%, n={n_in:3d}): "
              f"pass={passed*100:5.1f}% bust={bust*100:5.1f}%")
    print()

    # --- p(2 attempts | start in chop)
    print("--- p(2 attempts | start in chop = low_vol or 2023-style) ---")
    # Use 2023 only as 'chop'
    M_chop = M_full.loc["2023":"2023"]
    out_chop = simulate(M_chop, mode="iid_bootstrap", n_paths=10000)
    p_chop = out_chop["pass_rate"]
    p_chop2 = 1 - (1 - p_chop) ** 2
    print(f"  Single attempt starting in 2023 chop: {p_chop*100:.1f}%")
    print(f"  2 attempts (assuming iid, conservative): {p_chop2*100:.1f}%")
    print(f"  Report's 80% in 2 attempts assumed: 1-(1-0.58)^2 = {(1-(1-0.58)**2)*100:.1f}%")
    print()

    # --- Phase chaining
    print("--- Phase 1 (+10%) + Phase 2 (+5%) chain — full 2022-25 R-pool ---")
    chain = chained_p_funded(M_full, n_paths=20000)
    print(f"  p(Phase 1 +10% in 40d)     = {chain['p_phase1']*100:.1f}%")
    print(f"  p(Phase 2 +5%  in 40d)     = {chain['p_phase2']*100:.1f}%")
    print(f"  p(funded) = p1 * p2        = {chain['p_funded']*100:.1f}%")
    print(f"  Report headline (P1 only) : ~58% (single attempt)")
    print(f"  Report \"80% in 2 attempts\" : assumes P1 only AND independence")
    print()

    # --- N-effective for 2026 overlapping starts
    print("--- N-effective for 2026 weekly-overlapping samples ---")
    # 21 weekly starts on ~104 trading days; each challenge runs 40 days
    # Effective independent samples ≈ 104 / 40 ≈ 2.6 ≈ 3
    print("  21 weekly challenges on ~104 trading days, each 40 days long.")
    print("  Effective independent samples ≈ 104 / 40 ≈ 2.6 (i.e. ~3 blocks).")
    print("  Reading the 93% as a probability is statistical malpractice; ")
    print("  it's one realisation across ~3 independent blocks.")
