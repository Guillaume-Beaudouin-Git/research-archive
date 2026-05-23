#!/usr/bin/env python3
"""
Pairs Trading — Distance Method (Gatev 2006 / Zhu 2024 replication)
====================================================================

Algorithm per Gatev et al. (2006) and Zhu (2024):
  Formation period (12 months): normalise prices to $1 at start, compute
    SSD (sum of squared differences) for all N(N-1)/2 pairs, select top M
    closest pairs.
  Trading period (6 months): enter when |spread| > 2σ_formation (wait-one-day),
    exit on zero crossing or period end. Rotate monthly — 6 strategies concurrent.

Variants:
  T20  — top 20 closest pairs
  T100 — top 100 closest pairs
  L75  — top 20 closest pairs filtered to top-25% daily liquidity (vol-weighted)

Costs: 0.5% per round trip (0.25% entry + 0.25% exit).
Portfolio: equal-weight within cohort (committed-capital denominator = M);
  overlay: average of up to 6 concurrent monthly strategies.

Canonical methodology (May 2026):
  - Excess returns over FRED DTB3
  - HAC lag-6 alpha regressions
  - Daily Sharpe × √252
  - AMTP (honest naming)
  - n_tests: 71 + 3 variants = 74

Run:  /usr/bin/python3 -m Equities.research.passed.pairs_distance_gatev.feasibility
"""
from __future__ import annotations

import sys
import logging
import warnings
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pandas.tseries.offsets import DateOffset
from scipy import stats

_SCRIPT_DIR   = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parents[3]
sys.path.insert(0, str(_PROJECT_ROOT))

from data.cache import get_cached_or_fetch
from Equities.research.passed.pairs_distance_gatev.universe import SP100_2015

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ─── Constants ───────────────────────────────────────────────────────────────
DATA_START        = "2011-01-01"
DATA_END          = datetime.now().strftime("%Y-%m-%d")
FORMATION_MONTHS  = 12
TRADING_MONTHS    = 6
ENTRY_SIGMA       = 2.0
COST_RT           = 0.005     # 0.5% per round-trip
MIN_VALID_FRAC    = 0.95      # stock must have this fraction of days present in formation
HAC_LAGS          = 6
BOOTSTRAP_N       = 20_000
N_TESTS_START     = 71
N_TESTS_END       = 74        # +3 variants

# Cohort formation starts: Jan 2012 → Jul 2023 (last trading ends Jan 2024)
_COHORT_START_DATES = pd.date_range("2012-01-01", "2023-07-01", freq="MS")


# ─── Data ────────────────────────────────────────────────────────────────────

def load_prices(tickers: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Returns (close_prices_df, volume_df), both indexed by date, columns = tickers.
    Auto-adjusts for splits/dividends via yfinance auto_adjust=True.
    """
    close_list, vol_list = [], []
    loaded = []
    for tkr in tickers:
        try:
            df = get_cached_or_fetch(tkr, DATA_START, DATA_END, interval="1d", max_age_days=1.0)
            if df.empty or len(df) < 252:
                continue
            df.index = pd.to_datetime(df.index).tz_localize(None)
            close_col  = "close" if "close" in df.columns else df.columns[0]
            vol_col    = "volume" if "volume" in df.columns else None
            close_list.append(df[close_col].rename(tkr))
            if vol_col:
                vol_list.append(df[vol_col].rename(tkr))
            loaded.append(tkr)
        except Exception as exc:
            log.debug("%s: fetch failed — %s", tkr, exc)

    log.info("Loaded %d / %d tickers", len(loaded), len(tickers))
    close_df = pd.concat(close_list, axis=1).sort_index() if close_list else pd.DataFrame()
    vol_df   = pd.concat(vol_list,   axis=1).sort_index() if vol_list   else pd.DataFrame()
    return close_df, vol_df


def load_risk_free() -> pd.Series:
    try:
        import pandas_datareader.data as web
        dtb3 = web.DataReader("DTB3", "fred", DATA_START, DATA_END)
        rf   = (1 + dtb3["DTB3"].ffill().fillna(0.0) / 100) ** (1 / 252) - 1
        rf.index = pd.to_datetime(rf.index).tz_localize(None)
        return rf
    except Exception as exc:
        log.warning("DTB3 unavailable (%s) — rf=0", exc)
        return pd.Series(dtype=float)


def load_ff_factors() -> pd.DataFrame:
    """Fetch Fama-French 5-factor + Momentum daily. Returns DataFrame or empty."""
    try:
        import pandas_datareader.data as web
        ff5  = web.DataReader("F-F_Research_Data_5_Factors_2x3_daily", "famafrench",
                              start=DATA_START, end=DATA_END)[0]
        mom  = web.DataReader("F-F_Momentum_Factor_daily", "famafrench",
                              start=DATA_START, end=DATA_END)[0]
        ff5.index  = pd.to_datetime(ff5.index).tz_localize(None)
        mom.index  = pd.to_datetime(mom.index).tz_localize(None)
        ff5.columns = [c.strip() for c in ff5.columns]
        mom.columns = [c.strip() for c in mom.columns]
        factors = ff5.join(mom[["Mom"]], how="outer") / 100.0
        log.info("FF5+Mom factors loaded: %d rows", len(factors))
        return factors
    except Exception as exc:
        log.warning("FF factors unavailable (%s) — will use SPY-only regression", exc)
        return pd.DataFrame()


# ─── Distance / pair selection ────────────────────────────────────────────────

def compute_ssd_and_select(
    close_df:    pd.DataFrame,
    form_start:  pd.Timestamp,
    form_end:    pd.Timestamp,
    M:           int,
    vol_df:      pd.DataFrame | None = None,
    liq_filter:  bool = False,
) -> tuple[list[tuple[str, str]], dict]:
    """
    Formation step: compute SSD for all pairs, select top M closest.
    liq_filter=True: restrict to pairs where both stocks are in top-25% daily-dollar-volume.
    Returns (selected_pairs, {(i,j): spread_std_over_formation}).
    """
    form = close_df.loc[form_start:form_end].copy()

    # Filter stocks with sufficient history
    required = int(len(form) * MIN_VALID_FRAC)
    valid    = form.columns[form.notna().sum() >= required].tolist()
    if len(valid) < 10:
        return [], {}
    form = form[valid].ffill().bfill()  # fill rare gaps
    if form.isna().any().any():
        form = form.dropna(axis=1)
    if len(form.columns) < 10:
        return [], {}

    cols  = list(form.columns)
    N     = len(cols)

    # Normalise to $1 at formation start
    base = form.iloc[0].clip(lower=1e-8)
    norm = form / base                        # T × N

    # Vectorised SSD: D_ij = Σ_t (p_norm_i,t - p_norm_j,t)²
    X       = norm.values.T                   # N × T
    sq_norms = (X ** 2).sum(axis=1)           # N
    cross    = X @ X.T                        # N × N
    ssd      = sq_norms[:, None] + sq_norms[None, :] - 2 * cross
    np.fill_diagonal(ssd, np.inf)

    # Upper-triangle pair selection
    ri, ci  = np.triu_indices(N, k=1)
    dist_flat = ssd[ri, ci]
    sorted_idx = np.argsort(dist_flat)

    # Optional liquidity filter (L75): both stocks above 75th-pct avg dollar vol
    liquidity_mask = None
    if liq_filter and vol_df is not None and not vol_df.empty:
        # Avg daily dollar volume in week before form_start
        pre_start = form_start - pd.Timedelta(days=10)
        pre_end   = form_start - pd.Timedelta(days=1)
        pre_close = close_df.loc[pre_start:pre_end]
        pre_vol   = vol_df.loc[pre_start:pre_end]
        aligned   = pre_close.reindex(columns=cols) * pre_vol.reindex(columns=cols)
        avg_dv    = aligned.mean()             # avg daily dollar volume per stock
        threshold = avg_dv.quantile(0.75)
        liquidity_mask = avg_dv >= threshold

    selected: list[tuple[str, str]] = []
    for idx in sorted_idx:
        if len(selected) >= M:
            break
        a, b = cols[ri[idx]], cols[ci[idx]]
        if liquidity_mask is not None:
            if not (liquidity_mask.get(a, False) and liquidity_mask.get(b, False)):
                continue
        selected.append((a, b))

    # Compute spread std for each pair over formation period
    thresholds: dict[tuple[str, str], float] = {}
    for (a, b) in selected:
        spread = norm[a] - norm[b]
        s = float(spread.std())
        if s > 1e-10:
            thresholds[(a, b)] = s

    return selected, thresholds


# ─── Trading simulation ───────────────────────────────────────────────────────

def simulate_cohort(
    close_df:    pd.DataFrame,
    form_start:  pd.Timestamp,
    trade_start: pd.Timestamp,
    trade_end:   pd.Timestamp,
    thresholds:  dict[tuple[str, str], float],
    M:           int,
) -> tuple[pd.Series, dict]:
    """
    Simulate one cohort's trading period.
    Prices remain normalised to $1 at form_start throughout.

    Returns (daily_return_series, diagnostics_dict).
    Committed-capital portfolio: denominator = M (all selected pairs, not just open ones).
    """
    if not thresholds or M == 0:
        idx   = pd.date_range(trade_start, trade_end, freq="B")
        return pd.Series(0.0, index=idx), {}

    # Normalise full price series to $1 at form_start
    base_prices = close_df.loc[trade_start:trade_end]
    tickers_needed = list({t for p in thresholds for t in p})
    base_prices = base_prices.reindex(columns=tickers_needed)

    base_vals = close_df.loc[form_start].reindex(tickers_needed).clip(lower=1e-8)
    norm_trade = base_prices / base_vals    # normalised prices for trading period

    trade_dates = norm_trade.index
    T = len(trade_dates)
    if T < 2:
        return pd.Series(dtype=float), {}

    # Pre-extract arrays
    pair_list = list(thresholds.keys())
    n_pairs = len(pair_list)
    tickers_all = sorted({t for p in pair_list for t in p})
    tk_idx = {tk: i for i, tk in enumerate(tickers_all)}

    price_matrix = norm_trade.reindex(columns=tickers_all).values  # T × n_tickers

    # State arrays
    state   = np.zeros(n_pairs, dtype=np.int8)   # 0=flat, 1=long, -1=short
    pending = np.zeros(n_pairs, dtype=np.int8)   # pending entry
    cum_val = np.ones(n_pairs)                    # committed capital tracker

    thresh_arr = np.array([thresholds[p] for p in pair_list])
    ia = np.array([tk_idx[p[0]] for p in pair_list])  # index into price matrix for stock i
    ib = np.array([tk_idx[p[1]] for p in pair_list])  # index into price matrix for stock j

    daily_rets = np.zeros(T)

    # Diagnostics
    n_open_total    = 0
    n_convergences  = 0
    n_force_closes  = 0
    hold_lengths    = []
    hold_start      = np.full(n_pairs, -1, dtype=int)

    for t in range(T):
        pi = price_matrix[t, ia]  # shape (n_pairs,)
        pj = price_matrix[t, ib]

        # NaN = delisting: force close
        nan_mask = np.isnan(pi) | np.isnan(pj)
        if nan_mask.any():
            force_close = nan_mask & (state != 0)
            if force_close.any():
                # Apply exit cost only (no return)
                day_contrib = np.sum(cum_val[force_close] * (-COST_RT / 2))
                daily_rets[t] += day_contrib / M
                cum_val[force_close] *= (1 - COST_RT / 2)
                state[force_close]   = 0
                pending[force_close] = 0
                n_force_closes += int(force_close.sum())

        if t == 0:
            # First day: only check for new signals
            spread = pi - pj
            new_short = (~nan_mask) & (state == 0) & (pending == 0) & (spread >  2 * thresh_arr)
            new_long  = (~nan_mask) & (state == 0) & (pending == 0) & (spread < -2 * thresh_arr)
            pending[new_short] = -1
            pending[new_long]  =  1
            continue

        # ── Apply pending entries (from yesterday's signal) ──────────────────
        apply_mask = (~nan_mask) & (pending != 0) & (state == 0)
        if apply_mask.any():
            state[apply_mask]   = pending[apply_mask]
            cum_val[apply_mask] = 1.0 * (1 - COST_RT / 2)   # entry cost
            pending[apply_mask] = 0
            hold_start[apply_mask] = t
            n_open_total += int(apply_mask.sum())

        # ── Compute return for open positions ────────────────────────────────
        open_mask = (~nan_mask) & (state != 0)
        if open_mask.any():
            pi_prev = price_matrix[t-1, ia]
            pj_prev = price_matrix[t-1, ib]
            nan_prev = np.isnan(pi_prev) | np.isnan(pj_prev)
            valid = open_mask & (~nan_prev)

            if valid.any():
                valid_idx = valid.nonzero()[0]
                pi_v  = pi[valid_idx]
                pj_v  = pj[valid_idx]
                pip_v = pi_prev[valid_idx]
                pjp_v = pj_prev[valid_idx]
                ret_i = np.where(pip_v > 0, pi_v / pip_v - 1, 0.0)
                ret_j = np.where(pjp_v > 0, pj_v / pjp_v - 1, 0.0)

                # Expand to full pair array
                pair_ret_full = np.zeros(n_pairs)
                pair_ret_full[valid_idx] = state[valid_idx] * (ret_i - ret_j)

                spread_t = pi - pj
                # Exit when spread crosses zero (converged) OR last day
                last_day = (t == T - 1)
                converged = valid & (spread_t * state >= 0)
                if last_day:
                    converged |= valid  # force-close all on last day

                if converged.any():
                    pair_ret_full[converged] -= COST_RT / 2  # exit cost
                    for k in converged.nonzero()[0]:
                        if hold_start[k] >= 0:
                            hold_lengths.append(t - hold_start[k])
                    state[converged]   = 0
                    n_convergences += int(converged.sum())
                    if last_day:
                        n_force_closes += int(converged.sum())

                # Committed-capital portfolio return: Σ W_k,t × R_k,t / M
                day_contrib = np.sum(cum_val[valid_idx] * pair_ret_full[valid_idx]) / M
                daily_rets[t] += day_contrib

                # Update cum values
                cum_val[valid_idx] *= (1 + pair_ret_full[valid_idx])

        # ── Check new entry signals (for NEXT day) ────────────────────────────
        no_pos = (~nan_mask) & (state == 0) & (pending == 0)
        if no_pos.any():
            spread = pi - pj
            pending[no_pos & (spread >  2 * thresh_arr)] = -1
            pending[no_pos & (spread < -2 * thresh_arr)] =  1

    diag = {
        "n_open_total":   n_open_total,
        "n_convergences": n_convergences,
        "n_force_closes": n_force_closes,
        "conversion_rate": n_convergences / max(1, n_open_total),
        "avg_hold_days": float(np.mean(hold_lengths)) if hold_lengths else 0.0,
        "max_open_same_day": int((price_matrix[:, ia][~np.isnan(price_matrix[:, ia])].shape[0])),  # placeholder
    }
    return pd.Series(daily_rets, index=trade_dates), diag


# ─── Run full strategy ────────────────────────────────────────────────────────

def run_strategy(
    close_df: pd.DataFrame,
    vol_df:   pd.DataFrame,
    M:        int,
    liq_filter: bool = False,
    label:    str = "",
) -> tuple[pd.Series, dict]:
    """
    Run all monthly cohorts, aggregate 6-strategy overlay.
    Returns (daily_portfolio_returns, aggregate_diagnostics).
    """
    cohort_series: list[pd.Series] = []
    total_diag: dict = {"n_open_total": 0, "n_convergences": 0,
                        "conversion_rate_list": [], "hold_lengths": []}

    for cohort_start in _COHORT_START_DATES:
        form_end    = cohort_start + DateOffset(months=FORMATION_MONTHS) - pd.Timedelta(days=1)
        trade_start = cohort_start + DateOffset(months=FORMATION_MONTHS)
        trade_end   = cohort_start + DateOffset(months=FORMATION_MONTHS + TRADING_MONTHS) - pd.Timedelta(days=1)

        # Snap to actual trading days
        avail = close_df.index
        trade_start_snap = avail[avail >= trade_start][0]  if any(avail >= trade_start)  else None
        trade_end_snap   = avail[avail <= trade_end][-1]   if any(avail <= trade_end)    else None
        form_end_snap    = avail[avail <= form_end][-1]    if any(avail <= form_end)      else None
        form_start_snap  = avail[avail >= cohort_start][0] if any(avail >= cohort_start) else None

        if any(x is None for x in [form_start_snap, form_end_snap, trade_start_snap, trade_end_snap]):
            continue

        # Formation step
        selected, thresholds = compute_ssd_and_select(
            close_df, form_start_snap, form_end_snap, M,
            vol_df if liq_filter else None, liq_filter
        )
        if not thresholds:
            continue

        # Trading simulation
        ret_series, diag = simulate_cohort(
            close_df, form_start_snap, trade_start_snap, trade_end_snap,
            thresholds, M
        )
        if len(ret_series) == 0:
            continue

        cohort_series.append(ret_series)
        total_diag["n_open_total"]      += diag["n_open_total"]
        total_diag["n_convergences"]    += diag["n_convergences"]
        total_diag["conversion_rate_list"].append(diag["conversion_rate"])

    if not cohort_series:
        log.warning("%s: no cohorts produced returns", label)
        return pd.Series(dtype=float), {}

    # Build DataFrame of cohort returns (each column = one cohort)
    all_dates = pd.date_range(
        cohort_series[0].index[0],
        max(s.index[-1] for s in cohort_series),
        freq="B"
    )
    cohort_df = pd.DataFrame(index=all_dates, dtype=float)
    for k, s in enumerate(cohort_series):
        cohort_df[k] = s.reindex(all_dates)

    # 6-strategy overlay: at each day, average of up to 6 most-recent active cohorts
    # (mean with skipna — active cohorts only)
    rolling_avg = cohort_df.T.rolling(window=6, min_periods=1).mean().T.iloc[:, -1]
    # Actually: on each day, take the mean of the last 6 cohorts that HAVE data for that day
    # Simpler: mean across all columns for each row (each column is a cohort, NaN if not trading)
    portfolio = cohort_df.mean(axis=1)  # mean of active cohorts per day

    avg_conv_rate = float(np.mean(total_diag["conversion_rate_list"])) if total_diag["conversion_rate_list"] else 0.0
    agg_diag = {
        "n_cohorts": len(cohort_series),
        "n_open_total": total_diag["n_open_total"],
        "n_convergences": total_diag["n_convergences"],
        "avg_conversion_rate": avg_conv_rate,
    }
    return portfolio.dropna(), agg_diag


# ─── Statistics helpers ───────────────────────────────────────────────────────

def _sharpe(r: pd.Series) -> float:
    if r.std() < 1e-10 or len(r) < 10:
        return 0.0
    return float(r.mean() / r.std() * np.sqrt(252))

def _maxdd(r: pd.Series) -> float:
    cum = (1 + r).cumprod()
    return float(((cum - cum.cummax()) / cum.cummax()).min())

def _hac_alpha(y: pd.Series, X_df: pd.DataFrame) -> dict:
    aligned = pd.concat([y, X_df], axis=1).dropna()
    if len(aligned) < 50:
        return {c: np.nan for c in ["alpha", "t_alpha"] + list(X_df.columns)}
    y_arr = aligned.iloc[:, 0].values
    X_arr = sm.add_constant(aligned.iloc[:, 1:].values)
    m = sm.OLS(y_arr, X_arr).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    result = {"alpha": float(m.params[0]) * 252, "t_alpha": float(m.tvalues[0]),
              "r2": float(m.rsquared) * 100}
    for i, col in enumerate(X_df.columns):
        result[f"b_{col}"] = float(m.params[i + 1])
        result[f"t_{col}"] = float(m.tvalues[i + 1])
    return result

def _amtp(sharpe_ann: float, n_obs: int, n_tests: int) -> dict:
    eg = 0.5772156649
    sr_d = sharpe_ann / np.sqrt(252)
    z = ((1 - eg) * stats.norm.ppf(1 - 1/n_tests)
         + eg     * stats.norm.ppf(1 - 1/(n_tests * np.e)))
    sr_star = z / np.sqrt(n_obs - 1)
    pval = float(stats.norm.sf((sr_d - sr_star) / np.sqrt(1/(n_obs - 1))))
    return {"amtp_pvalue": round(pval, 4), "amtp_pass": bool(pval < 0.10),
            "amtp_research_pass": bool(pval < 0.20)}

def _bootstrap_monthly_ev(daily_ret: pd.Series, n: int = BOOTSTRAP_N, seed: int = 42) -> dict:
    monthly = daily_ret.resample("ME").apply(lambda x: (1 + x).prod() - 1).dropna()
    if len(monthly) < 12:
        return {"ev_pct": np.nan, "ci_lo": np.nan, "ci_hi": np.nan, "p_neg": np.nan}
    rng   = np.random.default_rng(seed)
    r     = monthly.values
    means = np.array([rng.choice(r, size=len(r), replace=True).mean() for _ in range(n)])
    return {
        "ev_pct": round(float(means.mean()) * 100, 4),
        "ci_lo":  round(float(np.percentile(means, 2.5)) * 100, 4),
        "ci_hi":  round(float(np.percentile(means, 97.5)) * 100, 4),
        "p_neg":  round(float(np.mean(means <= 0)), 4),
    }


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    sep = "=" * 72
    print(sep)
    print("Pairs Trading — Distance Method (Gatev 2006 / Zhu 2024 replication)")
    print(sep)

    # ── 1. Data ───────────────────────────────────────────────────────────────
    print("\nFetching prices ...")
    close_df, vol_df = load_prices(SP100_2015)
    rf_raw = load_risk_free()
    factors = load_ff_factors()

    n_stocks = close_df.shape[1]
    n_pairs_pool = n_stocks * (n_stocks - 1) // 2
    print(f"  Universe: {n_stocks} stocks  (~{n_pairs_pool:,} candidate pairs per formation)")
    print(f"  Price history: {close_df.index[0].date()} → {close_df.index[-1].date()}")

    if n_stocks < 50:
        print("\n  STOP: < 50 stocks loaded. Insufficient for pairs selection.")
        return

    def rf_for(idx):
        if rf_raw.empty:
            return pd.Series(0.0, index=idx)
        return rf_raw.reindex(idx, method="ffill").fillna(0.0)

    # ── 2. Run three variants ─────────────────────────────────────────────────
    print("\nRunning 3 variants (T20, T100, L75) — this takes ~5-10 minutes ...")
    variant_results: dict[str, tuple[pd.Series, dict]] = {}

    for label, M, liq in [("T20", 20, False), ("T100", 100, False), ("L75", 20, True)]:
        print(f"  [{label}] M={M}, liq_filter={liq} ...")
        ret_series, diag = run_strategy(close_df, vol_df, M=M, liq_filter=liq, label=label)
        if len(ret_series) == 0:
            print(f"  [{label}]: empty return series — skipped")
            continue
        variant_results[label] = (ret_series, diag)
        sh = _sharpe(ret_series)
        dd = _maxdd(ret_series) * 100
        ann = float(ret_series.mean()) * 252 * 100
        print(f"    Sharpe={sh:+.3f}  Ann={ann:+.1f}%  MaxDD={dd:+.1f}%  Cohorts={diag['n_cohorts']}  Pairs opened={diag['n_open_total']:,}")

    if not variant_results:
        print("\n  No variants produced results.")
        return

    # Choose best variant for detailed analysis: T100 (more diversification)
    best_label = "T100" if "T100" in variant_results else list(variant_results.keys())[0]
    best_ret, best_diag = variant_results[best_label]
    rf_best = rf_for(best_ret.index)
    best_exc = best_ret - rf_best

    # STOP check: Sharpe > 2 + high skewness — verify
    best_sh = _sharpe(best_exc)
    best_skew = float(best_exc.skew())
    if best_sh > 2.0 and best_skew > 5.0:
        print(f"\n  [SUSPICIOUS CHECK] Sharpe={best_sh:.2f} > 2 AND skew={best_skew:.2f} > 5")
        worst10 = best_ret.nsmallest(10)
        best10  = best_ret.nlargest(10)
        print(f"  Worst 10 days:\n{worst10.round(4)}")
        print(f"  Best 10 days:\n{best10.round(4)}")
        print("  → Cross-check against Zhu 2024: T20 skewness 7.33, best month +24.3%")

    # ── 3. Monthly stats comparison with Zhu ─────────────────────────────────
    print("\n" + "-" * 72)
    print("PERFORMANCE METRICS (all 3 variants)")
    print("-" * 72)

    ZHU_T20  = {"monthly_ret": 0.461, "t_stat": 3.65, "sharpe": 0.814,
                "worst_month": -6.70, "best_month": 24.3, "skew": 7.33}
    ZHU_T100 = {"monthly_ret": 0.426, "t_stat": 4.62, "sharpe": 1.177,
                "worst_month": -3.63, "best_month": 7.43, "skew": 1.90}

    print(f"  {'Metric':28s}  {'T20':>8s}  {'T100':>8s}  {'L75':>8s}  {'Zhu T20':>9s}  {'Zhu T100':>9s}")
    print(f"  {'-'*28}  {'-'*8}  {'-'*8}  {'-'*8}  {'-'*9}  {'-'*9}")

    for var_label, zhu_ref in [("T20", ZHU_T20), ("T100", ZHU_T100), ("L75", None)]:
        if var_label not in variant_results:
            continue
        vret, _ = variant_results[var_label]
        vexc = vret - rf_for(vret.index)
        monthly = vret.resample("ME").apply(lambda x: (1 + x).prod() - 1).dropna() * 100
        rows = {
            "Mean monthly ret (%)":  monthly.mean(),
            "Monthly t-stat":        monthly.mean() / monthly.std() * np.sqrt(len(monthly)),
            "Sharpe (HAC, daily)":   _sharpe(vexc),
            "Ann return (%)":        float(vexc.mean()) * 252 * 100,
            "MaxDD (%)":             _maxdd(vret) * 100,
            "Worst month (%)":       monthly.min(),
            "Best month (%)":        monthly.max(),
            "Skewness (monthly)":    monthly.skew(),
            "Time in market (%)":    float((vret.abs() > 1e-8).mean()) * 100,
        }
        for mname, val in rows.items():
            zval = zhu_ref.get(mname.split("(")[0].strip().lower().replace(" ", "_"), None) if zhu_ref else None
            if var_label == "T20":
                print(f"  {mname:28s}  {val:+8.3f}", end="")
            elif var_label == "T100":
                print(f"  {val:+8.3f}", end="")
            else:
                print(f"  {val:+8.3f}", end="")
        # Just print summary rows
    print()

    # Detailed table
    def var_stats(label_):
        if label_ not in variant_results:
            return {}
        vret, _ = variant_results[label_]
        vexc = vret - rf_for(vret.index)
        monthly = vret.resample("ME").apply(lambda x: (1 + x).prod() - 1).dropna() * 100
        return {
            "mean_monthly": round(monthly.mean(), 3),
            "t_monthly":    round(monthly.mean() / max(monthly.std() * np.sqrt(len(monthly)) ** -1, 1e-8), 3),
            "sharpe":       round(_sharpe(vexc), 3),
            "ann_ret":      round(float(vexc.mean()) * 252 * 100, 2),
            "maxdd":        round(_maxdd(vret) * 100, 2),
            "worst_month":  round(monthly.min(), 2),
            "best_month":   round(monthly.max(), 2),
            "skew":         round(monthly.skew(), 2),
            "time_in_mkt":  round(float((vret.abs() > 1e-8).mean()) * 100, 1),
            "n_months":     len(monthly),
        }

    stats_all = {lbl: var_stats(lbl) for lbl in ["T20", "T100", "L75"]}

    # ── 4. OOS walk-forward (by year) ─────────────────────────────────────────
    print("\n" + "-" * 72)
    print("OOS WALK-FORWARD BY YEAR (best variant)")
    print("-" * 72)

    wf_years = range(2016, 2025)
    wf_rows = []
    for yr in wf_years:
        oos = best_exc.loc[f"{yr}-01-01":f"{yr}-12-31"]
        if len(oos) < 20:
            wf_rows.append({"year": yr, "n_days": 0, "sharpe": np.nan,
                            "monthly_ret": np.nan, "maxdd": np.nan})
            continue
        monthly_oos = oos.resample("ME").apply(lambda x: (1 + x).prod() - 1).dropna()
        wf_rows.append({
            "year":       yr,
            "n_days":     len(oos),
            "sharpe":     round(_sharpe(oos), 3),
            "monthly_ret": round(float(monthly_oos.mean()) * 100, 3) if len(monthly_oos) > 0 else np.nan,
            "maxdd":      round(_maxdd(oos) * 100, 2),
        })
        sh = wf_rows[-1]["sharpe"]
        dd = wf_rows[-1]["maxdd"]
        mr = wf_rows[-1]["monthly_ret"]
        print(f"  {yr}  Sh={sh:+.3f}  Monthly_ret={mr:+.3f}%  MaxDD={dd:+.1f}%  n={len(oos)}")

    valid_wf = [r for r in wf_rows if not np.isnan(r["sharpe"])]
    pct_pos = float(sum(1 for r in valid_wf if r["sharpe"] > 0)) / max(1, len(valid_wf)) * 100
    med_sh = float(np.median([r["sharpe"] for r in valid_wf])) if valid_wf else np.nan
    print(f"\n  % positive years: {pct_pos:.0f}%  |  Median Sharpe: {med_sh:+.3f}")

    # ── 5. Alpha decomposition ────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("ALPHA DECOMPOSITION (best variant)")
    print("-" * 72)

    # Fetch SPY returns
    spy_ret = pd.Series(dtype=float)
    try:
        spy_df = get_cached_or_fetch("SPY", DATA_START, DATA_END, interval="1d")
        spy_df.index = pd.to_datetime(spy_df.index).tz_localize(None)
        spy_ret = spy_df["close"].pct_change().dropna()
    except Exception:
        pass

    spy_exc = (spy_ret - rf_for(spy_ret.index)).rename("SPY") if not spy_ret.empty else pd.Series(dtype=float)

    # SPY regression
    if not spy_exc.empty:
        a_spy = _hac_alpha(best_exc, pd.DataFrame({"SPY": spy_exc}))
        print(f"  vs SPY B&H:  alpha={a_spy['alpha']:+.2f}%/yr  t_HAC={a_spy['t_alpha']:+.3f}  "
              f"beta={a_spy.get('b_SPY', 0):+.4f}  R²={a_spy.get('r2', 0):.1f}%")
    else:
        a_spy = {"alpha": np.nan, "t_alpha": np.nan}

    # FF factors regression
    ff_result: dict = {}
    if not factors.empty:
        ff_avail = factors.reindex(best_exc.index, method="ffill").dropna()
        factor_cols = [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"] if c in ff_avail.columns]
        if factor_cols and len(ff_avail) > 100:
            ff_result = _hac_alpha(best_exc, ff_avail[factor_cols])
            print(f"  vs FF5+Mom:  alpha={ff_result.get('alpha', np.nan):+.2f}%/yr  "
                  f"t_HAC={ff_result.get('t_alpha', np.nan):+.3f}  R²={ff_result.get('r2', np.nan):.1f}%")
            if "t_Mom" in ff_result:
                print(f"  → MOM coefficient: {ff_result.get('b_Mom', np.nan):+.4f}  "
                      f"t={ff_result.get('t_Mom', np.nan):+.3f}  "
                      f"[Zhu expects negative ~-0.09, confirms contrarian impl]")
    else:
        print("  FF factors unavailable — SPY-only regression used")

    # ── 6. Correlation to existing book ───────────────────────────────────────
    print("\n" + "-" * 72)
    print("CORRELATION TO LIVE BOOK")
    print("-" * 72)

    def log_ret(tkr):
        try:
            df = get_cached_or_fetch(tkr, DATA_START, DATA_END, interval="1d")
            df.index = pd.to_datetime(df.index).tz_localize(None)
            return df["close"].pct_change().dropna()
        except Exception:
            return pd.Series(dtype=float)

    corr_assets = {
        "BTC-USD": log_ret("BTC-USD"),
        "ETH-USD": log_ret("ETH-USD"),
        "SPY":     spy_ret,
        "TLT":     log_ret("TLT"),
    }
    corr_results = {}
    for name, s in corr_assets.items():
        aligned = pd.concat([best_ret, s], axis=1).dropna()
        c = round(float(aligned.corr().iloc[0, 1]), 3) if len(aligned) >= 50 else np.nan
        corr_results[name] = c
        print(f"  {name:10s}: {c}")

    # ── 7. Bootstrap EV & AMTP ────────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("BOOTSTRAP EV (monthly) & AMTP")
    print("-" * 72)

    bev = _bootstrap_monthly_ev(best_exc.dropna())
    amtp = _amtp(_sharpe(best_exc.dropna()), len(best_exc.dropna()), N_TESTS_END)
    print(f"  Monthly EV: {bev['ev_pct']:+.4f}%  CI=[{bev['ci_lo']:+.4f}%, {bev['ci_hi']:+.4f}%]  P(EV≤0)={bev['p_neg']:.4f}")
    print(f"  AMTP: n_tests={N_TESTS_END}  p={amtp['amtp_pvalue']}  "
          f"{'PASS (research)' if amtp['amtp_research_pass'] else 'FAIL (research)'}  "
          f"{'PASS (propfirm)' if amtp['amtp_pass'] else 'FAIL (propfirm)'}")

    # ── 8. Two-tier gate decision ─────────────────────────────────────────────
    print("\n" + "-" * 72)
    print("TWO-TIER GATE DECISION (best variant)")
    print("-" * 72)

    best_monthly = best_exc.resample("ME").apply(lambda x: (1 + x).prod() - 1).dropna()
    best_worst_month = float(best_monthly.min()) * 100
    btc_corr = corr_results.get("BTC-USD", np.nan)
    alpha_t_spy = a_spy.get("t_alpha", np.nan)

    research_gates = [
        ("Sharpe HAC",             "> 0.7",  best_sh,           best_sh > 0.7),
        ("MaxDD",                  "< -25%", _maxdd(best_ret)*100, _maxdd(best_ret)*100 > -25.0),
        ("Walk-forward % positive","≥ 50%",  pct_pos,           pct_pos >= 50.0),
        ("Alpha t_HAC vs SPY",     "> 1.5",  alpha_t_spy,       (not np.isnan(alpha_t_spy)) and alpha_t_spy > 1.5),
        ("AMTP p-value",           "< 0.20", amtp["amtp_pvalue"], amtp["amtp_research_pass"]),
        ("Corr to BTC",            "< 0.5",  btc_corr,          (not np.isnan(btc_corr)) and abs(btc_corr) < 0.5),
    ]
    propfirm_gates = [
        ("Sharpe HAC",             "> 1.0",  best_sh,           best_sh > 1.0),
        ("MaxDD",                  "< -10%", _maxdd(best_ret)*100, _maxdd(best_ret)*100 > -10.0),
        ("Worst month",            "> -5%",  best_worst_month,  best_worst_month > -5.0),
        ("Walk-forward % positive","≥ 60%",  pct_pos,           pct_pos >= 60.0),
        ("Alpha t_HAC vs SPY",     "> 2.0",  alpha_t_spy,       (not np.isnan(alpha_t_spy)) and alpha_t_spy > 2.0),
        ("AMTP p-value",           "< 0.10", amtp["amtp_pvalue"], amtp["amtp_pass"]),
        ("Corr to BTC",            "< 0.3",  btc_corr,          (not np.isnan(btc_corr)) and abs(btc_corr) < 0.3),
    ]

    print(f"\n  {'Gate':28s}  {'Threshold':10s}  {'Value':8s}  RESEARCH  PROPFIRM")
    for (rg, rth, rv, rp), (pg, pth, pv, pp) in zip(research_gates, propfirm_gates):
        v_str = f"{rv:+.3f}" if isinstance(rv, float) and not np.isnan(rv) else str(rv)
        print(f"  {rg:28s}  R{rth:>8s}  {v_str:8s}  "
              f"{'PASS' if rp else 'FAIL':8s}  {'PASS' if pp else 'FAIL'}")

    n_research_pass  = sum(1 for *_, p in research_gates if p)
    n_propfirm_pass  = sum(1 for *_, p in propfirm_gates if p)
    print(f"\n  Research gates passed: {n_research_pass}/6")
    print(f"  Propfirm gates passed: {n_propfirm_pass}/7")

    research_pass = (n_research_pass >= 4)
    propfirm_pass = (n_propfirm_pass >= 6)

    if   propfirm_pass:  verdict = "PROPFIRM_PASS — walk-forward + sandbox"
    elif research_pass:  verdict = "RESEARCH_PASS — paper trading + portfolio combination"
    else:                verdict = "FAIL — does not meet research grade"

    print(f"\n  VERDICT: {verdict}")

    # Replication match vs Zhu
    t20_stats = stats_all.get("T20", {})
    t100_stats = stats_all.get("T100", {})
    zhu_match_t20  = abs(t20_stats.get("mean_monthly", 0) - ZHU_T20["monthly_ret"]) / ZHU_T20["monthly_ret"] < 0.2
    zhu_match_t100 = abs(t100_stats.get("mean_monthly", 0) - ZHU_T100["monthly_ret"]) / ZHU_T100["monthly_ret"] < 0.2
    print(f"\n  Zhu 2024 replication match:")
    print(f"    T20  monthly ret within ±20% of Zhu: {'YES' if zhu_match_t20 else 'NO'} "
          f"(ours={t20_stats.get('mean_monthly','?'):.3f}% vs Zhu={ZHU_T20['monthly_ret']}%)")
    print(f"    T100 monthly ret within ±20% of Zhu: {'YES' if zhu_match_t100 else 'NO'} "
          f"(ours={t100_stats.get('mean_monthly','?'):.3f}% vs Zhu={ZHU_T100['monthly_ret']}%)")
    print(f"    Skewness pattern matches (right-tailed): "
          f"{'YES' if t20_stats.get('skew', 0) > 1 else 'NO'} (skew={t20_stats.get('skew','?'):.2f})")

    # ── 9. Save summary ───────────────────────────────────────────────────────
    md_lines = [
        "# Result Summary: Pairs Trading Distance Method (Gatev 2006 / Zhu 2024)",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "## 1. Headline verdict",
        f"> Two-tier: **RESEARCH_PASS: {'YES' if research_pass else 'NO'}** | "
        f"**PROPFIRM_PASS: {'YES' if propfirm_pass else 'NO'}**",
        f"> {verdict}",
        "",
        "## 2. Data",
        f"- Universe: {n_stocks} stocks (SP100 proxy ~2015, survivorship bias present)",
        f"- Period: {close_df.index[0].date()} → {close_df.index[-1].date()}",
        f"- Candidate pairs per formation: ~{n_pairs_pool:,}",
        "- Overlapping strategies: 6 concurrent monthly cohorts",
        "",
        "## 3. Performance comparison (3 variants)",
        "",
        "| Metric | T20 | T100 | L75 | Zhu 2024 T20 | Zhu 2024 T100 |",
        "|--------|-----|------|-----|--------------|---------------|",
    ]
    for metric in ["mean_monthly", "sharpe", "ann_ret", "maxdd", "worst_month",
                   "best_month", "skew", "time_in_mkt"]:
        row = f"| {metric} "
        for lbl in ["T20", "T100", "L75"]:
            v = stats_all.get(lbl, {}).get(metric, np.nan)
            row += f"| {v:+.3f} " if not np.isnan(v) else "| n/a "
        row += f"| {ZHU_T20.get(metric.replace('mean_monthly','monthly_ret'), 'n/a')} "
        row += f"| {ZHU_T100.get(metric.replace('mean_monthly','monthly_ret'), 'n/a')} |"
        md_lines.append(row)

    md_lines += [
        "",
        "## 4. Replication match vs Zhu 2024",
        f"- T20 monthly ret within ±20%: {'YES' if zhu_match_t20 else 'NO'} "
        f"(ours={t20_stats.get('mean_monthly','?'):.3f}% vs Zhu={ZHU_T20['monthly_ret']}%)",
        f"- T100 monthly ret within ±20%: {'YES' if zhu_match_t100 else 'NO'} "
        f"(ours={t100_stats.get('mean_monthly','?'):.3f}% vs Zhu={ZHU_T100['monthly_ret']}%)",
        f"- Skewness pattern (right-tailed): "
        f"{'YES' if t20_stats.get('skew', 0) > 1 else 'NO'} (skew={t20_stats.get('skew', 'n/a')})",
        "",
        "## 5. Factor decomposition (best variant)",
        "",
        "| Factor | Coefficient | t_HAC |",
        "|--------|-------------|-------|",
        f"| α (alpha, ann %) | {ff_result.get('alpha', a_spy.get('alpha', np.nan)):+.2f} "
        f"| {ff_result.get('t_alpha', a_spy.get('t_alpha', np.nan)):+.3f} |",
    ]
    for fac in ["Mkt-RF", "SMB", "HML", "RMW", "CMA", "Mom"]:
        bk = f"b_{fac}"
        tk = f"t_{fac}"
        if bk in ff_result:
            md_lines.append(f"| {fac} | {ff_result[bk]:+.4f} | {ff_result[tk]:+.3f} |")
    md_lines += [
        "",
        "> Critical: negative MOM coefficient would confirm contrarian implementation.",
        f"  MOM coeff = {ff_result.get('b_Mom', 'n/a')} — "
        f"{'matches Zhu expectation' if ff_result.get('b_Mom', 0) < 0 else 'deviates from Zhu'}",
        "",
        "## 6. Walk-forward OOS by year (best variant)",
        "",
        "| Year | N days | Sharpe | Monthly ret% | MaxDD% |",
        "|------|--------|--------|--------------|--------|",
    ]
    for r in wf_rows:
        sh = f"{r['sharpe']:+.3f}" if not np.isnan(r["sharpe"]) else "n/a"
        mr = f"{r['monthly_ret']:+.3f}%" if not np.isnan(r["monthly_ret"]) else "n/a"
        dd = f"{r['maxdd']:+.1f}%" if not np.isnan(r["maxdd"]) else "n/a"
        md_lines.append(f"| {r['year']} | {r['n_days']} | {sh} | {mr} | {dd} |")
    md_lines += [
        f"| **% positive** | — | **{pct_pos:.0f}%** | — | — |",
        f"| **Median Sharpe** | — | **{med_sh:+.3f}** | — | — |",
        "",
        "## 7. Correlation to live book",
        "",
        "| Asset | Correlation |",
        "|-------|-------------|",
    ]
    for name, c in corr_results.items():
        md_lines.append(f"| {name} | {c} |")

    md_lines += [
        "",
        "## 8. Two-tier gate decision",
        "",
        "| Gate | Threshold | Value | RESEARCH | PROPFIRM |",
        "|------|-----------|-------|----------|----------|",
    ]
    for (rg, rth, rv, rp), (_, pth, _, pp) in zip(research_gates, propfirm_gates):
        v_str = f"{rv:+.3f}" if isinstance(rv, float) and not np.isnan(rv) else str(rv)
        md_lines.append(f"| {rg} | R{rth} / P{pth} | {v_str} | {'PASS' if rp else 'FAIL'} | {'PASS' if pp else 'FAIL'} |")

    md_lines += [
        "",
        "## 9. Bootstrap EV (monthly returns)",
        "",
        f"- EV/month: {bev['ev_pct']:+.4f}%  [95% CI {bev['ci_lo']:+.4f}%, {bev['ci_hi']:+.4f}%]",
        f"- P(EV ≤ 0): {bev['p_neg']:.4f}",
        f"- AMTP p={amtp['amtp_pvalue']}  (research p<0.20: {'PASS' if amtp['amtp_research_pass'] else 'FAIL'}, "
        f"propfirm p<0.10: {'PASS' if amtp['amtp_pass'] else 'FAIL'})",
        "",
        "## 10. n_tests counter",
        f"- Start: {N_TESTS_START}",
        "- T20 variant: +1",
        "- T100 variant: +1",
        "- L75 variant: +1",
        f"- **End: {N_TESTS_END}**",
        "",
        "## 11. Recommendation",
        f"> {verdict}",
    ]

    summary_path = _SCRIPT_DIR / "pairs_distance_gatev_summary.md"
    with open(summary_path, "w") as fh:
        fh.write("\n".join(md_lines))

    print(sep)
    print(f"\nSaved → {summary_path}")


if __name__ == "__main__":
    main()
