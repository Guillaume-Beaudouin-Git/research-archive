"""
IC visualization — rolling IC plots and signal summary heatmap.
All plots saved to results/ic_per_signal/. No plt.show() calls.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_RESULTS_DIR = Path(__file__).parents[1] / "results" / "ic_per_signal"


def plot_rolling_ic(
    roll_ic:    pd.Series,
    label:      str,
    ic_full:    float,
    h:          int,
    out_dir:    Path = _RESULTS_DIR,
) -> Path:
    """
    Plot rolling 2y IC with full-sample IC reference line.

    Parameters
    ----------
    roll_ic  : rolling IC series (504-day window)
    label    : e.g. 's1_vrp_SPY_h5'
    ic_full  : full-sample IC (horizontal reference line)
    h        : horizon in days (for title)
    out_dir  : directory to save the PNG
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates

        out_dir.mkdir(parents=True, exist_ok=True)
        fig, ax = plt.subplots(figsize=(10, 4))

        valid = roll_ic.dropna()
        ax.plot(valid.index, valid.values, color="#2166ac", lw=1.2, label="Rolling 2y IC")
        ax.axhline(ic_full, color="#d6604d", lw=1.5, ls="--",
                   label=f"Full-sample IC = {ic_full:.3f}")
        ax.axhline(0, color="black", lw=0.8, ls="-", alpha=0.3)
        ax.fill_between(valid.index, valid.values, 0,
                        where=valid.values > 0, alpha=0.15, color="#2166ac")
        ax.fill_between(valid.index, valid.values, 0,
                        where=valid.values < 0, alpha=0.15, color="#d6604d")

        ax.set_title(f"Rolling 2y Spearman IC — {label.upper()}  (h={h}d)", fontsize=11)
        ax.set_ylabel("IC")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.legend(loc="upper right", fontsize=9)
        ax.grid(axis="y", alpha=0.3)

        out_path = out_dir / f"{label}.png"
        fig.tight_layout()
        fig.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("Saved plot: %s", out_path)
        return out_path
    except Exception as exc:
        log.warning("plot_rolling_ic failed for %s: %s", label, exc)
        return Path("/dev/null")


def plot_tom_event_study(
    event_df: pd.DataFrame,
    out_dir:  Path = _RESULTS_DIR,
) -> Path:
    """
    Bar chart: mean daily return by TOM offset with t-stat annotations.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        out_dir.mkdir(parents=True, exist_ok=True)
        fig, axes = plt.subplots(1, 2, figsize=(12, 4))

        # Mean return bar chart
        colors = ["#2166ac" if v > 0 else "#d6604d" for v in event_df["mean_ret"]]
        axes[0].bar(event_df["offset"], event_df["mean_ret"] * 100, color=colors, alpha=0.8)
        axes[0].axhline(0, color="black", lw=0.8)
        axes[0].set_xlabel("Day offset from month-end")
        axes[0].set_ylabel("Mean daily return (%)")
        axes[0].set_title("TOM Event Study — Mean Return by Day Offset")
        axes[0].set_xticks(event_df["offset"])

        # T-stat bar chart
        sig_colors = ["#2166ac" if abs(t) > 2 else "gray"
                      for t in event_df["t_stat"].fillna(0)]
        axes[1].bar(event_df["offset"], event_df["t_stat"].fillna(0), color=sig_colors, alpha=0.8)
        axes[1].axhline(2.0,  color="#d6604d", lw=1.2, ls="--", label="|t|=2.0")
        axes[1].axhline(-2.0, color="#d6604d", lw=1.2, ls="--")
        axes[1].axhline(0, color="black", lw=0.8)
        axes[1].set_xlabel("Day offset from month-end")
        axes[1].set_ylabel("t-statistic")
        axes[1].set_title("TOM Event Study — t-statistic by Day Offset")
        axes[1].set_xticks(event_df["offset"])
        axes[1].legend(fontsize=9)

        fig.tight_layout()
        out_path = out_dir / "s3_tom_event_study.png"
        fig.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("Saved TOM event study plot: %s", out_path)
        return out_path
    except Exception as exc:
        log.warning("plot_tom_event_study failed: %s", exc)
        return Path("/dev/null")


def plot_ic_heatmap(
    summary_df: pd.DataFrame,
    out_dir:    Path = _RESULTS_DIR,
) -> Path:
    """
    Heatmap of IC mean values across signals × horizons for each asset.
    """
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        out_dir.mkdir(parents=True, exist_ok=True)
        assets = summary_df["asset"].unique()
        n_assets = len(assets)
        fig, axes = plt.subplots(1, n_assets, figsize=(5 * n_assets, 5), squeeze=False)

        for ax, asset in zip(axes[0], assets):
            sub = summary_df[summary_df["asset"] == asset].copy()
            pivot = sub.pivot(index="signal", columns="h", values="ic_mean")
            im = ax.imshow(pivot.values, aspect="auto", cmap="RdBu_r",
                           vmin=-0.1, vmax=0.1)
            ax.set_xticks(range(len(pivot.columns)))
            ax.set_xticklabels([f"h={c}" for c in pivot.columns])
            ax.set_yticks(range(len(pivot.index)))
            ax.set_yticklabels(pivot.index, fontsize=8)
            ax.set_title(f"IC — {asset}", fontsize=11)

            # Annotate with IC values
            for i in range(len(pivot.index)):
                for j in range(len(pivot.columns)):
                    val = pivot.values[i, j]
                    if not np.isnan(val):
                        ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                                fontsize=7, color="white" if abs(val) > 0.05 else "black")

        fig.colorbar(im, ax=axes[0], shrink=0.8, label="Spearman IC")
        fig.suptitle("IC Heatmap — Sprint 1 Signal Scan", fontsize=12, y=1.02)
        fig.tight_layout()
        out_path = out_dir / "ic_heatmap_all.png"
        fig.savefig(out_path, dpi=120, bbox_inches="tight")
        plt.close(fig)
        log.info("Saved IC heatmap: %s", out_path)
        return out_path
    except Exception as exc:
        log.warning("plot_ic_heatmap failed: %s", exc)
        return Path("/dev/null")
