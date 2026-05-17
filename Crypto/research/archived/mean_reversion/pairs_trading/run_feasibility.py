"""
Pairs trading feasibility gate — Strategy B.

Runs the full 4-stage funnel on TRAIN data, produces:
  - data/pairs_funnel_results.csv
  - outputs/top_pairs_zscore.png
  - docs/strategy_B_feasibility.md

Usage:
    cd ~/Desktop/Algo_claude
    python -m strategies.pairs_trading.run_feasibility
    # or to force re-download:
    python -m strategies.pairs_trading.run_feasibility --refresh
"""
from __future__ import annotations

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup (allow running from repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from strategies.pairs_trading.data_fetcher import (
    build_universe_csv,
    get_train_test_split,
    pivot_close,
    pivot_volume,
)
from strategies.pairs_trading.funnel import (
    filter_universe,
    filter_by_correlation,
    filter_by_cointegration,
    filter_by_ic,
    compute_ic_for_pair,
    IC_THRESHOLD,
    ZSCORE_WINDOW_HOURS,
    _compute_residuals,
    _compute_zscore,
)
from strategies.pairs_trading.naive_backtest import (
    run_naive_backtest,
    compute_backtest_metrics,
)

OUTPUT_DIR  = REPO_ROOT / "outputs"
DATA_DIR    = REPO_ROOT / "data"
DOCS_DIR    = REPO_ROOT / "docs"
RESULTS_CSV = DATA_DIR / "pairs_funnel_results.csv"
PLOT_FILE   = OUTPUT_DIR / "top_pairs_zscore.png"
REPORT_FILE = DOCS_DIR / "strategy_B_feasibility.md"

OUTPUT_DIR.mkdir(exist_ok=True)
DOCS_DIR.mkdir(exist_ok=True)

# GO/NO-GO thresholds (per spec)
GO_MIN_PAIRS_IC010   = 5
GO_MIN_NAIVE_SHARPE  = 1.0
STRONG_IC_THRESHOLD  = -0.10


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(force_refresh: bool = False) -> None:
    print("=" * 70)
    print("PAIRS TRADING FEASIBILITY STUDY — Strategy B")
    print(f"Run date: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 70)

    # -----------------------------------------------------------------------
    # 0. Load data
    # -----------------------------------------------------------------------
    print("\n[0] Loading data...")
    raw = build_universe_csv(force_refresh=force_refresh)
    train_df, test_df = get_train_test_split(raw)

    close_train = pivot_close(train_df)
    vol_train   = pivot_volume(train_df)

    # For open prices in backtest (approx from train open column)
    open_train = train_df.pivot_table(index="timestamp", columns="symbol", values="open", aggfunc="last")

    # -----------------------------------------------------------------------
    # Stage 1: Universe filter
    # -----------------------------------------------------------------------
    print("\n[Stage 1] Universe filter...")
    # Resample vol to daily before passing to filter
    vol_train_daily = vol_train.resample("24h").sum()
    surviving_syms = filter_universe(close_train, vol_train_daily)

    n_stage1 = len(surviving_syms)
    print(f"  Surviving: {surviving_syms}")

    if n_stage1 < 2:
        _write_no_go_report("Stage 1 left < 2 symbols. Check data / liquidity thresholds.")
        return

    # -----------------------------------------------------------------------
    # Stage 2: Correlation filter
    # -----------------------------------------------------------------------
    print("\n[Stage 2] Correlation filter (all pairs)...")
    close_filt = close_train[surviving_syms]
    corr_pairs = filter_by_correlation(close_filt, surviving_syms)

    n_stage2 = len(corr_pairs)
    if n_stage2 == 0:
        _write_no_go_report("No pairs survived Stage 2 correlation filter.")
        return

    # -----------------------------------------------------------------------
    # Stage 3: Cointegration filter
    # -----------------------------------------------------------------------
    print("\n[Stage 3] Cointegration filter (rolling ADF)...")
    coint_results = filter_by_cointegration(close_filt, corr_pairs)
    passing_coint = [r for r in coint_results if r.passes]
    n_stage3 = len(passing_coint)

    # -----------------------------------------------------------------------
    # Stage 4: IC test
    # -----------------------------------------------------------------------
    print("\n[Stage 4] IC test (Z-score predictive power)...")
    if n_stage3 == 0:
        print("  WARNING: No pairs passed Stage 3. Running IC on Stage 2 survivors for diagnostic.")
        # Still include correlation-passing pairs in results with coint=FAIL
        df_results = filter_by_ic(close_filt, coint_results, require_coint_pass=False)
    else:
        df_results = filter_by_ic(close_filt, coint_results, require_coint_pass=True)

    # -----------------------------------------------------------------------
    # Naive backtest on IC-passing pairs
    # -----------------------------------------------------------------------
    print("\n[Backtest] Naive spread backtest (no costs, signal-existence test)...")

    bt_metrics: dict[tuple, dict] = {}
    ic_pairs_df = df_results[df_results["passes_ic"] == True].copy() if len(df_results) else pd.DataFrame()

    for _, row in ic_pairs_df.iterrows():
        a, b = row["asset_A"], row["asset_B"]
        beta_mean = row["beta_mean"] if not np.isnan(row["beta_mean"]) else 1.0
        print(f"  Backtesting {a}/{b}...")

        # Recompute residuals and Z-score for this pair
        ic_data = compute_ic_for_pair(close_filt, a, b, beta_mean)
        z = ic_data["z_series"]
        beta_fit = ic_data["beta_fit"]
        alpha_fit = ic_data["alpha_fit"]

        bt = run_naive_backtest(close_filt, open_train, a, b, beta_fit, alpha_fit, z)
        metrics = compute_backtest_metrics(bt)
        bt_metrics[(a, b)] = metrics
        print(f"    Sharpe={metrics['sharpe']:.2f}  total_ret={metrics['total_return']:.3f}  "
              f"trades={metrics['n_trades']}")

    # Add backtest metrics to results
    if len(df_results):
        df_results["naive_sharpe"] = df_results.apply(
            lambda r: bt_metrics.get((r["asset_A"], r["asset_B"]), {}).get("sharpe", np.nan),
            axis=1
        )
        df_results["naive_total_ret"] = df_results.apply(
            lambda r: bt_metrics.get((r["asset_A"], r["asset_B"]), {}).get("total_return", np.nan),
            axis=1
        )
        df_results["naive_max_dd"] = df_results.apply(
            lambda r: bt_metrics.get((r["asset_A"], r["asset_B"]), {}).get("max_dd", np.nan),
            axis=1
        )
        df_results["naive_n_trades"] = df_results.apply(
            lambda r: bt_metrics.get((r["asset_A"], r["asset_B"]), {}).get("n_trades", 0),
            axis=1
        )

    # -----------------------------------------------------------------------
    # Save CSV
    # -----------------------------------------------------------------------
    df_results.to_csv(RESULTS_CSV, index=False)
    print(f"\nSaved funnel results to {RESULTS_CSV}")

    # -----------------------------------------------------------------------
    # GO / NO-GO determination
    # -----------------------------------------------------------------------
    n_strong_ic = int((df_results["best_IC"] < STRONG_IC_THRESHOLD).sum()) if len(df_results) else 0
    sharpe_ok_pairs = []
    if len(ic_pairs_df):
        for _, row in ic_pairs_df.iterrows():
            a, b = row["asset_A"], row["asset_B"]
            m = bt_metrics.get((a, b), {})
            if m.get("sharpe", -999) > GO_MIN_NAIVE_SHARPE:
                sharpe_ok_pairs.append((a, b))

    is_go = (n_strong_ic >= GO_MIN_PAIRS_IC010) and (len(sharpe_ok_pairs) > 0)
    verdict = "GO" if is_go else "NO-GO"
    print(f"\n{'='*70}")
    print(f"VERDICT: {verdict}")
    print(f"  Pairs with IC < {STRONG_IC_THRESHOLD}: {n_strong_ic} (need ≥ {GO_MIN_PAIRS_IC010})")
    print(f"  Pairs with naive Sharpe > {GO_MIN_NAIVE_SHARPE}: {len(sharpe_ok_pairs)}")
    print(f"{'='*70}")

    # -----------------------------------------------------------------------
    # Plots — top 5 pairs by IC
    # -----------------------------------------------------------------------
    top_pairs = []
    if len(df_results):
        # Sort by best_IC ascending (most negative = best mean reversion)
        candidates = df_results[df_results["passes_ic"] == True].copy()
        if len(candidates) == 0:
            # Fallback: show top-5 by IC regardless of threshold
            candidates = df_results.dropna(subset=["best_IC"]).copy()
        candidates = candidates.sort_values("best_IC", ascending=True).head(5)

        for _, row in candidates.iterrows():
            a, b = row["asset_A"], row["asset_B"]
            beta_mean = row["beta_mean"] if not np.isnan(row["beta_mean"]) else 1.0
            ic_data = compute_ic_for_pair(close_filt, a, b, beta_mean)
            z = ic_data["z_series"]
            beta_fit = ic_data["beta_fit"]
            alpha_fit = ic_data["alpha_fit"]
            bt = run_naive_backtest(close_filt, open_train, a, b, beta_fit, alpha_fit, z)
            ic_val = row["best_IC"]
            sharpe_val = bt_metrics.get((a, b), {}).get("sharpe", np.nan)
            top_pairs.append((a, b, z, bt, ic_val, sharpe_val))

    _make_plot(top_pairs, close_filt)

    # -----------------------------------------------------------------------
    # Markdown report
    # -----------------------------------------------------------------------
    _write_report(
        df_results=df_results,
        n_stage1=n_stage1,
        n_stage2=n_stage2,
        n_stage3=n_stage3,
        surviving_syms=surviving_syms,
        verdict=verdict,
        is_go=is_go,
        n_strong_ic=n_strong_ic,
        sharpe_ok_pairs=sharpe_ok_pairs,
        bt_metrics=bt_metrics,
    )

    print(f"\nReport: {REPORT_FILE}")
    print(f"Plot:   {PLOT_FILE}")


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def _make_plot(
    top_pairs: list[tuple],
    close: pd.DataFrame,
) -> None:
    """Plot Z-score time series and naive P&L for top 5 pairs."""
    n = len(top_pairs)
    if n == 0:
        print("  No pairs to plot.")
        return

    fig = plt.figure(figsize=(18, 4 * n))
    gs = gridspec.GridSpec(n, 2, figure=fig, hspace=0.5, wspace=0.3)
    fig.suptitle("Top Pairs — Z-score & Naive Spread P&L (Train Period)", fontsize=14, y=1.01)

    for i, (a, b, z, bt, ic_val, sharpe_val) in enumerate(top_pairs):
        # Left panel: Z-score time series
        ax_z = fig.add_subplot(gs[i, 0])
        z_plot = z.dropna()
        ax_z.plot(z_plot.index, z_plot.values, color="#2c7bb6", linewidth=0.6, alpha=0.8)
        ax_z.axhline(2.0,  color="#d7191c", linestyle="--", linewidth=1, label="+2σ (short entry)")
        ax_z.axhline(-2.0, color="#1a9641", linestyle="--", linewidth=1, label="-2σ (long entry)")
        ax_z.axhline(0.5,  color="#fdae61", linestyle=":", linewidth=0.8, label="±0.5σ (exit)")
        ax_z.axhline(-0.5, color="#fdae61", linestyle=":", linewidth=0.8)
        ax_z.set_title(f"{a}/{b}  |  IC={ic_val:.3f}", fontsize=11)
        ax_z.set_ylabel("Z-score")
        ax_z.legend(fontsize=7, loc="upper right")
        ax_z.grid(True, alpha=0.3)

        # Right panel: cumulative P&L
        ax_p = fig.add_subplot(gs[i, 1])
        cum = bt["cum_pnl"].dropna()
        color = "#1a9641" if cum.iloc[-1] > 0 else "#d7191c"
        ax_p.plot(cum.index, cum.values, color=color, linewidth=0.8)
        ax_p.axhline(0, color="black", linewidth=0.5)
        sharpe_str = f"{sharpe_val:.2f}" if not np.isnan(sharpe_val) else "n/a"
        ax_p.set_title(f"{a}/{b}  |  Naive Sharpe={sharpe_str}", fontsize=11)
        ax_p.set_ylabel("Cumulative log-return")
        ax_p.grid(True, alpha=0.3)

        # Shade entries
        pos = bt["position"].fillna(0)
        long_entry  = (pos > 0.5).astype(int).diff().fillna(0)
        short_entry = (pos < -0.5).astype(int).diff().fillna(0)
        for t_idx in bt.index[long_entry == 1]:
            ax_z.axvline(t_idx, color="#1a9641", alpha=0.3, linewidth=0.4)
        for t_idx in bt.index[short_entry == 1]:
            ax_z.axvline(t_idx, color="#d7191c", alpha=0.3, linewidth=0.4)

    plt.tight_layout()
    plt.savefig(PLOT_FILE, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved plot to {PLOT_FILE}")


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def _write_report(
    df_results: pd.DataFrame,
    n_stage1: int,
    n_stage2: int,
    n_stage3: int,
    surviving_syms: list[str],
    verdict: str,
    is_go: bool,
    n_strong_ic: int,
    sharpe_ok_pairs: list,
    bt_metrics: dict,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")

    # Top 10 by IC
    if len(df_results):
        top10 = df_results.dropna(subset=["best_IC"]).sort_values("best_IC").head(10)
    else:
        top10 = pd.DataFrame()

    # Funnel summary
    n_universe = len(DOCS_DIR.parent) if False else len(surviving_syms)   # cheating workaround
    n_corr = n_stage2
    n_coint = n_stage3
    n_ic = int(df_results["passes_ic"].sum()) if len(df_results) else 0

    verdict_emoji = "✅" if is_go else "❌"

    # Format top-10 table
    if len(top10):
        header = ("| # | Pair | corr_logP | corr_ret | ADF pass% | β_mean | β_std | "
                  "IC_4h | IC_12h | IC_24h | IC_72h | Best IC | Horizon | Sharpe | Trades |")
        sep = ("|---|------|-----------|----------|-----------|--------|-------|"
               "------|--------|--------|--------|---------|---------|--------|--------|")
        rows_md = [header, sep]
        for rank, (_, row) in enumerate(top10.iterrows(), 1):
            a, b = row["asset_A"], row["asset_B"]
            m = bt_metrics.get((a, b), {})
            sharpe_str = f"{m.get('sharpe', float('nan')):.2f}" if not np.isnan(m.get('sharpe', float('nan'))) else "—"
            trades_str = str(m.get('n_trades', '—'))
            rows_md.append(
                f"| {rank} | {a}/{b} "
                f"| {row['corr_logP']:.3f} "
                f"| {row['corr_ret']:.3f} "
                f"| {row['adf_pass_rate']:.0%} "
                f"| {row['beta_mean']:.3f} "
                f"| {row['beta_std']:.3f} "
                f"| {_fmt(row['ic_4h'])} "
                f"| {_fmt(row['ic_12h'])} "
                f"| {_fmt(row['ic_24h'])} "
                f"| {_fmt(row['ic_72h'])} "
                f"| **{_fmt(row['best_IC'])}** "
                f"| {row['best_horizon']}h "
                f"| {sharpe_str} "
                f"| {trades_str} |"
            )
        top10_md = "\n".join(rows_md)
    else:
        top10_md = "_No pairs survived all stages._"

    report = f"""# Strategy B: Pairs Trading Feasibility Study

**Generated:** {now}
**Universe:** Hyperliquid perpetuals (hourly, 18-month window)
**Method:** Stoikov et al. (Cornell CFEM, Dec 2025) multi-stage funnel — adapted with ADF cointegration retained

---

## Verdict: {verdict_emoji} {verdict}

| Criterion | Required | Achieved | Pass? |
|-----------|----------|----------|-------|
| Pairs with IC < -0.10 | ≥ 5 | {n_strong_ic} | {"✅" if n_strong_ic >= GO_MIN_PAIRS_IC010 else "❌"} |
| Pairs with naive Sharpe > 1.0 | ≥ 1 | {len(sharpe_ok_pairs)} | {"✅" if len(sharpe_ok_pairs) > 0 else "❌"} |

{"**PROCEED** to walk-forward backtest with realistic costs." if is_go else "**DO NOT PROCEED.** Mean-reversion edge insufficient in current universe / time window."}

---

## Funnel Summary

| Stage | Description | Input pairs/symbols | Surviving |
|-------|-------------|---------------------|-----------|
| 0 | Raw universe | {HYPERLIQUID_UNIVERSE_LEN} symbols | {n_stage1} symbols |
| 1 | Liquidity + completeness filter | {n_stage1} symbols | {n_stage1} symbols |
| 2 | Correlation filter (corr_logP > 0.85, corr_ret > 0.40) | {n_stage1*(n_stage1-1)//2} pairs | {n_corr} pairs |
| 3 | Cointegration (ADF pass rate ≥ 60%, β stable) | {n_corr} pairs | {n_coint} pairs |
| 4 | IC test (best IC < -0.05 at any horizon) | {n_coint} pairs | {n_ic} pairs |

### Surviving symbols (Stage 1)
`{", ".join(surviving_syms)}`

---

## Top 10 Pairs by IC (Train Period)

> IC = Pearson correlation between Z[t-1] and forward spread return.
> Mean reversion → IC should be **negative** (high Z → spread falls).
> Signal on bar t-1 close, position at bar t open (no look-ahead).

{top10_md}

---

## Methodology Notes

### Data
- Source: yfinance (Yahoo Finance) — hourly OHLCV, approximately 18 months
- Train: first 12 months | Test: last 6 months (test not touched in this report)
- Liquidity floor: median 24h USD volume ≥ $10M
- Completeness floor: ≤ 5% missing hourly bars

### Signal Construction
1. Full-sample OLS: log(P_A) = α + β × log(P_B)
2. Residual: u_t = log(P_A) - α - β × log(P_B)
3. Z-score: Z_t = (u_t - μ_30d) / σ_30d  (rolling 30-day window)

### Cointegration Test
- Engle-Granger ADF on residuals of rolling 90-day OLS windows
- Window step = 22.5 days (25% overlap)
- Pass criteria: ADF p-value < 0.05 in ≥ 60% of windows
- Hedge ratio stability: CV(β) = std(β)/|mean(β)| < 0.50

### Naive Backtest Rules
- Long spread (long A, short B×β) when Z[t-1] < -2
- Short spread (short A, long B×β) when Z[t-1] > +2
- Exit long when Z[t-1] > -0.5; exit short when Z[t-1] < +0.5
- **No costs, no leverage** — pure signal-existence test
- **Execution timing:** signal on bar t-1 close → position at bar t open ✓

### Known Limitations
- yfinance data quality varies for smaller assets (MATIC, SEI, ENA)
- No funding rate adjustments modelled (separate concern per design spec)
- Naive backtest ignores bid-ask spread and market impact
- Multiple testing not corrected here (DSR reserved for full backtest phase)

---

## Next Steps (if GO)

1. Walk-forward backtest (12-month rolling train, 6-month test, 1-month step)
2. Realistic costs: 0.035% taker × 4 legs + 0.05% slippage × 4 legs
3. Funding income/cost tracked per leg separately
4. DSR correction across surviving pairs
5. Correlation analysis vs TSMOM (Strategy A) returns
"""

    REPORT_FILE.write_text(report)
    print(f"  Saved markdown report to {REPORT_FILE}")


def _fmt(val) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "—"
    return f"{val:.3f}"


def _write_no_go_report(reason: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    REPORT_FILE.write_text(
        f"# Strategy B: Pairs Trading Feasibility Study\n\n"
        f"**Generated:** {now}\n\n"
        f"## Verdict: ❌ NO-GO\n\n"
        f"Stopped early: {reason}\n"
    )
    print(f"NO-GO report written: {reason}")


# Store universe size for report
HYPERLIQUID_UNIVERSE_LEN = 23  # len(HYPERLIQUID_UNIVERSE) — avoid circular import

# GO/NO-GO thresholds (duplicated for report access)
GO_MIN_PAIRS_IC010 = 5


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pairs trading feasibility study")
    parser.add_argument("--refresh", action="store_true", help="Force re-download of hourly data")
    args = parser.parse_args()
    main(force_refresh=args.refresh)
