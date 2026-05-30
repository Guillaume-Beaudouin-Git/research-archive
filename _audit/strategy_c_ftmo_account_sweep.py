"""
Strategy C — FTMO account-size sweep
=====================================

Generalises `_audit/strategy_c_ftmo10k_sim.py` to find the smallest FTMO
account size where p(pass combined phase1 + phase2) > 70% within ≤40
trading days.

Account sizes swept: {10k, 25k, 50k, 100k, 200k}
For each size:
  - daily limit = 5% × capital (trailing from EOD peak)  ← propfirm_canonical.py:5,37
  - max DD      = 10% × capital STATIC from starting balance  ← propfirm_canonical.py:5,38
  - target P1   = 10% × capital
  - target P2   = 5%  × capital

For each (capital, N MNQ), the same engine, the same trade log, the same
block-bootstrap pipeline. NO pre-computed numbers reused (Tradeify 57% etc.
are recomputed from scratch with corrected TV_TRAILING_DD post LOT 3).

If no size meets 70% under the 40-day constraint, the script reruns the
phase 1 simulation with horizon=∞ (FTMO has no time limit) for that size.

Bonus: for the smallest passing size (or the closest if none pass), a finer
sweep of N* ± 2 confirms the local optimum.

Outputs (under _audit/):
  strategy_c_ftmo_account_sweep_results.json
  strategy_c_ftmo_account_sweep_heatmap.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from data.cache import load_nq_1min
from Futures.research.active.nq_intraday.engine import (
    NQBacktestEngine, POINT_VALUE,
)
from Futures.research.active.nq_intraday.iter_05 import (
    build_opening_features,
)
from Futures.research.active.nq_intraday.analysis.iter_10_refined import (
    build_signals,
)

# ─────────────────────────────────────────────────────────────────────────────
# Parameters
# ─────────────────────────────────────────────────────────────────────────────

# FTMO canonical (propfirm_canonical.py:37-38)
FTMO_DAILY_PCT   = 0.05  # 5% trailing from EOD peak
FTMO_MAX_DD_PCT  = 0.10  # 10% STATIC from starting balance
FTMO_P1_PCT      = 0.10  # +10% target
FTMO_P2_PCT      = 0.05  # +5% target

# MNQ specs (config.py:84-86)
MNQ_POINT_VALUE  = 2.0
MNQ_COST_RT      = 2.15

# Sweep parameters
CAPITAL_LIST = [10_000, 25_000, 50_000, 100_000, 200_000]

# N MNQ candidates per capital (rough scaling: ~5 per $10K to start)
N_CANDIDATES_PER_CAPITAL = {
    10_000:  [1, 2, 3, 4, 5, 7, 10],
    25_000:  [3, 5, 8, 10, 12, 15, 20, 25],
    50_000:  [5, 10, 15, 20, 25, 30, 40, 50],
    100_000: [10, 25, 40, 50, 60, 80, 100],
    200_000: [25, 50, 75, 100, 125, 150, 200],
}

MAX_DAYS_BASE   = 40            # user constraint
PASS_THRESHOLD  = 0.70          # 70% target on p(comb)
N_PATHS         = 20_000
SEED            = 42

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Build the iter_10 trade log (once, reused for all sims)
# ─────────────────────────────────────────────────────────────────────────────

def build_iter10_trade_log() -> tuple[pd.DataFrame, dict]:
    print("Loading NQ 1-min...")
    df = load_nq_1min()
    eng = NQBacktestEngine(df)
    feats = build_opening_features(eng.rth)
    sigs = build_signals(feats)
    tl, met = eng.run(sigs)
    print(f"  baseline: N={len(tl)}, Sharpe={met.get('sharpe_daily_hac', 0):.4f}, "
          f"MaxDD={met.get('max_dd_pct', 0)*100:.2f}%, "
          f"Total=${met.get('total_pnl_usd', 0):,.0f}")
    return tl, met


def daily_pnl_for_size(tl_nq: pd.DataFrame, n_contracts: int) -> np.ndarray:
    """
    Convert NQ-full trade log to MNQ at N contracts, aggregate to daily series
    with zero-fill of non-trading days.

    pnl_mnq_per_contract = pnl_pts × $2 - $2.15
    """
    tl = tl_nq.copy()
    pnl_per_mnq = tl["pnl_pts"] * MNQ_POINT_VALUE - MNQ_COST_RT
    tl["pnl_total"] = n_contracts * pnl_per_mnq
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None)
    daily = tl.groupby("date")["pnl_total"].sum()
    all_dates = pd.bdate_range(daily.index.min(), daily.index.max(),
                                freq="C", holidays=[])
    return daily.reindex(pd.DatetimeIndex(all_dates).normalize(),
                          fill_value=0.0).values.astype(np.float64)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Bootstrap and phase simulation (reused from earlier sim)
# ─────────────────────────────────────────────────────────────────────────────

def stationary_block_indices(T: int, length: int, block_size: int,
                              rng: np.random.Generator) -> np.ndarray:
    """Politis-Romano stationary block bootstrap index sampler."""
    idx = np.empty(length, dtype=np.int64)
    pos = 0
    while pos < length:
        block_len = max(1, int(rng.geometric(1.0 / block_size)))
        block_len = min(block_len, length - pos)
        start = int(rng.integers(0, T))
        for k in range(block_len):
            idx[pos + k] = (start + k) % T
        pos += block_len
    return idx


def simulate_phase(daily_pnl: np.ndarray, n_paths: int, max_days: int,
                   capital: float, target: float, daily_limit: float,
                   max_dd: float, block_size: int,
                   rng: np.random.Generator) -> dict:
    """
    One FTMO phase simulation.

    Barriers (absorbing):
      - daily PnL ≤ -(daily_limit × max(1, peak_eod/capital))
        (5% trailing from EOD peak per propfirm_canonical.py:5,37)
      - equity ≤ capital - max_dd  (10% STATIC floor per :38)

    If max_days is None, the loop runs until success or breach (no timeout).
    """
    T = len(daily_pnl)
    status         = np.zeros(n_paths, dtype=np.int8)   # 0=pass, 1=daily, 2=dd, 3=timeout
    days_to_pass   = np.zeros(n_paths, dtype=np.int32)
    max_dd_seen    = np.zeros(n_paths, dtype=np.float64)
    static_floor = capital - max_dd

    # When max_days is None we need a hard sample cap; use T to keep bootstrap valid
    horizon = max_days if max_days is not None else T

    for p in range(n_paths):
        idx = stationary_block_indices(T, horizon, block_size, rng)
        path = daily_pnl[idx]

        equity = capital
        peak_eod = capital
        breached = 0
        passed = False
        for d, day_pnl in enumerate(path):
            day_loss_threshold = -daily_limit * (max(capital, peak_eod) / capital)
            if day_pnl <= day_loss_threshold:
                breached = 1
                equity += day_pnl
                break
            equity += day_pnl
            if equity <= static_floor:
                breached = 2
                break
            peak_eod = max(peak_eod, equity)
            if (equity - capital) >= target:
                passed = True
                days_to_pass[p] = d + 1
                break

        if passed:
            status[p] = 0
        elif breached == 1:
            status[p] = 1
        elif breached == 2:
            status[p] = 2
        else:
            status[p] = 3
        max_dd_seen[p] = (peak_eod - equity) / capital

    return {"status": status, "days_to_pass": days_to_pass,
            "max_dd_seen": max_dd_seen}


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Helpers
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_ci_bernoulli(success: np.ndarray, n_boot: int = 2_000,
                            rng: np.random.Generator | None = None
                            ) -> tuple[float, float]:
    """95% CI by resampling a Bernoulli array."""
    if rng is None:
        rng = np.random.default_rng(SEED + 99)
    n = len(success)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = rng.choice(success, size=n, replace=True).mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def run_one(daily_arr: np.ndarray, capital: float, n_mnq: int,
            max_days: int | None, seed_offset: int) -> dict:
    """Run both phases for a (capital, N MNQ, max_days) combination."""
    T = len(daily_arr)
    block_size = max(1, int(round(np.sqrt(T))))

    daily_limit = FTMO_DAILY_PCT * capital
    max_dd      = FTMO_MAX_DD_PCT * capital
    target_p1   = FTMO_P1_PCT * capital
    target_p2   = FTMO_P2_PCT * capital

    rng1 = np.random.default_rng(SEED + seed_offset)
    p1 = simulate_phase(daily_arr, N_PATHS, max_days, capital,
                         target_p1, daily_limit, max_dd, block_size, rng1)
    p1_pass = (p1["status"] == 0)

    rng2 = np.random.default_rng(SEED + seed_offset + 1)
    p2 = simulate_phase(daily_arr, N_PATHS, max_days, capital,
                         target_p2, daily_limit, max_dd, block_size, rng2)
    p2_pass = (p2["status"] == 0)

    p1_rate = float(p1_pass.mean())
    p2_rate = float(p2_pass.mean())
    p_comb  = p1_rate * p2_rate

    p1_lo, p1_hi = bootstrap_ci_bernoulli(p1_pass.astype(int))
    p2_lo, p2_hi = bootstrap_ci_bernoulli(p2_pass.astype(int))
    se1 = np.sqrt(p1_rate * (1 - p1_rate) / N_PATHS)
    se2 = np.sqrt(p2_rate * (1 - p2_rate) / N_PATHS)
    se_comb = np.sqrt((p2_rate * se1) ** 2 + (p1_rate * se2) ** 2)
    comb_lo = max(0.0, p_comb - 1.96 * se_comb)
    comb_hi = min(1.0, p_comb + 1.96 * se_comb)

    n = N_PATHS
    both_pass = p1_pass & p2_pass
    days_comb = (p1["days_to_pass"][both_pass]
                  + p2["days_to_pass"][both_pass])
    med_days = float(np.median(days_comb)) if len(days_comb) > 0 else None
    med_p1 = (float(np.median(p1["days_to_pass"][p1_pass]))
              if p1_pass.any() else None)

    return {
        "capital":         int(capital),
        "n_mnq":           int(n_mnq),
        "max_days":        max_days,
        "block_size":      int(block_size),
        "T_days":          int(T),
        "daily_limit_usd": float(daily_limit),
        "max_dd_usd":      float(max_dd),
        "target_p1_usd":   float(target_p1),
        "target_p2_usd":   float(target_p2),
        "p1_pass":         p1_rate,
        "p1_ci95_lo":      p1_lo,
        "p1_ci95_hi":      p1_hi,
        "p1_daily":        float((p1["status"] == 1).mean()),
        "p1_dd":           float((p1["status"] == 2).mean()),
        "p1_timeout":      float((p1["status"] == 3).mean()),
        "p1_median_days":  med_p1,
        "p2_pass":         p2_rate,
        "p2_ci95_lo":      p2_lo,
        "p2_ci95_hi":      p2_hi,
        "p_combined":      p_comb,
        "p_combined_lo":   comb_lo,
        "p_combined_hi":   comb_hi,
        "median_days_comb":med_days,
        "p99_max_dd_p1":   float(np.percentile(p1["max_dd_seen"], 99)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Step 4 — Main sweep
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 80)
    print("Strategy C — FTMO Account Size Sweep")
    print(f"Threshold target: p(comb) > {PASS_THRESHOLD*100:.0f}%  in ≤ {MAX_DAYS_BASE} days")
    print(f"Bootstrap: stationary block, n_paths={N_PATHS:,}")
    print("=" * 80)

    tl_nq, met = build_iter10_trade_log()

    # Sanity check
    if not (1.51 < met.get("sharpe_daily_hac", 0) < 1.53):
        print(f"  WARN: baseline Sharpe drift = {met.get('sharpe_daily_hac', 0)}")

    # Pre-cache daily series per N (independent of capital — only depends on N)
    n_set = sorted({n for ns in N_CANDIDATES_PER_CAPITAL.values() for n in ns})
    print(f"\nBuilding daily series for {len(n_set)} distinct N values...")
    daily_per_n: dict[int, np.ndarray] = {}
    for n in n_set:
        daily_per_n[n] = daily_pnl_for_size(tl_nq, n)

    # ── Main grid sweep ────────────────────────────────────────────────────
    print(f"\nGrid sweep ({sum(len(ns) for ns in N_CANDIDATES_PER_CAPITAL.values())} cells)...")
    grid_results: list[dict] = []
    seed_off = 0
    for capital in CAPITAL_LIST:
        for n_mnq in N_CANDIDATES_PER_CAPITAL[capital]:
            r = run_one(daily_per_n[n_mnq], capital, n_mnq,
                         MAX_DAYS_BASE, seed_off)
            grid_results.append(r)
            seed_off += 2
            print(f"  capital=${capital:>8,d} N={n_mnq:>3}  "
                  f"p1={r['p1_pass']*100:>5.1f}% p2={r['p2_pass']*100:>5.1f}% "
                  f"comb={r['p_combined']*100:>5.1f}%  "
                  f"breach_dd={r['p1_dd']*100:>4.1f}% to={r['p1_timeout']*100:>4.1f}%  "
                  f"med_days={r['median_days_comb']}")

    # ── For each capital, find N* maximising p(combined) ───────────────────
    per_capital_best: dict[int, dict] = {}
    for capital in CAPITAL_LIST:
        cells = [r for r in grid_results if r["capital"] == capital]
        cells_sorted = sorted(cells, key=lambda r: r["p_combined"], reverse=True)
        per_capital_best[capital] = cells_sorted[0]
        print(f"\n  Best at ${capital:,}: N={cells_sorted[0]['n_mnq']} → "
              f"p(comb)={cells_sorted[0]['p_combined']*100:.2f}%")

    # ── Smallest capital crossing 70% ──────────────────────────────────────
    crossing = None
    for capital in CAPITAL_LIST:
        if per_capital_best[capital]["p_combined"] >= PASS_THRESHOLD:
            crossing = capital
            break

    if crossing is not None:
        print(f"\n  ✓ Smallest capital crossing {PASS_THRESHOLD*100:.0f}%: ${crossing:,}")
    else:
        print(f"\n  ✗ NO capital reaches {PASS_THRESHOLD*100:.0f}% with ≤{MAX_DAYS_BASE}-day cap")

    # ── Fine sweep around N* for the smallest passing (or closest) size ────
    if crossing is None:
        # take the size with the highest p(comb)
        target_capital = max(per_capital_best,
                              key=lambda c: per_capital_best[c]["p_combined"])
    else:
        target_capital = crossing

    n_star = per_capital_best[target_capital]["n_mnq"]
    fine_ns = sorted({max(1, n_star + d) for d in range(-2, 3)})
    print(f"\nFine sweep around N* = {n_star} at ${target_capital:,}: {fine_ns}")
    fine_results = []
    for n_mnq in fine_ns:
        # cached daily series may exist; otherwise build
        if n_mnq not in daily_per_n:
            daily_per_n[n_mnq] = daily_pnl_for_size(tl_nq, n_mnq)
        r = run_one(daily_per_n[n_mnq], target_capital, n_mnq,
                     MAX_DAYS_BASE, seed_off)
        fine_results.append(r)
        seed_off += 2
        print(f"  N={n_mnq:>3}: p(comb)={r['p_combined']*100:.2f}%  "
              f"med_days={r['median_days_comb']}")

    # ── If no size crossed 70%, retry without time limit (FTMO has no cap) ─
    unlimited_results = None
    if crossing is None:
        print(f"\n--- Retrying WITHOUT time limit (FTMO has no max-days cap) ---")
        unlimited_results = []
        for capital in CAPITAL_LIST:
            n_mnq = per_capital_best[capital]["n_mnq"]
            r = run_one(daily_per_n[n_mnq], capital, n_mnq, None, seed_off)
            unlimited_results.append(r)
            seed_off += 2
            print(f"  ${capital:>8,d} N={n_mnq}: p(comb)={r['p_combined']*100:.2f}% "
                  f"(unlimited horizon)  "
                  f"breach_dd={r['p1_dd']*100:.1f}%")

    # ── Save results ──────────────────────────────────────────────────────
    out_json = REPO / "_audit" / "strategy_c_ftmo_account_sweep_results.json"
    payload = {
        "params": {
            "ftmo_daily_pct": FTMO_DAILY_PCT,
            "ftmo_max_dd_pct": FTMO_MAX_DD_PCT,
            "ftmo_max_dd_type": "STATIC from starting balance (propfirm_canonical.py:38)",
            "ftmo_p1_pct": FTMO_P1_PCT,
            "ftmo_p2_pct": FTMO_P2_PCT,
            "max_days_base": MAX_DAYS_BASE,
            "n_paths": N_PATHS,
            "seed": SEED,
            "mnq_point_value": MNQ_POINT_VALUE,
            "mnq_cost_rt": MNQ_COST_RT,
            "baseline_sharpe_hac": met.get("sharpe_daily_hac", None),
            "baseline_maxdd_pct": met.get("max_dd_pct", None),
            "baseline_n_trades": met.get("n_trades", None),
        },
        "grid_sweep": grid_results,
        "per_capital_best": per_capital_best,
        "smallest_crossing_70pct": crossing,
        "fine_sweep_capital": int(target_capital),
        "fine_sweep_results": fine_results,
        "unlimited_horizon": unlimited_results,
    }
    out_json.write_text(json.dumps(payload, indent=2, default=str))
    print(f"\n  → {out_json.relative_to(REPO)}")

    # ── Heatmap p(comb) on (capital × N) ──────────────────────────────────
    # Build a unified N axis from the union of all candidates
    all_ns = sorted({r["n_mnq"] for r in grid_results})
    heat = np.full((len(CAPITAL_LIST), len(all_ns)), np.nan)
    for r in grid_results:
        i = CAPITAL_LIST.index(r["capital"])
        j = all_ns.index(r["n_mnq"])
        heat[i, j] = r["p_combined"] * 100

    fig, ax = plt.subplots(figsize=(13, 6))
    im = ax.imshow(heat, aspect="auto", cmap="viridis",
                    vmin=0, vmax=max(70.0, np.nanmax(heat)))
    ax.set_xticks(range(len(all_ns)))
    ax.set_xticklabels(all_ns)
    ax.set_yticks(range(len(CAPITAL_LIST)))
    ax.set_yticklabels([f"${c:,}" for c in CAPITAL_LIST])
    ax.set_xlabel("N MNQ contracts")
    ax.set_ylabel("Account capital")
    ax.set_title(f"p(pass combined P1+P2) %  —  Strategy C iter_10 — "
                  f"FTMO 5%/10% — ≤{MAX_DAYS_BASE} days/phase")
    for i in range(len(CAPITAL_LIST)):
        for j in range(len(all_ns)):
            v = heat[i, j]
            if not np.isnan(v):
                color = "white" if v < 40 else "black"
                ax.text(j, i, f"{v:.0f}", ha="center", va="center",
                        color=color, fontsize=8)
    fig.colorbar(im, ax=ax, label="p(combined) %")
    plt.tight_layout()
    out_png = REPO / "_audit" / "strategy_c_ftmo_account_sweep_heatmap.png"
    fig.savefig(out_png, dpi=120)
    print(f"  → {out_png.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
