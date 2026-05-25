"""
Performance metrics for strategy tear sheets.

All Sharpe computations use:
  - Excess returns (daily returns minus DTB3 RF via FRED, annualised fraction / 365)
  - HAC Newey-West standard errors, lag = 6 (CLAUDE.md §Methodology L8)

PSR/DSR follow Bailey & López de Prado (2012/2014) exactly, consistent with
_automation/feasibility/stats/dsr.py (same formulas, self-contained for path safety).
"""
from __future__ import annotations

import io
import math
from typing import Optional

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as scipy_stats

TRADING_DAYS: int = 252
HAC_LAG: int = 6
EULER_MASCHERONI: float = 0.5772156649015329


# ── Risk-free rate (FRED DTB3) ─────────────────────────────────────────────────

def _fetch_fred_dtb3_raw() -> Optional[pd.Series]:
    """Download FRED DTB3 (annualised %, as decimal fraction). Returns None on failure."""
    try:
        import urllib.request
        url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DTB3"
        with urllib.request.urlopen(url, timeout=10) as resp:
            text = resp.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(text), parse_dates=["DATE"])
        df = df.rename(columns={"DATE": "date", "DTB3": "rf"})
        df = df[df["rf"] != "."].copy()
        df["rf"] = df["rf"].astype(float) / 100.0
        return df.set_index("date")["rf"].sort_index()
    except Exception:
        return None


def fetch_risk_free(start: pd.Timestamp, end: pd.Timestamp) -> pd.Series:
    """
    Daily risk-free rate (annualised fraction) for the given period.

    Fetches FRED DTB3; falls back to zero series if FRED is unreachable.
    Caller divides by 365 to get the daily rate.

    Returns
    -------
    pd.Series
        Index: business days start..end. Values: annualised RF fraction.
    """
    bdays = pd.bdate_range(start, end)
    rf_raw = _fetch_fred_dtb3_raw()
    if rf_raw is None:
        return pd.Series(0.0, index=bdays)
    mask = (rf_raw.index >= start) & (rf_raw.index <= end)
    rf_period = rf_raw.loc[mask]
    if rf_period.empty:
        return pd.Series(0.0, index=bdays)
    return rf_period.reindex(bdays).ffill().fillna(0.0)


def to_excess_returns(returns: pd.Series, rf: Optional[pd.Series] = None) -> pd.Series:
    """
    Subtract daily RF from a total-return series.

    Parameters
    ----------
    returns : pd.Series
        Daily total return series.
    rf : pd.Series, optional
        Annualised RF fraction series. Fetched from FRED if None.

    Returns
    -------
    pd.Series
        Excess returns aligned to returns.index.
    """
    if rf is None:
        rf = fetch_risk_free(returns.index.min(), returns.index.max())
    daily_rf = rf.div(365.0)
    daily_rf = daily_rf.reindex(returns.index).ffill().fillna(0.0)
    return returns - daily_rf


# ── Sharpe with HAC SE ─────────────────────────────────────────────────────────

def hac_sharpe_ratio(
    returns_excess: pd.Series,
    lag: int = HAC_LAG,
) -> tuple[float, float, float]:
    """
    Annualised Sharpe ratio with HAC Newey-West standard error.

    Parameters
    ----------
    returns_excess : pd.Series
        Daily excess returns (already RF-subtracted).
    lag : int
        Newey-West bandwidth (default 6, CLAUDE.md L8).

    Returns
    -------
    tuple (sharpe_ann, t_stat, se_ann)
        sharpe_ann : annualised SR = (mu/sigma) × sqrt(252)
        t_stat     : HAC t-statistic on the mean
        se_ann     : HAC SE in annualised SR units
    """
    r = returns_excess.dropna()
    if len(r) < 10 or r.std() == 0:
        return np.nan, np.nan, np.nan

    mu = float(r.mean())
    sigma = float(r.std())
    sharpe_ann = (mu / sigma) * math.sqrt(TRADING_DAYS)

    X = np.ones((len(r), 1))
    res = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lag})
    t_stat = float(res.tvalues[0])
    se_mean = float(res.bse[0])
    se_ann = (se_mean / sigma) * math.sqrt(TRADING_DAYS)

    return sharpe_ann, t_stat, se_ann


# ── PSR / DSR (Bailey-LdP 2012/2014) ─────────────────────────────────────────

def _sr_se_per_period(
    sr_per: float,
    skewness: float,
    raw_kurtosis: float,
    n_obs: int,
) -> float:
    """SE of the per-period SR estimator (Bailey-LdP 2014, eq. 3)."""
    inner = 1.0 - skewness * sr_per + (raw_kurtosis - 1.0) / 4.0 * sr_per ** 2
    inner = max(inner, 1e-8)
    return math.sqrt(inner / max(n_obs - 1, 1))


def _expected_max_std_normal(n_trials: int) -> float:
    """E[max of n IID N(0,1)] via Euler-Mascheroni approximation (Bailey-LdP 2014, eq. 8)."""
    if n_trials <= 1:
        return 0.0
    z1 = scipy_stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = scipy_stats.norm.ppf(1.0 - 1.0 / (n_trials * math.e))
    return (1.0 - EULER_MASCHERONI) * z1 + EULER_MASCHERONI * z2


def compute_psr_dsr(
    returns_excess: pd.Series,
    n_trials: int = 1,
) -> dict:
    """
    Probabilistic Sharpe Ratio (PSR) and Deflated Sharpe Ratio (DSR).

    When n_trials=1, DSR == PSR (no multi-test correction applied).

    Parameters
    ----------
    returns_excess : pd.Series
        Daily excess return series.
    n_trials : int
        Total independent backtests tested (for DSR selection-bias correction).

    Returns
    -------
    dict
        psr, dsr, sharpe_threshold_ann, verdict ('PASS' if dsr > 0.95)
    """
    r = returns_excess.dropna()
    n = len(r)
    if n < 10 or r.std() == 0:
        return {
            "psr": np.nan, "dsr": np.nan,
            "sharpe_threshold_ann": np.nan, "verdict": "FAIL",
        }

    sr_per = float(r.mean() / r.std())
    skew = float(r.skew())
    raw_kurt = float(r.kurt()) + 3.0   # pandas returns excess kurtosis; Bailey-LdP uses raw

    se = _sr_se_per_period(sr_per, skew, raw_kurt, n)

    # PSR: P(true SR > 0)
    psr = float(scipy_stats.norm.cdf(sr_per / se))

    # DSR: P(true SR > SR*) where SR* = E[max from n_trials IID random strategies]
    e_max = _expected_max_std_normal(n_trials)
    sr_threshold_per = se * e_max
    dsr = float(scipy_stats.norm.cdf((sr_per - sr_threshold_per) / se))

    return {
        "psr": psr,
        "dsr": dsr,
        "sharpe_threshold_ann": sr_threshold_per * math.sqrt(TRADING_DAYS),
        "verdict": "PASS" if dsr > 0.95 else "FAIL",
    }


# ── Drawdown utilities ─────────────────────────────────────────────────────────

def drawdown_series(equity: pd.Series) -> pd.Series:
    """Underwater drawdown series (fraction from peak, ≤ 0)."""
    roll_max = equity.cummax()
    return (equity - roll_max) / roll_max


def max_drawdown_duration(dd: pd.Series) -> int:
    """Maximum consecutive calendar days spent in drawdown (dd < 0)."""
    max_dur = cur = 0
    for v in (dd < 0).values:
        if v:
            cur += 1
            max_dur = max(max_dur, cur)
        else:
            cur = 0
    return max_dur


# ── Full metric suite ──────────────────────────────────────────────────────────

def compute_all_metrics(
    returns: pd.Series,
    benchmark: Optional[pd.Series],
    n_trials: int,
    rf: Optional[pd.Series],
) -> dict:
    """
    Compute the full metric suite for a daily return series.

    Parameters
    ----------
    returns : pd.Series
        Daily total returns with datetime index.
    benchmark : pd.Series or None
        Daily benchmark returns for beta/alpha; optional.
    n_trials : int
        Number of independent backtests for DSR correction.
    rf : pd.Series or None
        Annualised RF series (FRED DTB3). Fetched if None.

    Returns
    -------
    dict
        Scalar metrics plus intermediate pd.Series prefixed with '_'.
    """
    r = returns.dropna().sort_index()

    if rf is None:
        rf_fetched = fetch_risk_free(r.index.min(), r.index.max())
    else:
        rf_fetched = rf

    r_excess = to_excess_returns(r, rf_fetched)

    n = len(r)
    n_years = n / TRADING_DAYS
    ann_return = float(r.mean() * TRADING_DAYS)
    total_return = float((1 + r).prod() - 1)

    sharpe_ann, sharpe_t, sharpe_se = hac_sharpe_ratio(r_excess)

    # Sortino (downside std on excess returns)
    down = r_excess[r_excess < 0]
    sortino: float = np.nan
    if len(down) > 1 and float(down.std()) > 0:
        sortino = float((r_excess.mean() / down.std()) * math.sqrt(TRADING_DAYS))

    # Equity curve and drawdown
    equity = (1 + r).cumprod()
    dd = drawdown_series(equity)
    max_dd = float(dd.min())
    dd_dur = max_drawdown_duration(dd)

    calmar = float(ann_return / abs(max_dd)) if max_dd != 0 else np.nan

    # PSR / DSR
    psr_dsr = compute_psr_dsr(r_excess, n_trials)

    # Tail statistics (on total returns for interpretability)
    r_vals = r.values
    p5 = float(np.percentile(r_vals, 5))
    p95 = float(np.percentile(r_vals, 95))
    p1 = float(np.percentile(r_vals, 1))
    tail_ratio = float(abs(p95) / abs(p5)) if p5 != 0 else np.nan
    cvar_95 = float(r_vals[r_vals <= p5].mean()) if (r_vals <= p5).any() else np.nan
    cvar_99 = float(r_vals[r_vals <= p1].mean()) if (r_vals <= p1).any() else np.nan

    # Distribution
    skewness = float(r.skew())
    excess_kurtosis = float(r.kurt())

    # Monthly returns (ME = month-end, pandas 3.x)
    monthly = r.resample("ME").apply(lambda x: (1 + x).prod() - 1)
    pct_pos_months = float((monthly > 0).mean())
    best_month = float(monthly.max())
    worst_month = float(monthly.min())

    # Rolling 6-month Sharpe (naive, for plotting — HAC too slow in rolling windows)
    win = 126
    roll_sr = r_excess.rolling(win).apply(
        lambda x: (float(x.mean()) / float(x.std())) * math.sqrt(TRADING_DAYS)
        if float(x.std()) > 0 else 0.0,
        raw=True,
    )

    out: dict = {
        "start_date": r.index.min(),
        "end_date": r.index.max(),
        "n_obs": n,
        "n_years": round(n_years, 2),
        "total_return": total_return,
        "ann_return": ann_return,
        "sharpe_hac": sharpe_ann,
        "sharpe_t_stat": sharpe_t,
        "sharpe_se": sharpe_se,
        "sortino": sortino,
        "calmar": calmar,
        "mar": calmar,
        "psr": psr_dsr["psr"],
        "dsr": psr_dsr["dsr"],
        "sharpe_threshold_ann": psr_dsr["sharpe_threshold_ann"],
        "dsr_verdict": psr_dsr["verdict"],
        "n_trials": n_trials,
        "max_dd": max_dd,
        "max_dd_duration_days": dd_dur,
        "tail_ratio": tail_ratio,
        "cvar_95": cvar_95,
        "cvar_99": cvar_99,
        "skewness": skewness,
        "excess_kurtosis": excess_kurtosis,
        "pct_pos_months": pct_pos_months,
        "best_month": best_month,
        "worst_month": worst_month,
        # Intermediate series for plots
        "_equity": equity,
        "_dd": dd,
        "_returns": r,
        "_returns_excess": r_excess,
        "_monthly": monthly,
        "_roll_sr": roll_sr,
    }

    # Optional benchmark metrics
    if benchmark is not None:
        bm = benchmark.reindex(r.index)
        valid = r.notna() & bm.notna()
        r_c = r[valid]
        bm_c = bm[valid]
        if len(r_c) > 20:
            bm_equity = (1 + bm_c).cumprod()
            bm_equity = bm_equity.reindex(equity.index).ffill()
            bm_equity = bm_equity / bm_equity.iloc[0]
            ols = sm.OLS(r_c.values, sm.add_constant(bm_c.values)).fit()
            out["benchmark_beta"] = float(ols.params[1])
            out["benchmark_alpha_ann"] = float(ols.params[0] * TRADING_DAYS)
            out["_bm_equity"] = bm_equity

    return out
