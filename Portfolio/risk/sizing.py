"""
sizing.py — Portfolio sizing algorithms
=========================================
Two methods:
  1. equal_risk_contribution (ERC) — each strategy contributes equal fraction
     of total portfolio volatility. The theoretically correct approach.
  2. inverse_vol_weighting — simpler proxy, good when correlations are near-zero.

Both return weights (0-1) that sum to 1.0.

Usage:
    from Portfolio.risk.sizing import equal_risk_contribution, inverse_vol_weighting

    # From daily returns (n_days × n_strategies)
    weights_erc = equal_risk_contribution(returns_df, target_vol=0.15)
    weights_iv  = inverse_vol_weighting(returns_df, target_vol=0.15)

Next session will:
  (1) Call these with live A/B returns + C backtest proxy
  (2) Compare ERC vs inverse-vol weights
  (3) Feed weights into PortfolioState.capital_allocation
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ─────────────────────────────────────────────────────────────────────────────
# Inverse-vol weighting (simple baseline)
# ─────────────────────────────────────────────────────────────────────────────

def inverse_vol_weighting(
    returns_df: pd.DataFrame,
    target_vol: float = 0.15,
    window: int = 63,
    max_weight: float = 0.60,
) -> Dict[str, float]:
    """
    Assign capital weights inversely proportional to each strategy's volatility.

    w_i = (1/σ_i) / Σ(1/σ_j)   then scaled so portfolio vol = target_vol.

    Args:
        returns_df: daily returns DataFrame (columns = strategy names).
        target_vol: annualised portfolio volatility target (e.g. 0.15 = 15%).
        window: lookback in trading days for vol estimation.
        max_weight: hard cap per strategy (prevents concentration).

    Returns:
        dict {strategy: weight} summing to 1.0 (before scaling by target_vol).

    Note:
        The weights here are CAPITAL weights (how much of the $50K each gets).
        The actual contract sizing per strategy is handled separately.
    """
    clean = returns_df.dropna(how="all").tail(window)
    strats = list(clean.columns)

    vols = {}
    for s in strats:
        v = float(clean[s].std() * np.sqrt(252))   # annualised
        if v > 1e-12:
            vols[s] = v

    if not vols:
        n = len(strats)
        return {s: 1.0 / n for s in strats}

    inv_vol = {s: 1.0 / v for s, v in vols.items()}
    total   = sum(inv_vol.values())
    weights = {s: inv_vol[s] / total for s in inv_vol}

    # Apply per-strategy cap
    weights = _apply_max_weight(weights, max_weight)

    return weights


# ─────────────────────────────────────────────────────────────────────────────
# Equal Risk Contribution (ERC)
# ─────────────────────────────────────────────────────────────────────────────

def equal_risk_contribution(
    returns_df: pd.DataFrame,
    target_vol: float = 0.15,
    window: int = 63,
    max_weight: float = 0.60,
    tol: float = 1e-8,
    max_iter: int = 500,
) -> Dict[str, float]:
    """
    Compute Equal Risk Contribution (ERC) weights via iterative algorithm.

    ERC requires: w_i × (Σw)_i = 1/N for all i, where (Σw)_i is the
    marginal risk contribution of strategy i.

    Algorithm: Maillard, Roncalli & Teiletche (2010) iterative solver.

    Args:
        returns_df: daily returns DataFrame.
        target_vol: annualised target volatility (used for scaling check).
        window: lookback window for covariance estimation.
        max_weight: hard cap per strategy.
        tol: convergence tolerance.
        max_iter: maximum iterations.

    Returns:
        dict {strategy: weight} summing to 1.0.

    Falls back to inverse_vol_weighting if covariance matrix is singular
    or fewer than 2 strategies.
    """
    clean = returns_df.dropna(how="all").tail(window)
    strats = list(clean.columns)
    n = len(strats)

    if n < 2:
        return {strats[0]: 1.0} if n == 1 else {}

    # Annualised covariance matrix
    cov = clean.cov() * 252
    cov_arr = cov.values

    # Check for near-singular covariance
    try:
        eigvals = np.linalg.eigvalsh(cov_arr)
        if eigvals.min() < 1e-10:
            # Regularise slightly
            cov_arr += np.eye(n) * 1e-8
    except Exception:
        return inverse_vol_weighting(returns_df, target_vol, window, max_weight)

    # Iterative ERC solver
    w = np.ones(n) / n           # start from equal weights
    target_rc = 1.0 / n          # target risk contribution per strategy

    for _ in range(max_iter):
        sigma_p = float(np.sqrt(w @ cov_arr @ w))
        if sigma_p < 1e-12:
            break

        # Marginal risk contributions
        mrc = cov_arr @ w / sigma_p

        # Risk contributions
        rc = w * mrc

        # Update: scale each weight so its RC equals target
        w_new = np.array([
            w[i] * target_rc / rc[i] if rc[i] > 1e-12 else w[i]
            for i in range(n)
        ])
        w_new = w_new / w_new.sum()

        if np.max(np.abs(w_new - w)) < tol:
            w = w_new
            break
        w = w_new

    weights = dict(zip(strats, w.tolist()))
    weights = _apply_max_weight(weights, max_weight)
    return weights


# ─────────────────────────────────────────────────────────────────────────────
# Scaling to target volatility
# ─────────────────────────────────────────────────────────────────────────────

def scale_to_target_vol(
    weights: Dict[str, float],
    returns_df: pd.DataFrame,
    target_vol: float = 0.15,
    window: int = 63,
) -> Dict[str, float]:
    """
    Scale all weights uniformly so portfolio realised vol ≈ target_vol.

    Returns weights scaled by (target_vol / realised_port_vol).
    If realised vol is 0, returns unchanged weights.
    """
    clean = returns_df.dropna(how="all").tail(window)
    strats = [s for s in weights if s in clean.columns]
    if not strats:
        return weights

    port_pnl = sum(clean[s] * weights[s] for s in strats)
    realised = float(port_pnl.std() * np.sqrt(252))

    if realised < 1e-12:
        return weights

    scale = target_vol / realised
    return {s: w * scale for s, w in weights.items()}


# ─────────────────────────────────────────────────────────────────────────────
# Risk contribution diagnostics
# ─────────────────────────────────────────────────────────────────────────────

def risk_contribution_breakdown(
    weights: Dict[str, float],
    returns_df: pd.DataFrame,
    window: int = 63,
) -> pd.DataFrame:
    """
    Show each strategy's marginal and percentage risk contribution.

    Returns:
        DataFrame with columns: weight, vol_ann, marginal_rc, pct_rc
        Useful for verifying ERC is actually balanced.
    """
    clean = returns_df.dropna(how="all").tail(window)
    strats = [s for s in weights if s in clean.columns]
    cov_ann = clean[strats].cov() * 252
    w = np.array([weights[s] for s in strats])

    sigma_p = float(np.sqrt(w @ cov_ann.values @ w))
    if sigma_p < 1e-12:
        return pd.DataFrame()

    mrc = cov_ann.values @ w / sigma_p
    rc  = w * mrc
    pct = rc / rc.sum()

    rows = []
    for i, s in enumerate(strats):
        rows.append({
            "strategy":    s,
            "weight":      weights[s],
            "vol_ann":     float(np.sqrt(cov_ann.loc[s, s])),
            "marginal_rc": float(mrc[i]),
            "pct_rc":      float(pct[i]),
        })

    return pd.DataFrame(rows).set_index("strategy")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _apply_max_weight(weights: Dict[str, float], max_weight: float) -> Dict[str, float]:
    """Apply per-strategy cap, then re-normalise."""
    capped = {s: min(w, max_weight) for s, w in weights.items()}
    total  = sum(capped.values())
    if total < 1e-12:
        return weights
    return {s: w / total for s, w in capped.items()}
