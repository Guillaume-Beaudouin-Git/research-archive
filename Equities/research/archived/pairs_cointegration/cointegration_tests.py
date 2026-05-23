"""
Cointegration screening functions for pairs trading.

Tests applied to each pair (all 4 must pass):
  1. Engle-Granger: ADF on OLS residuals, p < 0.05
  2. Johansen: trace statistic > 95% critical value
  3. Half-life of mean reversion: 1 ≤ HL ≤ 30 trading days
  4. Hurst exponent on spread: H < 0.5 (mean-reverting)
"""
from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint
from statsmodels.tsa.vector_ar.vecm import coint_johansen


def engle_granger_test(
    y: pd.Series,
    x: pd.Series,
    significance: float = 0.05,
) -> dict:
    """ADF test on OLS residuals of log(Y) ~ α + β·log(X)."""
    log_y = np.log(y)
    log_x = np.log(x)
    aligned = pd.concat([log_y, log_x], axis=1).dropna()
    if len(aligned) < 60:
        return {"pass": False, "pvalue": np.nan, "reason": "insufficient data"}
    score, pvalue, _ = coint(aligned.iloc[:, 0], aligned.iloc[:, 1])
    return {
        "pass":      bool(pvalue < significance),
        "pvalue":    float(pvalue),
        "test_stat": float(score),
    }


def johansen_test(y: pd.Series, x: pd.Series) -> dict:
    """
    Johansen trace test. H0: rank=0 (no cointegration).
    Pass: trace statistic > 95% critical value.
    """
    log_y = np.log(y)
    log_x = np.log(x)
    aligned = pd.concat([log_y, log_x], axis=1).dropna()
    if len(aligned) < 60:
        return {"pass": False, "trace_stat": np.nan, "crit95": np.nan}
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = coint_johansen(aligned.values, det_order=0, k_ar_diff=1)
    trace_stat = float(result.lr1[0])
    crit95     = float(result.cvt[0, 1])
    return {
        "pass":       bool(trace_stat > crit95),
        "trace_stat": trace_stat,
        "crit95":     crit95,
    }


def compute_half_life(spread: pd.Series) -> float:
    """
    Half-life of mean reversion via OLS:
      Δspread[t] = α + θ·spread[t-1] + ε
      HL = -log(2) / θ
    Returns inf if spread is not mean-reverting (θ ≥ 0).
    """
    spread = spread.dropna()
    if len(spread) < 30:
        return np.inf
    lag  = spread.shift(1)
    diff = spread.diff()
    data = pd.concat([diff, lag], axis=1).dropna()
    data.columns = ["diff", "lag"]
    model = sm.OLS(data["diff"], sm.add_constant(data["lag"])).fit()
    theta = float(model.params["lag"])
    if theta >= 0:
        return np.inf
    return float(-np.log(2) / theta)


def hurst_exponent(series: pd.Series, max_lag: int = 100) -> float:
    """
    Hurst exponent via variance ratio method.
      H < 0.5 → mean-reverting
      H = 0.5 → random walk
      H > 0.5 → trending
    """
    vals    = series.dropna().values
    n       = len(vals)
    max_lag = min(max_lag, n // 4)
    if max_lag < 4:
        return 0.5
    lags    = np.arange(2, max_lag + 1)
    tau     = np.array([np.std(vals[lag:] - vals[:-lag]) for lag in lags])
    mask    = tau > 0
    if mask.sum() < 2:
        return 0.5
    poly = np.polyfit(np.log(lags[mask]), np.log(tau[mask]), 1)
    return float(poly[0])


def screen_pair(
    y:             pd.Series,
    x:             pd.Series,
    min_half_life: float = 1.0,
    max_half_life: float = 30.0,
) -> dict:
    """
    Run all 4 cointegration tests. Returns dict with per-test results
    and overall 'pass' flag. Pair advances to backtesting only if all 4 pass.
    """
    aligned = pd.concat([y, x], axis=1).dropna()
    if len(aligned) < 252:
        return {
            "pass":   False,
            "reason": f"insufficient aligned data ({len(aligned)} days)",
        }
    y_al = aligned.iloc[:, 0]
    x_al = aligned.iloc[:, 1]

    # Full-sample OLS for spread (for HL + Hurst)
    log_y = np.log(y_al)
    log_x = np.log(x_al)
    ols   = sm.OLS(log_y.values, sm.add_constant(log_x.values)).fit()
    beta  = float(ols.params[1])
    spread = pd.Series(log_y.values - beta * log_x.values, index=y_al.index)

    eg = engle_granger_test(y_al, x_al)
    jo = johansen_test(y_al, x_al)
    hl = compute_half_life(spread)
    hu = hurst_exponent(spread)

    hl_pass  = (min_half_life <= hl <= max_half_life)
    hu_pass  = (hu < 0.5)
    all_pass = eg["pass"] and jo["pass"] and hl_pass and hu_pass

    reasons = []
    if not eg["pass"]:
        reasons.append(f"EG p={eg['pvalue']:.3f}")
    if not jo["pass"]:
        reasons.append(f"Johansen {jo.get('trace_stat', 'N/A'):.2f}<{jo.get('crit95', 'N/A'):.2f}")
    if not hl_pass:
        reasons.append(f"HL={hl:.1f}d (need 1-30)")
    if not hu_pass:
        reasons.append(f"Hurst={hu:.3f} (need <0.5)")

    return {
        "pass":              all_pass,
        "reason":            ", ".join(reasons) if reasons else "PASS",
        "eg_pvalue":         eg.get("pvalue"),
        "johansen_trace":    jo.get("trace_stat"),
        "johansen_crit95":   jo.get("crit95"),
        "half_life":         hl,
        "hurst":             hu,
        "beta_ols":          beta,
        "n_obs":             len(aligned),
    }
