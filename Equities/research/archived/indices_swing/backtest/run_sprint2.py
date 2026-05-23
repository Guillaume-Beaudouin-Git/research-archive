"""
run_sprint2.py — Full backtests on Sprint 1 IC-passed GO signals.

GO signals (from results/ic_summary.csv):
  S1 VRP  : SPY (h=1,3), QQQ (h=1,3,5,10)   IC > 0  → flip_sign=False
  S2 VIX  : SPY (h=1,3,5,10), QQQ (h=1), EWQ (h=1)  IC < 0  → flip_sign=True

Since signal values are h-independent (h only affects the IC target horizon),
5 unique (signal, ticker) backtests are run plus combined strategies.

Outputs:
  results/backtest_summary.csv
  results/backtest_detail.md
  results/equity_curves/*.png

Run from repo root:
  /usr/bin/python3 Equities/research/active/indices_swing/backtest/run_sprint2.py
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).parents[5]   # Algo_claude/
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

_HERE      = Path(__file__).parent
_PROJ      = _HERE.parent
_RESULTS   = _PROJ / "results"
_EQ_PLOTS  = _RESULTS / "equity_curves"
_RESULTS.mkdir(exist_ok=True)
_EQ_PLOTS.mkdir(exist_ok=True)

# ── Cost configurations ───────────────────────────────────────────────────────
COST_ETF     = 0.001   # 0.10% RT — conservative ETF/next-day entry
COST_FUTURES = 0.0001  # 0.01% RT — futures (propfirm execution)
VOL_TARGET   = 0.10    # 10% annualized portfolio vol target


def main() -> None:
    # ── 1. Load universe ──────────────────────────────────────────────────────
    log.info("Loading universe (start=2007-01-01)…")
    from Equities.research.active.indices_swing.data.universe import load_universe
    U = load_universe(start="2007-01-01")
    log.info(
        "Universe: %d trading days  %s → %s",
        U["meta"]["n_trading_days"],
        U["meta"]["date_start"],
        U["meta"]["date_end"],
    )

    prices    = U["prices"]
    rf        = U["rf"]

    # ── 2. Compute signals ────────────────────────────────────────────────────
    log.info("Computing S1 VRP and S2 VIX term signals…")
    from Equities.research.active.indices_swing.signals.s1_vrp import compute_s1_vrp
    from Equities.research.active.indices_swing.signals.s2_vix_term import compute_s2_vix_term

    s1_df = compute_s1_vrp(U)      # columns: SPY, QQQ  (EWQ=NaN without VSTOXX)
    s2_df = compute_s2_vix_term(U) # columns: SPY, QQQ, EWQ  (VIX9D fallback, 2011+)

    log.info("S1 obs: SPY=%d  QQQ=%d",
             s1_df["SPY"].notna().sum() if "SPY" in s1_df else 0,
             s1_df["QQQ"].notna().sum() if "QQQ" in s1_df else 0)
    log.info("S2 obs: SPY=%d  QQQ=%d  EWQ=%d",
             s2_df["SPY"].notna().sum() if "SPY" in s2_df else 0,
             s2_df["QQQ"].notna().sum() if "QQQ" in s2_df else 0,
             s2_df["EWQ"].notna().sum() if "EWQ" in s2_df else 0)

    # ── 3. Define backtest specs ──────────────────────────────────────────────
    #
    # Each entry: (name, signal_series, ticker, flip_sign)
    # flip_sign=True when IC < 0 (S2: backwardation=bullish → invert signal)
    #
    backtest_specs = [
        ("s1_vrp_SPY",      s1_df["SPY"] if "SPY" in s1_df.columns else pd.Series(dtype=float), "SPY", False),
        ("s1_vrp_QQQ",      s1_df["QQQ"] if "QQQ" in s1_df.columns else pd.Series(dtype=float), "QQQ", False),
        ("s2_vix_term_SPY", s2_df["SPY"] if "SPY" in s2_df.columns else pd.Series(dtype=float), "SPY", True),
        ("s2_vix_term_QQQ", s2_df["QQQ"] if "QQQ" in s2_df.columns else pd.Series(dtype=float), "QQQ", True),
        ("s2_vix_term_EWQ", s2_df["EWQ"] if "EWQ" in s2_df.columns else pd.Series(dtype=float), "EWQ", True),
    ]

    # ── 4. Run individual backtests ────────────────────────────────────────────
    from Equities.research.active.indices_swing.backtest.engine import (
        run_signal_backtest, run_combo_backtest, run_portfolio_backtest, verdict_gate
    )

    results: dict[str, dict] = {}

    for name, sig, ticker, flip in backtest_specs:
        if sig.notna().sum() < 200:
            log.warning("Skipping %s — insufficient signal obs (%d)", name, sig.notna().sum())
            continue

        close = prices.get((ticker, "close"))
        if close is None:
            log.warning("Skipping %s — ticker %s not in prices", name, ticker)
            continue

        log.info("Running backtest: %s  (flip=%s)", name, flip)
        res = run_signal_backtest(
            signal       = sig,
            prices_close = close,
            rf           = rf,
            name         = name,
            vol_target   = VOL_TARGET,
            cost_rt      = COST_ETF,
            flip_sign    = flip,
        )
        v, _ = verdict_gate(res["stats_full"], res["stats_wf"])
        res["verdict"] = v
        results[name]  = res

        sf  = res["stats_full"]
        wf  = res["stats_wf"]
        log.info(
            "  %-24s  Sharpe=%+.2f  MaxDD=%+.3f  WF=%.0f%%  %s",
            name, sf.get("sharpe", float("nan")), sf.get("max_dd", float("nan")),
            (wf.get("wf_positive_frac") or 0) * 100, v,
        )

    # ── 5. Combined (S1+S2) per ticker ────────────────────────────────────────
    for ticker in ("SPY", "QQQ"):
        s1_key = f"s1_vrp_{ticker}"
        s2_key = f"s2_vix_term_{ticker}"

        if s1_key not in results or s2_key not in results:
            log.info("Combo %s skipped — missing component", ticker)
            continue

        s1_z  = results[s1_key]["signal_z"]
        s2_z  = results[s2_key]["signal_z"]   # already direction-corrected (flip applied)

        close = prices.get((ticker, "close"))
        combo_name = f"combo_{ticker}"

        log.info("Running combo backtest: %s", combo_name)
        res = run_combo_backtest(
            signals_z    = {"s1": s1_z, "s2": s2_z},
            prices_close = close,
            rf           = rf,
            name         = combo_name,
            vol_target   = VOL_TARGET,
            cost_rt      = COST_ETF,
        )
        v, _ = verdict_gate(res["stats_full"], res["stats_wf"])
        res["verdict"] = v
        results[combo_name] = res

        sf  = res["stats_full"]
        wf  = res["stats_wf"]
        log.info(
            "  %-24s  Sharpe=%+.2f  MaxDD=%+.3f  WF=%.0f%%  %s",
            combo_name, sf.get("sharpe", float("nan")), sf.get("max_dd", float("nan")),
            (wf.get("wf_positive_frac") or 0) * 100, v,
        )

    # ── 6. ERC portfolio of all individual strategies ─────────────────────────
    individual_pnls = {k: v["pnl"] for k, v in results.items()
                       if k in {n for n, _, _, _ in backtest_specs}}

    if len(individual_pnls) >= 2:
        log.info("Running ERC portfolio (%d components)…", len(individual_pnls))
        port_res = run_portfolio_backtest(individual_pnls, name="portfolio_erc")
        v, _ = verdict_gate(port_res["stats_full"], port_res["stats_wf"])
        port_res["verdict"] = v
        results["portfolio_erc"] = port_res

        sf  = port_res["stats_full"]
        wf  = port_res["stats_wf"]
        log.info(
            "  %-24s  Sharpe=%+.2f  MaxDD=%+.3f  WF=%.0f%%  %s",
            "portfolio_erc", sf.get("sharpe", float("nan")), sf.get("max_dd", float("nan")),
            (wf.get("wf_positive_frac") or 0) * 100, v,
        )

    # ── 7. Save CSV summary ───────────────────────────────────────────────────
    rows = []
    for label, res in results.items():
        sf  = res["stats_full"]
        sg  = res.get("stats_gross", {})
        wf  = res["stats_wf"]
        rows.append({
            "strategy":        label,
            "n_days":          sf.get("n_days", np.nan),
            "n_years":         sf.get("n_years", np.nan),
            "sharpe_gross":    sg.get("sharpe", np.nan),
            "sharpe_net":      sf.get("sharpe", np.nan),
            "ann_ret":         sf.get("ann_ret", np.nan),
            "ann_vol":         sf.get("ann_vol", np.nan),
            "max_dd":          sf.get("max_dd", np.nan),
            "calmar":          sf.get("calmar", np.nan),
            "turnover_ann":    res.get("turnover_ann", np.nan),
            "wf_pos_frac":     wf.get("wf_positive_frac", np.nan),
            "wf_sharpes":      str(wf.get("wf_sharpe_list", [])),
            "verdict":         res.get("verdict", "?"),
        })

    summary = pd.DataFrame(rows)
    summary.to_csv(_RESULTS / "backtest_summary.csv", index=False)
    log.info("Saved backtest_summary.csv (%d rows)", len(summary))

    # ── 8. Equity curve plots ─────────────────────────────────────────────────
    log.info("Generating equity curve plots…")
    _plot_equity_curves(results)

    # ── 9. Write backtest_detail.md ───────────────────────────────────────────
    log.info("Writing backtest_detail.md…")
    _write_detail(summary, results)

    # ── 10. Print results to console ──────────────────────────────────────────
    print("\n" + "=" * 110)
    print("SPRINT 2 — FULL BACKTEST RESULTS  (vol_target=10%, cost=0.10% RT ETF)")
    print("=" * 110)
    cols = ["strategy", "n_years", "sharpe_gross", "sharpe_net", "ann_ret",
            "max_dd", "turnover_ann", "wf_pos_frac", "verdict"]
    cols = [c for c in cols if c in summary.columns]
    print(summary[cols].to_string(index=False, float_format="{:.3f}".format))
    print("=" * 110)
    print("\nCost-drag analysis (ETF 0.10% RT vs futures 0.01% RT projection):")
    for _, row in summary.iterrows():
        sg   = row.get("sharpe_gross", float("nan"))
        sn   = row.get("sharpe_net",   float("nan"))
        to   = row.get("turnover_ann", float("nan"))
        if not (np.isnan(sg) or np.isnan(sn)):
            drag_etf  = sg - sn
            sn_fut    = sg - drag_etf * (COST_FUTURES / COST_ETF)  # linear scaling of drag
            gate_str  = "RESEARCH✓" if sn_fut > 0.70 else ("PARTIAL" if sn_fut > 0.40 else "FAIL")
        else:
            drag_etf = sn_fut = float("nan")
            gate_str = "?"
        print(f"  {row['strategy']:<26}: gross={sg:+.3f}  net_etf={sn:+.3f}  "
              f"net_fut={sn_fut:+.3f}  turn={to:.0f}x/yr  [{gate_str}]")


# ─────────────────────────────────────────────────────────────────────────────
# Plotting
# ─────────────────────────────────────────────────────────────────────────────

def _plot_equity_curves(results: dict) -> None:
    """One figure: overlaid equity curves for all strategies."""
    fig, ax = plt.subplots(figsize=(12, 6))

    color_map = plt.cm.get_cmap("tab10")
    labels_plotted = []
    for i, (label, res) in enumerate(results.items()):
        if "pnl" not in res:
            continue
        equity = res["equity"]
        if equity.empty or equity.notna().sum() < 50:
            continue

        sr   = res["stats_full"].get("sharpe", float("nan"))
        v    = res.get("verdict", "?")
        lw   = 2.0 if "combo" in label or "portfolio" in label else 1.0
        ls   = "-" if "portfolio" in label else ("--" if "combo" in label else "-")
        c    = color_map(i % 10)

        ax.plot(equity.index, equity.values, label=f"{label} (SR={sr:.2f}, {v})",
                linewidth=lw, linestyle=ls, color=c, alpha=0.85)
        labels_plotted.append(label)

    ax.axhline(0, color="black", linewidth=0.5, linestyle=":")
    ax.set_xlabel("Date")
    ax.set_ylabel("Cumulative P&L (fraction of notional)")
    ax.set_title("Sprint 2 — Equity Curves  (vol_target=10%, cost=0.10% RT)")
    ax.legend(fontsize=7, loc="upper left")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    plt.tight_layout()

    out = _EQ_PLOTS / "all_strategies.png"
    fig.savefig(out, dpi=130)
    plt.close(fig)
    log.info("Saved %s", out.name)

    # Individual equity curves
    for label, res in results.items():
        if "pnl" not in res or res["equity"].empty:
            continue
        equity = res["equity"]
        pnl    = res["pnl"]
        sf     = res["stats_full"]
        wf     = res["stats_wf"]
        v      = res.get("verdict", "?")

        fig, axes = plt.subplots(2, 1, figsize=(10, 7), height_ratios=[3, 1],
                                 sharex=True)

        # Equity curve + drawdown
        ax_eq = axes[0]
        cum   = equity
        dd    = cum - cum.cummax()
        ax_eq.plot(cum.index, cum.values, color="steelblue", linewidth=1.5)
        ax_eq.fill_between(dd.index, dd.values, 0, color="red", alpha=0.25, label="Drawdown")
        ax_eq.axhline(0, color="black", linewidth=0.5, linestyle=":")
        ax_eq.set_ylabel("Cumulative P&L")
        ax_eq.legend(fontsize=8, loc="upper left")
        ax_eq.set_title(
            f"{label}  |  Sharpe={sf.get('sharpe', float('nan')):.2f}  "
            f"MaxDD={sf.get('max_dd', float('nan')):.3f}  "
            f"WF={wf.get('wf_positive_frac', float('nan')):.0%}  "
            f"→ {v}"
        )

        # Rolling 252d Sharpe
        ax_sr = axes[1]
        roll_pnl_mean = pnl.rolling(252, min_periods=126).mean() * 252
        roll_pnl_std  = pnl.rolling(252, min_periods=126).std() * (252 ** 0.5)
        roll_sr       = roll_pnl_mean / roll_pnl_std
        ax_sr.plot(roll_sr.index, roll_sr.values, color="darkorange", linewidth=1.2)
        ax_sr.axhline(0, color="black", linewidth=0.5, linestyle=":")
        ax_sr.axhline(1, color="green",  linewidth=0.5, linestyle="--")
        ax_sr.set_ylabel("Rolling 1y Sharpe")
        ax_sr.set_xlabel("Date")
        ax_sr.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

        plt.tight_layout()
        out = _EQ_PLOTS / f"{label}.png"
        fig.savefig(out, dpi=130)
        plt.close(fig)
        log.info("Saved %s", out.name)


# ─────────────────────────────────────────────────────────────────────────────
# Report generation
# ─────────────────────────────────────────────────────────────────────────────

def _write_detail(summary: pd.DataFrame, results: dict) -> None:
    lines = [
        "# Sprint 2 — Full Backtest Results",
        "",
        f"**Generated**: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}  ",
        "**Vol target**: 10% annualized  ",
        "**Cost**: 0.10% round-trip (conservative ETF/next-day entry)  ",
        "**Position model**: daily vol-targeted; signal z-score 252d rolling; clip ±3σ  ",
        "",
        "**Gates**:  ",
        "- RESEARCH_PASS: Sharpe > 0.7, MaxDD > -25%, WF positive fraction > 50%  ",
        "- PROPFIRM_PASS: Sharpe > 1.0, MaxDD > -10%, WF positive fraction > 60%  ",
        "",
        "---",
        "",
        "## Results Summary",
        "",
        "```",
    ]

    cols = ["strategy", "n_years", "sharpe_gross", "sharpe_net", "ann_ret", "ann_vol",
            "max_dd", "calmar", "turnover_ann", "wf_pos_frac", "verdict"]
    cols = [c for c in cols if c in summary.columns]
    lines.append(summary[cols].to_string(index=False, float_format="{:.3f}".format))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Per-strategy detail
    lines.append("## Per-Strategy Detail")
    lines.append("")

    for _, row in summary.iterrows():
        label = row["strategy"]
        res   = results.get(label, {})
        sf    = res.get("stats_full", {})
        wf    = res.get("stats_wf", {})

        lines.append(f"### {label}")
        lines.append(f"**Verdict**: {row['verdict']}  ")
        lines.append(f"**Period**: {sf.get('n_years', '?')} years, {sf.get('n_days', '?')} days  ")
        lines.append(f"**Sharpe**: {sf.get('sharpe', float('nan')):.3f}  ")
        lines.append(f"**Ann. return**: {sf.get('ann_ret', float('nan'))*100:.2f}%  ")
        lines.append(f"**Ann. vol**: {sf.get('ann_vol', float('nan'))*100:.2f}%  ")
        lines.append(f"**Max DD**: {sf.get('max_dd', float('nan'))*100:.2f}%  ")
        lines.append(f"**Calmar**: {sf.get('calmar', float('nan')):.3f}  ")

        sg  = res.get("stats_gross", {})
        to  = res.get("turnover_ann", float("nan"))
        lines.append(f"**Sharpe (gross/net)**: {sg.get('sharpe', float('nan')):.3f} / {sf.get('sharpe', float('nan')):.3f}  ")
        lines.append(f"**Annual turnover**: {to:.1f}× (position notional)  ")
        wf_list  = wf.get("wf_sharpe_list", [])
        pos_frac = wf.get("wf_positive_frac", float("nan"))
        lines.append(f"**WF positive frac**: {pos_frac:.0%} ({wf.get('n_folds', 0)} folds)  ")
        lines.append(f"**WF fold Sharpes**: {wf_list}  ")
        lines.append("")

    # Cost-sensitivity section
    lines += [
        "---",
        "",
        "## Cost Sensitivity (ETF 0.10% RT vs Futures 0.01% RT)",
        "",
        "Futures cost projection = gross_sharpe − drag_etf × 0.10  (linear cost assumption)",
        "",
        "| Strategy | Gross SR | ETF net (0.10%RT) | Fut net (0.01%RT) | Turnover/yr |",
        "|----------|----------|-------------------|--------------------|-------------|",
    ]
    for _, row in summary.iterrows():
        sg  = row.get("sharpe_gross", float("nan"))
        sn  = row.get("sharpe_net",   float("nan"))
        to  = row.get("turnover_ann", float("nan"))
        if not (np.isnan(sg) or np.isnan(sn)):
            sn_fut = sg - (sg - sn) * (COST_FUTURES / COST_ETF)
        else:
            sn_fut = float("nan")
        lines.append(
            f"| {row['strategy']} | {sg:.3f} | {sn:.3f} | {sn_fut:.3f} | {to:.0f}× |"
        )
    lines.append("")

    # Sprint 2 remaining items
    lines += [
        "---",
        "",
        "## Sprint 2 Remaining Items",
        "",
        "1. **S1 EWQ VRP with VSTOXX**: download `data/vstoxx_manual.csv` from STOXX.com",
        "2. **S2 primary (VX1/VX2)**: download `data/vx_futures_manual.csv` from CBOE; "
        "   VX ratio is the mechanistically correct term structure signal",
        "3. **S4 extended coverage**: AAII weekly + post-2019 CBOE PCR (manual downloads)",
        "4. **Propfirm sizing**: if PROPFIRM_PASS, compute MES/MNQ contract sizing for $50K account",
        "",
    ]

    out = _RESULTS / "backtest_detail.md"
    out.write_text("\n".join(lines))
    log.info("Saved backtest_detail.md")


if __name__ == "__main__":
    main()
