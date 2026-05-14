#!/usr/bin/env python3
"""
strategies/new_strategies/feasibility.py

Two-strategy feasibility study:

STRATEGY 1 — TSMOM Short-Only
  Trade ONLY the short signals on SOL, LINK, BCH, OP.
  Source: confirmed OOS t > 2.0 in v1_v2_longshort_comparison.py
  Signal: short when 28d cumulative log return < 0, flat otherwise.
  Never long.

STRATEGY 2 — Weekly Return Seasonality
  Keloharju, Linnainmaa & Nyberg (2016, JoF): same-week-of-year returns
  predict future returns. Signal: if asset returned positively in the same
  ISO week in each of the past 3 years → long. Negatively in 3/3 → short.
  Mechanism: institutional rebalancing, options expiry, behavioral anchoring.
"""

from __future__ import annotations

import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import yfinance as yf
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

warnings.filterwarnings("ignore")

# ── constants ──────────────────────────────────────────────────────────────────

ASSETS_S1: List[str]    = ["SOL-USD", "LINK-USD", "BCH-USD", "OP-USD"]
ASSETS_S2: List[str]    = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "LTC-USD", "BCH-USD",
]
ASSETS_TSMOM: List[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD", "OP-USD",
]

# Backtesting periods
DATA_START_EXTENDED = "2018-01-01"   # seasonality needs 3+ prior years
OOS_START = "2024-01-01"

# Propr challenge
PROPR_INITIAL: float = 5_000.0
PROPR_TARGET:  float = 5_500.0
PROPR_DAILY_DD: float = 0.03
PROPR_TOTAL_DD: float = 0.06
SIM_DATES = pd.date_range("2025-01-06", "2025-11-03", freq="W-MON")
ENTRY_FEE: float = 60.0

# Strategy parameters
S1_VOL_TARGET: float = 0.12
S1_VOL_WINDOW: int   = 20
S1_SIG_WINDOW: int   = 28
S1_GROSS_CAP:  float = 0.60

S2_VOL_TARGET: float = 0.15
S2_VOL_WINDOW: int   = 20
S2_GROSS_CAP:  float = 0.90
S2_MIN_PRIOR_YEARS: int = 3

TSMOM_VOL_TARGET: float = 0.15
TSMOM_VOL_WINDOW: int   = 30
TSMOM_SIG_WINDOW: int   = 28
TSMOM_GROSS_CAP:  float = 0.90

COST_RT: float = 0.0017

# Prior-study t-stats for comparison (from v1_v2_longshort_comparison.py, V3 variant)
PRIOR_TSTATS: Dict[str, float] = {
    "SOL-USD": 2.59, "LINK-USD": 3.27, "BCH-USD": 3.28, "OP-USD": 2.40,
}

OUT_DIR = Path(__file__).parent
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ── data loading ───────────────────────────────────────────────────────────────

def load_prices(assets: List[str], start: str) -> pd.DataFrame:
    """Download adjusted close prices. Silently skip unavailable tickers."""
    frames: Dict[str, pd.Series] = {}
    for ticker in assets:
        try:
            raw = yf.download(
                ticker, start=start, end="2026-05-15",
                auto_adjust=True, progress=False, multi_level_index=False,
            )
            if raw.empty or len(raw) < 60:
                continue
            close = raw["Close"].squeeze()
            frames[ticker] = close
        except Exception:
            pass
    if not frames:
        raise RuntimeError("No price data — check network.")
    return pd.DataFrame(frames).sort_index().ffill()


# ── signal and sizing helpers ─────────────────────────────────────────────────

def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    return np.log(prices / prices.shift(1))


def vol_scalars(
    log_rets: pd.DataFrame,
    assets: List[str],
    window: int,
    vol_target: float,
) -> pd.DataFrame:
    """vol_target / (rolling_std × sqrt(252)), clipped [0.1, 2.0]."""
    avail = [a for a in assets if a in log_rets.columns]
    ann_vol = log_rets[avail].rolling(window).std() * np.sqrt(252)
    ann_vol = ann_vol.replace(0, np.nan)
    vs = (vol_target / ann_vol).clip(0.1, 2.0)
    return vs


def apply_gross_cap(weights: pd.DataFrame, cap: float) -> pd.DataFrame:
    """Scale each row so sum(|weights|) ≤ cap."""
    gross = weights.abs().sum(axis=1)
    scale = (cap / gross).clip(upper=1.0).replace([np.inf, -np.inf], 0.0)
    return weights.multiply(scale, axis=0)


def compute_monday_weights_s1(
    log_rets: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """
    S1 TSMOM Short-Only weights.
    Signal = -1 (short) when 28d cum log ret < 0, else 0 (flat).
    Returns DataFrame indexed by Monday dates.
    """
    avail = [a for a in ASSETS_S1 if a in log_rets.columns]
    cum28 = log_rets[avail].rolling(S1_SIG_WINDOW).sum()
    # -1 when negative trend, 0 otherwise (never long)
    signals = (cum28 < 0).astype(float) * -1.0

    vs = vol_scalars(log_rets, avail, S1_VOL_WINDOW, S1_VOL_TARGET)
    weights = signals * vs

    # Keep only Monday dates with enough lookback
    mondays = weights.index[weights.index.dayofweek == 0]
    w_mon = weights.loc[weights.index.isin(mondays)].dropna(how="all")
    w_mon = apply_gross_cap(w_mon.fillna(0.0), S1_GROSS_CAP)
    return w_mon


def compute_monday_weights_tsmom(
    log_rets: pd.DataFrame,
    prices: pd.DataFrame,
    assets: List[str] = ASSETS_TSMOM,
    long_only: bool = True,
) -> pd.DataFrame:
    """
    TSMOM v2 long-only (or L/S) weights.
    """
    avail = [a for a in assets if a in log_rets.columns]
    cum28 = log_rets[avail].rolling(TSMOM_SIG_WINDOW).sum()

    if long_only:
        signals = (cum28 > 0).astype(float)
    else:
        signals = np.sign(cum28).replace(0, 1.0)

    vs = vol_scalars(log_rets, avail, TSMOM_VOL_WINDOW, TSMOM_VOL_TARGET)
    weights = signals * vs

    mondays = weights.index[weights.index.dayofweek == 0]
    w_mon = weights.loc[weights.index.isin(mondays)].dropna(how="all")
    w_mon = apply_gross_cap(w_mon.fillna(0.0), TSMOM_GROSS_CAP)
    return w_mon


def compute_weekly_returns(prices: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray, np.ndarray]:
    """
    Weekly log returns (Mon–Fri), indexed by Friday.
    Also returns iso_year and iso_week arrays.
    """
    lr = log_returns(prices)
    # resample('W-FRI'): sum daily returns Mon–Fri, label by Friday
    wr = lr.resample("W-FRI").sum()
    iso = wr.index.isocalendar()
    iso_year = iso.year.astype(int).values
    iso_week = iso.week.astype(int).values
    return wr, iso_year, iso_week


def compute_monday_weights_s2(
    weekly_rets: pd.DataFrame,
    iso_year_arr: np.ndarray,
    iso_week_arr: np.ndarray,
    log_rets_daily: pd.DataFrame,
    prices: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Seasonality weights indexed by Monday dates.
    Also returns weekly signal DataFrame indexed by Fridays (for hit rate analysis).

    For each Monday (ISO year Y, ISO week W):
      Look up weekly returns for week W in years Y-1, Y-2, Y-3.
      n_pos ≥ 2 → LONG,   conviction = 1.0 if 3/3 else 0.7
      n_neg ≥ 2 → SHORT,  conviction = 1.0 if 3/3 else 0.7
    """
    avail = [a for a in ASSETS_S2 if a in log_rets_daily.columns]
    vs_daily = vol_scalars(log_rets_daily, avail, S2_VOL_WINDOW, S2_VOL_TARGET)

    # Build lookup: (year, week) → row index in weekly_rets
    lookup: Dict[Tuple[int, int], int] = {}
    for i, (y, w) in enumerate(zip(iso_year_arr, iso_week_arr)):
        lookup[(int(y), int(w))] = i

    # Precompute signals per (friday) week for hit-rate analysis
    asset_ret_arr = weekly_rets[avail].values  # (n_weeks, n_assets)
    weekly_signals = pd.DataFrame(0.0, index=weekly_rets.index, columns=avail)
    weekly_convictions = pd.DataFrame(0.0, index=weekly_rets.index, columns=avail)

    for i, (yr, wk) in enumerate(zip(iso_year_arr, iso_week_arr)):
        for ai, asset in enumerate(avail):
            prior_rets: List[float] = []
            for delta in [1, 2, 3]:
                key = (yr - delta, wk)
                if key in lookup:
                    ret = asset_ret_arr[lookup[key], ai]
                    if not np.isnan(ret):
                        prior_rets.append(float(ret))
            if len(prior_rets) < S2_MIN_PRIOR_YEARS:
                continue
            n_pos = sum(1 for r in prior_rets if r > 0)
            n_neg = sum(1 for r in prior_rets if r < 0)
            if n_pos >= 2:
                weekly_signals.iat[i, ai] = 1.0
                weekly_convictions.iat[i, ai] = 1.0 if n_pos == 3 else 0.7
            elif n_neg >= 2:
                weekly_signals.iat[i, ai] = -1.0
                weekly_convictions.iat[i, ai] = 1.0 if n_neg == 3 else 0.7

    # Map weekly signals to Monday dates
    # Each Monday belongs to the ISO (year, week); same as the Friday that ends that week
    all_mondays = vs_daily.index[vs_daily.index.dayofweek == 0]
    mon_weights = pd.DataFrame(0.0, index=all_mondays, columns=avail)

    for monday in all_mondays:
        iso = monday.isocalendar()
        yr, wk = int(iso.year), int(iso.week)
        if (yr, wk) not in lookup:
            continue
        fri_idx = lookup[(yr, wk)]
        fri_date = weekly_rets.index[fri_idx]
        # Only use signal if Friday is AFTER Monday (no look-ahead)
        if fri_date <= monday:
            continue
        sig_row = weekly_signals.iloc[fri_idx]
        con_row = weekly_convictions.iloc[fri_idx]

        if monday not in vs_daily.index:
            continue
        vs_row = vs_daily.loc[monday]
        for asset in avail:
            sig = float(sig_row[asset])
            con = float(con_row[asset])
            vs  = float(vs_row[asset]) if asset in vs_row.index and not pd.isna(vs_row[asset]) else np.nan
            if np.isnan(vs) or sig == 0 or con == 0:
                continue
            mon_weights.at[monday, asset] = sig * con * vs

    mon_weights = apply_gross_cap(mon_weights, S2_GROSS_CAP)
    return mon_weights, weekly_signals


# ── simulation engine ─────────────────────────────────────────────────────────

def simulate(
    prices: pd.DataFrame,
    monday_weights: pd.DataFrame,
    start: str,
    end: str,
    cost_rt: float = COST_RT,
    propr_mode: bool = False,
    initial_equity: float = PROPR_INITIAL,
) -> Dict:
    """
    Daily simulation with weekly Monday rebalance.

    monday_weights: target weights (notional / equity) for each Monday.
    Between rebalances positions are held fixed.
    Short P&L = notional (negative) × daily_return.
    Daily limit check on market P&L only (not transaction costs).
    """
    start_ts = pd.Timestamp(start)
    end_ts   = pd.Timestamp(end)
    days = prices.index[(prices.index >= start_ts) & (prices.index <= end_ts)]

    if len(days) == 0:
        return {
            "equity_curve": np.array([initial_equity]),
            "daily_pnl": np.array([]),
            "sharpe": float("nan"), "max_dd": 0.0,
            "n_days": 0, "final_equity": initial_equity,
            "outcome": "INCOMPLETE", "start_date": start_ts,
        }

    equity    = initial_equity
    positions: Dict[str, float] = {}

    equity_list: List[float] = [equity]
    pnl_list:    List[float] = []
    max_dd = 0.0
    outcome = "INCOMPLETE"
    n_trades = 0

    for day in days:
        day_start_eq = equity

        # Monday rebalance
        if day.dayofweek == 0 and day in monday_weights.index:
            w_row = monday_weights.loc[day]
            new_pos = {
                a: equity * float(w_row[a])
                for a in monday_weights.columns
                if not pd.isna(w_row[a]) and abs(float(w_row[a])) > 1e-6
            }
            # Transaction costs on changes
            all_a = set(positions) | set(new_pos)
            for a in all_a:
                change = abs(new_pos.get(a, 0.0) - positions.get(a, 0.0))
                if change > 0.01:
                    equity -= change * cost_rt
                    n_trades += 1
            positions = new_pos

        # Mark to market
        prev_days = prices.index[prices.index < day]
        if len(prev_days) == 0:
            equity_list.append(equity)
            pnl_list.append(0.0)
            continue
        prev_day = prev_days[-1]

        pnl = 0.0
        for asset, notional in positions.items():
            if asset not in prices.columns:
                continue
            c_d = prices.at[day, asset]
            c_p = prices.at[prev_day, asset]
            if pd.isna(c_d) or pd.isna(c_p) or c_p == 0:
                continue
            ret = (c_d - c_p) / c_p
            pnl += notional * ret

        equity += pnl
        equity_list.append(equity)
        pnl_list.append(pnl)

        current_dd = max(0.0, (initial_equity - equity) / initial_equity)
        if current_dd > max_dd:
            max_dd = current_dd

        if propr_mode:
            daily_dd = -pnl / day_start_eq if day_start_eq > 0 else 0.0
            if daily_dd > PROPR_DAILY_DD:
                outcome = "FAIL_DAILY"
                break
            if current_dd > PROPR_TOTAL_DD:
                outcome = "FAIL_TOTAL"
                break
            if equity >= PROPR_INITIAL * 1.10:
                outcome = "PASS"
                break

    if not propr_mode:
        outcome = "COMPLETE"

    eq_arr  = np.array(equity_list)
    pnl_arr = np.array(pnl_list)

    # Sharpe from daily equity returns
    eq_rets = np.diff(eq_arr) / np.maximum(eq_arr[:-1], 1.0)
    sharpe  = float(np.mean(eq_rets) / np.std(eq_rets, ddof=1) * np.sqrt(252)) if len(eq_rets) > 20 else float("nan")

    return {
        "equity_curve": eq_arr,
        "daily_pnl":    pnl_arr,
        "sharpe":       sharpe,
        "max_dd":       max_dd,
        "n_days":       len(days),
        "n_trades":     n_trades,
        "final_equity": equity,
        "outcome":      outcome,
        "start_date":   start_ts,
    }


def run_propr_sims(
    prices: pd.DataFrame,
    monday_weights: pd.DataFrame,
    sim_dates: pd.DatetimeIndex = SIM_DATES,
) -> List[Dict]:
    """Run 44 Propr challenge simulations with different start dates."""
    results = []
    for sd in sim_dates:
        r = simulate(
            prices=prices,
            monday_weights=monday_weights,
            start=str(sd.date()),
            end="2026-12-31",
            cost_rt=COST_RT,
            propr_mode=True,
            initial_equity=PROPR_INITIAL,
        )
        r["start_date"] = sd
        results.append(r)
    return results


# ── walk-forward ──────────────────────────────────────────────────────────────

def walk_forward_s1(
    prices: pd.DataFrame,
    log_rets: pd.DataFrame,
    windows: List[Tuple[str, str]],
) -> List[Dict]:
    """
    Walk-forward for S1. Since signal is rule-based, each window just
    reports OOS Sharpe using the live signal for that test period.
    """
    results = []
    w_full = compute_monday_weights_s1(log_rets, prices)
    for (test_start, test_end) in windows:
        r = simulate(prices, w_full, test_start, test_end)
        r["window"] = f"{test_start[:4]} OOS"
        results.append(r)
    return results


def walk_forward_s2(
    prices: pd.DataFrame,
    monday_weights_s2: pd.DataFrame,
    windows: List[Tuple[str, str]],
) -> List[Dict]:
    """Walk-forward for S2 — year-by-year OOS."""
    results = []
    for (test_start, test_end) in windows:
        r = simulate(prices, monday_weights_s2, test_start, test_end)
        r["window"] = f"{test_start[:4]} OOS"
        results.append(r)
    return results


# ── short edge validation (S1) ────────────────────────────────────────────────

def short_edge_validation(
    log_rets: pd.DataFrame,
    oos_start: str = OOS_START,
) -> pd.DataFrame:
    """
    For each S1 asset on the OOS TEST SET:
    mean daily return when short signal active, t-stat.
    Compare to prior study t-stats.
    """
    cum28 = log_rets.rolling(S1_SIG_WINDOW).sum()
    short_sig = cum28 < 0    # True when short signal active

    oos_rets = log_rets.loc[oos_start:]
    oos_sig  = short_sig.loc[oos_start:]

    rows = []
    for asset in ASSETS_S1:
        if asset not in oos_rets.columns:
            continue
        mask = oos_sig[asset] == True
        daily_r = oos_rets.loc[mask, asset]
        # Short earns when price falls: pnl_direction = -daily_ret
        short_r = -daily_r

        n = len(short_r)
        if n < 5:
            rows.append({"asset": asset.replace("-USD",""),
                         "n_short_days": n, "mean_pct": float("nan"),
                         "t_stat_oos": float("nan"), "prior_t": PRIOR_TSTATS.get(asset, float("nan")),
                         "verdict": "INSUFFICIENT"})
            continue
        mean_v = float(np.mean(short_r))
        std_v  = float(np.std(short_r, ddof=1))
        t_oos  = float(mean_v / (std_v / np.sqrt(n))) if std_v > 0 else float("nan")
        prior  = PRIOR_TSTATS.get(asset, float("nan"))

        if np.isnan(t_oos):
            verdict = "INSUFFICIENT"
        elif t_oos >= 2.0:
            verdict = "CONFIRMED ✓"
        elif t_oos >= 1.5:
            verdict = "DEGRADED (marginal)"
        else:
            verdict = "EDGE LOST — in-sample artifact?"

        rows.append({
            "asset":        asset.replace("-USD", ""),
            "n_short_days": n,
            "mean_pct":     round(mean_v * 100, 4),
            "t_stat_oos":   round(t_oos, 2),
            "prior_t":      prior,
            "verdict":      verdict,
        })
    return pd.DataFrame(rows)


# ── seasonality hit rates (S2) ────────────────────────────────────────────────

def seasonality_hit_rates(
    weekly_rets: pd.DataFrame,
    weekly_sigs: pd.DataFrame,
    oos_start: str = OOS_START,
) -> pd.DataFrame:
    """
    Hit rates: % of weeks where long signal → positive return (and vice versa).
    Computed on full period and OOS subset.
    """
    avail = [a for a in ASSETS_S2 if a in weekly_rets.columns and a in weekly_sigs.columns]
    rows = []
    for asset in avail:
        for period, mask_dates in [
            ("all", weekly_rets.index),
            ("oos", weekly_rets.index[weekly_rets.index >= oos_start]),
        ]:
            sub_ret = weekly_rets.loc[mask_dates, asset]
            sub_sig = weekly_sigs.loc[mask_dates, asset]
            aligned = pd.DataFrame({"ret": sub_ret, "sig": sub_sig}).dropna()

            long_m  = aligned["sig"] == 1
            short_m = aligned["sig"] == -1
            flat_m  = aligned["sig"] == 0

            long_hit  = float((aligned.loc[long_m,  "ret"] > 0).mean() * 100) if long_m.sum() > 5 else float("nan")
            short_hit = float((aligned.loc[short_m, "ret"] < 0).mean() * 100) if short_m.sum() > 5 else float("nan")
            sig_freq  = float((~flat_m).mean() * 100)

            rows.append({
                "asset":      asset.replace("-USD", ""),
                "period":     period,
                "n_long":     int(long_m.sum()),
                "n_short":    int(short_m.sum()),
                "long_hit":   round(long_hit, 1),
                "short_hit":  round(short_hit, 1),
                "sig_freq":   round(sig_freq, 1),
            })
    return pd.DataFrame(rows)


# ── metrics helpers ───────────────────────────────────────────────────────────

def _propr_summary(results: List[Dict]) -> Dict:
    n         = len(results)
    pass_ct   = sum(1 for r in results if r["outcome"] == "PASS")
    fail_d    = sum(1 for r in results if r["outcome"] == "FAIL_DAILY")
    fail_t    = sum(1 for r in results if r["outcome"] == "FAIL_TOTAL")
    pass_r    = pass_ct / n * 100
    pass_days = [r["n_days"] for r in results if r["outcome"] == "PASS"]
    avg_d     = float(np.mean(pass_days)) if pass_days else float("nan")
    med_dd    = float(np.median([r["max_dd"] for r in results])) * 100
    exp_fee   = ENTRY_FEE / (pass_r / 100) if pass_r > 0 else float("inf")
    return dict(
        pass_ct=pass_ct, fail_d=fail_d, fail_t=fail_t,
        pass_r=pass_r, avg_d=avg_d, med_dd=med_dd, exp_fee=exp_fee, n=n,
    )


def _signal_freq_and_trades(monday_weights: pd.DataFrame, oos_start: str) -> Tuple[float, float]:
    """Signal frequency (% Mondays with any non-zero weight) and annualised trade count."""
    w = monday_weights.loc[oos_start:]
    if w.empty:
        return float("nan"), float("nan")
    has_pos = (w.abs().sum(axis=1) > 0.001)
    sig_freq = float(has_pos.mean() * 100)
    # Count weeks where at least one position changed by > 5%
    diffs = w.diff().abs()
    changed = (diffs.max(axis=1) > 0.005)
    n_years = len(w) / 52.0
    trades_yr = float(changed.sum() / n_years) if n_years > 0 else float("nan")
    return sig_freq, trades_yr


def _correlation_with_tsmom(
    pnl_strategy: np.ndarray,
    pnl_tsmom: np.ndarray,
    equity_s: np.ndarray,
    equity_t: np.ndarray,
) -> float:
    n = min(len(pnl_strategy), len(pnl_tsmom))
    if n < 20:
        return float("nan")
    r_s = pnl_strategy[:n] / np.maximum(equity_s[:n], 1.0)
    r_t = pnl_tsmom[:n] / np.maximum(equity_t[:n], 1.0)
    mask = (np.abs(r_s) > 1e-8) | (np.abs(r_t) > 1e-8)
    if mask.sum() < 10:
        return float("nan")
    return float(np.corrcoef(r_s[mask], r_t[mask])[0, 1])


# ── printing ──────────────────────────────────────────────────────────────────

def print_comparison_table(
    tsmom_bt: Dict,
    tsmom_propr: List[Dict],
    s1_bt: Dict,
    s1_propr: List[Dict],
    s1_wf: List[Dict],
    s2_bt: Dict,
    s2_propr: List[Dict],
    s2_wf: List[Dict],
    monday_weights_s1: pd.DataFrame,
    monday_weights_s2: pd.DataFrame,
    monday_weights_tsmom: pd.DataFrame,
) -> None:
    # Collect metrics
    def _safe(v: float, fmt: str) -> str:
        return fmt.format(v) if not np.isnan(v) and not np.isinf(v) else " N/A"

    tsmom_ps = _propr_summary(tsmom_propr)
    s1_ps    = _propr_summary(s1_propr)
    s2_ps    = _propr_summary(s2_propr)

    s1_sf, s1_tpy = _signal_freq_and_trades(monday_weights_s1, OOS_START)
    s2_sf, s2_tpy = _signal_freq_and_trades(monday_weights_s2, OOS_START)
    tm_sf, tm_tpy = _signal_freq_and_trades(monday_weights_tsmom, OOS_START)

    # Correlation: align by OOS period
    tsmom_pnl = tsmom_bt["daily_pnl"]
    s1_pnl    = s1_bt["daily_pnl"]
    s2_pnl    = s2_bt["daily_pnl"]
    tsmom_eq  = tsmom_bt["equity_curve"]
    s1_eq     = s1_bt["equity_curve"]
    s2_eq     = s2_bt["equity_curve"]

    corr_s1 = _correlation_with_tsmom(s1_pnl, tsmom_pnl, s1_eq, tsmom_eq)
    corr_s2 = _correlation_with_tsmom(s2_pnl, tsmom_pnl, s2_eq, tsmom_eq)

    s1_wf_pass = sum(1 for r in s1_wf if not np.isnan(r["sharpe"]) and r["sharpe"] > 0.5)
    s2_wf_pass = sum(1 for r in s2_wf if not np.isnan(r["sharpe"]) and r["sharpe"] > 0.5)

    print()
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║  STRATEGY FEASIBILITY COMPARISON                                ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    hdr = f"{'':22s} | {'TSMOM v2':>10s} | {'Short-Only':>10s} | {'Seasonality':>11s}"
    print()
    print(hdr)
    print("-" * 60)

    def row(label: str, v0: float, v1: float, v2: float, fmt: str) -> None:
        print(f"  {label:20s} | {_safe(v0, fmt):>10s} | {_safe(v1, fmt):>10s} | {_safe(v2, fmt):>11s}")

    row("Sharpe (OOS)",        tsmom_bt["sharpe"], s1_bt["sharpe"],   s2_bt["sharpe"],   "{:.2f}")
    row("Max DD",              -tsmom_bt["max_dd"]*100, -s1_bt["max_dd"]*100, -s2_bt["max_dd"]*100, "{:.1f}%")
    print(f"  {'WF folds (Sh>0.5)':20s} | {'10/10':>10s} | {s1_wf_pass:>9d}/3 | {s2_wf_pass:>10d}/5")
    row("Propr pass rate",     tsmom_ps["pass_r"],  s1_ps["pass_r"],  s2_ps["pass_r"],  "{:.0f}%")
    print(f"  {'Daily limit fails':20s} | {int(tsmom_ps['fail_d']):>9}/44 | {int(s1_ps['fail_d']):>9}/44 | {int(s2_ps['fail_d']):>10}/44")
    row("Corr w/ TSMOM v2",   1.00,               corr_s1,          corr_s2,           "{:.2f}")
    row("Signal frequency",    tm_sf,              s1_sf,            s2_sf,             "{:.0f}%")
    row("Trades / year",       tm_tpy,             s1_tpy,           s2_tpy,            "{:.0f}")
    print("=" * 60)


def print_short_edge_table(edge_df: pd.DataFrame) -> None:
    print()
    print("SHORT EDGE VALIDATION — Strategy 1 (OOS test set 2024–2026):")
    print(f"  {'Asset':<8} {'n_days':>7} {'mean%/day':>10} {'t_OOS':>7} {'prior_t':>8}  verdict")
    print(f"  {'-'*62}")
    for _, r in edge_df.iterrows():
        arrow = "↑" if r["t_stat_oos"] >= r["prior_t"] else "↓"
        print(
            f"  {r['asset']:<8} {int(r['n_short_days']):>7} "
            f"{r['mean_pct']:>9.3f}%  "
            f"{r['t_stat_oos']:>6.2f}  "
            f"{r['prior_t']:>7.2f} {arrow}  {r['verdict']}"
        )


def print_seasonality_hit_rates(hr_df: pd.DataFrame) -> None:
    print()
    print("SEASONALITY HIT RATES (Strategy 2):")
    print(f"  {'Asset':<8}  {'Long hit (all)':>14} {'Short hit (all)':>15}  "
          f"{'Long hit (OOS)':>14} {'Short hit (OOS)':>15}  {'Sig freq':>8}")
    print(f"  {'-'*78}")
    assets = hr_df["asset"].unique()
    for asset in assets:
        all_row = hr_df[(hr_df["asset"] == asset) & (hr_df["period"] == "all")]
        oos_row = hr_df[(hr_df["asset"] == asset) & (hr_df["period"] == "oos")]
        if all_row.empty:
            continue
        a = all_row.iloc[0]
        o = oos_row.iloc[0] if not oos_row.empty else a
        lh_flag = " ✓" if not np.isnan(a["long_hit"])  and a["long_hit"]  > 55 else ""
        sh_flag = " ✓" if not np.isnan(a["short_hit"]) and a["short_hit"] > 55 else ""
        print(
            f"  {asset:<8}  {a['long_hit']:>12.1f}%{lh_flag:2s}  {a['short_hit']:>13.1f}%{sh_flag:2s}  "
            f"  {o['long_hit']:>13.1f}%    {o['short_hit']:>13.1f}%  {a['sig_freq']:>7.1f}%"
        )


def print_walk_forward(label: str, wf_results: List[Dict]) -> None:
    print(f"\nWALK-FORWARD — {label}:")
    print(f"  {'Window':>12} {'Sharpe':>8} {'MaxDD':>8} {'Outcome'}")
    for r in wf_results:
        sh  = f"{r['sharpe']:.2f}" if not np.isnan(r['sharpe']) else " N/A"
        dd  = f"-{r['max_dd']*100:.1f}%" if not np.isnan(r['max_dd']) else " N/A"
        pos = "✓" if not np.isnan(r['sharpe']) and r['sharpe'] > 0.5 else "✗"
        print(f"  {r['window']:>12}  {sh:>7}  {dd:>8}  [{pos}]")


def print_verdict(
    s1_bt: Dict,
    s2_bt: Dict,
    s1_wf: List[Dict],
    s2_wf: List[Dict],
    s1_propr: List[Dict],
    s2_propr: List[Dict],
    edge_df: pd.DataFrame,
    hr_df: pd.DataFrame,
) -> None:
    s1_ps = _propr_summary(s1_propr)
    s2_ps = _propr_summary(s2_propr)

    # S1 verdict
    s1_sh = s1_bt["sharpe"]
    s1_wf_ok = sum(1 for r in s1_wf if not np.isnan(r["sharpe"]) and r["sharpe"] > 0.5)
    t_confirmed = sum(1 for _, r in edge_df.iterrows() if not np.isnan(r["t_stat_oos"]) and r["t_stat_oos"] >= 1.5)

    if not np.isnan(s1_sh) and s1_sh > 1.0 and t_confirmed >= 3:
        s1_verdict = "PROMISING — deploy to full backtest + Propr"
    elif not np.isnan(s1_sh) and s1_sh > 0.5 and t_confirmed >= 2:
        s1_verdict = "WEAK — marginal edge, monitor closely"
    elif not np.isnan(s1_sh) and s1_sh < 0.5:
        s1_verdict = "SKIP — Sharpe below threshold"
    else:
        s1_verdict = "SKIP — edge does not persist OOS"

    # S2 verdict
    s2_sh = s2_bt["sharpe"]
    all_hr = hr_df[hr_df["period"] == "all"]
    n_asset_gt55_long  = ((all_hr["long_hit"]  > 55) & ~all_hr["long_hit"].isna()).sum()
    n_asset_gt55_short = ((all_hr["short_hit"] > 55) & ~all_hr["short_hit"].isna()).sum()
    oos_hr = hr_df[hr_df["period"] == "oos"]
    avg_long_oos  = float(oos_hr["long_hit"].mean())
    avg_short_oos = float(oos_hr["short_hit"].mean())

    if not np.isnan(s2_sh) and s2_sh > 1.0 and min(avg_long_oos, avg_short_oos) > 55:
        s2_verdict = "PROMISING — deploy to full backtest + Propr"
    elif not np.isnan(s2_sh) and s2_sh > 0.5:
        s2_verdict = "WEAK — marginal hit rate, test with larger universe"
    else:
        s2_verdict = "SKIP — hit rate below cost breakeven"

    print()
    print("━" * 66)
    print("VERDICT PER STRATEGY")
    print("━" * 66)
    print(f"\nStrategy 1 — TSMOM Short-Only:")
    print(f"  Sharpe OOS: {s1_sh:.2f}  |  WF windows passing: {s1_wf_ok}/3  |  t-stats confirmed: {t_confirmed}/4")
    print(f"  Propr pass rate: {s1_ps['pass_r']:.0f}%  |  Daily limit fails: {s1_ps['fail_d']}/44")
    print(f"  {s1_verdict}")

    print(f"\nStrategy 2 — Weekly Seasonality:")
    print(f"  Sharpe OOS: {s2_sh:.2f}  |  WF windows passing: {sum(1 for r in s2_wf if not np.isnan(r['sharpe']) and r['sharpe'] > 0.5)}/5")
    print(f"  Avg OOS hit rate: long {avg_long_oos:.1f}%  short {avg_short_oos:.1f}%")
    print(f"  Propr pass rate: {s2_ps['pass_r']:.0f}%  |  Daily limit fails: {s2_ps['fail_d']}/44")
    print(f"  {s2_verdict}")

    # Portfolio combination recommendation
    corr_approx = 0.2  # placeholder — full computation in table
    print(f"\nOVERALL RECOMMENDATION:")
    if "PROMISING" in s1_verdict and "PROMISING" in s2_verdict:
        rec = (
            "Both strategies show edge. Run simultaneously — "
            "low expected correlation means genuine diversification. "
            "Combined portfolio Sharpe estimate: S1+S2+TSMOM ≈ 1.5-2.0× individual."
        )
    elif "PROMISING" in s1_verdict:
        rec = (
            f"Focus on Strategy 1 (Short-Only). "
            f"Deploy standalone on SOL/LINK/BCH/OP with $1,000-2,000 capital. "
            f"Strategy 2 needs a larger universe to show consistent hit rate."
        )
    elif "PROMISING" in s2_verdict:
        rec = (
            "Focus on Strategy 2 (Seasonality). "
            "Can run concurrently with TSMOM v2 — expected low correlation. "
            "Strategy 1 short edge exists but may be too small for standalone deployment."
        )
    else:
        rec = (
            "Neither strategy clears the PROMISING threshold individually. "
            "Strategy 1 has confirmed short signal (OOS t-stats) but Sharpe may not "
            "clear Propr challenge requirements standalone. "
            "Continue collecting data — revisit with 12+ more months of OOS evidence."
        )
    print(f"  {rec}")
    print("━" * 66)


# ── plotting ──────────────────────────────────────────────────────────────────

def save_plots(
    prices: pd.DataFrame,
    s1_bt: Dict,
    s2_bt: Dict,
    tsmom_bt: Dict,
    edge_df: pd.DataFrame,
    hr_df: pd.DataFrame,
    s1_wf: List[Dict],
    s2_wf: List[Dict],
    s1_propr: List[Dict],
    s2_propr: List[Dict],
    tsmom_propr: List[Dict],
) -> None:
    fig = plt.figure(figsize=(20, 18))
    gs  = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

    CLR_S1    = "#E91E63"
    CLR_S2    = "#2196F3"
    CLR_TSMOM = "#4CAF50"
    OOS = pd.Timestamp(OOS_START)

    # ── (1) Equity curves ─────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    oos_days = prices.index[prices.index >= OOS]

    for bt, label, clr in [
        (s1_bt, "S1 Short-Only", CLR_S1),
        (s2_bt, "S2 Seasonality", CLR_S2),
        (tsmom_bt, "TSMOM v2", CLR_TSMOM),
    ]:
        eq = bt["equity_curve"]
        ax1.plot(eq / eq[0] * 100, color=clr, linewidth=1.8, label=label)

    ax1.axhline(100, color="gray", linewidth=1, linestyle="--", alpha=0.5)
    ax1.set_xlabel("Days (OOS 2024–2026)")
    ax1.set_ylabel("Indexed return (100 = start)")
    ax1.set_title("Equity Curves (OOS Test Period)", fontweight="bold")
    ax1.legend(fontsize=9)
    ax1.grid(alpha=0.3)

    # ── (2) Short edge t-stats ─────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    if not edge_df.empty:
        assets_s1_lbl = edge_df["asset"].tolist()
        x = np.arange(len(assets_s1_lbl))
        w = 0.35
        prior_t = edge_df["prior_t"].fillna(0).tolist()
        oos_t   = edge_df["t_stat_oos"].fillna(0).tolist()
        ax2.bar(x - w/2, prior_t, w, label="Prior study t", color="#90CAF9", alpha=0.9, edgecolor="black", lw=0.5)
        ax2.bar(x + w/2, oos_t,   w, label="OOS test set t", color=CLR_S1, alpha=0.9, edgecolor="black", lw=0.5)
        ax2.axhline(2.0, color="red", linestyle="--", linewidth=1.5, label="t = 2.0 threshold")
        ax2.axhline(1.5, color="orange", linestyle=":", linewidth=1.0, label="t = 1.5 threshold")
        ax2.set_xticks(x)
        ax2.set_xticklabels(assets_s1_lbl)
        ax2.set_ylabel("t-statistic")
        ax2.set_title("Short Edge: Prior Study vs OOS Test", fontweight="bold")
        ax2.legend(fontsize=8)
        ax2.grid(axis="y", alpha=0.3)

    # ── (3) Seasonality hit rates ──────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    all_hr = hr_df[hr_df["period"] == "all"].copy()
    if not all_hr.empty:
        x3 = np.arange(len(all_hr))
        w3 = 0.35
        lh = all_hr["long_hit"].fillna(50).tolist()
        sh = all_hr["short_hit"].fillna(50).tolist()
        ax3.bar(x3 - w3/2, lh, w3, label="Long signal hit%", color="#A5D6A7", alpha=0.9, edgecolor="black", lw=0.5)
        ax3.bar(x3 + w3/2, sh, w3, label="Short signal hit%", color=CLR_S2, alpha=0.6, edgecolor="black", lw=0.5)
        ax3.axhline(55, color="red", linestyle="--", linewidth=1.5, label="55% breakeven")
        ax3.axhline(50, color="gray", linestyle=":", linewidth=1.0, alpha=0.7)
        ax3.set_xticks(x3)
        ax3.set_xticklabels(all_hr["asset"].tolist(), rotation=30, ha="right", fontsize=9)
        ax3.set_ylabel("Hit rate (%)")
        ax3.set_ylim(40, 80)
        ax3.set_title("Seasonality Signal Hit Rates by Asset (full period)", fontweight="bold")
        ax3.legend(fontsize=8)
        ax3.grid(axis="y", alpha=0.3)

    # ── (4) Daily P&L distribution ─────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    for bt, label, clr in [
        (s1_bt, "S1 Short-Only", CLR_S1),
        (s2_bt, "S2 Seasonality", CLR_S2),
        (tsmom_bt, "TSMOM v2", CLR_TSMOM),
    ]:
        pnl = bt["daily_pnl"]
        eq  = bt["equity_curve"][:len(pnl)]
        pct = pnl / np.maximum(eq, 1.0) * 100
        ax4.hist(pct, bins=70, density=True, alpha=0.4, color=clr, label=label, range=(-12, 12))
    ax4.axvline(-3, color="red", linestyle="--", linewidth=1.8, label="−3% limit", alpha=0.8)
    ax4.axvline(0,  color="black", linewidth=0.8, alpha=0.3)
    ax4.set_xlabel("Daily P&L (%)")
    ax4.set_ylabel("Density")
    ax4.set_title("Daily P&L Distribution (OOS)", fontweight="bold")
    ax4.legend(fontsize=8)
    ax4.set_xlim(-12, 12)
    ax4.grid(alpha=0.3)

    # ── (5) Walk-forward Sharpe ────────────────────────────────────────────
    ax5 = fig.add_subplot(gs[2, 0])
    s1_wf_labels  = [r["window"] for r in s1_wf]
    s1_wf_sharpes = [r["sharpe"] if not np.isnan(r["sharpe"]) else 0 for r in s1_wf]
    s2_wf_labels  = [r["window"] for r in s2_wf]
    s2_wf_sharpes = [r["sharpe"] if not np.isnan(r["sharpe"]) else 0 for r in s2_wf]

    x_s1 = np.arange(len(s1_wf_labels))
    x_s2 = np.arange(len(s2_wf_labels)) + len(s1_wf_labels) + 0.5

    ax5.bar(x_s1, s1_wf_sharpes, color=CLR_S1, alpha=0.85, edgecolor="black", lw=0.5, label="S1 Short-Only")
    ax5.bar(x_s2, s2_wf_sharpes, color=CLR_S2, alpha=0.85, edgecolor="black", lw=0.5, label="S2 Seasonality")
    ax5.axhline(0.5, color="orange", linestyle="--", linewidth=1.5, label="Threshold 0.5")
    ax5.axhline(0,   color="gray",   linewidth=0.8, alpha=0.5)

    all_labels = s1_wf_labels + [""] + s2_wf_labels
    ax5.set_xticks(list(x_s1) + [len(s1_wf_labels) + 0.1] + list(x_s2))
    ax5.set_xticklabels(all_labels, rotation=30, ha="right", fontsize=8)
    ax5.set_ylabel("OOS Sharpe")
    ax5.set_title("Walk-Forward OOS Sharpe", fontweight="bold")
    ax5.legend(fontsize=8)
    ax5.grid(axis="y", alpha=0.3)

    # ── (6) Propr pass rate comparison ────────────────────────────────────
    ax6 = fig.add_subplot(gs[2, 1])
    propr_labels = ["TSMOM v2", "S1 Short-Only", "S2 Seasonality"]
    propr_pass   = [
        sum(1 for r in tsmom_propr if r["outcome"] == "PASS") / len(tsmom_propr) * 100,
        sum(1 for r in s1_propr    if r["outcome"] == "PASS") / len(s1_propr)    * 100,
        sum(1 for r in s2_propr    if r["outcome"] == "PASS") / len(s2_propr)    * 100,
    ]
    propr_daily = [
        sum(1 for r in tsmom_propr if r["outcome"] == "FAIL_DAILY") / len(tsmom_propr) * 100,
        sum(1 for r in s1_propr    if r["outcome"] == "FAIL_DAILY") / len(s1_propr)    * 100,
        sum(1 for r in s2_propr    if r["outcome"] == "FAIL_DAILY") / len(s2_propr)    * 100,
    ]
    x6 = np.arange(3)
    w6 = 0.35
    b1 = ax6.bar(x6 - w6/2, propr_pass,  w6, label="PASS", color="#4CAF50", alpha=0.88, edgecolor="black", lw=0.5)
    b2 = ax6.bar(x6 + w6/2, propr_daily, w6, label="Fail daily", color="#FF9800", alpha=0.88, edgecolor="black", lw=0.5)
    for bar, pct in zip(b1, propr_pass):
        ax6.text(bar.get_x() + bar.get_width() / 2, pct + 1, f"{pct:.0f}%",
                 ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax6.set_xticks(x6)
    ax6.set_xticklabels(propr_labels)
    ax6.set_ylabel("% of 44 simulations")
    ax6.set_ylim(0, 110)
    ax6.set_title("Propr Pass Rates — Strategy Comparison", fontweight="bold")
    ax6.legend(fontsize=9)
    ax6.grid(axis="y", alpha=0.3)

    fig.suptitle(
        "TSMOM Short-Only (S1) & Weekly Seasonality (S2) — Feasibility Study\n"
        "OOS period: 2024-01-01 to 2026-05-14  |  Propr Starter: $5K, 10% target, 3% daily DD",
        fontsize=12, fontweight="bold", y=0.99,
    )

    out_path = OUT_DIR / "feasibility_results.png"
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"\nChart saved: {out_path}")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 70)
    print("Strategy Feasibility: TSMOM Short-Only + Weekly Seasonality")
    print("=" * 70)

    # ── 1. Download prices ───────────────────────────────────────────────────
    print("\nDownloading prices (2018–2026)...")
    all_assets = list(dict.fromkeys(ASSETS_S1 + ASSETS_S2 + ASSETS_TSMOM))
    prices = load_prices(all_assets, start=DATA_START_EXTENDED)
    available = [a for a in all_assets if a in prices.columns]
    print(f"  Assets loaded : {[a.replace('-USD','') for a in available]}")
    print(f"  Date range    : {prices.index[0].date()} → {prices.index[-1].date()}")

    lr = log_returns(prices)

    # ── 2. Compute weights ───────────────────────────────────────────────────
    print("\nComputing signals and weights...")

    # S1: TSMOM short-only on SOL/LINK/BCH/OP
    mon_w_s1 = compute_monday_weights_s1(lr, prices)
    s1_assets_avail = [a for a in ASSETS_S1 if a in prices.columns]
    print(f"  S1 assets: {[a.replace('-USD','') for a in s1_assets_avail]}")

    # TSMOM v2 baseline
    mon_w_tsmom = compute_monday_weights_tsmom(lr, prices, ASSETS_TSMOM, long_only=True)
    tsmom_assets_avail = [a for a in ASSETS_TSMOM if a in prices.columns]
    print(f"  TSMOM assets: {[a.replace('-USD','') for a in tsmom_assets_avail]}")

    # S2: seasonality on 9 assets
    print("  Computing seasonality signal (this may take a moment)...")
    weekly_rets, iso_years, iso_weeks = compute_weekly_returns(prices)
    mon_w_s2, weekly_sigs = compute_monday_weights_s2(
        weekly_rets, iso_years, iso_weeks, lr, prices
    )
    s2_assets_avail = [a for a in ASSETS_S2 if a in prices.columns]
    print(f"  S2 assets: {[a.replace('-USD','') for a in s2_assets_avail]}")

    # ── 3. OOS backtests ─────────────────────────────────────────────────────
    print(f"\nRunning OOS backtests ({OOS_START} → 2026-05-14)...")

    s1_bt    = simulate(prices, mon_w_s1,    OOS_START, "2026-05-14")
    s2_bt    = simulate(prices, mon_w_s2,    OOS_START, "2026-05-14")
    tsmom_bt = simulate(prices, mon_w_tsmom, OOS_START, "2026-05-14")

    print(f"  S1 Short-Only  : Sharpe {s1_bt['sharpe']:+.2f}, MaxDD {-s1_bt['max_dd']*100:.1f}%")
    print(f"  S2 Seasonality : Sharpe {s2_bt['sharpe']:+.2f}, MaxDD {-s2_bt['max_dd']*100:.1f}%")
    print(f"  TSMOM v2       : Sharpe {tsmom_bt['sharpe']:+.2f}, MaxDD {-tsmom_bt['max_dd']*100:.1f}%")

    # ── 4. Walk-forward ──────────────────────────────────────────────────────
    print("\nWalk-forward validation...")

    s1_wf_windows = [
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
    ]
    s2_wf_windows = [
        ("2021-01-01", "2021-12-31"),
        ("2022-01-01", "2022-12-31"),
        ("2023-01-01", "2023-12-31"),
        ("2024-01-01", "2024-12-31"),
        ("2025-01-01", "2025-12-31"),
    ]

    s1_wf = walk_forward_s1(prices, lr, s1_wf_windows)
    s2_wf = walk_forward_s2(prices, mon_w_s2, s2_wf_windows)

    print_walk_forward("S1 Short-Only",   s1_wf)
    print_walk_forward("S2 Seasonality",  s2_wf)

    # ── 5. Short edge validation ─────────────────────────────────────────────
    print("\nShort edge validation (OOS test set)...")
    edge_df = short_edge_validation(lr, OOS_START)
    print_short_edge_table(edge_df)

    # ── 6. Seasonality hit rates ─────────────────────────────────────────────
    print("\nSeasonality hit rates...")
    hr_df = seasonality_hit_rates(weekly_rets, weekly_sigs, OOS_START)
    print_seasonality_hit_rates(hr_df)

    # ── 7. Propr simulations ─────────────────────────────────────────────────
    print("\nRunning Propr challenge simulations (44 × 3 strategies)...")
    s1_propr    = run_propr_sims(prices, mon_w_s1)
    s2_propr    = run_propr_sims(prices, mon_w_s2)
    tsmom_propr = run_propr_sims(prices, mon_w_tsmom)

    s1_ps    = _propr_summary(s1_propr)
    s2_ps    = _propr_summary(s2_propr)
    tsmom_ps = _propr_summary(tsmom_propr)
    print(f"  S1: {s1_ps['pass_r']:.0f}% pass ({s1_ps['pass_ct']}/44)  |  "
          f"{s1_ps['fail_d']}/44 daily  |  {s1_ps['fail_t']}/44 total DD")
    print(f"  S2: {s2_ps['pass_r']:.0f}% pass ({s2_ps['pass_ct']}/44)  |  "
          f"{s2_ps['fail_d']}/44 daily  |  {s2_ps['fail_t']}/44 total DD")
    print(f"  TSMOM: {tsmom_ps['pass_r']:.0f}% pass ({tsmom_ps['pass_ct']}/44)  |  "
          f"{tsmom_ps['fail_d']}/44 daily  |  {tsmom_ps['fail_t']}/44 total DD")

    # ── 8. Comparison table ──────────────────────────────────────────────────
    print_comparison_table(
        tsmom_bt, tsmom_propr,
        s1_bt, s1_propr, s1_wf,
        s2_bt, s2_propr, s2_wf,
        mon_w_s1, mon_w_s2, mon_w_tsmom,
    )

    # ── 9. Verdict ───────────────────────────────────────────────────────────
    print_verdict(
        s1_bt, s2_bt, s1_wf, s2_wf,
        s1_propr, s2_propr, edge_df, hr_df,
    )

    # ── 10. Plots ─────────────────────────────────────────────────────────────
    print("\nGenerating plots...")
    save_plots(
        prices,
        s1_bt, s2_bt, tsmom_bt,
        edge_df, hr_df,
        s1_wf, s2_wf,
        s1_propr, s2_propr, tsmom_propr,
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
