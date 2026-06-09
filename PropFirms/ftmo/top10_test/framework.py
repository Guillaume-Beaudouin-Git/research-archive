"""
Shared utilities for rigorous backtesting of FTMO candidate strategies.

Mandates (per CLAUDE.md):
- Signal at T-1, trade at T.
- Excess returns vs RF (FRED DTB3).
- HAC Newey-West lag-6 t-stat.
- AMTP across n_tests > 1.
- Walk-forward >=5 expanding folds.
- Daily vol targeting.
- Block bootstrap (Politis-Romano).
- DSR (Bailey-Lopez de Prado).
- FTMO trailing-DD Monte Carlo simulation.
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# FTMO costs (per PropFirms/ftmo/rules.md, last_verified 2026-06-01)
# Per-trade RT cost in bps; overnight swap in bps per night
# ---------------------------------------------------------------------------

FTMO_COST_BPS_RT = {
    "FX_major":         1.5,
    "FX_cross":         4.0,
    "Index_CFD_major":  1.5,
    "Index_CFD_minor":  2.5,
    "Crypto_CFD":       12.0,
    "Metals_CFD_gold":  3.5,
    "Commodity_CFD":    8.0,
}

# Overnight financing in bps per night (negative for any direction held).
# Sourced from overnight_verification_2026-06 memory (G2 swap resolution):
# US100.cash -3.08 bps, EURUSD -1.11 bps, XAUUSD -2.93 bps.
FTMO_SWAP_BPS_PER_NIGHT = {
    "FX_major":         -1.1,
    "FX_cross":         -1.3,
    "Index_CFD_major":  -3.1,
    "Index_CFD_minor":  -3.1,
    "Metals_CFD_gold":  -2.9,
    "Commodity_CFD":    -3.0,
    "Crypto_CFD":       -3.5,
}

# FTMO 2-step Standard $100K account
FTMO_CAPITAL = 100_000.0
FTMO_DLL_PCT = 0.05    # 5% daily loss limit, on balance at 00:00 CET
FTMO_MLL_PCT = 0.10    # 10% trailing max loss, EOD high-watermarked, never decreases
FTMO_P1_TARGET = 0.10  # 10% profit target for P1
FTMO_P2_TARGET = 0.05  # 5% profit target for P2


# ---------------------------------------------------------------------------
# Statistical tests
# ---------------------------------------------------------------------------

def hac_tstat(x: np.ndarray, lag: int = 6) -> float:
    """Newey-West HAC t-stat for H0: mean=0."""
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < lag + 5:
        return float("nan")
    mean = x.mean()
    centered = x - mean
    gamma0 = (centered ** 2).sum() / n
    s = gamma0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        gk = (centered[k:] * centered[:-k]).sum() / n
        s += 2.0 * w * gk
    if s <= 0:
        return float("nan")
    se = math.sqrt(s / n)
    return mean / se if se > 0 else float("nan")


def block_bootstrap_sharpe(returns: np.ndarray, n_boot: int = 1000,
                           block_len: int = 5, n_per_year: int = 252,
                           seed: int = 42) -> dict:
    """Stationary block bootstrap on Sharpe (Politis-Romano).

    Returns mean, 95% CI bounds, std.
    """
    rng = np.random.default_rng(seed)
    r = np.asarray(returns, dtype=float)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < block_len * 3:
        return {"sr_mean": float("nan"), "sr_lo95": float("nan"),
                "sr_hi95": float("nan"), "sr_std": float("nan"), "n_boot": 0}
    sharpes = []
    n_blocks = max(1, n // block_len + 1)
    for _ in range(n_boot):
        idx_start = rng.integers(0, n, size=n_blocks)
        boot = np.concatenate([r[s: s + block_len] for s in idx_start])[:n]
        std = boot.std(ddof=1)
        if std > 0:
            sr = boot.mean() / std * math.sqrt(n_per_year)
            sharpes.append(sr)
    sharpes = np.array(sharpes)
    return {
        "sr_mean": float(sharpes.mean()),
        "sr_lo95": float(np.percentile(sharpes, 2.5)),
        "sr_hi95": float(np.percentile(sharpes, 97.5)),
        "sr_std": float(sharpes.std(ddof=1)),
        "n_boot": int(len(sharpes)),
    }


def deflated_sharpe(sr: float, t_obs: int, n_trials: int = 1,
                    skew: float = 0.0, kurt: float = 3.0) -> dict:
    """Bailey-LdP Deflated Sharpe Ratio.

    sr_dsr = (sr_obs - sr_bench_under_H0) / sigma_sr.

    DSR_threshold = max-of-trials adjusted Sharpe Ratio expected under H0.
    """
    if t_obs < 30 or not np.isfinite(sr):
        return {"dsr": float("nan"), "dsr_threshold": float("nan"),
                "dsr_passes": False, "p_value": float("nan")}
    from scipy.stats import norm
    emc = 0.5772156649
    sr_threshold = math.sqrt(2.0 * math.log(max(2, n_trials))) \
        * (1.0 - emc / math.sqrt(2.0 * math.log(max(2, n_trials))))
    sigma_sr = math.sqrt((1 - skew * sr + (kurt - 1) / 4.0 * sr * sr) / (t_obs - 1))
    if sigma_sr <= 0:
        return {"dsr": float("nan"), "dsr_threshold": float("nan"),
                "dsr_passes": False, "p_value": float("nan")}
    dsr = (sr - sr_threshold) / sigma_sr
    p_value = 1.0 - norm.cdf(dsr)
    return {
        "dsr": float(dsr),
        "dsr_threshold": float(sr_threshold),
        "dsr_passes": bool(dsr > 0.95),
        "p_value": float(p_value),
    }


def walk_forward_folds(returns: pd.Series, n_folds: int = 5,
                       min_train_years: float = 2.0,
                       n_per_year: int = 252) -> list:
    """Expanding-window walk-forward.

    Returns list of dicts: {fold, train_start, train_end, test_start, test_end,
    sr_train, sr_test, sign_consistent}.
    """
    r = returns.dropna()
    n = len(r)
    min_train = int(min_train_years * n_per_year)
    if n < min_train + n_folds * 50:
        return []
    test_size = max(50, (n - min_train) // n_folds)
    folds = []
    for i in range(n_folds):
        train_end = min_train + i * test_size
        test_start = train_end
        test_end = min(train_end + test_size, n)
        if test_end - test_start < 30:
            break
        r_train = r.iloc[:train_end]
        r_test = r.iloc[test_start:test_end]
        sr_train = _sharpe(r_train.values, n_per_year)
        sr_test = _sharpe(r_test.values, n_per_year)
        folds.append({
            "fold": i + 1,
            "train_end_date": str(r.index[train_end - 1].date()) if isinstance(r.index, pd.DatetimeIndex) else train_end,
            "test_start_date": str(r.index[test_start].date()) if isinstance(r.index, pd.DatetimeIndex) else test_start,
            "test_end_date": str(r.index[test_end - 1].date()) if isinstance(r.index, pd.DatetimeIndex) else test_end,
            "sr_train": sr_train,
            "sr_test": sr_test,
            "sign_consistent": (sr_train > 0) == (sr_test > 0),
        })
    return folds


def _sharpe(r: np.ndarray, n_per_year: int = 252) -> float:
    r = r[np.isfinite(r)]
    if len(r) < 30:
        return float("nan")
    std = r.std(ddof=1)
    if std <= 0:
        return float("nan")
    return r.mean() / std * math.sqrt(n_per_year)


def max_drawdown_pct(equity: np.ndarray) -> float:
    """Max drawdown as negative fraction (e.g., -0.135 means -13.5%)."""
    if len(equity) == 0:
        return 0.0
    e = np.asarray(equity, dtype=float)
    hwm = np.maximum.accumulate(e)
    dd = (e - hwm) / hwm
    return float(dd.min())


def amtp_bonferroni(t_stats: list, alpha: float = 0.05) -> list:
    """Bonferroni-adjusted p-values across multiple tests."""
    from scipy.stats import norm
    n = len([t for t in t_stats if np.isfinite(t)])
    if n == 0:
        return [float("nan")] * len(t_stats)
    out = []
    for t in t_stats:
        if not np.isfinite(t):
            out.append(float("nan"))
            continue
        p_two = 2.0 * (1.0 - norm.cdf(abs(t)))
        out.append(min(1.0, p_two * n))
    return out


# ---------------------------------------------------------------------------
# FTMO Monte Carlo simulator
# ---------------------------------------------------------------------------

@dataclass
class FTMOResult:
    p_pass_p1: float = 0.0
    p_pass_p1_p2: float = 0.0
    p_bust_dll: float = 0.0
    p_bust_mll: float = 0.0
    median_days_pass_p1: float = float("nan")
    median_days_pass_p2: float = float("nan")
    n_runs: int = 0


def ftmo_montecarlo(daily_pnl_pct: pd.Series, n_runs: int = 5000,
                    max_days_per_phase: int = 365, seed: int = 7,
                    block_len: int = 5) -> FTMOResult:
    """Monte Carlo: bootstrap daily PnL (% capital) and simulate P1 + P2.

    Rules:
    - DLL: equity intraday low - balance@T-1 >= -5% (using EOD pnl as proxy)
    - MLL: equity_HWM_EOD - equity_current >= -10% (HWM never decreases)
    - P1 target: cumulative return >= 10%
    - P2 target: cumulative return >= 5%
    - Min trading days: 4 (almost always satisfied by simulator)
    - Unlimited time per phase (capped at max_days_per_phase for sim tractability)
    """
    rng = np.random.default_rng(seed)
    pnl = daily_pnl_pct.dropna().values
    if len(pnl) < 30:
        return FTMOResult(n_runs=0)

    n = len(pnl)
    n_blocks = max(1, max_days_per_phase // block_len + 1)

    passed_p1 = 0
    passed_p1_p2 = 0
    busted_dll = 0
    busted_mll = 0
    days_pass_p1 = []
    days_pass_p2 = []

    for run in range(n_runs):
        # Phase 1
        starts = rng.integers(0, n, size=n_blocks)
        path = np.concatenate([pnl[s: s + block_len] for s in starts])[:max_days_per_phase]

        eq = 1.0  # start at 1.0 (relative to initial capital)
        hwm_eod = 1.0
        dll_floor_today = 1.0 - FTMO_DLL_PCT  # balance@T-1 - 5%
        p1_passed_day = None
        p1_bust = None

        for day, pct in enumerate(path):
            # intraday DLL check: model worst-case as EOD pnl realized at lowest point
            # Approximation: if pct < -DLL: bust.
            eq_next = eq * (1.0 + pct)
            # DLL: eq_next < dll_floor_today
            if eq_next < dll_floor_today:
                p1_bust = "dll"
                break
            # MLL: eq_next < hwm_eod - MLL
            mll_floor = max(1.0 - FTMO_MLL_PCT, hwm_eod - FTMO_MLL_PCT)
            if eq_next < mll_floor:
                p1_bust = "mll"
                break

            eq = eq_next
            hwm_eod = max(hwm_eod, eq)
            dll_floor_today = eq - FTMO_DLL_PCT

            if eq >= 1.0 + FTMO_P1_TARGET:
                p1_passed_day = day + 1
                break

        if p1_bust == "dll":
            busted_dll += 1
            continue
        if p1_bust == "mll":
            busted_mll += 1
            continue
        if p1_passed_day is None:
            continue  # timed out (rare with max_days=365)
        passed_p1 += 1
        days_pass_p1.append(p1_passed_day)

        # Phase 2 — fresh equity, same MLL/DLL
        starts = rng.integers(0, n, size=n_blocks)
        path2 = np.concatenate([pnl[s: s + block_len] for s in starts])[:max_days_per_phase]
        eq2 = 1.0
        hwm2 = 1.0
        dll_floor2 = 1.0 - FTMO_DLL_PCT
        p2_passed = None
        p2_bust = None
        for day, pct in enumerate(path2):
            eq_next = eq2 * (1.0 + pct)
            if eq_next < dll_floor2:
                p2_bust = "dll"
                break
            mll_floor = max(1.0 - FTMO_MLL_PCT, hwm2 - FTMO_MLL_PCT)
            if eq_next < mll_floor:
                p2_bust = "mll"
                break
            eq2 = eq_next
            hwm2 = max(hwm2, eq2)
            dll_floor2 = eq2 - FTMO_DLL_PCT
            if eq2 >= 1.0 + FTMO_P2_TARGET:
                p2_passed = day + 1
                break

        if p2_passed is not None:
            passed_p1_p2 += 1
            days_pass_p2.append(p2_passed)

    return FTMOResult(
        p_pass_p1=passed_p1 / n_runs,
        p_pass_p1_p2=passed_p1_p2 / n_runs,
        p_bust_dll=busted_dll / n_runs,
        p_bust_mll=busted_mll / n_runs,
        median_days_pass_p1=float(np.median(days_pass_p1)) if days_pass_p1 else float("nan"),
        median_days_pass_p2=float(np.median(days_pass_p2)) if days_pass_p2 else float("nan"),
        n_runs=n_runs,
    )


# ---------------------------------------------------------------------------
# Excess returns (vs cash rate)
# ---------------------------------------------------------------------------

def load_rf_daily() -> pd.Series:
    """Best-effort load of FRED DTB3 cached locally. Fall back to flat 2%."""
    import os
    candidates = [
        "<HOME>/Desktop/Algo_claude/data/macro/DTB3.csv",
        "<HOME>/Desktop/Algo_claude/data/fred/DTB3.csv",
        "<HOME>/Desktop/Algo_claude/data/panels/DTB3.csv",
        "<HOME>/Desktop/Algo_claude/data/panels/rf_daily.csv",
    ]
    for p in candidates:
        if os.path.exists(p):
            df = pd.read_csv(p)
            cols = list(df.columns)
            if "Date" in cols or "date" in cols:
                date_col = "Date" if "Date" in cols else "date"
                df[date_col] = pd.to_datetime(df[date_col])
                df = df.set_index(date_col).sort_index()
                val_col = [c for c in df.columns if c.upper() in {"DTB3", "RF", "VALUE"}]
                if val_col:
                    s = df[val_col[0]].astype(float)
                    return (s / 100.0 / 252.0).ffill()
    # Fallback: constant 2% annual = ~7.94 bps/day
    idx = pd.date_range("2010-01-01", "2027-01-01", freq="B")
    return pd.Series(0.02 / 252.0, index=idx, name="rf_daily")


# ---------------------------------------------------------------------------
# Daily vol targeting
# ---------------------------------------------------------------------------

def vol_target(returns: pd.Series, target_annual: float = 0.10,
               lookback: int = 63, n_per_year: int = 252,
               max_lev: float = 5.0) -> pd.Series:
    """Apply daily vol targeting (63-day rolling std).

    Position = target / realized_vol. Capped at max_lev.
    Signal-at-T-1 is enforced by shifting the realized vol by 1.
    """
    r = returns.copy()
    vol = r.rolling(lookback, min_periods=20).std(ddof=1) * math.sqrt(n_per_year)
    lev = (target_annual / vol).clip(upper=max_lev).shift(1)
    return r * lev


@dataclass
class StrategyResult:
    id: str
    name: str
    n_trades: int = 0
    n_days: int = 0
    win_rate: float = 0.0
    wl_ratio: float = 0.0
    mean_bps_per_trade_gross: float = 0.0
    mean_bps_per_trade_net: float = 0.0
    cost_gate_ratio: float = 0.0
    sharpe_gross: float = 0.0
    sharpe_net: float = 0.0
    sharpe_excess: float = 0.0  # vs RF
    max_dd_pct: float = 0.0
    hac_t_excess: float = 0.0
    hac_t_net: float = 0.0
    bootstrap_sr_mean: float = 0.0
    bootstrap_sr_lo95: float = 0.0
    bootstrap_sr_hi95: float = 0.0
    dsr: float = 0.0
    dsr_passes: bool = False
    wf_n_folds: int = 0
    wf_pass_rate: float = 0.0
    wf_sign_consistent_pct: float = 0.0
    ftmo_p_pass_p1: float = 0.0
    ftmo_p_pass_p1_p2: float = 0.0
    ftmo_p_bust: float = 0.0
    ftmo_median_days_p1: float = float("nan")
    amtp_p_value: float = float("nan")
    research_pass: bool = False
    propfirm_pass: bool = False
    notes: str = ""
