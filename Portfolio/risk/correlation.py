"""
correlation.py — Rolling correlation and divergence alerts
===========================================================
Tools for monitoring pairwise correlations between strategies to detect
when diversification is breaking down (e.g. A+C both going short during a
volatility spike — supposed to be uncorrelated, correlation suddenly +0.7).

Next session: integrate with PortfolioState.historical_returns to generate
daily alerts when any pair exceeds threshold.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


def rolling_correlation_matrix(
    returns_df: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """
    Compute pairwise Pearson correlation using a rolling window.

    Args:
        returns_df: DataFrame of daily returns, columns = strategy names.
        window: rolling window in trading days (default 60 = ~3 months).

    Returns:
        DataFrame with same columns as returns_df, but only the LAST window
        correlation matrix (most recent snapshot).

    Example:
        corr = rolling_correlation_matrix(ps.historical_returns, window=60)
        print(corr.round(3))
    """
    clean = returns_df.dropna(how="all")
    if len(clean) < window // 2:
        # Not enough data — return full-period correlation
        return clean.corr()

    tail = clean.tail(window)
    return tail.corr()


def rolling_correlation_history(
    returns_df: pd.DataFrame,
    pair: Tuple[str, str],
    window: int = 60,
) -> pd.Series:
    """
    Time series of rolling pairwise correlation for a specific pair.

    Args:
        returns_df: daily returns DataFrame.
        pair: tuple of two strategy names, e.g. ("A", "C").
        window: rolling window in days.

    Returns:
        pd.Series indexed by date.

    Useful for plotting correlation drift over time — e.g. were A and C
    always uncorrelated, or did they become correlated post-2025 vol regime shift?
    """
    a, b = pair
    if a not in returns_df.columns or b not in returns_df.columns:
        raise KeyError(f"Strategies {a} or {b} not found in returns_df.")

    series_a = returns_df[a].dropna()
    series_b = returns_df[b].dropna()
    aligned  = pd.concat([series_a, series_b], axis=1).dropna()

    return aligned[a].rolling(window).corr(aligned[b])


def correlation_alert(
    correlation_matrix: pd.DataFrame,
    threshold: float = 0.50,
    ignore_self: bool = True,
) -> List[Dict]:
    """
    Scan a correlation matrix for pairs exceeding the alert threshold.

    Args:
        correlation_matrix: output of rolling_correlation_matrix().
        threshold: absolute correlation threshold (default 0.5).
        ignore_self: skip diagonal entries.

    Returns:
        List of dicts: [{pair: (A, B), correlation: 0.72, severity: "HIGH"}, ...]
        Empty list if no alerts.

    Severity:
        LOW:      0.50 <= |corr| < 0.65
        MEDIUM:   0.65 <= |corr| < 0.80
        HIGH:     |corr| >= 0.80

    Usage:
        alerts = correlation_alert(corr_matrix, threshold=0.5)
        if alerts:
            print("⚠ Diversification alert:")
            for a in alerts:
                print(f"  {a['pair']}: corr={a['correlation']:+.2f} [{a['severity']}]")
    """
    alerts = []
    strats = list(correlation_matrix.columns)

    for i, s1 in enumerate(strats):
        for j, s2 in enumerate(strats):
            if ignore_self and i >= j:
                continue
            corr = correlation_matrix.loc[s1, s2]
            if not np.isfinite(corr):
                continue
            if abs(corr) >= threshold:
                if abs(corr) >= 0.80:
                    severity = "HIGH"
                elif abs(corr) >= 0.65:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"
                alerts.append({
                    "pair":        (s1, s2),
                    "correlation": float(corr),
                    "severity":    severity,
                })

    # Sort by abs correlation descending
    alerts.sort(key=lambda x: abs(x["correlation"]), reverse=True)
    return alerts


def diversification_ratio(
    returns_df: pd.DataFrame,
    weights: Optional[Dict[str, float]] = None,
    window: int = 60,
) -> float:
    """
    Diversification ratio = weighted avg individual vol / portfolio vol.
    DR > 1 means genuine diversification benefit; DR = 1 means no benefit.

    Args:
        returns_df: daily returns DataFrame.
        weights: dict {strategy: weight}. Default: equal weights.
        window: lookback window for vol estimation.

    Returns:
        float (typically 1.0 to 3.0 for well-diversified portfolios)

    TODO next session: track over time to detect regime changes where DR drops.
    """
    clean = returns_df.dropna(how="all").tail(window)
    strats = list(clean.columns)
    if not strats:
        return float("nan")

    if weights is None:
        w = {s: 1.0 / len(strats) for s in strats}
    else:
        w = weights

    # Weighted average of individual vols
    indiv_vols = {s: float(clean[s].std()) for s in strats}
    avg_vol = sum(w.get(s, 0) * indiv_vols[s] for s in strats)

    # Portfolio vol
    port = sum(clean[s] * w.get(s, 0) for s in strats)
    port_vol = float(port.std())

    if port_vol < 1e-12:
        return float("nan")

    return avg_vol / port_vol
