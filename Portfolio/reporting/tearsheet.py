"""
Generate self-contained HTML tear sheets for strategy backtests.

Usage
-----
>>> from Portfolio.reporting.tearsheet import generate_tearsheet
>>> path = generate_tearsheet(
...     returns=my_daily_returns,
...     strategy_name="Strategy C — NQ Opening Momentum iter_10",
...     output_path="Portfolio/reporting/output/strategy_c.html",
...     n_trials=321,
...     metadata={"Asset": "MNQ", "Propfirm": "Tradeify 25K"},
... )
>>> print(f"Tear sheet: {path}")
"""
from __future__ import annotations

import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from jinja2 import Environment, FileSystemLoader

from Portfolio.reporting.metrics import compute_all_metrics
from Portfolio.reporting.plots import (
    equity_curve_plot,
    excess_equity_plot,
    monthly_heatmap_plot,
    returns_distribution_plot,
    rolling_sharpe_plot,
)

_TEMPLATE_DIR = Path(__file__).parent


# ── Jinja2 filters ─────────────────────────────────────────────────────────────

def _fmt_num(value: object, fmt: str = ".2f", fallback: str = "n/a") -> str:
    """Format a float, returning fallback string for NaN/None/Inf."""
    if value is None:
        return fallback
    try:
        f = float(value)  # type: ignore[arg-type]
        if math.isnan(f) or math.isinf(f):
            return fallback
        return format(f, fmt)
    except (TypeError, ValueError):
        return fallback


def _color_cls(
    value: object,
    green_thresh: float = 0.0,
    amber_thresh: Optional[float] = None,
    invert: bool = False,
) -> str:
    """
    Return a CSS class name based on the value relative to thresholds.

    Parameters
    ----------
    value : numeric
        The metric value to classify.
    green_thresh : float
        Values ≥ green_thresh → 'pos'; below → check amber or 'neg'.
    amber_thresh : float, optional
        If given, values between amber_thresh and green_thresh → 'neu'.
    invert : bool
        If True, treat lower as better (e.g. for drawdown).
    """
    if value is None:
        return "neu"
    try:
        v = float(value)  # type: ignore[arg-type]
        if math.isnan(v) or math.isinf(v):
            return "neu"
    except (TypeError, ValueError):
        return "neu"

    if invert:
        v = -v
        green_thresh = -green_thresh
        if amber_thresh is not None:
            amber_thresh = -amber_thresh

    if v >= green_thresh:
        return "pos"
    if amber_thresh is not None and v >= amber_thresh:
        return "neu"
    return "neg"


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ── Public API ─────────────────────────────────────────────────────────────────

def generate_tearsheet(
    returns: pd.Series,
    strategy_name: str,
    output_path: str | Path,
    benchmark: Optional[pd.Series] = None,
    n_trials: int = 1,
    metadata: Optional[dict] = None,
    rf: Optional[pd.Series] = None,
) -> Path:
    """
    Compute metrics, generate plots, and write a self-contained HTML tear sheet.

    Parameters
    ----------
    returns : pd.Series
        Daily total return series with datetime index.
        Values are fractions (e.g. 0.012 = +1.2%), NOT cumulative.
    strategy_name : str
        Header display name.
    output_path : str or Path
        Destination path for the HTML file (directories created automatically).
    benchmark : pd.Series, optional
        Daily benchmark returns for the excess-equity section.
    n_trials : int
        Total independent backtests tested; used for DSR correction.
        Pass the project's current n_tests counter for honest reporting.
    metadata : dict, optional
        Additional key-value pairs shown in the header line
        (e.g. {"Asset": "NQ MNQ", "Broker": "Tradeify"}).
    rf : pd.Series, optional
        Pre-fetched FRED DTB3 annualised series (fraction).
        Fetched automatically from FRED if None; falls back to zero
        if FRED is unreachable (tear sheet notes this in the footer).

    Returns
    -------
    Path
        Absolute path to the written HTML file.
    """
    out = Path(output_path).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    metrics = compute_all_metrics(
        returns=returns,
        benchmark=benchmark,
        n_trials=n_trials,
        rf=rf,
    )

    equity_b64 = equity_curve_plot(metrics["_equity"], metrics["_dd"])
    heatmap_b64 = monthly_heatmap_plot(metrics["_monthly"])
    rolling_b64 = rolling_sharpe_plot(metrics["_roll_sr"])
    dist_b64 = returns_distribution_plot(metrics["_returns"])

    excess_b64: Optional[str] = None
    if benchmark is not None and "_bm_equity" in metrics:
        excess_b64 = excess_equity_plot(metrics["_equity"], metrics["_bm_equity"])

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=False,
    )
    env.filters["fn"] = _fmt_num
    env.filters["color_cls"] = _color_cls

    template = env.get_template("template.html")

    ctx: dict = {
        "strategy_name": strategy_name,
        "start_date": str(metrics["start_date"])[:10],
        "end_date": str(metrics["end_date"])[:10],
        "n_obs": metrics["n_obs"],
        "n_years": metrics["n_years"],
        "metadata": metadata or {},
        # Scalars
        "sharpe_hac": metrics["sharpe_hac"],
        "sharpe_t_stat": metrics["sharpe_t_stat"],
        "sharpe_se": metrics["sharpe_se"],
        "sortino": metrics["sortino"],
        "calmar": metrics["calmar"],
        "mar": metrics["mar"],
        "ann_return": metrics["ann_return"],
        "total_return": metrics["total_return"],
        "psr": metrics["psr"],
        "dsr": metrics["dsr"],
        "sharpe_threshold_ann": metrics["sharpe_threshold_ann"],
        "dsr_verdict": metrics["dsr_verdict"],
        "n_trials": n_trials,
        "max_dd": metrics["max_dd"],
        "max_dd_duration_days": metrics["max_dd_duration_days"],
        "tail_ratio": metrics["tail_ratio"],
        "cvar_95": metrics["cvar_95"],
        "cvar_99": metrics["cvar_99"],
        "skewness": metrics["skewness"],
        "excess_kurtosis": metrics["excess_kurtosis"],
        "pct_pos_months": metrics["pct_pos_months"],
        "best_month": metrics["best_month"],
        "worst_month": metrics["worst_month"],
        # Benchmark (None if not computed)
        "benchmark_beta": metrics.get("benchmark_beta"),
        "benchmark_alpha_ann": metrics.get("benchmark_alpha_ann"),
        # Plots
        "equity_plot": equity_b64,
        "heatmap_plot": heatmap_b64,
        "rolling_sr_plot": rolling_b64,
        "dist_plot": dist_b64,
        "excess_plot": excess_b64,
        # Footer
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "git_commit": _git_commit(),
        "python_version": (
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ),
    }

    html = template.render(**ctx)
    out.write_text(html, encoding="utf-8")
    return out
