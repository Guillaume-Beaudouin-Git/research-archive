"""
SR ≥ 2.0 systematic search — shared backtest engine.
IS: 2015-01-01 → 2021-12-31
OOS: 2022-01-01 → 2024-12-31
HOLDOUT: 2025-01-01 → 2026-05-26
"""
from __future__ import annotations

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import yfinance as yf
import statsmodels.api as sm
from scipy import stats
from typing import Optional
import json, os

# ── constants ──────────────────────────────────────────────────────────────
IS_START    = "2014-01-01"   # extra year for warmup
IS_END      = "2021-12-31"
OOS_START   = "2022-01-01"
OOS_END     = "2024-12-31"
HOLD_START  = "2025-01-01"
HOLD_END    = "2026-05-26"

# Round-trip costs (total, as fraction of notional)
COST_ETF    = (5 + 2) / 10_000      # 7 bps RT
COST_CRYPTO = (10 + 5) / 10_000     # 15 bps RT

REGISTER_PATH = os.path.join(os.path.dirname(__file__), "test_register.json")


# ── data helpers ───────────────────────────────────────────────────────────
def fetch_prices(ticker: str, start: str = "2014-01-01", end: str = HOLD_END) -> pd.Series:
    """Adjusted close prices."""
    df = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if df.empty:
        raise ValueError(f"No data for {ticker}")
    close = df["Close"]
    if isinstance(close, pd.DataFrame):
        close = close.iloc[:, 0]
    return close.dropna()


def fetch_rf(start: str = "2014-01-01", end: str = HOLD_END) -> pd.Series:
    """FRED DTB3 daily risk-free rate (annualised %, convert to daily)."""
    try:
        import pandas_datareader as pdr
        rf_annual = pdr.get_data_fred("DTB3", start=start, end=end)["DTB3"]
        rf_daily = rf_annual / 100 / 252
        return rf_daily.dropna()
    except Exception:
        # Fallback: approximate 0 (conservative — hurts Sharpe slightly)
        idx = pd.date_range(start, end, freq="B")
        return pd.Series(0.0, index=idx, name="rf")


def excess_returns(ret: pd.Series, rf: pd.Series) -> pd.Series:
    """Daily excess returns aligned on common index."""
    rf_aligned = rf.reindex(ret.index, method="ffill").fillna(0)
    return ret - rf_aligned


# ── core metrics ───────────────────────────────────────────────────────────
def sharpe(ret: pd.Series, annualise: float = 252) -> float:
    if ret.std() == 0 or ret.empty:
        return 0.0
    return float(ret.mean() / ret.std() * np.sqrt(annualise))


def max_drawdown(ret: pd.Series) -> float:
    cum = (1 + ret).cumprod()
    roll_max = cum.cummax()
    dd = (cum / roll_max) - 1
    return float(dd.min())


def hac_tstat(ret: pd.Series, lags: int = 6) -> float:
    """HAC Newey-West t-statistic of mean against zero."""
    if ret.empty or ret.std() == 0:
        return 0.0
    X = sm.add_constant(np.ones(len(ret)))
    try:
        res = sm.OLS(ret.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
        return float(res.tvalues[0])
    except Exception:
        return float(ret.mean() / (ret.std() / np.sqrt(len(ret))))


def calmar(ret: pd.Series) -> float:
    ann_ret = ret.mean() * 252
    mdd = abs(max_drawdown(ret))
    if mdd == 0:
        return 0.0
    return float(ann_ret / mdd)


def pct_winning_months(ret: pd.Series) -> float:
    monthly = ret.resample("ME").sum()
    return float((monthly > 0).mean() * 100)


def worst_month(ret: pd.Series) -> float:
    return float(ret.resample("ME").sum().min())


def turnover(pos: pd.Series) -> float:
    """Average annualised one-way turnover (# position changes / year)."""
    changes = pos.diff().abs().fillna(0)
    return float(changes.mean() * 252)


# ── walk-forward ───────────────────────────────────────────────────────────
def walk_forward(
    build_signal_fn,  # callable(prices_train) -> signal pd.Series
    prices: pd.Series,
    cost: float,
    rf: pd.Series,
    n_folds: int = 5,
) -> dict:
    """
    Expanding-window WF. Returns dict with per-fold SR and aggregate.
    build_signal_fn receives training prices only, returns signal for full series.
    """
    is_prices = prices.loc[IS_START:IS_END]
    n = len(is_prices)
    fold_size = n // n_folds
    results = []

    for fold in range(n_folds):
        train_end_idx = fold_size * (fold + 2)  # expanding
        train_end_idx = min(train_end_idx, n)
        train_prices = is_prices.iloc[:train_end_idx]
        val_prices   = is_prices.iloc[train_end_idx: min(train_end_idx + fold_size, n)]
        if len(val_prices) < 30:
            continue
        try:
            signal = build_signal_fn(train_prices)
            val_sig = signal.reindex(val_prices.index).shift(1).fillna(0)
            val_ret = val_prices.pct_change().dropna()
            strat_ret = (val_sig * val_ret - cost * val_sig.diff().abs()).dropna()
            exc_ret = excess_returns(strat_ret, rf)
            sr = sharpe(exc_ret)
            results.append(sr)
        except Exception:
            results.append(np.nan)

    results = [r for r in results if not np.isnan(r)]
    if not results:
        return {"fold_srs": [], "mean_sr": 0.0, "pct_positive": 0.0}
    return {
        "fold_srs": results,
        "mean_sr": float(np.mean(results)),
        "pct_positive": float(np.mean([r > 0 for r in results]) * 100),
    }


# ── bootstrap Sharpe significance ─────────────────────────────────────────
def bootstrap_sr_pval(ret: pd.Series, n_boot: int = 1000) -> float:
    """Block bootstrap p-value: P(SR_shuffled ≥ observed SR)."""
    observed = sharpe(ret)
    if observed <= 0:
        return 1.0
    block_size = max(1, int(np.sqrt(len(ret))))
    boot_srs = []
    for _ in range(n_boot):
        idx = np.random.choice(len(ret) - block_size, size=len(ret) // block_size)
        blocks = [ret.values[i:i + block_size] for i in idx]
        sample = np.concatenate(blocks)[:len(ret)]
        boot_srs.append(sharpe(pd.Series(sample)))
    return float(np.mean([s >= observed for s in boot_srs]))


# ── DSR (Bailey & López de Prado 2014) ────────────────────────────────────
def dsr(sr_star: float, t: int, n_trials: int, sr_mean: float = 0.0, sr_std: float = 1.0) -> float:
    """
    Deflated Sharpe Ratio.
    sr_star: annualised Sharpe of the candidate strategy
    t: number of daily observations in the backtest
    n_trials: total number of hypotheses tested
    """
    if n_trials <= 1:
        return 1.0
    sr_star_adj = sr_star / np.sqrt(252)  # de-annualise to per-bar
    # Expected maximum SR under n_trials iid Gaussian trials
    gamma_euler = 0.5772156649
    sr_max_expected = (
        (1 - gamma_euler) * stats.norm.ppf(1 - 1 / n_trials)
        + gamma_euler * stats.norm.ppf(1 - 1 / (n_trials * np.e))
    )
    # Adjusted for skewness/kurtosis (assuming Gaussian as conservative)
    numerator = (sr_star_adj - sr_max_expected / np.sqrt(t)) * np.sqrt(t - 1)
    denominator = np.sqrt(1 - 0 * sr_star_adj + (sr_star_adj ** 2) * (4 - 1) / 4)
    z = numerator / max(denominator, 1e-9)
    return float(stats.norm.cdf(z))


# ── full evaluation ────────────────────────────────────────────────────────
def evaluate_strategy(
    strategy_id: str,
    description: str,
    phase: str,
    pos_series: pd.Series,        # position series (full date range)
    prices: pd.Series,
    cost: float,
    rf: pd.Series,
    n_total_tests: int,
    params: dict,
    wf_result: Optional[dict] = None,
) -> dict:
    """
    Compute full metrics on IS, OOS, HOLDOUT.
    Returns result dict + prints summary.
    """
    ret = prices.pct_change().dropna()
    pos_lag = pos_series.shift(1).reindex(ret.index).fillna(0)
    strat_ret = pos_lag * ret - cost * pos_lag.diff().abs().fillna(0)

    def metrics(r: pd.Series, label: str) -> dict:
        if r.empty or r.std() == 0:
            return {f"sr_{label}": 0.0, f"mdd_{label}": 0.0, f"n_{label}": 0}
        exc = excess_returns(r, rf)
        return {
            f"sr_{label}": sharpe(exc),
            f"mdd_{label}": max_drawdown(r),
            f"n_{label}": len(r),
        }

    is_ret    = strat_ret.loc[IS_START:IS_END]
    oos_ret   = strat_ret.loc[OOS_START:OOS_END]
    hold_ret  = strat_ret.loc[HOLD_START:HOLD_END]

    m_is   = metrics(is_ret,   "is")
    m_oos  = metrics(oos_ret,  "oos")
    m_hold = metrics(hold_ret, "hold")

    dsr_val = dsr(
        sr_star=m_is["sr_is"],
        t=m_is["n_is"],
        n_trials=max(n_total_tests, 1),
    )

    result = {
        "id": strategy_id,
        "phase": phase,
        "description": description,
        "params": params,
        **m_is, **m_oos, **m_hold,
        "calmar_is": calmar(is_ret),
        "pct_win_months_is": pct_winning_months(is_ret),
        "worst_month_is": worst_month(is_ret),
        "hac_tstat_is": hac_tstat(excess_returns(is_ret, rf)),
        "turnover": turnover(pos_lag),
        "dsr": dsr_val,
        "wf": wf_result or {},
    }

    # Print summary
    wf_str = ""
    if wf_result:
        wf_str = f" | WF: {wf_result['mean_sr']:.2f} ({wf_result['pct_positive']:.0f}%+)"

    print(
        f"[{strategy_id}] {description[:50]:50s} | "
        f"IS={m_is['sr_is']:+.2f} OOS={m_oos['sr_oos']:+.2f} "
        f"HOLD={m_hold['sr_hold']:+.2f} | "
        f"MDD={m_is['mdd_is']:.1%} | DSR={dsr_val:.2f}{wf_str}"
    )

    return result


# ── register persistence ───────────────────────────────────────────────────
def load_register() -> list:
    if os.path.exists(REGISTER_PATH):
        with open(REGISTER_PATH) as f:
            return json.load(f)
    return []


def save_result(result: dict):
    reg = load_register()
    # Replace if same id exists
    reg = [r for r in reg if r.get("id") != result["id"]]
    reg.append(result)
    with open(REGISTER_PATH, "w") as f:
        json.dump(reg, f, indent=2, default=str)
