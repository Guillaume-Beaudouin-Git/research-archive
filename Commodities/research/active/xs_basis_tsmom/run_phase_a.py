"""
run_phase_a.py — Phase A: fetch + validate commodity futures universe.

Outputs (written to results/):
  universe_stats.csv       — per-ticker data quality table
  roll_plots/              — 5 plots of continuous returns + roll artifact markers
  basis_coverage.csv       — monthly basis proxy coverage per ticker
  phase_a_report.txt       — summary text for manual review

Usage:
  python run_phase_a.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

ROOT = Path(__file__).parents[4]   # Algo_claude/
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).parent / "results"
PLOTS_DIR   = RESULTS_DIR / "roll_plots"
RESULTS_DIR.mkdir(exist_ok=True)
PLOTS_DIR.mkdir(exist_ok=True)

# ── Tickers to plot (diversified across sectors) ───────────────────────────
PLOT_TICKERS = ["CL", "GC", "ZC", "KC", "LE"]   # Energy, Metal, Grain, Soft, Livestock


def main() -> None:
    log.info("=" * 60)
    log.info("PHASE A — Commodity futures universe validation")
    log.info("=" * 60)

    # ── 1. Fetch all continuous contracts ─────────────────────────────────
    log.info("Step 1/5: Fetching continuous contracts from yfinance…")
    from Commodities.research.active.xs_basis_tsmom.data.fetch_continuous import fetch_all_continuous, COMMODITY_UNIVERSE
    prices_daily = fetch_all_continuous(start="2005-01-01", max_age_days=3)

    if prices_daily.empty:
        log.error("No data fetched — aborting Phase A")
        sys.exit(1)

    tickers_all = sorted({c[0] for c in prices_daily.columns})
    log.info("Fetched %d tickers, %d daily rows (%.0f yr)",
             len(tickers_all), len(prices_daily),
             len(prices_daily) / 252)

    # ── 2. Extract close / volume ─────────────────────────────────────────
    close_daily  = prices_daily.xs("close",  axis=1, level=1, drop_level=False)
    close_daily.columns = close_daily.columns.droplevel(1)   # → simple ticker cols
    volume_daily = None
    if "volume" in prices_daily.columns.get_level_values(1):
        volume_daily = prices_daily.xs("volume", axis=1, level=1, drop_level=False)
        volume_daily.columns = volume_daily.columns.droplevel(1)

    # ── 3. Roll validation ───────────────────────────────────────────────
    log.info("Step 2/5: Running roll validation…")
    from Commodities.research.active.xs_basis_tsmom.data.roll_validation import (
        detect_roll_artifacts, validate_universe
    )
    roll_df      = detect_roll_artifacts(close_daily, threshold_sigma=5.0)
    universe_stats = validate_universe(close_daily, volume_daily, adv_threshold=5_000)

    # ── 4. Basis proxy ────────────────────────────────────────────────────
    log.info("Step 3/5: Building roll-gap basis proxy…")
    from Commodities.research.active.xs_basis_tsmom.data.fetch_front_second import build_basis_monthly
    basis_monthly = build_basis_monthly(prices_daily, threshold_sigma=3.0)

    # ── 5. Write universe_stats.csv ───────────────────────────────────────
    log.info("Step 4/5: Writing results…")
    stats_path = RESULTS_DIR / "universe_stats.csv"
    universe_stats.to_csv(stats_path, float_format="%.3f")
    log.info("  universe_stats.csv → %s", stats_path)

    basis_cov_path = RESULTS_DIR / "basis_coverage.csv"
    # Roll counts per ticker from roll_df (threshold 3σ for basis)
    roll_df3 = detect_roll_artifacts(close_daily, threshold_sigma=3.0)
    roll_counts = (
        roll_df3[roll_df3["is_roll_artifact"]]
        .groupby("ticker")
        .size()
        .rename("n_roll_artifacts_3sigma")
    )
    basis_cov = basis_monthly.notna().sum().rename("n_months_with_basis")
    basis_cov_df = pd.concat([roll_counts, basis_cov], axis=1).fillna(0)
    basis_cov_df["basis_coverage_pct"] = (
        basis_cov_df["n_months_with_basis"] / max(len(basis_monthly), 1)
    ).round(3)
    basis_cov_df.to_csv(basis_cov_path)
    log.info("  basis_coverage.csv → %s", basis_cov_path)

    # ── 6. Roll artifact plots ────────────────────────────────────────────
    log.info("Step 5/5: Generating roll artifact plots…")
    roll_df5 = roll_df  # already computed with 5σ threshold
    roll_is  = roll_df5[roll_df5["is_roll_artifact"]].copy()
    roll_mkt = roll_df5[~roll_df5["is_roll_artifact"]].copy()

    actual_plot_tickers = [t for t in PLOT_TICKERS if t in close_daily.columns]
    # Fallback: add random tickers up to 5
    if len(actual_plot_tickers) < 5:
        extras = [t for t in tickers_all if t not in actual_plot_tickers]
        actual_plot_tickers += extras[: 5 - len(actual_plot_tickers)]

    for ticker in actual_plot_tickers[:5]:
        _plot_roll_artifacts(
            ticker, close_daily, roll_is, roll_mkt, PLOTS_DIR
        )
        log.info("  saved plot: %s", PLOTS_DIR / f"{ticker}_roll_artifacts.png")

    # ── 7. Phase A report ────────────────────────────────────────────────
    report = _build_report(
        tickers_all, universe_stats, roll_df5, basis_cov_df, basis_monthly, prices_daily
    )
    report_path = RESULTS_DIR / "phase_a_report.txt"
    report_path.write_text(report)
    log.info("  phase_a_report.txt → %s", report_path)

    print("\n" + "=" * 60)
    print(report)
    print("=" * 60)
    log.info("Phase A complete.")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _plot_roll_artifacts(
    ticker:    str,
    close:     pd.DataFrame,
    roll_is:   pd.DataFrame,
    roll_mkt:  pd.DataFrame,
    out_dir:   Path,
) -> None:
    """Plot continuous close price with roll artifact / market-event markers."""
    prices = close[ticker].dropna()
    if prices.empty:
        return

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 7), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})

    # ─ Top: price with markers ─
    ax1.plot(prices.index, prices.values, color="#1f77b4", lw=0.8, label="Close (continuous)")

    t_roll = roll_is[roll_is["ticker"] == ticker].copy()
    t_mkt  = roll_mkt[roll_mkt["ticker"] == ticker].copy()

    if not t_roll.empty:
        p_roll = prices.reindex(t_roll["date"]).dropna()
        ax1.scatter(p_roll.index, p_roll.values,
                    color="orange", zorder=5, s=60, marker="^",
                    label=f"Roll artifact ({len(t_roll)})")

    if not t_mkt.empty:
        p_mkt = prices.reindex(t_mkt["date"]).dropna()
        ax1.scatter(p_mkt.index, p_mkt.values,
                    color="red", zorder=5, s=40, marker="x",
                    label=f"Market event ({len(t_mkt)})")

    ax1.set_title(f"{ticker} — Continuous futures + roll artifact detection (|z| > 5σ)",
                  fontsize=11)
    ax1.set_ylabel("Price")
    ax1.legend(fontsize=8, loc="upper left")
    ax1.grid(alpha=0.3)

    # ─ Bottom: daily log return ─
    lr = np.log(prices).diff()
    ax2.bar(lr.index, lr.values, width=1, color="#1f77b4", alpha=0.5)

    if not t_roll.empty:
        lr_roll = lr.reindex(t_roll["date"]).dropna()
        ax2.bar(lr_roll.index, lr_roll.values, width=1, color="orange", alpha=0.9, label="Roll")

    if not t_mkt.empty:
        lr_mkt = lr.reindex(t_mkt["date"]).dropna()
        ax2.bar(lr_mkt.index, lr_mkt.values, width=1, color="red", alpha=0.9, label="Market")

    ax2.set_ylabel("Log return")
    ax2.set_xlabel("Date")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator(2))
    ax2.grid(alpha=0.3)
    ax2.legend(fontsize=8)

    plt.tight_layout()
    fig.savefig(out_dir / f"{ticker}_roll_artifacts.png", dpi=120)
    plt.close(fig)


def _build_report(
    tickers_all:   list[str],
    universe_stats: pd.DataFrame,
    roll_df:       pd.DataFrame,
    basis_cov_df:  pd.DataFrame,
    basis_monthly: pd.DataFrame,
    prices_daily:  pd.DataFrame,
) -> str:
    lines: list[str] = []
    a = lines.append

    a("PHASE A REPORT — Commodity Futures Universe")
    a(f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
    a("")

    # Universe coverage
    n_tickers = len(tickers_all)
    date_min  = prices_daily.index.min().date()
    date_max  = prices_daily.index.max().date()
    n_days    = len(prices_daily)
    a(f"Universe: {n_tickers} tickers  |  {date_min} → {date_max}  ({n_days:,} trading days)")
    a("")

    # Per-ticker summary table (sorted by first_date)
    a("── Universe stats (sorted by first_date) ──────────────────────────────")
    cols_show = ["n_obs", "first_date", "last_date",
                 "n_jumps_5sigma", "n_suspected_rolls", "n_market_events",
                 "median_adv", "adv_filter_pct", "basis_coverage_pct"]
    cols_avail = [c for c in cols_show if c in universe_stats.columns]
    preview = universe_stats[cols_avail].copy()
    if "first_date" in preview.columns:
        preview = preview.sort_values("first_date")
    a(preview.to_string())
    a("")

    # Roll artifact summary
    n_rolls  = int(roll_df["is_roll_artifact"].sum())
    n_mkt    = int((~roll_df["is_roll_artifact"]).sum())
    n_total  = len(roll_df)
    a(f"── Roll artifact detection (|z| > 5σ) ────────────────────────────────")
    a(f"  Total 5σ jumps detected: {n_total}")
    a(f"  Classified as roll:      {n_rolls}  ({100*n_rolls/max(n_total,1):.0f}%)")
    a(f"  Classified as mkt event: {n_mkt}  ({100*n_mkt/max(n_total,1):.0f}%)")
    a("")

    # Basis proxy coverage
    a("── Basis proxy coverage (3σ roll-gap, Approach C) ─────────────────────")
    cov_mean = float(basis_cov_df["basis_coverage_pct"].mean()) if not basis_cov_df.empty else 0.0
    n_zero   = int((basis_cov_df["n_roll_artifacts_3sigma"] == 0).sum()) if not basis_cov_df.empty else 0
    a(f"  Mean month-end basis coverage: {cov_mean:.1%}")
    a(f"  Tickers with 0 roll artifacts: {n_zero} (basis will be NaN for these)")
    a("")
    a("  Per-ticker (sorted by basis_coverage_pct):")
    if not basis_cov_df.empty:
        a(basis_cov_df.sort_values("basis_coverage_pct", ascending=False).to_string())
    a("")

    # ADV filter assessment
    if "adv_filter_pct" in universe_stats.columns:
        adv_ok = universe_stats["adv_filter_pct"].fillna(0) >= 0.50
        n_adv_ok = int(adv_ok.sum())
        a(f"── ADV filter (≥5000 contracts/day, 60d rolling) ───────────────────────")
        a(f"  Tickers passing ADV ≥50% of months: {n_adv_ok}/{n_tickers}")
        low_adv = universe_stats[~adv_ok]["adv_filter_pct"].sort_values()
        if not low_adv.empty:
            a(f"  Low-ADV tickers (may be filtered out frequently):")
            for tk, v in low_adv.items():
                adv_med = universe_stats.loc[tk, "median_adv"] if "median_adv" in universe_stats.columns else float("nan")
                a(f"    {tk}: adv_pass={v:.1%}  median_adv={adv_med:.0f}")
        a("")

    # Decision
    a("── DECISION: S_BASIS approach ──────────────────────────────────────────")
    a("  Approach A (Stooq second-month): BLOCKED — Stooq requires paid API key")
    a("  Approach B (yfinance per-delivery ticker): IMPRACTICAL — requires per-")
    a("             delivery-month ticker management (e.g. CLF25, CLG25, ...)")
    a("  Approach C (Roll-Gap Proxy): ADOPTED ✓")
    a(f"    Mean basis coverage = {cov_mean:.1%} of month-ends")
    a("    Mathematically: at roll, continuous jumps from F_near → F_far,")
    a("    so roll_ret = log(F_far/F_near); basis_proxy = -roll_ret × 12.")
    a("    Positive = backwardation = bullish (Erb-Harvey 2006 sign convention).")
    a("")
    a("  PHASE A: READY FOR VALIDATION")
    a("  Awaiting user approval before proceeding to Phase B (IC scan).")

    return "\n".join(lines)


if __name__ == "__main__":
    main()
