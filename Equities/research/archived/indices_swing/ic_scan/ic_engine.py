"""
IC engine — Spearman IC + HAC Newey-West t-stat + rolling 2y stability.

Gate criteria (from README):
  |IC mean|  > 0.02
  |t_HAC|    > 2.0
  stability  > 0.70   (rolling 2y IC same sign as full-sample IC in ≥70% of windows)
  post-2020 IC same sign as full-sample IC

Methodology:
  IC = Spearman rank correlation of signal[T] vs fwd_ret[T] over the full sample.
  HAC t-stat: OLS regression of z-scored ranks with Newey-West covariance matrix.
    maxlags = max(2, round(1.5 × h)) per sprint spec (HAC lag notation = NW lag).
  Stability: rolling 504-day (2y) Spearman IC; fraction where sign == full-sample sign.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

log = logging.getLogger(__name__)

ROLL_WINDOW     = 504      # 2-year rolling IC window (trading days)
POST2020_START  = "2020-01-01"


def compute_ic(
    signal:    pd.Series,
    target:    pd.Series,
    hac_lag:   int,
    roll_window: int   = ROLL_WINDOW,
) -> dict[str, Any]:
    """
    Compute full IC statistics for a single (signal, target) pair.

    Parameters
    ----------
    signal      : pd.Series of signal values indexed by date
    target      : pd.Series of forward return values indexed by date
    hac_lag     : Newey-West lag for HAC standard errors
    roll_window : trading-day window for rolling IC stability

    Returns
    -------
    dict with keys:
        n_obs, ic_mean, ic_std, t_hac, ic_post2020, ic_pre2020,
        stability, post2020_consistent, verdict
    """
    # Align on shared non-NaN index
    df = pd.DataFrame({"sig": signal, "tgt": target}).dropna()
    if len(df) < 30:
        return _empty_result(n_obs=len(df))

    sig_arr = df["sig"].values
    tgt_arr = df["tgt"].values

    # ── Full-sample Spearman IC ───────────────────────────────────────────────
    ic_full, _ = spearmanr(sig_arr, tgt_arr)

    # ── HAC t-stat via OLS on z-scored ranks ─────────────────────────────────
    t_hac = _hac_tstat(df["sig"], df["tgt"], hac_lag)

    # ── Rolling 2y IC ─────────────────────────────────────────────────────────
    roll_ic = _rolling_spearman(df["sig"], df["tgt"], roll_window)

    # Stability: fraction of windows where sign matches full-sample IC
    valid_roll = roll_ic.dropna()
    if len(valid_roll) > 0 and not np.isnan(ic_full):
        stability = (np.sign(valid_roll) == np.sign(ic_full)).mean()
    else:
        stability = np.nan

    # ── Pre/post-2020 split ───────────────────────────────────────────────────
    post_mask = df.index >= POST2020_START
    pre_mask  = df.index  < POST2020_START

    ic_post = _safe_spearman(df.loc[post_mask, "sig"], df.loc[post_mask, "tgt"])
    ic_pre  = _safe_spearman(df.loc[pre_mask,  "sig"], df.loc[pre_mask,  "tgt"])

    post_consistent = (not np.isnan(ic_post)) and (np.sign(ic_post) == np.sign(ic_full))

    # ── Verdict ───────────────────────────────────────────────────────────────
    verdict = _verdict(ic_full, t_hac, stability, post_consistent)

    return {
        "n_obs":            len(df),
        "ic_mean":          round(ic_full, 4),
        "t_hac":            round(t_hac, 3),
        "ic_post2020":      round(ic_post, 4) if not np.isnan(ic_post) else np.nan,
        "ic_pre2020":       round(ic_pre,  4) if not np.isnan(ic_pre)  else np.nan,
        "stability":        round(stability, 3) if not np.isnan(stability) else np.nan,
        "post2020_consistent": post_consistent,
        "verdict":          verdict,
        "roll_ic":          roll_ic,   # pd.Series for plotting
    }


def _verdict(ic: float, t_hac: float, stability: float, post_consistent: bool) -> str:
    if np.isnan(ic) or np.isnan(t_hac):
        return "INCONCLUSIVE"
    fails = []
    if abs(ic) <= 0.02:       fails.append(f"|IC|={abs(ic):.3f}≤0.02")
    if abs(t_hac) <= 2.0:     fails.append(f"|t_HAC|={abs(t_hac):.2f}≤2.0")
    if not np.isnan(stability) and stability < 0.70:
        fails.append(f"stability={stability:.2f}<0.70")
    if not post_consistent:   fails.append("post2020_sign_flip")
    return "GO" if not fails else "NO-GO"


def _hac_tstat(signal: pd.Series, target: pd.Series, maxlags: int) -> float:
    """
    OLS t-stat for Spearman IC with Newey-West HAC standard errors.

    Method: regress z-scored rank(target) on z-scored rank(signal).
    Slope = Spearman IC when both series are standardized.
    HAC t-stat from statsmodels OLS(cov_type='HAC').
    """
    try:
        import statsmodels.api as sm
        n   = len(signal)
        xr  = pd.Series(_znorm_rank(signal.values), index=signal.index)
        yr  = pd.Series(_znorm_rank(target.values),  index=target.index)
        X   = sm.add_constant(xr)
        res = sm.OLS(yr, X).fit(cov_type='HAC', cov_kwds={'maxlags': maxlags})
        return float(res.tvalues.iloc[1])
    except Exception as exc:
        log.warning("HAC t-stat failed: %s — falling back to iid t-stat", exc)
        # Fallback: iid t-stat from Fisher z
        n    = len(signal)
        r, _ = spearmanr(signal.values, target.values)
        se   = 1.0 / np.sqrt(n - 3) if n > 3 else np.nan
        return np.arctanh(r) / se if se and se > 0 else np.nan


def _rolling_spearman(sig: pd.Series, tgt: pd.Series, window: int) -> pd.Series:
    """Compute rolling Spearman IC over aligned (sig, tgt) series."""
    n   = len(sig)
    res = np.full(n, np.nan)
    xv  = sig.values
    yv  = tgt.values

    for i in range(window - 1, n):
        xi = xv[i - window + 1: i + 1]
        yi = yv[i - window + 1: i + 1]
        mask = ~(np.isnan(xi) | np.isnan(yi))
        if mask.sum() >= window // 2:
            r, _ = spearmanr(xi[mask], yi[mask])
            res[i] = r

    return pd.Series(res, index=sig.index)


def _safe_spearman(x: pd.Series, y: pd.Series) -> float:
    df = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(df) < 20:
        return np.nan
    r, _ = spearmanr(df["x"].values, df["y"].values)
    return float(r)


def _znorm_rank(arr: np.ndarray) -> np.ndarray:
    """Fractional rank normalized to mean-0, std-1."""
    from scipy.stats import rankdata
    r = rankdata(arr).astype(float)
    mu, sig = r.mean(), r.std()
    return (r - mu) / sig if sig > 0 else r - mu


def _empty_result(n_obs: int = 0) -> dict[str, Any]:
    return {
        "n_obs":               n_obs,
        "ic_mean":             np.nan,
        "t_hac":               np.nan,
        "ic_post2020":         np.nan,
        "ic_pre2020":          np.nan,
        "stability":           np.nan,
        "post2020_consistent": False,
        "verdict":             "INCONCLUSIVE",
        "roll_ic":             pd.Series(dtype=float),
    }
