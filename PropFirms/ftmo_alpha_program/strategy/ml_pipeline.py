"""
ml_pipeline.py — Family-6 ML combo: walk-forward & CPCV pipelines
===================================================================

Two pipelines, both strictly IS / hold-out separated (the hold-out is touched
ONCE for the final verdict — see run_family6_ml_combo.py):

  • cpcv_oos_sharpe_distribution()
      For ONE model variant, generate the per-path OOS Sharpe distribution via
      Combinatorial Purged Cross-Validation (skfolio backend, López de Prado
      AFML ch.12). Returns the distribution → used for PBO sanity, mean OOS,
      and the *decisive* GROSS-OOS isolation diagnostic.

  • walk_forward_returns_matrix()
      For K hyperparameter variants, expanding-window walk-forward training on
      IS to produce a (T_oos, K) per-bar returns matrix. Feeds PBO across
      variants. Each variant's column is its honest OOS performance on IS.

Standardisation: features are standardised inside each fit on the train fold
only (sklearn Pipeline with StandardScaler → no leakage).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import sys as _sys
from pathlib import Path as _P
_REPO = _P(__file__).resolve().parents[3]
if str(_REPO) not in _sys.path:
    _sys.path.insert(0, str(_REPO))
from Portfolio.validation.cpcv import run_cpcv  # noqa: E402


# ────────────────────────────────────────────────────────────────────────────────
# Model builders (simple → complex per the sprint protocol)
# ────────────────────────────────────────────────────────────────────────────────

def build_logistic(C: float = 1.0, max_iter: int = 2000) -> Pipeline:
    """Logistic regression with L2 penalty (default; `C` = inverse regularisation
    strength) and a StandardScaler step (essential for L2)."""
    return Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(C=C, max_iter=max_iter,
                                   solver="lbfgs", class_weight=None)),
    ])


def build_lgbm(max_depth: int = 3, num_leaves: int = 7,
               min_child_samples: int = 200, learning_rate: float = 0.05,
               n_estimators: int = 200, reg_lambda: float = 1.0) -> "object":
    """Shallow gradient boosting tree with strong leaf regularisation.

    Loaded lazily so the module doesn't fail at import on systems without lgb.
    """
    from lightgbm import LGBMClassifier
    return LGBMClassifier(
        objective="binary",
        max_depth=max_depth,
        num_leaves=num_leaves,
        min_child_samples=min_child_samples,
        learning_rate=learning_rate,
        n_estimators=n_estimators,
        reg_lambda=reg_lambda,
        verbosity=-1,
        n_jobs=1,
    )


# ────────────────────────────────────────────────────────────────────────────────
# Forecast → position → strategy return
# ────────────────────────────────────────────────────────────────────────────────

def position_from_proba(proba_up: np.ndarray, threshold: float = 0.0) -> np.ndarray:
    """Map P(up) to a continuous position in [-1, +1].

    Default: position = 2*P - 1 (continuous, allows partial sizing).
    With threshold>0: zero out the dead-zone |P-0.5| < threshold for turnover
    control (acts as an entry-band, matches the banded MR pattern in Family-1).
    """
    p = np.asarray(proba_up, dtype=float)
    pos = 2.0 * p - 1.0
    if threshold > 0:
        pos = np.where(np.abs(p - 0.5) < threshold, 0.0, pos)
    return np.clip(pos, -1.0, 1.0)


def strategy_returns(position: np.ndarray, y_fwd: np.ndarray) -> np.ndarray:
    """Per-bar gross strategy return = position(t) * forward_return(t).

    NaNs in y_fwd (session-boundary) propagate to zero contribution.
    """
    y = np.where(np.isfinite(y_fwd), y_fwd, 0.0)
    return position * y


# ────────────────────────────────────────────────────────────────────────────────
# CPCV — distribution of OOS Sharpes for ONE variant
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class CPCVOutcome:
    sharpes: np.ndarray
    mean: float
    std: float
    median: float
    ci_5_95: tuple[float, float]
    n_paths: int
    n_folds: int
    n_test_folds: int
    purge_size: int
    embargo_size: int


def cpcv_oos_sharpe_distribution(
    X: np.ndarray, y: np.ndarray, y_fwd: np.ndarray, index: pd.DatetimeIndex,
    model_factory: Callable[[], object],
    bars_per_year: int,
    n_folds: int | None = None, n_test_folds: int | None = None,
    purge_size: int | None = None, embargo_pct: float = 0.01,
    threshold: float = 0.0, target_n_paths: int = 20,
    target_train_size: int = 2000, verbose: bool = True,
) -> CPCVOutcome:
    """Run CPCV over a single variant; per-path OOS Sharpe (annualised).

    The backtest_fn (closure) fits the model on the train_idx slice and reports
    the GROSS Sharpe on test_idx — this is the **decisive diagnostic** the
    sprint protocol calls out.
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    y_fwd = np.asarray(y_fwd, dtype=float)

    # Build a dummy daily Series for skfolio (the CPCV slicer just needs T).
    rets_series = pd.Series(y_fwd, index=index)

    def _bt(train_idx: np.ndarray, test_idx: np.ndarray) -> float:
        if len(train_idx) < 200 or len(test_idx) < 50:
            return np.nan
        clf = model_factory()
        Xtr, ytr = X[train_idx], y[train_idx]
        if len(np.unique(ytr)) < 2:
            return np.nan
        try:
            clf.fit(Xtr, ytr)
        except Exception:
            return np.nan
        p_up = clf.predict_proba(X[test_idx])[:, 1]
        pos = position_from_proba(p_up, threshold=threshold)
        r = strategy_returns(pos, y_fwd[test_idx])
        if r.std(ddof=1) <= 0:
            return 0.0
        return float(r.mean() / r.std(ddof=1) * np.sqrt(bars_per_year))

    out = run_cpcv(
        rets_series, _bt,
        n_folds=n_folds, n_test_folds=n_test_folds,
        target_n_paths=target_n_paths, target_train_size=target_train_size,
        purge_size=purge_size, embargo_pct=embargo_pct, verbose=verbose,
    )
    return CPCVOutcome(
        sharpes=out["sharpes"],
        mean=out["mean"],
        std=out["std"],
        median=out["median"],
        ci_5_95=out["ci_5_95"],
        n_paths=out["n_paths"],
        n_folds=out["n_folds"],
        n_test_folds=out["n_test_folds"],
        purge_size=out["purge_size"],
        embargo_size=out["embargo_size"],
    )


# ────────────────────────────────────────────────────────────────────────────────
# Walk-forward returns matrix — for PBO over K variants
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class WalkForwardOutcome:
    returns_matrix: np.ndarray    # (T_oos, K)
    variant_names: list[str]
    is_oos_mask: np.ndarray       # bool, True where bar is in the OOS slice
    fold_boundaries: list[int]    # bar indices marking the start of each OOS fold
    sharpes_per_variant: np.ndarray
    n_folds: int


def walk_forward_returns_matrix(
    X: np.ndarray, y: np.ndarray, y_fwd: np.ndarray,
    variants: list[tuple[str, Callable[[], object], float]],
    bars_per_year: int, n_folds: int = 5,
    purge_size: int = 5,
) -> WalkForwardOutcome:
    """Expanding-window walk-forward training across K variants on the SAME
    time slices. Produces a (T_oos, K) per-bar gross-return matrix.

    Each variant = (name, model_factory, threshold).
    """
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=int)
    y_fwd = np.asarray(y_fwd, dtype=float)
    T = len(X)
    fold_size = T // (n_folds + 1)  # first fold = initial training set
    init_train_end = fold_size

    K = len(variants)
    names = [v[0] for v in variants]
    pieces: list[np.ndarray] = []
    boundaries: list[int] = []

    for f in range(n_folds):
        tr_end = init_train_end + f * fold_size
        te_start = tr_end + purge_size
        te_end = min(te_start + fold_size, T)
        if te_end - te_start < 50:
            continue
        Xtr, ytr = X[:tr_end], y[:tr_end]
        if len(np.unique(ytr)) < 2:
            continue
        Xte, yfte = X[te_start:te_end], y_fwd[te_start:te_end]
        col_returns = np.zeros((te_end - te_start, K))
        for k, (_, factory, thresh) in enumerate(variants):
            try:
                clf = factory()
                clf.fit(Xtr, ytr)
                p_up = clf.predict_proba(Xte)[:, 1]
                pos = position_from_proba(p_up, threshold=thresh)
                col_returns[:, k] = strategy_returns(pos, yfte)
            except Exception:
                col_returns[:, k] = 0.0
        boundaries.append(te_start)
        pieces.append(col_returns)

    if not pieces:
        raise RuntimeError("walk_forward produced no folds (check sample size)")

    R = np.vstack(pieces)
    sharpes = np.empty(K, dtype=float)
    for k in range(K):
        col = R[:, k]
        sd = col.std(ddof=1)
        sharpes[k] = (col.mean() / sd * np.sqrt(bars_per_year)) if sd > 0 else 0.0

    mask = np.zeros(T, dtype=bool)
    cursor = 0
    for s in boundaries:
        chunk_len = next(p.shape[0] for p in pieces[len(boundaries) - len(pieces) + boundaries.index(s):])
        mask[s:s + chunk_len] = True
        cursor += chunk_len
    return WalkForwardOutcome(
        returns_matrix=R, variant_names=names,
        is_oos_mask=mask, fold_boundaries=boundaries,
        sharpes_per_variant=sharpes, n_folds=len(pieces),
    )


# ────────────────────────────────────────────────────────────────────────────────
# Full backtest with costs (gross + net daily series) on a slice of bars
# ────────────────────────────────────────────────────────────────────────────────

@dataclass
class BacktestSeries:
    daily_gross: pd.Series
    daily_net: pd.Series
    daily_turnover: pd.Series
    bar_gross: pd.Series
    bar_net: pd.Series
    metrics: dict = field(default_factory=dict)


def backtest_predictions(
    proba_up: pd.Series, y_fwd: pd.Series, close: pd.Series, spread: pd.Series,
    symbol: str, threshold: float = 0.0, markup: float = 3.0,
    sigma_target: float | None = None, vol_lookback: int = 63,
    max_leverage: float = 8.0, bars_per_year: int = 252 * 26,
) -> BacktestSeries:
    """Translate model probabilities into a costed daily-return series.

    Costs: CFD round-trip on turnover, scaled by `markup` (retail L23b);
    spreads come from the realised MT5 `spread` column. Optional daily vol-
    targeting on the gross daily series (lagged 63-day std).
    """
    from engine.cfd_costs import CFDCostModel
    pos = pd.Series(position_from_proba(proba_up.values, threshold), index=proba_up.index)
    # intraday-flat: zero position at last bar of each day (no overnight carry)
    norm = pos.index.normalize()
    last = (pd.Series(norm).shift(-1).values != norm)
    pos[last] = 0.0

    gross_bar = pos.values * np.where(np.isfinite(y_fwd.values), y_fwd.values, 0.0)
    cost_model = CFDCostModel(symbol, markup=markup)
    rt_cost = cost_model.rt_cost_return(spread.values, close.values)
    turnover_bar = np.abs(pos.values - np.concatenate([[0.0], pos.values[:-1]]))
    cost_bar = turnover_bar * 0.5 * rt_cost

    bar_gross = pd.Series(gross_bar, index=pos.index)
    bar_net = pd.Series(gross_bar - cost_bar, index=pos.index)
    turnover_bar_s = pd.Series(turnover_bar, index=pos.index)
    cost_bar_s = pd.Series(cost_bar, index=pos.index)

    g_daily = bar_gross.groupby(bar_gross.index.normalize()).sum()
    n_daily = bar_net.groupby(bar_net.index.normalize()).sum()
    t_daily = turnover_bar_s.groupby(turnover_bar_s.index.normalize()).sum()
    c_daily = cost_bar_s.groupby(cost_bar_s.index.normalize()).sum()

    if sigma_target is not None:
        trail_vol = g_daily.rolling(vol_lookback).std().shift(1)
        scale = (sigma_target / trail_vol).clip(upper=max_leverage).fillna(0.0)
        g_daily = g_daily * scale
        n_daily = (g_daily - c_daily * scale)  # apply same scale to costs
        t_daily = t_daily * scale

    n_daily = n_daily.dropna()
    g_daily = g_daily.reindex(n_daily.index)
    t_daily = t_daily.reindex(n_daily.index)

    import scipy.stats as _ss
    r = n_daily.values
    mu, sd = r.mean(), r.std(ddof=1)
    sharpe_d = (mu / sd) if sd > 0 else 0.0
    metrics = {
        "n_days": int(len(r)),
        "daily_sharpe": float(sharpe_d),
        "ann_sharpe": float(sharpe_d * np.sqrt(252)),
        "ann_return_net": float(mu * 252),
        "ann_return_gross": float(g_daily.mean() * 252),
        "ann_cost_drag": float(c_daily.sum() / max(1, len(r)) * 252),
        "win_rate_daily": float((r > 0).mean()),
        "excess_kurtosis": float(_ss.kurtosis(r, fisher=True, bias=False)),
        "skew": float(_ss.skew(r, bias=False)),
        "max_dd": _max_dd(r),
        "avg_daily_turnover": float(t_daily.mean()),
    }
    return BacktestSeries(
        daily_gross=g_daily, daily_net=n_daily, daily_turnover=t_daily,
        bar_gross=bar_gross, bar_net=bar_net, metrics=metrics,
    )


def _max_dd(r: np.ndarray) -> float:
    eq = np.cumsum(r)
    peak = np.maximum.accumulate(np.concatenate([[0.0], eq]))[1:]
    return float((peak - eq).max())
