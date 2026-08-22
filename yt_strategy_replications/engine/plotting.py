"""
Plotting helpers (kept separate from core logic per the project's code style:
no matplotlib inside strategy/backtest modules). Saves PNGs for the reports.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import stats as S


def plot_equity(curves: pd.DataFrame, title: str, out_path: str | Path,
                logy: bool = True) -> None:
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), height_ratios=[3, 1], sharex=True)
    ax1.plot(curves.index, curves["strategy"], label="Strategy", lw=1.3)
    if "buy_hold" in curves:
        ax1.plot(curves.index, curves["buy_hold"], label="Buy & Hold", lw=1.0, alpha=0.7)
    ax1.set_title(title)
    ax1.set_ylabel("Equity (×, start=1)")
    if logy:
        ax1.set_yscale("log")
    ax1.legend(loc="upper left")
    ax1.grid(alpha=0.25)

    _, dd = S.max_drawdown(curves["strategy"].to_numpy(float))
    ax2.fill_between(curves.index, dd * 100, 0, color="crimson", alpha=0.4)
    ax2.set_ylabel("Drawdown (%)")
    ax2.grid(alpha=0.25)
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def plot_sharpe_distribution(sharpes: dict[str, float], title: str, out_path: str | Path) -> None:
    """Bar chart of per-instrument Sharpe (shows cross-sectional robustness)."""
    items = sorted(sharpes.items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    vals = [v for _, v in items]
    fig, ax = plt.subplots(figsize=(10, max(3, 0.35 * len(names))))
    colors = ["seagreen" if v > 0 else "indianred" for v in vals]
    ax.barh(names, vals, color=colors)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_title(title)
    ax.set_xlabel("Annualised Sharpe (net of costs)")
    ax.grid(alpha=0.25, axis="x")
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def plot_curve_pair(series: dict[str, pd.Series], title: str, ylabel: str,
                    out_path: str | Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 5))
    for name, s in series.items():
        ax.plot(s.index, s.values, label=name, lw=1.2)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(loc="best")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=110)
    plt.close(fig)
