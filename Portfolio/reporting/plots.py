"""
Plot generation for strategy tear sheets.

All public functions return a base64-encoded PNG string suitable for
embedding directly in the HTML tear sheet (data:image/png;base64,...).
"""
from __future__ import annotations

import base64
import io
import math
from typing import Optional

import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Seaborn heatmap colorbar and sharex subplots are incompatible with tight_layout.
# bbox_inches="tight" in savefig already handles the bounding box correctly.
warnings.filterwarnings(
    "ignore",
    message="This figure includes Axes that are not compatible with tight_layout",
    category=UserWarning,
)
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import gaussian_kde, norm as scipy_norm

# ── GitHub dark-mode palette ───────────────────────────────────────────────────
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
    "axes.titlecolor": _TEXT,
    "xtick.color": _TEXT,
    "ytick.color": _TEXT,
    "grid.color": _BORDER,
    "grid.alpha": 0.5,
    "text.color": _TEXT,
    "legend.facecolor": _PANEL,
    "legend.edgecolor": _BORDER,
    "legend.fontsize": 8,
}


def _fig_to_b64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _style_ax(ax: plt.Axes) -> None:
    ax.set_facecolor(_PANEL)
    ax.tick_params(colors=_TEXT, labelsize=8)
    ax.grid(True, color=_BORDER, alpha=0.5, linewidth=0.5)
    for spine in ax.spines.values():
        spine.set_edgecolor(_BORDER)


def equity_curve_plot(equity: pd.Series, dd: pd.Series) -> str:
    """
    Equity curve (top panel) + underwater drawdown (bottom panel).

    Parameters
    ----------
    equity : pd.Series
        Cumulative product of (1 + daily returns), starting near 1.0.
    dd : pd.Series
        Drawdown series (≤ 0).

    Returns
    -------
    str
        Base64-encoded PNG.
    """
    with plt.rc_context(_RC):
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(11, 5.5),
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05},
            sharex=True,
        )
        fig.patch.set_facecolor(_BG)

        # Equity
        _style_ax(ax1)
        dates = equity.index
        vals = equity.values
        ax1.plot(dates, vals, color=_BLUE, linewidth=1.5, label="Strategy", zorder=3)
        ax1.fill_between(dates, 1.0, vals, where=(vals >= 1.0),
                         alpha=0.12, color=_GREEN, zorder=2)
        ax1.fill_between(dates, 1.0, vals, where=(vals < 1.0),
                         alpha=0.12, color=_RED, zorder=2)
        ax1.axhline(1.0, color=_BORDER, linewidth=0.8, linestyle="--", zorder=1)

        final = vals[-1]
        color = _GREEN if final >= 1.0 else _RED
        ax1.annotate(
            f"{final:.2f}×",
            xy=(dates[-1], final),
            xytext=(-6, 6), textcoords="offset points",
            ha="right", fontsize=9, fontweight="bold", color=color,
        )
        ax1.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.2f×"))
        ax1.set_ylabel("Equity", color=_TEXT, fontsize=9)
        ax1.legend(loc="upper left")

        # Drawdown
        _style_ax(ax2)
        dd_vals = dd.values
        ax2.fill_between(dates, dd_vals, 0, color=_RED, alpha=0.55)
        ax2.plot(dates, dd_vals, color=_RED, linewidth=0.8)
        ax2.axhline(0, color=_BORDER, linewidth=0.8)
        ax2.set_ylim(min(dd_vals) * 1.15 if dd_vals.min() < 0 else -0.01, 0.02)
        ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=1))
        ax2.set_ylabel("DD", color=_TEXT, fontsize=9)

        try:
            plt.tight_layout(pad=0.4)
        except Exception:
            pass
        return _fig_to_b64(fig)


def monthly_heatmap_plot(monthly: pd.Series) -> str:
    """
    Monthly returns heatmap — rows = years, columns = Jan..Dec.

    Parameters
    ----------
    monthly : pd.Series
        Month-end return series (values are fractions, not percent).

    Returns
    -------
    str
        Base64-encoded PNG.
    """
    df = monthly.to_frame("ret")
    df.index = pd.to_datetime(df.index)
    df["year"] = df.index.year
    df["month"] = df.index.month
    pivot = df.pivot(index="year", columns="month", values="ret")
    pivot.columns = pd.Index(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        name=None,
    )

    n_years = len(pivot)
    fig_h = max(2.0, n_years * 0.60)

    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(13, fig_h))
        fig.patch.set_facecolor(_BG)
        ax.set_facecolor(_PANEL)

        valid_vals = pivot.values[~np.isnan(pivot.values)]
        vmax = max(abs(valid_vals).max(), 0.005) * 100 if len(valid_vals) > 0 else 5.0

        sns.heatmap(
            pivot * 100,
            ax=ax,
            cmap="RdYlGn",
            center=0,
            vmin=-vmax,
            vmax=vmax,
            annot=True,
            fmt=".1f",
            linewidths=0.6,
            linecolor=_BG,
            annot_kws={"size": 8, "color": _BG},
            cbar_kws={"label": "Return (%)", "shrink": 0.8, "pad": 0.02},
        )
        ax.set_title("Monthly Returns (%)", color=_TEXT, fontsize=11, pad=8)
        ax.set_xlabel("", color=_TEXT)
        ax.set_ylabel("", color=_TEXT)
        ax.tick_params(colors=_TEXT, labelsize=8)

        cbar = ax.collections[0].colorbar
        if cbar is not None:
            cbar.ax.tick_params(colors=_TEXT, labelsize=8)
            cbar.ax.yaxis.label.set_color(_TEXT)

        try:
            plt.tight_layout(pad=0.3)
        except Exception:
            pass
        return _fig_to_b64(fig)


def rolling_sharpe_plot(roll_sr: pd.Series) -> str:
    """
    Rolling 6-month (126-day) Sharpe ratio on excess returns (naive, for plot).

    Parameters
    ----------
    roll_sr : pd.Series
        Pre-computed rolling Sharpe series (NaN for first 125 obs).

    Returns
    -------
    str
        Base64-encoded PNG.
    """
    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(11, 3))
        fig.patch.set_facecolor(_BG)
        _style_ax(ax)

        valid = roll_sr.dropna()
        ax.plot(valid.index, valid.values, color=_ORANGE, linewidth=1.2, label="6M Sharpe")
        ax.axhline(0, color=_BORDER, linewidth=1.0, linestyle="--")
        ax.axhline(1.0, color=_GREEN, linewidth=0.8, linestyle=":", alpha=0.7, label="SR = 1")
        ax.fill_between(valid.index, 0, valid.values,
                        where=(valid.values >= 0), alpha=0.18, color=_GREEN)
        ax.fill_between(valid.index, 0, valid.values,
                        where=(valid.values < 0), alpha=0.18, color=_RED)
        ax.set_ylabel("Sharpe (6M, naive)", color=_TEXT, fontsize=9)
        ax.set_title("Rolling 6-Month Sharpe Ratio", color=_TEXT, fontsize=10)
        ax.legend()
        try:
            plt.tight_layout(pad=0.4)
        except Exception:
            pass
        return _fig_to_b64(fig)


def returns_distribution_plot(returns: pd.Series) -> str:
    """
    Return distribution: histogram + KDE + normal overlay + VaR/CVaR markers.

    Parameters
    ----------
    returns : pd.Series
        Daily total return series (fractions).

    Returns
    -------
    str
        Base64-encoded PNG.
    """
    r = returns.dropna().values * 100  # work in percent for readability

    with plt.rc_context(_RC):
        fig, ax = plt.subplots(figsize=(11, 3.5))
        fig.patch.set_facecolor(_BG)
        _style_ax(ax)

        ax.hist(r, bins=80, color=_BLUE, alpha=0.55, density=True,
                edgecolor=_BG, linewidth=0.2, label="Empirical")

        # KDE
        if len(r) > 5:
            kde = gaussian_kde(r, bw_method=0.35)
            x_grid = np.linspace(r.min() * 1.15, r.max() * 1.15, 400)
            ax.plot(x_grid, kde(x_grid), color=_ORANGE, linewidth=1.6, label="KDE")

        # Normal overlay
        mu_r, sig_r = r.mean(), r.std()
        x_norm = np.linspace(r.min() * 1.15, r.max() * 1.15, 400)
        ax.plot(x_norm, scipy_norm.pdf(x_norm, mu_r, sig_r),
                color=_MUTED, linewidth=1.0, linestyle="--", alpha=0.7, label="Normal fit")

        # VaR 95% and CVaR 95%
        var95 = float(np.percentile(r, 5))
        cvar95 = float(r[r <= var95].mean()) if (r <= var95).any() else var95
        ax.axvline(var95, color=_RED, linewidth=1.6, linestyle="--",
                   label=f"VaR 95%: {var95:.2f}%")
        ax.axvline(cvar95, color="#ff6b6b", linewidth=1.0, linestyle=":",
                   label=f"CVaR 95%: {cvar95:.2f}%")

        ax.set_xlabel("Daily Return (%)", color=_TEXT, fontsize=9)
        ax.set_ylabel("Density", color=_TEXT, fontsize=9)
        ax.set_title("Return Distribution", color=_TEXT, fontsize=10)
        ax.legend(fontsize=7, ncol=3)
        try:
            plt.tight_layout(pad=0.4)
        except Exception:
            pass
        return _fig_to_b64(fig)


def excess_equity_plot(equity: pd.Series, bm_equity: pd.Series) -> str:
    """
    Strategy vs benchmark normalised equity + excess curve.

    Parameters
    ----------
    equity : pd.Series
        Strategy cumulative equity.
    bm_equity : pd.Series
        Benchmark cumulative equity, already normalised to same start.

    Returns
    -------
    str
        Base64-encoded PNG.
    """
    with plt.rc_context(_RC):
        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(11, 5),
            gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08},
            sharex=True,
        )
        fig.patch.set_facecolor(_BG)

        # Normalised equity comparison
        _style_ax(ax1)
        eq_n = equity / equity.iloc[0]
        bm_n = bm_equity.reindex(equity.index).ffill()
        bm_n = bm_n / bm_n.iloc[0]

        ax1.plot(eq_n.index, eq_n.values, color=_BLUE, linewidth=1.5, label="Strategy")
        ax1.plot(bm_n.index, bm_n.values, color=_ORANGE, linewidth=1.0,
                 alpha=0.75, label="Benchmark")
        ax1.set_ylabel("Equity (normalised)", color=_TEXT, fontsize=9)
        ax1.legend()

        # Excess equity (strategy / benchmark)
        _style_ax(ax2)
        with np.errstate(divide="ignore", invalid="ignore"):
            excess = np.where(bm_n.values != 0, eq_n.values / bm_n.values, np.nan)
        excess_series = pd.Series(excess, index=eq_n.index)
        ax2.plot(excess_series.index, excess_series.values, color=_GREEN, linewidth=1.2)
        ax2.axhline(1.0, color=_BORDER, linewidth=0.8, linestyle="--")
        ax2.fill_between(excess_series.index, 1.0, excess_series.values,
                         where=(excess_series.values >= 1.0), alpha=0.2, color=_GREEN)
        ax2.fill_between(excess_series.index, 1.0, excess_series.values,
                         where=(excess_series.values < 1.0), alpha=0.2, color=_RED)
        ax2.set_ylabel("Excess vs BM", color=_TEXT, fontsize=9)

        try:
            plt.tight_layout(pad=0.4)
        except Exception:
            pass
        return _fig_to_b64(fig)
