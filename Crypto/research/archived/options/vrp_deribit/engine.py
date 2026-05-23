"""
engine.py — Unconditional short straddle simulation engine (VRP Phase 3)

Strategy: always-short ATM straddle 30 DTE, roll/close at 14 DTE (HOLD_DAYS=16).
No signal timing. Premium harvest only.
Regime filter: skip entry if BTC DD30 > 15%; unwind existing if DD > 20%.

P&L model: Black-Scholes delta-hedge approximation
  PnL% ≈ ½ × N'(0) × (σ_implied² − σ_realized²) × T_hold / σ_implied
  (% of underlying notional per cycle)

Costs (per cycle, % of underlying notional):
  option_fees : 2 legs × (entry + exit) × 0.03% = 0.12%
  spread      : 0.5% × premium_30DTE + 0.6% × premium_14DTE  (vol-dependent)
  hedge       : 12 hedges × blended_maker_taker × delta_exposure
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

# ── Constants ──────────────────────────────────────────────────────────────────
HOLD_DAYS    = 16
RV_WINDOW    = 30
N_PRIME_0    = 0.39894228  # N'(0): ATM B-S normalization constant
DD_NO_ENTRY  = 0.15        # BTC 30d DD threshold: skip new cycle
DD_UNWIND    = 0.20        # BTC 30d DD threshold: unwind intra-cycle

# Cost model
OPTION_FEE_PER_LEG = 0.0003   # Deribit: 0.03% underlying per leg
SPREAD_ENTRY_PCT   = 0.005    # half-spread at entry: 0.5% of straddle premium
SPREAD_EXIT_PCT    = 0.006    # half-spread at exit:  0.6% of straddle premium
MAKER_REBATE       = -0.0001  # Deribit perp maker: -0.01% per trade
TAKER_FEE          =  0.0003  # Deribit perp taker: +0.03% per trade
MAKER_FILL_RATE    = 0.70     # 70% maker, 30% taker → blended hedge rate
N_HEDGES_PER_CYCLE = 12       # approx daily delta-hedges over 16-day cycle


@dataclass
class CycleResult:
    start_date:     pd.Timestamp
    end_date:       pd.Timestamp
    hold_days:      int
    dvol_entry:     float   # implied vol at entry (decimal, e.g. 0.60)
    dvol_exit:      float   # implied vol at exit  (decimal)
    rv_realized:    float   # realized vol over hold period (decimal)
    gross_pnl:      float   # B-S P&L % of underlying notional
    cost_options:   float   # % notional
    cost_spread:    float   # % notional
    cost_hedge:     float   # % notional
    net_pnl:        float   # gross − costs, % notional
    early_unwind:   bool
    dd30_at_entry:  float   # BTC 30d drawdown at cycle start


# ── Internal helpers ───────────────────────────────────────────────────────────

def _dd30(btc_arr: np.ndarray, idx: int, window: int = 30) -> float:
    lo = max(0, idx - window)
    hi = idx + 1
    peak = btc_arr[lo:hi].max()
    curr = btc_arr[idx]
    return float(max(0.0, 1.0 - curr / peak)) if peak > 0 else 0.0


def _straddle_premium_pct(dvol: float, dte: int) -> float:
    """ATM straddle premium as % of underlying: 2 × N'(0) × σ × sqrt(DTE/365)."""
    return 2.0 * N_PRIME_0 * dvol * np.sqrt(dte / 365.0)


# ── Cost model ─────────────────────────────────────────────────────────────────

def compute_cycle_costs(
    dvol_entry: float,
    dvol_exit: float,
    hold_days: int = HOLD_DAYS,
) -> dict[str, float]:
    """
    Per-cycle costs as fraction of underlying notional.

    Returns dict with keys: option_fees, spread, hedge, total.
    """
    # Exchange fees: 2 legs × (1 entry + 1 exit) × 0.03%
    option_fees = 4 * OPTION_FEE_PER_LEG

    # Bid-ask spread: % × straddle_premium_pct
    dte_exit = 30 - hold_days  # DTE at exit (14 for HOLD_DAYS=16)
    prem_entry = _straddle_premium_pct(dvol_entry, 30)
    prem_exit  = _straddle_premium_pct(dvol_exit,  max(dte_exit, 1))
    spread = SPREAD_ENTRY_PCT * prem_entry + SPREAD_EXIT_PCT * prem_exit

    # Delta hedge: blended maker/taker rate × approximate delta exposure
    blended_rate = MAKER_FILL_RATE * MAKER_REBATE + (1 - MAKER_FILL_RATE) * TAKER_FEE
    # Mean delta exposure ≈ 0.30 × dvol_entry (heuristic: ATM delta decays from 0.5→0)
    mean_delta_exp = 0.30 * dvol_entry
    hedge = abs(N_HEDGES_PER_CYCLE * blended_rate * mean_delta_exp)

    return {
        "option_fees": option_fees,
        "spread":      spread,
        "hedge":       hedge,
        "total":       option_fees + spread + hedge,
    }


# ── Cycle simulation ───────────────────────────────────────────────────────────

def simulate_cycles(
    dvol:         pd.Series,
    btc_close:    pd.Series,
    hold_days:    int   = HOLD_DAYS,
    rv_window:    int   = RV_WINDOW,
    n_concurrent: int   = 2,
    dd_no_entry:  float = DD_NO_ENTRY,
    dd_unwind:    float = DD_UNWIND,
) -> pd.DataFrame:
    """
    Simulate all straddle cycles (unconditional; no signal timing).

    n_concurrent staggered series are run in parallel, each offset by
    (hold_days / n_concurrent) days, to maintain ~n_concurrent active
    straddles at all times (max exposure = n_concurrent × portfolio_pct).

    Returns DataFrame with one row per executed cycle (regime-blocked entries
    are excluded). P&L columns are in % of underlying notional; multiply by
    portfolio sizing to get portfolio P&L.
    """
    common = dvol.index.intersection(btc_close.index)
    dvol_a  = dvol.reindex(common).ffill().to_numpy(dtype=float)
    btc_a   = btc_close.reindex(common).ffill().to_numpy(dtype=float)
    n       = len(common)
    log_ret = np.log(btc_a[1:] / btc_a[:-1])  # length n-1

    all_cycles: list[CycleResult] = []
    offset_step = max(1, hold_days // n_concurrent)

    for series_id in range(n_concurrent):
        offset = series_id * offset_step
        t = rv_window + offset

        while t < n - hold_days:
            dd_entry = _dd30(btc_a, t)
            if dd_entry > dd_no_entry:
                t += hold_days
                continue

            dvol_entry = dvol_a[t]
            if dvol_entry <= 0:
                t += hold_days
                continue

            # Scan ahead for early-unwind trigger
            actual_hold = hold_days
            early = False
            for k in range(1, hold_days + 1):
                if t + k >= n:
                    actual_hold = k - 1
                    early = True
                    break
                if _dd30(btc_a, t + k) > dd_unwind:
                    actual_hold = k
                    early = True
                    break

            if actual_hold < 2:
                t += hold_days
                continue

            exit_idx  = t + actual_hold
            dvol_exit = dvol_a[min(exit_idx, n - 1)]

            # Realized vol over holding window
            rets = log_ret[t: t + actual_hold]
            rv_realized = float(np.sqrt(np.sum(rets ** 2) * 365.0 / actual_hold))

            # Gross B-S P&L (% of underlying notional)
            T_hold    = actual_hold / 365.0
            gross_pnl = (
                0.5 * N_PRIME_0
                * (dvol_entry ** 2 - rv_realized ** 2)
                * T_hold
                / max(dvol_entry, 0.01)
            )

            costs = compute_cycle_costs(dvol_entry, dvol_exit, actual_hold)

            all_cycles.append(CycleResult(
                start_date   = common[t],
                end_date     = common[exit_idx],
                hold_days    = actual_hold,
                dvol_entry   = float(dvol_entry),
                dvol_exit    = float(dvol_exit),
                rv_realized  = float(rv_realized),
                gross_pnl    = float(gross_pnl),
                cost_options = float(costs["option_fees"]),
                cost_spread  = float(costs["spread"]),
                cost_hedge   = float(costs["hedge"]),
                net_pnl      = float(gross_pnl - costs["total"]),
                early_unwind = early,
                dd30_at_entry= float(dd_entry),
            ))

            t += hold_days

    if not all_cycles:
        return pd.DataFrame()

    df = pd.DataFrame([c.__dict__ for c in all_cycles])
    return df.sort_values("start_date").reset_index(drop=True)


# ── Daily P&L series ───────────────────────────────────────────────────────────

def cycles_to_daily_pnl(
    cycles:       pd.DataFrame,
    full_index:   pd.DatetimeIndex,
    portfolio_pct: float = 0.01,
) -> pd.Series:
    """
    Convert cycle-level P&L (% notional) to a daily portfolio P&L series.

    Each cycle's net P&L × portfolio_pct is distributed evenly across its
    holding days. Units: fraction of total portfolio per day.
    """
    daily = pd.Series(0.0, index=full_index, name="daily_pnl_portfolio")

    for _, row in cycles.iterrows():
        if row["hold_days"] < 1:
            continue
        # contribution per calendar day = net_pnl × sizing / hold_days
        contrib = row["net_pnl"] * portfolio_pct / row["hold_days"]
        mask = (full_index >= row["start_date"]) & (full_index <= row["end_date"])
        daily[mask] += contrib

    return daily


# ── Metrics ────────────────────────────────────────────────────────────────────

def compute_cycle_metrics(
    cycles: pd.DataFrame,
    hac_lags: int = 6,
    col: str = "net_pnl",
) -> dict:
    """
    Compute Sharpe and distribution metrics on cycle-level P&L (% of notional).

    This is the statistically clean estimate: cycles are non-overlapping within
    each series (one observation per 16-day window per series).  HAC with
    maxlags=min(6, n//5) corrects for any residual within-series correlation.

    Returns annualized metrics where annualization factor = cycles_per_year.
    """
    import statsmodels.api as sm
    from scipy import stats as sc_stats

    r = cycles[col].dropna()
    if len(r) < 10:
        return {"error": "insufficient cycles"}

    days_span   = (cycles["end_date"].max() - cycles["start_date"].min()).days
    cyc_per_yr  = len(r) / (days_span / 365.0)

    mean_cyc = float(r.mean())
    std_cyc  = float(r.std(ddof=1))

    ann_return = mean_cyc * cyc_per_yr
    ann_vol    = std_cyc  * np.sqrt(cyc_per_yr)
    sharpe_raw = ann_return / ann_vol if ann_vol > 0 else np.nan

    # HAC t-stat on cycle returns
    # t_HAC = mean / HAC_SE_of_mean  where HAC_SE_of_mean = long_run_vol / sqrt(n)
    # → HAC Sharpe = t_HAC × sqrt(cyc_per_yr / n)  (consistent with raw = mean/std×sqrt(cyc/yr))
    lags = min(hac_lags, len(r) // 5)
    X    = sm.add_constant(np.ones(len(r)))
    res  = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    t_hac   = float(res.tvalues[0])
    hac_se  = float(res.bse[0])
    sharpe_hac = t_hac * np.sqrt(cyc_per_yr / len(r)) if len(r) > 0 else np.nan

    skew = float(sc_stats.skew(r))
    kurt = float(sc_stats.kurtosis(r))

    return {
        "n_cycles":      len(r),
        "cycles_per_yr": round(cyc_per_yr, 2),
        "mean_cycle":    round(mean_cyc, 6),
        "std_cycle":     round(std_cyc,  6),
        "pct_positive":  round(float((r > 0).mean()), 3),
        "ann_return":    round(ann_return, 5),
        "ann_vol":       round(ann_vol, 5),
        "sharpe_raw":    round(sharpe_raw, 3),
        "sharpe_hac":    round(sharpe_hac, 3),
        "t_hac":         round(t_hac, 3),
        "skewness":      round(skew, 3),
        "excess_kurtosis": round(kurt, 3),
        "worst_cycle":   round(float(r.min()), 6),
        "best_cycle":    round(float(r.max()), 6),
    }


def compute_metrics(daily_pnl: pd.Series, hac_lags: int = 6) -> dict:
    """
    Compute standard risk/return metrics on a daily portfolio P&L series.
    Sharpe uses HAC t-stat (Newey-West) to be conservative with autocorrelation.
    """
    import statsmodels.api as sm

    r = daily_pnl.dropna()
    if len(r) < 20:
        return {"error": "insufficient data"}

    ann = 365.0
    mean_daily = float(r.mean())
    std_daily  = float(r.std(ddof=1))

    ann_return = mean_daily * ann
    ann_vol    = std_daily  * np.sqrt(ann)
    sharpe_raw = ann_return / ann_vol if ann_vol > 0 else np.nan

    # HAC-adjusted Sharpe: t-stat on mean return with Newey-West SE
    # HAC Sharpe = t_HAC × sqrt(ann / n)  (mirrors t_HAC × sqrt(cyc/n) logic)
    X   = sm.add_constant(np.ones(len(r)))
    res = sm.OLS(r.values, X).fit(cov_type="HAC", cov_kwds={"maxlags": hac_lags})
    t_hac = float(res.tvalues[0])  # intercept t-stat = HAC-adjusted mean test
    hac_se = float(res.bse[0])
    sharpe_hac = t_hac * np.sqrt(ann / len(r)) if len(r) > 0 else np.nan

    # Drawdown
    cum = (1 + r).cumprod()
    roll_max = cum.cummax()
    dd_series = (cum - roll_max) / roll_max
    max_dd = float(dd_series.min())
    calmar = ann_return / abs(max_dd) if max_dd != 0 else np.nan

    # Sortino (downside vol)
    neg = r[r < 0]
    sortino_den = float(neg.std(ddof=1) * np.sqrt(ann)) if len(neg) > 1 else np.nan
    sortino = ann_return / sortino_den if sortino_den and sortino_den > 0 else np.nan

    # Distribution
    from scipy import stats as sc_stats
    skew = float(sc_stats.skew(r))
    kurt = float(sc_stats.kurtosis(r))

    # Max single-day loss
    max_single_day_loss = float(r.min())

    return {
        "n_days":               len(r),
        "ann_return":           round(ann_return, 5),
        "ann_vol":              round(ann_vol, 5),
        "sharpe_raw":           round(sharpe_raw, 3),
        "sharpe_hac":           round(sharpe_hac, 3),
        "t_hac_mean":           round(t_hac, 3),
        "max_dd":               round(max_dd, 5),
        "calmar":               round(calmar, 3) if calmar and np.isfinite(calmar) else None,
        "sortino":              round(sortino, 3) if sortino and np.isfinite(sortino) else None,
        "skewness":             round(skew, 3),
        "excess_kurtosis":      round(kurt, 3),
        "max_single_day_loss":  round(max_single_day_loss, 6),
    }
