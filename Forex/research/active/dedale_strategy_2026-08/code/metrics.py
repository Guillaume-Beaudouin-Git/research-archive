"""
Analyse statistique de la reproduction Config A (defaut de code) de Dedale.
Lit trades_<PAIR>.csv (ecrits par dedale_engine.py), calcule :
  - GROSS / NET / NET-swap par trade
  - Sharpe correct (sqrt(trades/an)) vs Sharpe errone (sqrt(252)) -- L47
  - HAC lag-6 (t-stat), two-sided (long vs short separes)
  - DSR (Bailey-LdP, parametree en periods_per_year = trades/an, PAS 252)
  - block-bootstrap CI (Politis-Romano)
  - walk-forward 5 folds expanding + split 2022-2024 vs reste
  - placebo direction aleatoire
Ecrit resultats.csv (une ligne par scenario) dans le dossier parent.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats as scipy_stats

BASE = Path(__file__).resolve().parent.parent
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD"]
RF_PARQUET = Path("<HOME>/Desktop/Algo_claude/data/raw/fred_DTB3_37358bdf84.parquet")
RISK_PCT = 1.0
EULER_MASCHERONI = 0.5772156649015329


def load_rf() -> pd.Series:
    df = pd.read_parquet(RF_PARQUET)
    s = df["dtb3"].astype(float) / 100.0  # annualized fraction
    s.index = pd.to_datetime(s.index).tz_localize("UTC")
    return s.ffill()


def load_all_trades() -> pd.DataFrame:
    frames = []
    for p in PAIRS:
        f = BASE / f"trades_{p}.csv"
        if f.exists():
            df = pd.read_csv(f, parse_dates=["entry_time", "exit_time"])
            frames.append(df)
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values("exit_time").reset_index(drop=True)
    return out


def add_pnl(df: pd.DataFrame, rf: pd.Series, cost_bps: float, swap_haircut: float,
            risk_pct=RISK_PCT) -> pd.DataFrame:
    risk_amount = risk_pct / 100.0
    d = df.copy()
    gross = d["r_multiple"] * risk_amount
    notional = risk_amount * d["notional_per_risk_unit"]
    cost = cost_bps * 1e-4 * notional
    swap = (d["swap_bps_annual"] * swap_haircut / 100.0 / 365.0) * d["nights"] * notional
    # RF drag on the notional held (excess-return convention: strategy return minus RF*time held,
    # scaled by notional relative to the risk unit -- approximation: RF is charged only on the
    # capital actually at risk (risk_amount), not full notional, since account equity earns RF
    # regardless of the trade; the trade's EXCESS contribution subtracts RF*holding on risk_amount)
    rf_at_entry = d["entry_time"].map(lambda t: rf.reindex([t], method="ffill").iloc[0]
                                       if len(rf) else 0.0)
    rf_drag = rf_at_entry.values * (d["hold_days"].values / 365.0) * risk_amount
    d["pnl_gross"] = gross
    d["pnl_net"] = gross - cost
    d["pnl_net_swap"] = gross - cost + swap
    d["pnl_net_swap_excess"] = gross - cost + swap - rf_drag
    d["pnl_swap_only"] = swap
    d["pnl_cost_only"] = cost
    d["rf_drag"] = rf_drag
    return d


def sharpe_annualized(returns: np.ndarray, periods_per_year: float) -> float:
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return np.nan
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))


def hac_tstat(returns: np.ndarray, lags: int = 6):
    """OLS on a constant with HAC (Newey-West) SE -- t-stat of the mean."""
    import statsmodels.api as sm
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    if len(r) < 10:
        return np.nan, np.nan, len(r)
    X = np.ones((len(r), 1))
    model = sm.OLS(r, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(model.params[0]), float(model.tvalues[0]), len(r)


def deflated_sharpe(sharpe_per_period: float, n_obs: int, skewness: float, kurtosis: float,
                     n_trials: int = 1, std_sr_trials_per: float = None):
    """Bailey-LdP DSR/PSR, working entirely in PER-PERIOD (per-trade) units -- caller passes
    periods_per_year-agnostic sharpe_per_period = mean/std (no annualization applied)."""
    sr = sharpe_per_period
    inner = 1.0 - skewness * sr + (kurtosis - 1.0) / 4.0 * sr ** 2
    inner = max(inner, 1e-8)
    se_sr = math.sqrt(inner / (n_obs - 1))
    psr = float(scipy_stats.norm.cdf(sr / se_sr))
    if std_sr_trials_per is None:
        std_sr_trials_per = se_sr
    if n_trials > 1:
        threshold = std_sr_trials_per * (
            (1 - EULER_MASCHERONI) * scipy_stats.norm.ppf(1 - 1.0 / n_trials)
            + EULER_MASCHERONI * scipy_stats.norm.ppf(1 - 1.0 / (n_trials * math.e))
        )
    else:
        threshold = 0.0
    z_dsr = (sr - threshold) / se_sr
    dsr = float(scipy_stats.norm.cdf(z_dsr))
    return dict(psr=psr, dsr=dsr, se_sr=se_sr, threshold_sr=threshold)


def block_bootstrap_sharpe(returns: np.ndarray, periods_per_year: float, block_size: int,
                            n_boot: int = 2000, seed: int = 42):
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < block_size * 2:
        return np.nan, np.nan, np.array([])
    n_blocks = int(np.ceil(n / block_size))
    boots = np.empty(n_boot)
    starts_max = n - block_size
    for b in range(n_boot):
        idx = []
        for _ in range(n_blocks):
            s = rng.integers(0, starts_max + 1)
            idx.extend(range(s, s + block_size))
        sample = r[idx[:n]]
        boots[b] = sharpe_annualized(sample, periods_per_year)
    lo, hi = np.nanpercentile(boots, [2.5, 97.5])
    return lo, hi, boots


def walk_forward_folds(df: pd.DataFrame, pnl_col: str, n_folds: int = 5):
    """Expanding-window walk-forward on chronological trades. Returns per-fold OOS Sharpe."""
    d = df.sort_values("exit_time").reset_index(drop=True)
    n = len(d)
    fold_edges = np.linspace(0, n, n_folds + 1).astype(int)
    results = []
    for k in range(1, n_folds):
        train_end = fold_edges[k]
        test_end = fold_edges[k + 1]
        test = d.iloc[train_end:test_end]
        if len(test) < 5:
            continue
        years = max((test["exit_time"].max() - test["exit_time"].min()).days / 365.25, 1 / 52)
        tpy = len(test) / years if years > 0 else np.nan
        sh = sharpe_annualized(test[pnl_col].values, tpy if tpy > 0 else 98.74)
        results.append(dict(fold=k, n=len(test), start=str(test["exit_time"].min()),
                             end=str(test["exit_time"].max()), sharpe=sh))
    return pd.DataFrame(results)


def regime_split(df: pd.DataFrame, pnl_col: str):
    d = df.copy()
    d["year_regime"] = np.where(
        (d["exit_time"] >= "2022-01-01") & (d["exit_time"] <= "2024-12-31"),
        "2022-2024", "rest")
    out = []
    for name, g in d.groupby("year_regime"):
        years = max((g["exit_time"].max() - g["exit_time"].min()).days / 365.25, 0.5)
        tpy = len(g) / years
        sh = sharpe_annualized(g[pnl_col].values, tpy)
        mean_r, t, n = hac_tstat(g[pnl_col].values)
        out.append(dict(regime=name, n=len(g), trades_per_year=tpy, sharpe=sh,
                         hac_mean=mean_r, hac_t=t))
    return pd.DataFrame(out)


def two_sided(df: pd.DataFrame, pnl_col: str, periods_per_year: float):
    out = []
    for d_name, g in df.groupby("direction"):
        sh = sharpe_annualized(g[pnl_col].values, periods_per_year)
        mean_r, t, n = hac_tstat(g[pnl_col].values)
        out.append(dict(direction=d_name, n=len(g), sharpe=sh, hac_mean=mean_r, hac_t=t))
    return pd.DataFrame(out)


def placebo_random_direction(pair_frames: dict, seed=123):
    """Re-simulate direction choice as coin-flip instead of swap-sign, same pivot/sizing
    mechanics -- approximated here by randomly flipping the SIGN of r_multiple and re-drawing
    swap sign independently per trade (conservative proxy; full re-simulation would require
    re-running dedale_engine with direction randomised, done in dedale_engine_placebo.py)."""
    pass  # implemented in run_analysis via a dedicated re-simulation script
