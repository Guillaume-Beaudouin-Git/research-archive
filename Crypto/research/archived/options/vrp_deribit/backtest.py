"""
backtest.py — VRP Phase 3 walk-forward backtest

Strategy: unconditional short ATM straddle (30 DTE → roll at 14 DTE = 16d hold).
No signal timing. See engine.py for cost model and simulation logic.

Walk-forward: 18m train / 6m test / 3m step → target ≥ 3 OOS folds.
N_tests: 155 → 156.

HARD STOP: output results only. Do NOT proceed to Phase 4 without user GO.
"""
from __future__ import annotations

import json
from datetime import timezone
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from engine import (
    simulate_cycles,
    cycles_to_daily_pnl,
    compute_metrics,
    compute_cycle_metrics,
    HOLD_DAYS,
    RV_WINDOW,
    DD_NO_ENTRY,
    DD_UNWIND,
)

REPO_ROOT    = Path(__file__).resolve().parents[4]
CACHE_DIR    = REPO_ROOT / "data" / "vrp" / "cache"
RESULTS_PATH = Path(__file__).parent / "phase3_results.json"

PORTFOLIO_PCT  = 0.01   # 1% portfolio per straddle
N_CONCURRENT   = 2      # 2 offset straddle series in parallel
TRAIN_MONTHS   = 18
TEST_MONTHS    = 6
STEP_MONTHS    = 3
HAC_LAGS       = 6


# ── Data loading ───────────────────────────────────────────────────────────────

def load_data() -> tuple[pd.Series, pd.Series]:
    dvol_path = CACHE_DIR / "BTC_dvol_1d.parquet"
    btc_path  = CACHE_DIR / "BTC_daily_close.parquet"
    if not dvol_path.exists() or not btc_path.exists():
        raise FileNotFoundError(
            f"Cache missing in {CACHE_DIR}. Run phase2_ic_feasibility.py first."
        )
    dvol      = pd.read_parquet(dvol_path)["dvol"]
    btc_close = pd.read_parquet(btc_path)["close"]
    return dvol, btc_close


# ── Walk-forward folds ─────────────────────────────────────────────────────────

def generate_wf_folds(
    start: pd.Timestamp,
    end:   pd.Timestamp,
    train_months: int = TRAIN_MONTHS,
    test_months:  int = TEST_MONTHS,
    step_months:  int = STEP_MONTHS,
) -> list[dict]:
    folds = []
    test_start = start + pd.DateOffset(months=train_months)
    while test_start + pd.DateOffset(months=test_months) <= end:
        train_start = test_start - pd.DateOffset(months=train_months)
        test_end    = test_start + pd.DateOffset(months=test_months)
        folds.append({
            "fold":        len(folds) + 1,
            "train_start": train_start,
            "train_end":   test_start,
            "test_start":  test_start,
            "test_end":    test_end,
        })
        test_start += pd.DateOffset(months=step_months)
    return folds


# ── Walk-forward execution ─────────────────────────────────────────────────────

def run_walkforward(
    dvol:      pd.Series,
    btc_close: pd.Series,
) -> dict:
    # Simulate all cycles on full dataset (unconditional: no fitting needed)
    print("  Simulating all cycles on full dataset...")
    all_cycles = simulate_cycles(
        dvol, btc_close,
        hold_days    = HOLD_DAYS,
        rv_window    = RV_WINDOW,
        n_concurrent = N_CONCURRENT,
        dd_no_entry  = DD_NO_ENTRY,
        dd_unwind    = DD_UNWIND,
    )
    print(f"  Total cycles simulated: {len(all_cycles)}")

    common = dvol.index.intersection(btc_close.index)
    daily_full = cycles_to_daily_pnl(all_cycles, common, portfolio_pct=PORTFOLIO_PCT)

    # Full-period metrics — cycle-level Sharpe (primary), daily MaxDD (secondary)
    print("  Computing full-period metrics...")
    metrics_full        = compute_cycle_metrics(all_cycles, hac_lags=HAC_LAGS)
    metrics_full_daily  = compute_metrics(daily_full, hac_lags=HAC_LAGS)
    metrics_full["max_dd"]              = metrics_full_daily.get("max_dd")
    metrics_full["calmar"]              = (metrics_full["ann_return"] /
                                           abs(metrics_full["max_dd"])
                                           if metrics_full.get("max_dd") else None)
    metrics_full["sortino"]             = metrics_full_daily.get("sortino")
    metrics_full["max_single_day_loss"] = metrics_full_daily.get("max_single_day_loss")

    # Walk-forward folds
    data_start = common[RV_WINDOW]
    data_end   = common[-1]
    folds      = generate_wf_folds(data_start, data_end)
    print(f"  Walk-forward folds: {len(folds)}")

    fold_results = []
    for fold in folds:
        ts = fold["test_start"]
        te = fold["test_end"]

        # Filter cycles to test period
        mask = (all_cycles["start_date"] >= ts) & (all_cycles["end_date"] <= te)
        fold_cycles = all_cycles[mask]

        test_idx = common[(common >= ts) & (common <= te)]
        if len(test_idx) < 20:
            continue

        fold_daily = cycles_to_daily_pnl(fold_cycles, test_idx, portfolio_pct=PORTFOLIO_PCT)
        if len(fold_cycles) < 5:
            continue
        fold_m     = compute_cycle_metrics(fold_cycles, hac_lags=min(HAC_LAGS, len(fold_cycles) // 3))
        fold_m["n_cycles"]    = int(len(fold_cycles))
        fold_m["test_start"]  = str(ts.date())
        fold_m["test_end"]    = str(te.date())
        fold_m["fold"]        = fold["fold"]
        fold_results.append(fold_m)

    return {
        "all_cycles":   all_cycles,
        "daily_full":   daily_full,
        "metrics_full": metrics_full,
        "fold_results": fold_results,
        "common_index": common,
    }


# ── Verdict ────────────────────────────────────────────────────────────────────

def evaluate_phase3_verdict(metrics: dict) -> dict:
    sharpe = metrics.get("sharpe_hac", -999)
    max_dd = metrics.get("max_dd", -999)

    if sharpe > 0.7 and max_dd > -0.25:
        verdict = "RESEARCH_PASS"
        action  = "Proceed to Phase 4 validation (with user GO)."
    elif sharpe > 0.5:
        verdict = "GREY_ZONE"
        action  = "ARCHIVE with note — VRP premium marginal net of costs."
    else:
        verdict = "ARCHIVE"
        action  = ("VRP premium exists but not retail-accessible net of "
                   "realistic costs. Archive cleanly.")

    return {
        "sharpe_hac":    round(sharpe, 3),
        "max_dd":        round(max_dd, 5),
        "verdict":       verdict,
        "action":        action,
        "n_tests_before": 155,
        "n_tests_after":  156,
    }


# ── Reporting ──────────────────────────────────────────────────────────────────

def print_results(
    metrics:      dict,
    fold_results: list[dict],
    cycles:       pd.DataFrame,
    verdict:      dict,
) -> None:
    sep = "═" * 72

    print(f"\n{sep}")
    print(" VRP PHASE 3 — WALK-FORWARD BACKTEST RESULTS")
    print(f"{sep}")

    c_active = cycles[~cycles["net_pnl"].isna()]
    print(f"\n  Cycles executed : {len(c_active)}")
    if len(c_active):
        gross = c_active["gross_pnl"]
        costs = c_active["cost_options"] + c_active["cost_spread"] + c_active["cost_hedge"]
        net   = c_active["net_pnl"]
        early = c_active["early_unwind"].sum()
        print(f"  Early unwinds   : {early} ({100*early/len(c_active):.1f}%)")
        print(f"\n  Per-cycle P&L (% underlying notional):")
        print(f"    Gross  mean={gross.mean():.4f}  std={gross.std():.4f}  "
              f"pct_pos={100*(gross>0).mean():.0f}%")
        print(f"    Costs  mean={costs.mean():.4f}  (opt={c_active['cost_options'].mean():.4f}  "
              f"spread={c_active['cost_spread'].mean():.4f}  "
              f"hedge={c_active['cost_hedge'].mean():.4f})")
        print(f"    Net    mean={net.mean():.4f}  std={net.std():.4f}  "
              f"pct_pos={100*(net>0).mean():.0f}%")
        cycles_per_yr = len(c_active) / (
            (c_active["end_date"].max() - c_active["start_date"].min()).days / 365
        )
        print(f"  Cycles/yr       : {cycles_per_yr:.1f}")
        gross_annual = gross.mean() * cycles_per_yr
        cost_annual  = costs.mean() * cycles_per_yr
        net_annual   = net.mean()   * cycles_per_yr
        print(f"\n  Annualized (% underlying notional):")
        print(f"    Gross: {gross_annual:.2%}   Costs: {cost_annual:.2%}   Net: {net_annual:.2%}")

    m = metrics
    print(f"\n{sep}")
    print(" FULL-PERIOD METRICS  (cycle-level Sharpe on % notional; MaxDD at 2% portfolio sizing)")
    print(f"{sep}")
    print(f"  Ann return (% notional) : {m.get('ann_return', 0):.3%}")
    print(f"  Ann vol    (% notional) : {m.get('ann_vol', 0):.3%}")
    print(f"  Sharpe (raw, cycles)    : {m.get('sharpe_raw', 0):.3f}")
    print(f"  Sharpe (HAC, cycles)    : {m.get('sharpe_hac', 0):.3f}  ← primary gate metric")
    print(f"  t_HAC (mean≠0)          : {m.get('t_hac', 0):.3f}")
    maxdd = m.get('max_dd')
    print(f"  MaxDD (portfolio 2%)    : {maxdd:.4%}" if maxdd else "  MaxDD : n/a")
    calmar = m.get('calmar')
    print(f"  Calmar                  : {calmar:.3f}" if calmar and np.isfinite(calmar) else "  Calmar : n/a")
    print(f"  Skewness (cycles)       : {m.get('skewness', 0):.3f}  (negative = fat left tail)")
    print(f"  Ex. Kurtosis            : {m.get('excess_kurtosis', 0):.3f}")
    print(f"  Worst cycle (% notional): {m.get('worst_cycle', 0):.4%}")
    print(f"  Max 1d loss (portfolio) : {m.get('max_single_day_loss', 0):.4%}" if m.get('max_single_day_loss') else "")

    print(f"\n{sep}")
    print(" WALK-FORWARD FOLD PERFORMANCE")
    print(f"{sep}")
    print(f"  {'Fold':<5}  {'Period':<25}  {'Sharpe(HAC)':<12}  {'Ann Ret(notional)':>18}  {'N cycles':>8}")
    print(f"  {'-'*5}  {'-'*25}  {'-'*12}  {'-'*18}  {'-'*8}")
    for f in fold_results:
        period = f"{f.get('test_start','')} → {f.get('test_end','')}"
        sh = f.get("sharpe_hac", float("nan"))
        ar = f.get("ann_return", float("nan"))
        nc = f.get("n_cycles", 0)
        print(f"  {f.get('fold','-'):<5}  {period:<25}  {sh:<12.3f}  {ar:>18.3%}  {nc:>8}")

    n_pos = sum(1 for f in fold_results if f.get("sharpe_hac", -999) > 0)
    n_tot = len(fold_results)
    print(f"\n  Folds with positive Sharpe: {n_pos}/{n_tot} ({100*n_pos/n_tot:.0f}%)")

    print(f"\n{sep}")
    print(" PHASE 3 VERDICT")
    print(f"{sep}")
    print(f"  Sharpe HAC    : {verdict['sharpe_hac']}")
    print(f"  MaxDD         : {verdict['max_dd']:.3%}")
    print(f"  VERDICT       : {verdict['verdict']}")
    print(f"  ACTION        : {verdict['action']}")
    print(f"\n  N_tests       : {verdict['n_tests_before']} → {verdict['n_tests_after']}")
    print(f"\n  ⚠  HARD STOP — do NOT launch Phase 4 without explicit user GO.")
    print(f"{sep}\n")


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n══════════════════════════════════════════════════════════════════════")
    print(" VRP PHASE 3 — UNCONDITIONAL STRADDLE WALK-FORWARD BACKTEST")
    print("══════════════════════════════════════════════════════════════════════\n")

    print("── Loading data ────────────────────────────────────────────────────")
    dvol, btc_close = load_data()
    common = dvol.index.intersection(btc_close.index)
    print(f"  Data: {len(common)} days  ({common[0].date()} → {common[-1].date()})")

    print("\n── Running walk-forward ────────────────────────────────────────────")
    wf = run_walkforward(dvol, btc_close)

    metrics  = wf["metrics_full"]
    cycles   = wf["all_cycles"]
    folds    = wf["fold_results"]
    verdict  = evaluate_phase3_verdict(metrics)

    print_results(metrics, folds, cycles, verdict)

    # ── Serialisable results ─────────────────────────────────────────────────
    def _safe(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return None
        return x

    cycle_summary = {}
    if len(cycles):
        c_active = cycles
        costs = c_active["cost_options"] + c_active["cost_spread"] + c_active["cost_hedge"]
        cycles_per_yr = len(c_active) / (
            (c_active["end_date"].max() - c_active["start_date"].min()).days / 365
        )
        cycle_summary = {
            "n_cycles":            int(len(c_active)),
            "cycles_per_year":     round(float(cycles_per_yr), 2),
            "gross_mean_pct":      round(float(c_active["gross_pnl"].mean()), 6),
            "cost_mean_pct":       round(float(costs.mean()), 6),
            "net_mean_pct":        round(float(c_active["net_pnl"].mean()), 6),
            "net_pct_positive":    round(float((c_active["net_pnl"] > 0).mean()), 3),
            "gross_annual_pct":    round(float(c_active["gross_pnl"].mean() * cycles_per_yr), 5),
            "cost_annual_pct":     round(float(costs.mean() * cycles_per_yr), 5),
            "net_annual_pct":      round(float(c_active["net_pnl"].mean() * cycles_per_yr), 5),
            "n_early_unwinds":     int(c_active["early_unwind"].sum()),
            "cost_breakdown": {
                "option_fees_mean": round(float(c_active["cost_options"].mean()), 6),
                "spread_mean":      round(float(c_active["cost_spread"].mean()), 6),
                "hedge_mean":       round(float(c_active["cost_hedge"].mean()), 6),
            },
        }

    results = {
        "run_timestamp":  datetime.now(timezone.utc).isoformat(),
        "parameters": {
            "hold_days":     HOLD_DAYS,
            "rv_window":     RV_WINDOW,
            "n_concurrent":  N_CONCURRENT,
            "portfolio_pct": PORTFOLIO_PCT,
            "dd_no_entry":   DD_NO_ENTRY,
            "dd_unwind":     DD_UNWIND,
            "train_months":  TRAIN_MONTHS,
            "test_months":   TEST_MONTHS,
            "step_months":   STEP_MONTHS,
        },
        "cycle_summary":    cycle_summary,
        "metrics_full":     {k: _safe(v) for k, v in metrics.items()},
        "fold_results":     [
            {k: _safe(v) for k, v in f.items()} for f in folds
        ],
        "verdict": {k: _safe(v) for k, v in verdict.items()},
        "hard_stop": "Do NOT proceed to Phase 4 without explicit user GO.",
    }

    with open(RESULTS_PATH, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"  Results saved: {RESULTS_PATH}")

    # Save full cycles CSV for analysis scripts
    cycles_path = Path(__file__).parent / "phase3_cycles.csv"
    if len(cycles):
        cycles.to_csv(cycles_path, index=False)
        print(f"  Cycles saved:  {cycles_path}")

    print("  Done.\n")


if __name__ == "__main__":
    main()
