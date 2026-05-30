"""
Strategy C — FTMO $10K Monte Carlo simulator
=============================================

Reconstructs the iter_10 daily PnL series from the backtest trade log, converts
to MNQ at multiple sizing levels, applies FTMO 10K barriers (daily $500, max
DD $1,000 static), and estimates p(pass phase1), p(pass phase2 | phase1), and
the combined p(pass) inside ≤40 trading-day windows.

Bootstrap : block-stationary (Politis-Romano), block_size = round(sqrt(T_days))
on the daily PnL series (preserves autocorr from clustered intraday entries).

Read-only on disk except for:
  - _audit/strategy_c_ftmo10k_sim_results.json (numeric output)
  - _audit/strategy_c_ftmo10k_sim_distrib.png (matplotlib figure)
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
    build_signals, RNG_MIN,
)

# ─────────────────────────────────────────────────────────────────────────────
# Parameters
# ─────────────────────────────────────────────────────────────────────────────

# FTMO 10K rules (per user brief + Portfolio.risk.propfirm_canonical)
FTMO_CAPITAL          = 10_000.0
FTMO_DAILY_LIMIT      = 500.0      # 5% — applied from max(initial, last_eod_peak)
FTMO_MAX_DD           = 1_000.0    # 10% STATIC from starting balance (floor $9k)
FTMO_TARGET_P1        = 1_000.0    # +10% in phase 1
FTMO_TARGET_P2        = 500.0      # +5% in phase 2
MAX_DAYS              = 40         # user constraint: pass within 40 trading days

# MNQ specs (config.py:84-86)
MNQ_POINT_VALUE       = 2.0
MNQ_COST_RT           = 2.15

# Sizing candidates (number of MNQ contracts)
SIZING_CANDIDATES     = [1, 3, 5, 10]

# Monte Carlo
N_PATHS               = 20_000
SEED                  = 42

# ─────────────────────────────────────────────────────────────────────────────
# Step 1 — Build trade log via the audited engine (entry at next bar open)
# ─────────────────────────────────────────────────────────────────────────────

def build_iter10_trade_log() -> pd.DataFrame:
    """Run iter_10 backtest, return trade_log with pnl_pts column added."""
    print("Loading NQ 1-min...")
    df = load_nq_1min()
    eng = NQBacktestEngine(df)
    feats = build_opening_features(eng.rth)
    sigs = build_signals(feats)
    print(f"  signals: {len(sigs)} rows")
    tl, met = eng.run(sigs)
    print(f"  trades : {len(tl)}, Sharpe={met.get('sharpe_daily_hac', 0):.3f}, "
          f"MaxDD={met.get('max_dd_pct', 0)*100:.1f}%, total=${met.get('total_pnl_usd', 0):,.0f}")
    return tl, met


def convert_nq_to_mnq(tl: pd.DataFrame, n_contracts: int) -> pd.DataFrame:
    """
    Convert NQ-full pnl_usd to MNQ pnl_usd at N contracts.

    pnl_mnq_per_contract = pnl_pts × $2 - $2.15
    Total = N × pnl_mnq_per_contract.

    pnl_pts already accounts for the trade direction × (exit - entry).
    The original NQ pnl_usd in tl has the $19 RT already deducted, so we
    re-derive pnl_pts from pnl_usd to keep the calculation transparent.
    """
    tl = tl.copy()
    # Verify: pnl_pts already exists in the engine output (engine.py:178)
    if "pnl_pts" not in tl.columns:
        raise ValueError("trade_log missing pnl_pts column")
    pnl_per_mnq = tl["pnl_pts"] * MNQ_POINT_VALUE - MNQ_COST_RT
    tl["pnl_mnq_total"] = n_contracts * pnl_per_mnq
    return tl


def daily_pnl_from_log(tl: pd.DataFrame, pnl_col: str) -> pd.Series:
    """
    Aggregate trade-level pnl to daily series, expanding to all trading days
    (zero-fill non-trading days within the backtest window).
    """
    tl = tl.copy()
    tl["date"] = pd.to_datetime(tl["entry_ts"]).dt.normalize().dt.tz_localize(None)
    daily = tl.groupby("date")[pnl_col].sum()
    all_dates = pd.bdate_range(daily.index.min(), daily.index.max(), freq="C",
                                holidays=[])
    return daily.reindex(pd.DatetimeIndex(all_dates).normalize(),
                          fill_value=0.0)


# ─────────────────────────────────────────────────────────────────────────────
# Step 2 — Monte Carlo with FTMO barriers
# ─────────────────────────────────────────────────────────────────────────────

def stationary_block_indices(T: int, length: int, block_size: int,
                              rng: np.random.Generator) -> np.ndarray:
    """
    Politis-Romano stationary block bootstrap index sampler.

    Returns an array of `length` indices into a series of size T,
    drawn via blocks of geometric length with mean = block_size.
    """
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
                   max_dd: float, block_size: int, rng: np.random.Generator):
    """
    One FTMO phase simulation.

    Barriers (absorbing):
      - daily PnL ≤ -daily_limit  → breach daily (failure)
      - equity ≤ capital - max_dd → breach max DD (failure)

    The daily_limit is applied as 5% of max(capital, peak_eod_equity).

    Success = equity - capital ≥ target before max_days bars elapse and
              no breach occurred along the way.

    Returns dict with arrays of length n_paths:
      - status : 0 = pass, 1 = daily breach, 2 = dd breach, 3 = timeout
      - days_to_pass (only if status == 0)
      - final_equity
      - max_dd_seen
    """
    T = len(daily_pnl)
    status         = np.zeros(n_paths, dtype=np.int8)
    days_to_pass   = np.zeros(n_paths, dtype=np.int32)
    final_equity   = np.zeros(n_paths, dtype=np.float64)
    max_dd_seen    = np.zeros(n_paths, dtype=np.float64)

    static_floor = capital - max_dd   # absolute floor

    for p in range(n_paths):
        idx = stationary_block_indices(T, max_days, block_size, rng)
        path = daily_pnl[idx]

        equity = capital
        peak_eod = capital
        breach = 0
        for d, day_pnl in enumerate(path):
            # daily_limit applies as 5% of max(initial, peak_eod_equity)
            day_loss_threshold = -daily_limit * (max(capital, peak_eod) / capital)
            if day_pnl <= day_loss_threshold:
                breach = 1
                equity += day_pnl
                break
            equity += day_pnl
            # static max DD check
            if equity <= static_floor:
                breach = 2
                break
            peak_eod = max(peak_eod, equity)
            # success check
            if (equity - capital) >= target:
                status[p]       = 0
                days_to_pass[p] = d + 1
                final_equity[p] = equity
                max_dd_seen[p]  = (peak_eod - equity) / capital
                break
        else:
            # didn't break out of the loop: timeout or breach
            if breach == 1:
                status[p] = 1
            elif breach == 2:
                status[p] = 2
            else:
                status[p] = 3   # timeout
            final_equity[p] = equity
            max_dd_seen[p]  = (peak_eod - equity) / capital
            continue

        if breach == 1:
            status[p] = 1
        elif breach == 2:
            status[p] = 2
        final_equity[p] = equity
        max_dd_seen[p]  = (peak_eod - equity) / capital
    return {
        "status":        status,
        "days_to_pass":  days_to_pass,
        "final_equity":  final_equity,
        "max_dd_seen":   max_dd_seen,
    }


def bootstrap_ci(success: np.ndarray, n_boot: int = 2_000,
                  rng: np.random.Generator | None = None) -> tuple[float, float]:
    """95% CI by simple resampling (success array is iid Bernoulli)."""
    if rng is None:
        rng = np.random.default_rng(SEED + 99)
    n = len(success)
    means = np.empty(n_boot)
    for i in range(n_boot):
        means[i] = rng.choice(success, size=n, replace=True).mean()
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


# ─────────────────────────────────────────────────────────────────────────────
# Step 3 — Run for each sizing candidate
# ─────────────────────────────────────────────────────────────────────────────

def run_sizing(tl_nq: pd.DataFrame, n_contracts: int) -> dict:
    print(f"\n── MNQ × {n_contracts} ──")
    tl = convert_nq_to_mnq(tl_nq, n_contracts)
    daily = daily_pnl_from_log(tl, "pnl_mnq_total")
    T = len(daily)
    block_size = max(1, int(round(np.sqrt(T))))
    print(f"  Daily series: T={T} days, block_size={block_size}, "
          f"mean=${daily.mean():.2f}/day, std=${daily.std():.2f}/day, "
          f"min=${daily.min():.0f}, max=${daily.max():.0f}")

    rng = np.random.default_rng(SEED)
    daily_arr = daily.values.astype(np.float64)

    # Phase 1
    p1 = simulate_phase(daily_arr, N_PATHS, MAX_DAYS,
                        FTMO_CAPITAL, FTMO_TARGET_P1,
                        FTMO_DAILY_LIMIT, FTMO_MAX_DD,
                        block_size, rng)
    p1_pass = (p1["status"] == 0)
    p1_pass_rate = float(p1_pass.mean())
    p1_lo, p1_hi = bootstrap_ci(p1_pass.astype(int))

    # Phase 2 — fresh capital reset; same daily distrib; independent paths
    rng2 = np.random.default_rng(SEED + 1)
    p2 = simulate_phase(daily_arr, N_PATHS, MAX_DAYS,
                        FTMO_CAPITAL, FTMO_TARGET_P2,
                        FTMO_DAILY_LIMIT, FTMO_MAX_DD,
                        block_size, rng2)
    p2_pass = (p2["status"] == 0)
    p2_pass_rate = float(p2_pass.mean())
    p2_lo, p2_hi = bootstrap_ci(p2_pass.astype(int))

    # Combined: conditional independence (each phase drawn independently)
    p_combined = p1_pass_rate * p2_pass_rate
    # CI on the product (delta method approximation)
    se1 = np.sqrt(p1_pass_rate * (1 - p1_pass_rate) / N_PATHS)
    se2 = np.sqrt(p2_pass_rate * (1 - p2_pass_rate) / N_PATHS)
    se_combined = np.sqrt(
        (p2_pass_rate * se1) ** 2 + (p1_pass_rate * se2) ** 2
    )
    comb_lo = max(0.0, p_combined - 1.96 * se_combined)
    comb_hi = min(1.0, p_combined + 1.96 * se_combined)

    # Combined time-to-pass (only on paths where both passed)
    # Joint sampling: align indices
    both_pass = p1_pass & p2_pass
    days_combined = (p1["days_to_pass"][both_pass]
                      + p2["days_to_pass"][both_pass])

    # Breach decomposition
    n = len(p1["status"])
    p1_status_counts = {
        "pass":   int((p1["status"] == 0).sum()),
        "daily":  int((p1["status"] == 1).sum()),
        "dd":     int((p1["status"] == 2).sum()),
        "timeout":int((p1["status"] == 3).sum()),
    }
    p2_status_counts = {
        "pass":   int((p2["status"] == 0).sum()),
        "daily":  int((p2["status"] == 1).sum()),
        "dd":     int((p2["status"] == 2).sum()),
        "timeout":int((p2["status"] == 3).sum()),
    }

    return {
        "n_contracts": n_contracts,
        "daily_mean_usd": float(daily.mean()),
        "daily_std_usd":  float(daily.std()),
        "daily_min_usd":  float(daily.min()),
        "daily_max_usd":  float(daily.max()),
        "T_days":         int(T),
        "block_size":     int(block_size),
        "p1_pass":        p1_pass_rate,
        "p1_ci95_lo":     p1_lo,
        "p1_ci95_hi":     p1_hi,
        "p1_breach_daily":p1_status_counts["daily"] / n,
        "p1_breach_dd":   p1_status_counts["dd"] / n,
        "p1_timeout":     p1_status_counts["timeout"] / n,
        "p1_median_days_to_pass": (
            float(np.median(p1["days_to_pass"][p1_pass]))
            if p1_pass.any() else None
        ),
        "p2_pass":        p2_pass_rate,
        "p2_ci95_lo":     p2_lo,
        "p2_ci95_hi":     p2_hi,
        "p2_breach_daily":p2_status_counts["daily"] / n,
        "p2_breach_dd":   p2_status_counts["dd"] / n,
        "p2_timeout":     p2_status_counts["timeout"] / n,
        "p2_median_days_to_pass": (
            float(np.median(p2["days_to_pass"][p2_pass]))
            if p2_pass.any() else None
        ),
        "p_combined":     p_combined,
        "p_combined_lo":  comb_lo,
        "p_combined_hi":  comb_hi,
        "median_days_combined": (
            float(np.median(days_combined)) if len(days_combined) > 0 else None
        ),
        "p99_max_dd_p1":  float(np.percentile(p1["max_dd_seen"], 99)),
        "p99_max_dd_p2":  float(np.percentile(p2["max_dd_seen"], 99)),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> int:
    print("=" * 80)
    print("Strategy C — FTMO $10K Monte Carlo")
    print("=" * 80)
    print(f"Capital=${FTMO_CAPITAL:,.0f} | Daily limit=${FTMO_DAILY_LIMIT:.0f} | "
          f"Max DD=${FTMO_MAX_DD:.0f} | Phase1=+${FTMO_TARGET_P1:.0f} | "
          f"Phase2=+${FTMO_TARGET_P2:.0f}")
    print(f"Max days/phase=${MAX_DAYS} | n_paths={N_PATHS:,} | seed={SEED}")
    print()

    tl_nq, met = build_iter10_trade_log()
    print(f"\nBaseline (NQ full, 1 contract) reproduces results.json:")
    print(f"  Sharpe={met.get('sharpe_daily_hac', 0):.4f}  (results.json=1.5212)")
    print(f"  MaxDD={met.get('max_dd_pct', 0)*100:.2f}%  (results.json=-13.42%)")
    print(f"  Total=${met.get('total_pnl_usd', 0):,.0f}  (results.json=$45,510.5)")
    print(f"  N={met.get('n_trades', 0)}  (results.json=346)")

    results = []
    for n in SIZING_CANDIDATES:
        r = run_sizing(tl_nq, n)
        results.append(r)
        print(f"\n  N={n} MNQ summary:")
        print(f"    p(pass P1)   = {r['p1_pass']*100:.2f}%  "
              f"[CI95 {r['p1_ci95_lo']*100:.2f}, {r['p1_ci95_hi']*100:.2f}]")
        print(f"    p(pass P2)   = {r['p2_pass']*100:.2f}%  "
              f"[CI95 {r['p2_ci95_lo']*100:.2f}, {r['p2_ci95_hi']*100:.2f}]")
        print(f"    p(pass comb) = {r['p_combined']*100:.2f}%  "
              f"[CI95 {r['p_combined_lo']*100:.2f}, {r['p_combined_hi']*100:.2f}]")
        print(f"    Daily breach P1={r['p1_breach_daily']*100:.1f}%, "
              f"DD breach={r['p1_breach_dd']*100:.1f}%, "
              f"timeout={r['p1_timeout']*100:.1f}%")
        if r['median_days_combined'] is not None:
            print(f"    Median total days to pass: {r['median_days_combined']:.0f}")

    # Save results JSON
    out_json = REPO / "_audit" / "strategy_c_ftmo10k_sim_results.json"
    out_json.write_text(json.dumps(results, indent=2))
    print(f"\n  → {out_json.relative_to(REPO)}")

    # Plot distribution
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle("Strategy C @ MNQ — FTMO $10K Monte Carlo\n"
                  "(Phase1 +$1,000 then Phase2 +$500, max 40 days/phase, "
                  "$500 daily / $1,000 static DD)",
                  fontsize=11)

    # (a) p(pass) vs N contracts
    ax = axes[0, 0]
    Ns = [r["n_contracts"] for r in results]
    p1s = [r["p1_pass"] * 100 for r in results]
    p2s = [r["p2_pass"] * 100 for r in results]
    pcs = [r["p_combined"] * 100 for r in results]
    ax.plot(Ns, p1s, "o-", label="P(pass Phase 1)")
    ax.plot(Ns, p2s, "s-", label="P(pass Phase 2)")
    ax.plot(Ns, pcs, "^-", linewidth=2, color="C3", label="P(pass combined)")
    ax.axhline(70, color="gray", linestyle="--", alpha=0.5, label="70% target")
    ax.set_xlabel("Number of MNQ contracts")
    ax.set_ylabel("Probability (%)")
    ax.set_title("Pass probability vs sizing")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (b) Breach decomposition (combined daily + dd vs timeout)
    ax = axes[0, 1]
    width = 0.25
    x = np.arange(len(Ns))
    ax.bar(x - width, [r["p1_breach_daily"] * 100 for r in results], width,
           label="Daily breach", color="#e74c3c")
    ax.bar(x,         [r["p1_breach_dd"] * 100 for r in results], width,
           label="DD breach",    color="#c0392b")
    ax.bar(x + width, [r["p1_timeout"] * 100 for r in results], width,
           label="Timeout",      color="#95a5a6")
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in Ns])
    ax.set_xlabel("N MNQ")
    ax.set_ylabel("Frequency (%) in Phase 1")
    ax.set_title("Failure mode decomposition (Phase 1)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3, axis="y")

    # (c) median days to pass
    ax = axes[1, 0]
    med_days = [r["median_days_combined"] for r in results]
    has_days = [(n, m) for n, m in zip(Ns, med_days) if m is not None]
    if has_days:
        ax.plot([n for n, _ in has_days], [m for _, m in has_days], "o-")
        ax.axhline(2 * MAX_DAYS, color="red", linestyle="--", alpha=0.5,
                   label=f"2×{MAX_DAYS} day cap")
    ax.set_xlabel("N MNQ")
    ax.set_ylabel("Median days to complete both phases")
    ax.set_title("Time to pass (median, conditional on passing)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    # (d) p99 max DD vs N
    ax = axes[1, 1]
    p99_p1 = [r["p99_max_dd_p1"] * 100 for r in results]
    ax.plot(Ns, p99_p1, "o-")
    ax.axhline(10, color="red", linestyle="--", alpha=0.5, label="10% FTMO floor")
    ax.set_xlabel("N MNQ")
    ax.set_ylabel("P99 max DD reached (% of capital)")
    ax.set_title("Tail drawdown (Phase 1, 99th pct)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)

    plt.tight_layout(rect=(0, 0, 1, 0.95))
    out_png = REPO / "_audit" / "strategy_c_ftmo10k_sim_distrib.png"
    fig.savefig(out_png, dpi=120)
    print(f"  → {out_png.relative_to(REPO)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
