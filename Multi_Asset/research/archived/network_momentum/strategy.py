"""
strategy.py — Signal construction for Network Momentum (Strategy E)
====================================================================
Implements 4 variants from Pu et al. (2023):

  E1 — GMOM baseline:     graph-aggregated features + OLS, single lookback
  E2 — GMOM ensemble:     5-lookback averaged graph + OLS
  E3 — LinReg (control):  raw individual features + OLS (no graph)
  E4 — RegCombo:          16 features (8 individual + 8 graph-aggregated) + OLS

Signal pipeline per rebalance date:
  1. Aggregate features through graph: F_tilde = A_norm @ F
  2. OLS cross-sectional: fit beta on (F_tilde, next_return) pairs from past 252 days
  3. Predict: y = F_tilde @ beta
  4. Position: x = sign(y) × (sigma_target / sigma_i)   [vol-scaled long/short]
  5. Equal-weight portfolio

Usage:
    from Multi_Asset.research.active.network_momentum.strategy import run_strategy
    returns_E, positions = run_strategy(variant="E4", returns=ret, F=features,
                                        meta=meta, rebal_freq="ME")
"""
from __future__ import annotations

import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd
from numpy.linalg import lstsq

log = logging.getLogger(__name__)

SIGMA_TARGET     = 0.10      # 10% annual vol target
VOL_HALFLIFE     = 60        # EWMA vol halflife for position sizing
OLS_WINDOW       = 252       # days of history for OLS regression
GRAPH_ALPHA      = 0.1
GRAPH_BETA       = 0.1
GRAPH_LOOKBACK   = 504       # single lookback for E1 (504 days ≈ 2 years)


# ─────────────────────────────────────────────────────────────────────────────
# Helper: row-normalize adjacency matrix
# ─────────────────────────────────────────────────────────────────────────────

def _row_normalize(A: np.ndarray) -> np.ndarray:
    """Row-normalize A: A_norm[i,:] = A[i,:] / sum(A[i,:]). Handles zero-degree nodes."""
    row_sums = A.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    return A / row_sums


# ─────────────────────────────────────────────────────────────────────────────
# Helper: cross-sectional OLS with ridge regularisation
# ─────────────────────────────────────────────────────────────────────────────

def _ols_predict(
    X_train: np.ndarray,    # (T_win × N, K) stacked cross-sectional obs
    y_train: np.ndarray,    # (T_win × N,) stacked returns
    X_test:  np.ndarray,    # (N, K) current features
    ridge:   float = 1e-4,
) -> np.ndarray:
    """
    Fit cross-sectional OLS on (X_train, y_train) and predict on X_test.
    Returns predicted returns (N,).
    Adds intercept column; uses ridge to handle near-singular cases.
    """
    # Add intercept
    ones_train = np.ones((X_train.shape[0], 1))
    ones_test  = np.ones((X_test.shape[0], 1))
    Xa = np.hstack([ones_train, X_train])  # (T*N, K+1)
    Xb = np.hstack([ones_test,  X_test])   # (N, K+1)

    # Ridge OLS: beta = (X'X + ridge*I)^-1 X'y
    XtX  = Xa.T @ Xa
    XtX += ridge * np.eye(XtX.shape[0])
    Xty  = Xa.T @ y_train

    try:
        beta = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        beta, _, _, _ = lstsq(Xa, y_train, rcond=None)
        beta = np.append(np.zeros(1), beta[1:]) if beta.shape[0] < Xb.shape[1] else beta

    return Xb @ beta


# ─────────────────────────────────────────────────────────────────────────────
# Signal generation — single rebalance date
# ─────────────────────────────────────────────────────────────────────────────

def _generate_signal(
    F_hist:   np.ndarray,   # (T_avail, N, 8) — history available at rebalance date
    ret_hist: np.ndarray,   # (T_avail, N)    — corresponding returns
    A:        Optional[np.ndarray],  # (N, N) or None for LinReg
    ols_window: int = OLS_WINDOW,
    include_individual: bool = False,
) -> np.ndarray:
    """
    Generate raw signal (predicted returns) for N assets.

    Parameters
    ----------
    F_hist    : features history, most recent = F_hist[-1]
    ret_hist  : returns history, target = ret_hist[t+1] for training
    A         : adjacency matrix (None → no graph aggregation)
    include_individual : if True, concat individual + aggregated features (E4 RegCombo)

    Returns
    -------
    y_hat : (N,) predicted next-period returns
    """
    T_avail = F_hist.shape[0]
    N, K    = F_hist.shape[1], F_hist.shape[2]

    if T_avail < ols_window + 2:
        return np.zeros(N)

    # Build OLS training data: rolling window of (features_t, return_t+1) pairs
    # Use the ols_window days ending 1 day before current (no lookahead)
    t_start = max(0, T_avail - ols_window - 1)
    t_end   = T_avail - 1          # last complete day (not current)

    X_list = []
    y_list = []

    if A is not None:
        A_norm = _row_normalize(A)

    for t_idx in range(t_start, t_end):
        F_t     = F_hist[t_idx]                  # (N, 8)
        ret_t1  = ret_hist[t_idx + 1]            # (N,) next-day return (target)

        # Skip if any NaN in return target
        if np.isnan(ret_t1).any():
            # Replace NaN targets with 0 (asset not trading that day)
            ret_t1 = np.nan_to_num(ret_t1, nan=0.0)

        # Feature aggregation
        if A is not None:
            F_tilde = A_norm @ F_t               # (N, 8) graph-aggregated
        else:
            F_tilde = F_t

        # Replace NaN features with 0
        F_tilde = np.nan_to_num(F_tilde, nan=0.0)

        if include_individual and A is not None:
            F_comb = np.hstack([
                np.nan_to_num(F_t, nan=0.0),
                F_tilde
            ])                                    # (N, 16)
        else:
            F_comb = F_tilde                      # (N, 8)

        X_list.append(F_comb)
        y_list.append(ret_t1)

    if not X_list:
        return np.zeros(N)

    X_train = np.vstack(X_list)   # (T_win * N, K)
    y_train = np.concatenate(y_list)  # (T_win * N,)

    # Current features (last available)
    F_cur   = F_hist[-1]
    if A is not None:
        F_tilde_cur = A_norm @ np.nan_to_num(F_cur, nan=0.0)
    else:
        F_tilde_cur = np.nan_to_num(F_cur, nan=0.0)

    if include_individual and A is not None:
        F_test = np.hstack([np.nan_to_num(F_cur, nan=0.0), F_tilde_cur])  # (N, 16)
    else:
        F_test = F_tilde_cur  # (N, 8)

    # OLS prediction
    y_hat = _ols_predict(X_train, y_train, F_test)
    return y_hat


# ─────────────────────────────────────────────────────────────────────────────
# Vol-scaled position sizing
# ─────────────────────────────────────────────────────────────────────────────

def _vol_scale_positions(
    signal:   np.ndarray,   # (N,) predicted returns (sign used)
    vol_t:    np.ndarray,   # (N,) current EWMA annualized vol
    sigma_target: float = SIGMA_TARGET,
) -> np.ndarray:
    """
    position_i = sign(y_i) × (sigma_target / sigma_i)
    Clamp to [-2, +2] to avoid extreme leverage.
    """
    directions = np.sign(signal)
    # Replace zero signal with no position
    directions[directions == 0] = 0.0

    vol_t_safe = np.where(vol_t > 1e-6, vol_t, 1.0)
    pos = directions * (sigma_target / vol_t_safe)
    pos = np.clip(pos, -2.0, 2.0)
    return pos


# ─────────────────────────────────────────────────────────────────────────────
# Main strategy runner
# ─────────────────────────────────────────────────────────────────────────────

def run_strategy(
    variant:    str,
    returns:    pd.DataFrame,    # (T, N) daily log excess returns
    F:          np.ndarray,      # (T, N, 8) feature tensor
    prices:     pd.DataFrame,    # (T, N) for graph learning (passed through)
    rebal_freq: str = "ME",      # "ME" monthly, "QE" quarterly
    alpha:      float = GRAPH_ALPHA,
    beta:       float = GRAPH_BETA,
    ols_window: int   = OLS_WINDOW,
    min_graph_history: int = 504,
) -> Tuple[pd.Series, pd.DataFrame]:
    """
    Run one strategy variant end-to-end.

    Parameters
    ----------
    variant     : "E1", "E2", "E3", "E4"
    returns     : (T, N) daily log excess returns
    F           : (T, N, 8) feature tensor (aligned to returns)
    prices      : (T, N) for reference (not used directly here)
    rebal_freq  : pandas offset alias for rebalance dates

    Returns
    -------
    strat_returns : pd.Series — daily portfolio log returns
    positions_df  : pd.DataFrame — daily positions (T, N)
    """
    from Multi_Asset.research.active.network_momentum.graph_learning import (
        learn_graph, learn_graph_ensemble
    )

    T, N = returns.shape
    idx  = returns.index
    cols = returns.columns

    # EWMA vol for position sizing
    ewm_vol = (
        returns.ewm(halflife=VOL_HALFLIFE, min_periods=VOL_HALFLIFE // 2)
               .std()
        * np.sqrt(252)
    ).values  # (T, N)

    # Generate rebalance dates
    rebal_dates = (
        returns.resample(rebal_freq).last().index
    )

    positions = pd.DataFrame(
        np.zeros((T, N)), index=idx, columns=cols
    )

    last_A = None  # carry graph forward between rebalance dates

    for rb_date in rebal_dates:
        # Find index position of rebalance date
        t_loc = returns.index.get_indexer([rb_date], method="ffill")[0]
        if t_loc < 0 or t_loc >= T:
            continue

        # History available at this rebalance date (strict past)
        F_hist   = F[:t_loc]          # (t_loc, N, 8)
        ret_hist = returns.values[:t_loc]  # (t_loc, N)

        if F_hist.shape[0] < OLS_WINDOW + 10:
            continue   # insufficient history

        # ── Graph learning ────────────────────────────────────────────────────
        A = None
        if variant in ("E1", "E2", "E4"):
            if F_hist.shape[0] < min_graph_history:
                # Not enough history for graph — carry forward
                A = last_A
            elif variant == "E1":
                lb = min(GRAPH_LOOKBACK, F_hist.shape[0])
                A = learn_graph(F_hist[-lb:], alpha=alpha, beta=beta)
            elif variant in ("E2", "E4"):
                A = learn_graph_ensemble(F_hist, alpha=alpha, beta=beta)

            if A is None:
                A = last_A  # fall back to last known graph
            else:
                last_A = A

        # ── Signal ────────────────────────────────────────────────────────────
        include_individual = (variant == "E4")
        y_hat = _generate_signal(
            F_hist, ret_hist, A,
            ols_window=ols_window,
            include_individual=include_individual,
        )

        # ── Position sizing ───────────────────────────────────────────────────
        vol_t = ewm_vol[t_loc]
        pos   = _vol_scale_positions(y_hat, vol_t)

        # Handle NaN in assets (not yet trading at this date)
        valid = ~np.isnan(returns.values[t_loc])
        pos   = np.where(valid, pos, 0.0)

        # Determine next rebalance date to hold positions
        rb_idx_in_list = list(rebal_dates).index(rb_date)
        if rb_idx_in_list + 1 < len(rebal_dates):
            next_rb = rebal_dates[rb_idx_in_list + 1]
        else:
            next_rb = idx[-1]

        # Assign positions from t_loc+1 to next_rb (inclusive)
        mask = (idx > rb_date) & (idx <= next_rb)
        positions.loc[mask] = pos

        log.debug(
            f"  {rb_date.date()}: signal={np.sign(y_hat).sum():.0f} net, "
            f"pos_mean={np.abs(pos[valid]).mean():.2f}, "
            f"graph={'yes' if A is not None else 'no'}"
        )

    # ── Portfolio returns ──────────────────────────────────────────────────────
    # Equal-weight: divide by N_valid (number of assets with non-zero position)
    pos_vals = positions.values
    ret_vals = returns.values

    # Daily portfolio return = mean of (position_i × return_i) across active assets
    # Shift positions by 1 day to ensure signal is applied the next day
    pos_shifted = np.roll(pos_vals, 1, axis=0)
    pos_shifted[0] = 0.0

    portfolio_ret = np.nansum(pos_shifted * ret_vals, axis=1)
    # Normalize by number of active assets to get equal-weight average
    n_active = np.sum(pos_shifted != 0, axis=1)
    n_active = np.where(n_active > 0, n_active, 1)
    portfolio_ret = portfolio_ret / n_active

    strat_returns = pd.Series(portfolio_ret, index=idx, name=variant)

    # Trim to first signal date
    first_signal = positions.ne(0).any(axis=1).idxmax()
    strat_returns = strat_returns.loc[first_signal:]
    positions     = positions.loc[first_signal:]

    return strat_returns, positions


if __name__ == "__main__":
    import logging, sys, os
    from pathlib import Path
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

    repo = Path(__file__).parent.parent.parent.parent.parent
    sys.path.insert(0, str(repo))
    os.chdir(repo)

    from Multi_Asset.research.active.network_momentum.universe import load_universe
    from Multi_Asset.research.active.network_momentum.features import build_features

    log.info("Loading universe...")
    ret, meta = load_universe()
    log.info("Building features...")
    F, feat_names = build_features(ret, prices=meta["prices"].reindex(ret.index).ffill())

    log.info("Running E3 LinReg (fastest, no graph)...")
    strat_ret, pos = run_strategy("E3", ret, F, meta["prices"], rebal_freq="ME")
    ann = strat_ret.mean() * 252
    vol = strat_ret.std() * np.sqrt(252)
    sr  = ann / vol if vol > 0 else 0
    print(f"\nE3 LinReg: Sharpe={sr:.2f}, Ann={ann:.2%}, Vol={vol:.2%}")
    print(f"  Dates: {strat_ret.index[0].date()} → {strat_ret.index[-1].date()}")
