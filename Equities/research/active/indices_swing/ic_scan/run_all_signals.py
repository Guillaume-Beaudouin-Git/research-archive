"""
run_all_signals.py — Sprint 1 IC scan orchestrator.

Runs all 6 signals × 4 horizons × 3 assets (where data is available).
Outputs: results/ic_summary.csv, results/s3_tom_event_study.csv, results/verdict.md,
         results/ic_per_signal/*.png

Run from repo root:
  /usr/bin/python3 Equities/research/active/indices_swing/ic_scan/run_all_signals.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parents[5]   # Algo_claude/
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_HERE        = Path(__file__).parent
_RESULTS_DIR = _HERE.parent / "results"
_IC_PLOTS    = _RESULTS_DIR / "ic_per_signal"
_RESULTS_DIR.mkdir(exist_ok=True)
_IC_PLOTS.mkdir(exist_ok=True)

PRIMARY_TICKERS = ["SPY", "QQQ", "EWQ"]
HORIZONS        = [1, 3, 5, 10]
UNIVERSE_START  = "2007-01-01"   # enough lookback for rolling indicators


def main() -> None:
    # ── 1. Load universe ──────────────────────────────────────────────────────
    log.info("Loading universe (start=%s)…", UNIVERSE_START)
    from Equities.research.active.indices_swing.data.universe import load_universe
    U = load_universe(start=UNIVERSE_START)
    log.info(
        "Universe ready: %d trading days, %s → %s",
        U["meta"]["n_trading_days"],
        U["meta"]["date_start"],
        U["meta"]["date_end"],
    )

    # ── 2. Compute signals ────────────────────────────────────────────────────
    log.info("Computing signals…")
    from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
    from Equities.research.active.indices_swing.signals.s2_vix_term import compute_s2_vix_term
    from Equities.research.active.indices_swing.signals.s3_turn_of_month import (
        compute_s3_tom, compute_s3_event_study
    )
    from Equities.research.active.indices_swing.signals.s4_sentiment_composite import (
        compute_s4_variants
    )
    from Equities.research.active.indices_swing.signals.s5_xs_momentum import (
        compute_s5_xs_momentum
    )
    from Equities.research.active.indices_swing.signals.s6_hy_oas_regime import (
        compute_s6_hy_oas
    )

    s1  = compute_s1_vrp(U)
    s2  = compute_s2_vix_term(U)
    s3  = compute_s3_tom(U)
    s4d = compute_s4_variants(U)
    s5  = compute_s5_xs_momentum(U)
    s6  = compute_s6_hy_oas(U)

    # S3 event study (Amendment 2)
    s3_event = compute_s3_event_study(U, ticker="SPY", h=1)
    s3_event.to_csv(_RESULTS_DIR / "s3_tom_event_study.csv", index=False)
    log.info("Saved s3_tom_event_study.csv")

    # Signal registry: {signal_id: DataFrame with ticker columns}
    signal_registry = {
        "s1_vrp":           s1,
        "s2_vix_term":      s2,
        "s3_tom":           s3,
        "s4a_pcr_only":     s4d["s4a_pcr_only"],
        "s4b_naaim_only":   s4d["s4b_naaim_only"],
        "s4c_composite":    s4d["s4c_composite"],
        "s5_xs_mom":        s5,
        "s6_hy_oas":        s6,
    }

    # ── 3. Run IC engine ──────────────────────────────────────────────────────
    log.info("Running IC engine…")
    from Equities.research.active.indices_swing.ic_scan.ic_engine import compute_ic
    from Equities.research.active.indices_swing.ic_scan.plots import (
        plot_rolling_ic, plot_tom_event_study, plot_ic_heatmap
    )

    rows   = []
    roll_ic_store: dict[str, pd.Series] = {}

    for sig_id, sig_df in signal_registry.items():
        for ticker in PRIMARY_TICKERS:
            if ticker not in sig_df.columns:
                log.debug("Signal %s has no column %s — skipping", sig_id, ticker)
                continue

            sig_series = sig_df[ticker]
            if sig_series.notna().sum() < 50:
                log.info("Signal %s / %s has < 50 non-NaN obs — skipping", sig_id, ticker)
                continue

            for h in HORIZONS:
                if (ticker, h) not in U["fwd_ret"].columns:
                    continue

                fwd    = U["fwd_ret"][(ticker, h)]
                hac_lag = max(2, round(1.5 * h))

                stats = compute_ic(sig_series, fwd, hac_lag=hac_lag)
                row = {
                    "signal":  sig_id,
                    "asset":   ticker,
                    "h":       h,
                    "hac_lag": hac_lag,
                    **{k: v for k, v in stats.items() if k != "roll_ic"},
                }
                rows.append(row)

                # Store rolling IC for plotting
                label = f"{sig_id}_{ticker}_h{h}"
                roll_ic_store[label] = stats["roll_ic"]

                log.info(
                    "  %-20s %-4s h=%2d  n=%4d  IC=%+.3f  t=%+.2f  stab=%.2f  %s",
                    sig_id, ticker, h,
                    stats["n_obs"], stats["ic_mean"], stats["t_hac"],
                    stats["stability"] if not np.isnan(stats.get("stability", np.nan)) else -1,
                    stats["verdict"],
                )

    # ── 4. Save ic_summary.csv ────────────────────────────────────────────────
    summary = pd.DataFrame(rows)
    col_order = [
        "signal", "asset", "h", "hac_lag", "n_obs",
        "ic_mean", "t_hac", "ic_post2020", "ic_pre2020",
        "stability", "post2020_consistent", "verdict",
    ]
    col_order = [c for c in col_order if c in summary.columns]
    summary   = summary[col_order]
    summary.to_csv(_RESULTS_DIR / "ic_summary.csv", index=False)
    log.info("Saved ic_summary.csv (%d rows)", len(summary))

    # ── 5. Generate plots ─────────────────────────────────────────────────────
    log.info("Generating plots…")

    # Rolling IC plots for GO/borderline rows
    for label, roll_ic in roll_ic_store.items():
        parts  = label.split("_")
        # Parse signal, asset, horizon from label
        # label format: s1_vrp_SPY_h5 or s4a_pcr_only_QQQ_h3
        asset  = next((p for p in parts if p in PRIMARY_TICKERS), "?")
        h_part = next((p for p in parts if p.startswith("h") and p[1:].isdigit()), "h?")
        h_val  = int(h_part[1:]) if h_part != "h?" else -1

        # Find IC for this entry
        match = summary[
            (summary["asset"] == asset) & (summary["h"] == h_val) &
            (summary["signal"] == "_".join(parts[: parts.index(asset)]))
        ]
        ic_full = match["ic_mean"].iloc[0] if len(match) > 0 else 0.0

        # Only plot if some rolling IC exists
        if roll_ic.notna().sum() > 10:
            plot_rolling_ic(roll_ic, label, ic_full, h_val, _IC_PLOTS)

    # TOM event study plot (Amendment 2)
    plot_tom_event_study(s3_event, _IC_PLOTS)

    # IC heatmap
    plot_ic_heatmap(summary, _IC_PLOTS)

    # ── 6. Write verdict.md ───────────────────────────────────────────────────
    log.info("Writing verdict.md…")
    _write_verdict(summary, s3_event)

    # ── 7. Summary to console ─────────────────────────────────────────────────
    print("\n" + "=" * 80)
    print("SPRINT 1 IC SCAN — RESULTS SUMMARY")
    print("=" * 80)
    go_rows = summary[summary["verdict"] == "GO"]
    print(f"\nGO signals: {len(go_rows)} / {len(summary)} tested\n")
    print(summary.to_string(index=False, max_rows=100, float_format="{:.3f}".format))
    print("\n" + "=" * 80)
    if len(go_rows) > 0:
        print("\nGO SIGNALS:")
        print(go_rows[["signal", "asset", "h", "n_obs", "ic_mean", "t_hac",
                        "stability", "ic_post2020"]].to_string(index=False,
                        float_format="{:.3f}".format))


def _write_verdict(summary: pd.DataFrame, s3_event: pd.DataFrame) -> None:
    """Write verdict.md with per-signal narrative."""
    lines = [
        "# Sprint 1 IC Scan — Verdict",
        "",
        f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Universe**: SPY, QQQ, EWQ | **Horizons**: 1, 3, 5, 10d  ",
        f"**n_tests this sprint**: {len(summary)} (AMTP not applied at IC scan stage)  ",
        "",
        "**Gates**: |IC| > 0.02, |t_HAC| > 2.0, stability > 0.70, post-2020 consistent",
        "",
        "---",
        "",
        "## Results Table",
        "",
    ]

    # Table
    cols = ["signal", "asset", "h", "n_obs", "ic_mean", "t_hac",
            "ic_post2020", "stability", "verdict"]
    cols = [c for c in cols if c in summary.columns]
    lines.append("```")
    lines.append(summary[cols].to_string(index=False, float_format="{:.3f}".format))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-signal narrative
    lines.append("## Per-Signal Narrative")
    lines.append("")

    for sig_id in summary["signal"].unique():
        sub = summary[summary["signal"] == sig_id]
        go_sub = sub[sub["verdict"] == "GO"]
        lines.append(f"### {sig_id.upper()}")

        if len(go_sub) > 0:
            best = go_sub.sort_values("t_hac", ascending=False).iloc[0]
            lines.append(
                f"**Status**: GO on {len(go_sub)} (signal×asset×h) combinations.  "
            )
            lines.append(
                f"**Best**: {best['asset']} h={best['h']}d — "
                f"IC={best['ic_mean']:.3f}, t={best['t_hac']:.2f}, "
                f"stab={best['stability']:.2f}  "
            )
        else:
            nogo = sub.iloc[0] if len(sub) > 0 else None
            lines.append("**Status**: NO-GO (all tested combinations fail at least one gate).  ")
            if nogo is not None and not all(sub["ic_mean"].isna()):
                best_t = sub.loc[sub["t_hac"].abs().idxmax()]
                lines.append(
                    f"Best t_HAC: {best_t['asset']} h={best_t['h']}d — "
                    f"IC={best_t['ic_mean']:.3f}, t={best_t['t_hac']:.2f}  "
                )
        lines.append("")

    # Special notes
    lines += [
        "---",
        "",
        "## Known Limitations & Sprint 2 Items",
        "",
        "- **EWQ S1 VRP**: VSTOXX not available on free platforms (yfinance 404, Stooq requires API key)."
        " EWQ VRP excluded. Sprint 2: download `data/vstoxx_manual.csv` from STOXX.com.",
        "- **S2 primary (VX1/VX2)**: CBOE VX futures require manual CSV. Sprint 1 uses VIX9D/VIX fallback (2011+).",
        "- **S4 AAII**: Akamai-blocked. S4a/S4c use PCR only (2006-2019), S4b uses NAAIM alone.",
        "- **S4 PCR coverage**: CBOE PCR frozen at 2019-10-04. S4a and S4c limited to this window.",
        "- **BAMLH0A0HYM2 (HY OAS)**: ICE licensing restricts FRED download to ~3y. S6 uses HYG proxy (2007+).",
        "",
        "## S3 TOM Event Study",
        "",
    ]

    lines.append("```")
    lines.append(s3_event.to_string(index=False, float_format="{:.4f}".format))
    lines.append("```")
    lines.append("")

    verdict_path = _RESULTS_DIR / "verdict.md"
    verdict_path.write_text("\n".join(lines))
    log.info("Saved verdict.md")


if __name__ == "__main__":
    main()
