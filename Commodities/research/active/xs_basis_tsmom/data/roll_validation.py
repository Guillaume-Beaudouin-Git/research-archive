"""
roll_validation.py — Detect and classify roll artifacts in continuous futures.

yfinance =F continuous contracts are NOT back-adjusted; they splice prices at
roll with no adjustment. This creates observable price gaps at roll dates that
are used as the basis proxy for S_BASIS. This module:

  1. Detects large daily returns (|r| > threshold_sigma × rolling_std)
  2. Classifies as "roll artifact" vs "genuine market move":
     - Roll: affects a single commodity; the next-day return often partially
       reverts (market level unchanged, just contract switch)
     - Market event: correlated spike across multiple commodities; no reversion
  3. Reports per-ticker statistics for universe_stats.csv

Output contract:
  detect_roll_artifacts(close_df, threshold_sigma=5.0)
    → pd.DataFrame with columns: date, ticker, log_ret, rolling_std,
      zscore, is_roll_artifact, basis_proxy_annualized

  validate_universe(close_df)
    → pd.DataFrame indexed by ticker with columns:
      n_obs, first_date, last_date, n_jumps_5sigma,
      n_suspected_rolls, n_market_events, basis_coverage_pct
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

VOL_WINDOW       = 63    # rolling std window for z-score computation
JUMP_SIGMA       = 5.0   # threshold for "large" return
ROLL_SIGMA       = 3.0   # lower threshold for roll classification
REVERSION_WINDOW = 2     # days after jump to check for partial reversion
REVERSION_FRAC   = 0.20  # fraction of jump that must reverse for "roll" classification
CROSS_CORR_N     = 3     # if >= N other tickers also jump same day: market event


def detect_roll_artifacts(
    close_df:         pd.DataFrame,
    threshold_sigma:  float = JUMP_SIGMA,
    vol_window:       int   = VOL_WINDOW,
) -> pd.DataFrame:
    """
    Flag large daily log-return observations as suspected roll artifacts.

    Parameters
    ----------
    close_df : pd.DataFrame with (ticker, 'close') MultiIndex columns OR
               simple ticker columns (ticker → close prices)
    threshold_sigma : z-score threshold for flagging

    Returns
    -------
    pd.DataFrame with columns:
        date, ticker, log_ret, rolling_std, zscore,
        next2d_cumret, is_roll_artifact, basis_proxy_annualized
    """
    # Normalize to simple ticker → price DataFrame
    if isinstance(close_df.columns, pd.MultiIndex):
        close = close_df.xs("close", axis=1, level=1) if "close" in close_df.columns.get_level_values(1) else close_df.iloc[:, ::5]
    else:
        close = close_df

    records = []

    # Count how many tickers have a large jump on each date (for market-event filter)
    log_ret_all = np.log(close).diff()
    roll_std    = log_ret_all.rolling(vol_window, min_periods=vol_window // 2).std()
    zscore_all  = (log_ret_all / roll_std.replace(0, np.nan)).abs()

    # Date → number of tickers with |z| > ROLL_SIGMA
    dates_with_jumps: pd.Series = (zscore_all > ROLL_SIGMA).sum(axis=1)

    for ticker in close.columns:
        prices  = close[ticker].dropna()
        if len(prices) < vol_window * 2:
            continue

        lr      = np.log(prices).diff()
        r_std   = lr.rolling(vol_window, min_periods=vol_window // 2).std()
        z       = (lr / r_std.replace(0, np.nan)).abs()

        flagged = z[z >= threshold_sigma].index

        for dt in flagged:
            pos       = lr.index.get_loc(dt)
            jump_ret  = float(lr.iloc[pos])

            # Next-2d cumulative return (partial reversion check)
            end_pos   = min(pos + REVERSION_WINDOW + 1, len(lr))
            next_cum  = lr.iloc[pos + 1: end_pos].sum() if pos + 1 < len(lr) else np.nan

            # Classification heuristics
            n_comovers = int(dates_with_jumps.get(dt, 0))

            # Roll artifact if: few co-movers AND subsequent reversion > fraction of jump
            is_reversion = (
                not np.isnan(next_cum)
                and abs(jump_ret) > 0
                and np.sign(next_cum) != np.sign(jump_ret)
                and abs(next_cum) > abs(jump_ret) * REVERSION_FRAC
            )
            is_roll = (n_comovers < CROSS_CORR_N) and is_reversion

            # Annualized basis proxy from roll gap
            # At roll: jump_ret = log(F_far / F_near)
            # basis_proxy = -jump_ret × 12  (positive in backwardation)
            basis_proxy = -jump_ret * 12.0

            records.append({
                "date":                   dt,
                "ticker":                 ticker,
                "log_ret":                round(jump_ret, 6),
                "rolling_std":            round(float(r_std.get(dt, np.nan)), 6),
                "zscore":                 round(float(z.get(dt, np.nan)), 2),
                "n_comovers":             n_comovers,
                "next2d_cumret":          round(float(next_cum) if not np.isnan(next_cum) else np.nan, 6),
                "is_roll_artifact":       is_roll,
                "basis_proxy_annualized": round(basis_proxy, 4),
            })

    if not records:
        return pd.DataFrame(columns=[
            "date", "ticker", "log_ret", "rolling_std", "zscore",
            "n_comovers", "next2d_cumret", "is_roll_artifact", "basis_proxy_annualized"
        ])

    return pd.DataFrame(records).sort_values(["ticker", "date"]).reset_index(drop=True)


def validate_universe(
    close_df:        pd.DataFrame,
    volume_df:       pd.DataFrame | None = None,
    adv_threshold:   int   = 5_000,
    threshold_sigma: float = JUMP_SIGMA,
    vol_window:      int   = VOL_WINDOW,
) -> pd.DataFrame:
    """
    Per-ticker data quality summary for universe_stats.csv.

    Returns
    -------
    pd.DataFrame indexed by ticker with columns:
        n_obs, first_date, last_date,
        n_jumps_5sigma, n_suspected_rolls, n_market_events,
        median_adv, adv_filter_pct,   # fraction of months above ADV threshold
        basis_coverage_pct             # fraction of months with basis available
    """
    # Normalize close prices
    if isinstance(close_df.columns, pd.MultiIndex):
        level1 = close_df.columns.get_level_values(1)
        if "close" in level1:
            close = close_df.xs("close", axis=1, level=1)
        else:
            close = close_df.iloc[:, ::5]
    else:
        close = close_df

    # Normalize volume
    if volume_df is not None and isinstance(volume_df.columns, pd.MultiIndex):
        level1v = volume_df.columns.get_level_values(1)
        if "volume" in level1v:
            volume = volume_df.xs("volume", axis=1, level=1)
        else:
            volume = None
    elif volume_df is not None:
        volume = volume_df
    else:
        volume = None

    # Run roll detection
    roll_df = detect_roll_artifacts(close, threshold_sigma, vol_window)

    rows = []
    for ticker in close.columns:
        prices   = close[ticker].dropna()
        n_obs    = len(prices)

        if n_obs == 0:
            rows.append({"ticker": ticker, "n_obs": 0})
            continue

        # Jump stats
        tdf      = roll_df[roll_df["ticker"] == ticker]
        n_jumps  = len(tdf)
        n_rolls  = int(tdf["is_roll_artifact"].sum())
        n_mkt    = n_jumps - n_rolls

        # ADV stats (if volume available)
        if volume is not None and ticker in volume.columns:
            vol_s    = volume[ticker].dropna()
            adv_60   = vol_s.rolling(60, min_periods=30).mean()
            # Monthly pass rate
            monthly_adv = adv_60.resample("ME").last()
            adv_pass    = (monthly_adv >= adv_threshold).mean()
            median_adv  = float(vol_s.median())
        else:
            adv_pass   = np.nan
            median_adv = np.nan

        # Basis coverage: months where a roll artifact was detected in prior month
        if n_rolls > 0:
            roll_dates  = tdf.loc[tdf["is_roll_artifact"], "date"]
            n_months    = len(pd.date_range(prices.index[0], prices.index[-1], freq="ME"))
            basis_cov   = min(1.0, len(roll_dates) / max(n_months, 1))
        else:
            basis_cov   = 0.0

        rows.append({
            "ticker":           ticker,
            "n_obs":            n_obs,
            "first_date":       str(prices.index[0].date()),
            "last_date":        str(prices.index[-1].date()),
            "n_jumps_5sigma":   n_jumps,
            "n_suspected_rolls":n_rolls,
            "n_market_events":  n_mkt,
            "median_adv":       round(median_adv),
            "adv_filter_pct":   round(float(adv_pass), 3) if not np.isnan(adv_pass) else np.nan,
            "basis_coverage_pct": round(basis_cov, 3),
        })

    return pd.DataFrame(rows).set_index("ticker")
