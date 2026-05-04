"""
4-stage pairs trading funnel (Stoikov et al. 2025, adapted).

All computations run on TRAIN data only. No test data is ever seen here.

Stage 1 — Universe filter:   missing hours, liquidity floor
Stage 2 — Correlation filter: corr(log_price), corr(returns)
Stage 3 — Cointegration:     rolling ADF + hedge ratio stability
Stage 4 — IC test:           Z-score predictive power at multiple horizons
"""
from __future__ import annotations

import warnings
from itertools import combinations
from typing import NamedTuple

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.regression.linear_model import OLS
from statsmodels.tools import add_constant
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Stage 1 — Universe filter
# ---------------------------------------------------------------------------

MISSING_HOUR_THRESHOLD = 0.05    # drop if > 5% of hours missing
MIN_MEDIAN_24H_VOL_USD = 10e6    # $10M


def filter_universe(
    close: pd.DataFrame,
    vol_usd: pd.DataFrame,
) -> list[str]:
    """
    Returns list of symbols that pass:
      - ≤ 5% missing hourly bars
      - median 24-hour USD volume ≥ $10M
    """
    all_symbols = close.columns.tolist()
    expected_bars = len(close)
    surviving = []

    for sym in all_symbols:
        prices = close[sym].dropna()
        n_valid = len(prices)
        missing_frac = 1.0 - n_valid / expected_bars

        if missing_frac > MISSING_HOUR_THRESHOLD:
            print(f"  DROP {sym}: {missing_frac:.1%} missing hours")
            continue

        if sym in vol_usd.columns:
            # Aggregate hourly volume to 24-hour, take median
            vol_series = vol_usd[sym].resample("24h").sum()
            med_vol = vol_series.median()
        else:
            med_vol = 0.0

        if med_vol < MIN_MEDIAN_24H_VOL_USD:
            print(f"  DROP {sym}: median 24h vol ${med_vol/1e6:.1f}M < $10M")
            continue

        surviving.append(sym)

    print(f"\nStage 1: {len(all_symbols)} → {len(surviving)} symbols")
    return surviving


# ---------------------------------------------------------------------------
# Stage 2 — Correlation filter
# ---------------------------------------------------------------------------

CORR_LOGPRICE_MIN = 0.85
CORR_RETURNS_MIN  = 0.40


def _log_price_corr(close: pd.DataFrame, a: str, b: str) -> float:
    log_pa = np.log(close[a].dropna())
    log_pb = np.log(close[b].dropna())
    aligned = pd.concat([log_pa, log_pb], axis=1).dropna()
    if len(aligned) < 100:
        return 0.0
    return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))


def _returns_corr(close: pd.DataFrame, a: str, b: str) -> float:
    ret_a = close[a].pct_change().dropna()
    ret_b = close[b].pct_change().dropna()
    aligned = pd.concat([ret_a, ret_b], axis=1).dropna()
    if len(aligned) < 100:
        return 0.0
    return float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]))


def filter_by_correlation(
    close: pd.DataFrame,
    symbols: list[str],
) -> list[tuple[str, str, float, float]]:
    """
    Returns list of (asset_A, asset_B, corr_logP, corr_ret) for pairs that pass both thresholds.
    """
    passing = []
    for a, b in combinations(symbols, 2):
        c_logp = _log_price_corr(close, a, b)
        c_ret  = _returns_corr(close, a, b)
        if c_logp > CORR_LOGPRICE_MIN and c_ret > CORR_RETURNS_MIN:
            passing.append((a, b, c_logp, c_ret))

    n_total = len(list(combinations(symbols, 2)))
    print(f"\nStage 2: {n_total} pairs → {len(passing)} pairs pass correlation filter")
    return passing


# ---------------------------------------------------------------------------
# Stage 3 — Cointegration filter (rolling ADF + hedge ratio stability)
# ---------------------------------------------------------------------------

ADF_WINDOW_HOURS   = 90 * 24    # 90-day rolling window
ADF_MIN_PASS_RATE  = 0.60       # ≥ 60% of windows must have p-value < 0.05
BETA_STABILITY_MAX = 0.50       # std(β) / |mean(β)| < 0.5


class CointegrationResult(NamedTuple):
    asset_a: str
    asset_b: str
    corr_logp: float
    corr_ret: float
    adf_pass_rate: float
    beta_mean: float
    beta_std: float
    n_windows: int
    passes: bool


def _rolling_ols_beta(log_pa: pd.Series, log_pb: pd.Series, window: int) -> pd.Series:
    """Rolling OLS beta from log_pa = alpha + beta * log_pb."""
    betas = pd.Series(index=log_pa.index, dtype=float)
    for end in range(window, len(log_pa) + 1):
        chunk_a = log_pa.iloc[end - window: end]
        chunk_b = log_pb.iloc[end - window: end]
        aligned = pd.concat([chunk_a, chunk_b], axis=1).dropna()
        if len(aligned) < window * 0.8:
            continue
        y = aligned.iloc[:, 0].values
        x = add_constant(aligned.iloc[:, 1].values)
        try:
            model = OLS(y, x).fit()
            betas.iloc[end - 1] = model.params[1]
        except Exception:
            pass
    return betas


def _rolling_adf_residuals(
    log_pa: pd.Series, log_pb: pd.Series, window: int
) -> tuple[float, pd.Series]:
    """
    Slide a window across the series, compute OLS residuals, run ADF.
    Returns (pass_rate, betas_series).
    """
    step = window // 4   # 25% step → overlapping windows
    n = len(log_pa)
    adf_pvals = []
    betas = []

    starts = range(0, n - window, step)
    for s in starts:
        chunk_a = log_pa.iloc[s: s + window]
        chunk_b = log_pb.iloc[s: s + window]
        aligned = pd.concat([chunk_a, chunk_b], axis=1).dropna()
        if len(aligned) < int(window * 0.8):
            continue
        y = aligned.iloc[:, 0].values
        x = add_constant(aligned.iloc[:, 1].values)
        try:
            model = OLS(y, x).fit()
            resid = model.resid
            beta  = model.params[1]
            # ADF on residuals (no constant, since residuals are already mean-zero-ish)
            adf_stat, adf_p, *_ = adfuller(resid, maxlag=5, autolag=None)
            adf_pvals.append(adf_p)
            betas.append(beta)
        except Exception:
            pass

    if not adf_pvals:
        return 0.0, pd.Series([], dtype=float)

    pass_rate = float(np.mean(np.array(adf_pvals) < 0.05))
    return pass_rate, pd.Series(betas)


def filter_by_cointegration(
    close: pd.DataFrame,
    corr_pairs: list[tuple[str, str, float, float]],
) -> list[CointegrationResult]:
    """
    For each correlation-passing pair, run rolling ADF and beta stability check.
    Returns list of CointegrationResult for pairs that pass both criteria.
    """
    results = []
    for a, b, c_logp, c_ret in corr_pairs:
        log_pa = np.log(close[a]).dropna()
        log_pb = np.log(close[b]).dropna()
        aligned = pd.concat([log_pa, log_pb], axis=1).dropna()
        aligned.columns = ["pa", "pb"]

        pass_rate, betas = _rolling_adf_residuals(
            aligned["pa"], aligned["pb"], window=ADF_WINDOW_HOURS
        )

        if betas.empty:
            beta_mean = np.nan
            beta_std  = np.nan
            stable    = False
        else:
            beta_mean = float(betas.mean())
            beta_std  = float(betas.std())
            beta_cv   = beta_std / max(abs(beta_mean), 1e-9)
            stable    = beta_cv < BETA_STABILITY_MAX

        passes = (pass_rate >= ADF_MIN_PASS_RATE) and stable

        r = CointegrationResult(
            asset_a=a, asset_b=b,
            corr_logp=c_logp, corr_ret=c_ret,
            adf_pass_rate=pass_rate,
            beta_mean=beta_mean, beta_std=beta_std,
            n_windows=len(betas),
            passes=passes,
        )
        results.append(r)

        status = "PASS" if passes else "FAIL"
        print(f"  {a}/{b}: ADF pass rate={pass_rate:.0%}  β={beta_mean:.3f}±{beta_std:.3f}  [{status}]")

    surviving = [r for r in results if r.passes]
    print(f"\nStage 3: {len(corr_pairs)} → {len(surviving)} pairs pass cointegration filter")
    return results   # return ALL results (failing ones stored too for the CSV)


# ---------------------------------------------------------------------------
# Stage 4 — IC test (Z-score predictive power)
# ---------------------------------------------------------------------------

ZSCORE_WINDOW_HOURS = 30 * 24    # 30-day rolling mean/std for Z-score
IC_THRESHOLD        = -0.05
HORIZONS            = [4, 12, 24, 72]   # hours


def _compute_zscore(residuals: pd.Series, window: int) -> pd.Series:
    """Z-score of residual using rolling mean and std."""
    mu    = residuals.rolling(window).mean()
    sigma = residuals.rolling(window).std()
    z = (residuals - mu) / sigma.replace(0, np.nan)
    return z


def _compute_residuals(close: pd.DataFrame, a: str, b: str, beta_mean: float) -> pd.Series:
    """
    Residual u_t = log(P_A) - beta * log(P_B).
    Alpha absorbed into rolling mean of Z-score computation.
    """
    log_pa = np.log(close[a])
    log_pb = np.log(close[b])
    aligned = pd.concat([log_pa, log_pb], axis=1).dropna()
    aligned.columns = ["pa", "pb"]

    # Use full-sample beta for residual (consistent with mean-reversion intuition)
    y = aligned["pa"].values
    x = add_constant(aligned["pb"].values)
    try:
        model = OLS(y, x).fit()
        alpha = model.params[0]
        beta  = model.params[1]
    except Exception:
        beta  = beta_mean
        alpha = 0.0

    residuals = pd.Series(
        aligned["pa"].values - alpha - beta * aligned["pb"].values,
        index=aligned.index,
    )
    return residuals, beta, alpha


def compute_ic_for_pair(
    close: pd.DataFrame,
    a: str,
    b: str,
    beta_mean: float,
) -> dict:
    """
    Compute Information Coefficient (Pearson corr) between Z_t and
    forward spread returns at each horizon.

    Signal is Z[t-1] (shifted by 1 bar), applied at open of bar t.
    This enforces the bar-t-1 signal → bar-t execution rule.
    """
    residuals, beta_fit, alpha_fit = _compute_residuals(close, a, b, beta_mean)
    z = _compute_zscore(residuals, ZSCORE_WINDOW_HOURS)

    # Spread price = log(P_A) - beta * log(P_B)
    spread = residuals   # same as residuals when using full-sample beta

    ic_by_horizon: dict[int, float] = {}
    for h in HORIZONS:
        # Forward return of spread over h bars
        fwd_ret = spread.shift(-h) - spread   # spread[t+h] - spread[t]

        # Signal: Z[t-1] (shifted forward by 1 to avoid look-ahead)
        # i.e., at bar t we know Z up to bar t-1
        signal = z.shift(1)

        df_ic = pd.concat([signal, fwd_ret], axis=1).dropna()
        df_ic.columns = ["z", "fwd_ret"]

        if len(df_ic) < 50:
            ic_by_horizon[h] = np.nan
            continue

        ic = float(df_ic["z"].corr(df_ic["fwd_ret"]))
        ic_by_horizon[h] = ic

    best_h  = min(ic_by_horizon, key=lambda h: ic_by_horizon[h] if not np.isnan(ic_by_horizon[h]) else 0)
    best_ic = ic_by_horizon.get(best_h, np.nan)

    n_obs = len(spread.dropna())

    return {
        "ic_4h":   ic_by_horizon.get(4,  np.nan),
        "ic_12h":  ic_by_horizon.get(12, np.nan),
        "ic_24h":  ic_by_horizon.get(24, np.nan),
        "ic_72h":  ic_by_horizon.get(72, np.nan),
        "best_ic": best_ic,
        "best_horizon": best_h,
        "n_obs": n_obs,
        "beta_fit": beta_fit,
        "alpha_fit": alpha_fit,
        "z_series": z,
        "residuals": residuals,
    }


def filter_by_ic(
    close: pd.DataFrame,
    coint_results: list[CointegrationResult],
    require_coint_pass: bool = True,
) -> pd.DataFrame:
    """
    Run IC test on cointegration-passing pairs.
    Returns DataFrame with all funnel results.
    """
    rows = []

    # Run IC on all pairs that passed coint (or all if require_coint_pass=False)
    candidates = [r for r in coint_results if (not require_coint_pass or r.passes)]
    print(f"\nRunning IC test on {len(candidates)} pairs...")

    for r in candidates:
        ic_result = compute_ic_for_pair(close, r.asset_a, r.asset_b, r.beta_mean)
        best_ic = ic_result["best_ic"]
        passes_ic = (not np.isnan(best_ic)) and (best_ic < IC_THRESHOLD)
        status = "PASS" if passes_ic else "FAIL"
        print(f"  {r.asset_a}/{r.asset_b}: best IC={best_ic:.3f} @ {ic_result['best_horizon']}h  [{status}]")

        rows.append({
            "asset_A":      r.asset_a,
            "asset_B":      r.asset_b,
            "corr_logP":    round(r.corr_logp, 4),
            "corr_ret":     round(r.corr_ret,  4),
            "adf_pass_rate": round(r.adf_pass_rate, 4),
            "beta_mean":    round(r.beta_mean, 4) if not np.isnan(r.beta_mean) else np.nan,
            "beta_std":     round(r.beta_std,  4) if not np.isnan(r.beta_std)  else np.nan,
            "ic_4h":        round(ic_result["ic_4h"],  4) if not np.isnan(ic_result["ic_4h"])  else np.nan,
            "ic_12h":       round(ic_result["ic_12h"], 4) if not np.isnan(ic_result["ic_12h"]) else np.nan,
            "ic_24h":       round(ic_result["ic_24h"], 4) if not np.isnan(ic_result["ic_24h"]) else np.nan,
            "ic_72h":       round(ic_result["ic_72h"], 4) if not np.isnan(ic_result["ic_72h"]) else np.nan,
            "best_IC":      round(best_ic, 4) if not np.isnan(best_ic) else np.nan,
            "best_horizon": ic_result["best_horizon"],
            "n_obs":        ic_result["n_obs"],
            "passes_ic":    passes_ic,
        })

    if rows:
        df_results = pd.DataFrame(rows)
        # Also include pairs that failed cointegration (for the full CSV)
        failed_coint = [r for r in coint_results if not r.passes]
        for r in failed_coint:
            rows.append({
                "asset_A":       r.asset_a,
                "asset_B":       r.asset_b,
                "corr_logP":     round(r.corr_logp, 4),
                "corr_ret":      round(r.corr_ret,  4),
                "adf_pass_rate": round(r.adf_pass_rate, 4),
                "beta_mean":     round(r.beta_mean, 4) if not np.isnan(r.beta_mean) else np.nan,
                "beta_std":      round(r.beta_std,  4) if not np.isnan(r.beta_std)  else np.nan,
                "ic_4h":  np.nan, "ic_12h": np.nan, "ic_24h": np.nan, "ic_72h": np.nan,
                "best_IC": np.nan,
                "best_horizon": np.nan,
                "n_obs":     0,
                "passes_ic": False,
            })
        df_results = pd.DataFrame(rows)
    else:
        df_results = pd.DataFrame(columns=[
            "asset_A", "asset_B", "corr_logP", "corr_ret", "adf_pass_rate",
            "beta_mean", "beta_std", "ic_4h", "ic_12h", "ic_24h", "ic_72h",
            "best_IC", "best_horizon", "n_obs", "passes_ic",
        ])

    passing_ic = df_results["passes_ic"].sum() if len(df_results) else 0
    print(f"\nStage 4: {len(candidates)} → {passing_ic} pairs pass IC filter (IC < {IC_THRESHOLD})")
    return df_results
