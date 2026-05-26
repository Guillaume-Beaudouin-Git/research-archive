"""
High-level pipeline: generate a self-contained HTML CPCV report.

Design: standalone HTML via a separate template_cpcv.html (no coupling to
tearsheet.py or template.html). Reuses the same Jinja2 Environment pattern,
matplotlib base64 encoding, and CSS palette from Portfolio/reporting/.
"""
from __future__ import annotations

import base64
import io
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader

from Portfolio.validation.cpcv import run_cpcv
from Portfolio.validation.multi_test import deflated_sharpe, harvey_liu_bhy
from Portfolio.reporting.metrics import (
    TRADING_DAYS,
    compute_psr_dsr,
    to_excess_returns,
)

_TEMPLATE_DIR = Path(__file__).parent

# GitHub dark palette (consistent with plots.py)
_BG = "#0d1117"
_PANEL = "#161b22"
_BORDER = "#30363d"
_TEXT = "#e6edf3"
_MUTED = "#8b949e"
_GREEN = "#3fb950"
_RED = "#f85149"
_BLUE = "#58a6ff"
_ORANGE = "#d29922"

_RC = {
    "figure.facecolor": _BG,
    "axes.facecolor": _PANEL,
    "axes.edgecolor": _BORDER,
    "axes.labelcolor": _TEXT,
    "xtick.color": _TEXT,
    "ytick.color": _TEXT,
    "grid.color": _BORDER,
    "grid.alpha": 0.4,
    "text.color": _TEXT,
}


def _git_commit() -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def _sharpe_histogram_b64(
    sharpes: np.ndarray,
    wf_baseline: Optional[float],
    n_paths: int,
) -> str:
    """Return base64 PNG of the CPCV Sharpe distribution histogram."""
    from scipy.stats import gaussian_kde

    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(12, 4), facecolor=_BG)

        # Histogram
        n_bins = max(10, min(30, n_paths // 2))
        counts, edges, patches = ax.hist(sharpes, bins=n_bins, color=_BLUE,
                                          alpha=0.7, edgecolor=_BG, linewidth=0.5)
        # Colour bars by sign
        for patch, left in zip(patches, edges[:-1]):
            patch.set_facecolor(_GREEN if (left + (edges[1]-edges[0])/2) > 0 else _RED)
            patch.set_alpha(0.8)

        # KDE overlay
        if sharpes.std() > 0:
            kde_x = np.linspace(sharpes.min() - 0.5, sharpes.max() + 0.5, 300)
            kde_y = gaussian_kde(sharpes)(kde_x)
            scale = counts.max() / kde_y.max() if kde_y.max() > 0 else 1.0
            ax.plot(kde_x, kde_y * scale, color=_TEXT, linewidth=1.5,
                    alpha=0.9, label="KDE")

        # Vertical lines
        ax.axvline(0, color=_MUTED, linewidth=1.0, linestyle="--", alpha=0.6)
        ax.axvline(float(np.median(sharpes)), color=_BLUE, linewidth=1.5,
                   linestyle="-", alpha=0.9,
                   label=f"Median {np.median(sharpes):.2f}")
        if wf_baseline is not None:
            ax.axvline(wf_baseline, color=_ORANGE, linewidth=1.5,
                       linestyle="--", alpha=0.9,
                       label=f"WF baseline {wf_baseline:.2f}")

        ax.set_xlabel("Sharpe Ratio (OOS per path)", fontsize=10)
        ax.set_ylabel("Number of paths", fontsize=10)
        ax.set_title(
            f"CPCV Sharpe Distribution — {n_paths} paths "
            f"| mean={sharpes.mean():.2f} std={sharpes.std():.2f}",
            fontsize=11, pad=8,
        )
        ax.legend(fontsize=9, framealpha=0.7)
        ax.grid(axis="y", alpha=0.3)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        buf = io.BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight", dpi=140,
                    facecolor=_BG)
        plt.close(fig)

    return base64.b64encode(buf.getvalue()).decode("ascii")


def generate_cpcv_report(
    returns: pd.Series,
    strategy_name: str,
    backtest_fn: Callable,
    n_trials: int,
    output_path: str | Path,
    n_folds: int | None = None,
    wf_baseline_sharpe: float | None = None,
    _cpcv_result: dict | None = None,
) -> Path:
    """
    Produce an HTML report with CPCV distribution, DSR, and WF comparison.

    Parameters
    ----------
    returns : pd.Series
        Daily total return series with datetime index.
    strategy_name : str
        Header display name (e.g. "Strategy A — TSMOM v3").
    backtest_fn : Callable[[train_idx, test_idx], float]
        Passed directly to run_cpcv. For non-parametric strategies, build
        via make_tsmom_backtest_fn() in strategies/tsmom_signal.py.
    n_trials : int
        Project-wide n_tests counter for DSR correction (honest reporting).
    output_path : str or Path
        Destination HTML file (directories created automatically).
    n_folds : int, optional
        Override auto-selected fold count from optimal_folds_number.
    wf_baseline_sharpe : float, optional
        Walk-forward OOS Sharpe (e.g. 1.33 for Strategy A). Shown as
        comparison baseline in the report.

    Returns
    -------
    Path
        Absolute path to the written HTML file (guaranteed > 10 KB).
    """
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    r = returns.dropna()
    T = len(r)

    # ── Run CPCV (or reuse pre-computed result) ───────────────────────────────
    if _cpcv_result is not None:
        cpcv = _cpcv_result
        print(f"\n  Using pre-computed CPCV result for {strategy_name} "
              f"({cpcv['n_paths']} paths).")
    else:
        print(f"\n  Running CPCV on {strategy_name} (T={T} obs) …")
        cpcv = run_cpcv(
            returns=r,
            backtest_fn=backtest_fn,
            n_folds=n_folds,
            target_n_paths=30,
            target_train_size=252,
            verbose=True,
        )

    # ── Global DSR / PSR (on median path Sharpe) ─────────────────────────────
    sr_median_daily = float(np.median(cpcv["sharpes"])) / math.sqrt(TRADING_DAYS)
    dsr_global = deflated_sharpe(sr_median_daily, n_trials=n_trials, T=T)

    r_exc = to_excess_returns(r)
    psr_dsr_full = compute_psr_dsr(r_exc, n_trials=n_trials)
    psr_global = float(psr_dsr_full["psr"])

    # ── Per-path DSR ──────────────────────────────────────────────────────────
    per_path_dsr = []
    for sr_ann in cpcv["sharpes"]:
        sr_d = float(sr_ann) / math.sqrt(TRADING_DAYS)
        dsr = deflated_sharpe(sr_d, n_trials=n_trials, T=T)
        per_path_dsr.append(dsr)

    per_path_dsr_arr = np.array(per_path_dsr)

    # BHY on (1 - DSR) as p-values
    pvals = [1.0 - d for d in per_path_dsr]
    bhy = harvey_liu_bhy(pvals, alpha=0.05)

    # ── Histogram plot ────────────────────────────────────────────────────────
    histogram_b64 = _sharpe_histogram_b64(
        sharpes=cpcv["sharpes"],
        wf_baseline=wf_baseline_sharpe,
        n_paths=cpcv["n_paths"],
    )

    # ── DSR rows for table (max 30 shown) ────────────────────────────────────
    n_show = min(30, cpcv["n_paths"])
    dsr_rows = [
        {
            "path": i + 1,
            "sharpe": float(cpcv["sharpes"][i]),
            "dsr": float(per_path_dsr[i]),
        }
        for i in range(n_show)
    ]

    # ── Render HTML ───────────────────────────────────────────────────────────
    env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)), autoescape=False)
    template = env.get_template("template_cpcv.html")

    ctx: dict = {
        "strategy_name": strategy_name,
        "start_date": str(r.index.min())[:10],
        "end_date": str(r.index.max())[:10],
        "n_obs": T,
        "n_trials": n_trials,
        "n_paths": cpcv["n_paths"],
        "n_folds": cpcv["n_folds"],
        "n_test_folds": cpcv["n_test_folds"],
        "purge_size": cpcv["purge_size"],
        "embargo_size": cpcv["embargo_size"],
        # Distribution
        "mean_sharpe": cpcv["mean"],
        "median_sharpe": cpcv["median"],
        "std_sharpe": cpcv["std"],
        "ci_5": cpcv["ci_5_95"][0],
        "ci_95": cpcv["ci_5_95"][1],
        # Multiple testing
        "dsr_global": dsr_global,
        "psr_global": psr_global,
        # Comparison
        "wf_baseline": wf_baseline_sharpe,
        # Chart
        "histogram_b64": histogram_b64,
        # Per-path table
        "dsr_rows": dsr_rows,
        # Footer
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git_commit(),
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
    }

    html = template.render(**ctx)
    out.write_text(html, encoding="utf-8")

    size_kb = out.stat().st_size / 1024
    print(f"  Report written → {out} ({size_kb:.0f} KB)")
    return out
