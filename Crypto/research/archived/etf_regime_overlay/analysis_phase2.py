"""
Phase 2 — Conditional analysis: Gate 2 evaluation.

Gate 2 criterion (pre-registered in HYPOTHESIS.md):
    E[A_return | regime_active] - E[A_return | regime_inactive] > 0.10%/day
    HAC-corrected t-stat (Newey-West, lag=6); τ = +0.5σ (pre-registered).

Reads:  data/etf_flows_raw.parquet
        data/stablecoin_supply_raw.parquet
        (crypto prices fetched from Binance via ccxt if not cached)

Outputs: data/phase2_results.json
         phase2_regime_plot.png
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add repo root to path for strategy imports
REPO_ROOT = Path(__file__).parents[4]
sys.path.insert(0, str(REPO_ROOT))

from strategies.tsmom_v2_propfirm.config import UNIVERSE, LOOKBACK_DAYS, REBALANCE_WEEKDAY
from strategies.tsmom_v2_propfirm.signal import compute_signal, apply_weekly_rebalance

DATA_DIR = Path(__file__).parent / "data"
RESULTS_PATH = DATA_DIR / "phase2_results.json"

TAU = 0.5       # pre-registered threshold — do not change
HAC_LAG = 6     # mandatory HAC correction per HYPOTHESIS.md §L12b

# ── Data loading ──────────────────────────────────────────────────────────────

def load_etf_flows() -> pd.Series:
    df = pd.read_parquet(DATA_DIR / "etf_flows_raw.parquet")
    return df["net_flow_all"].rename("net_flow")


def load_stablecoin_supply() -> pd.Series:
    df = pd.read_parquet(DATA_DIR / "stablecoin_supply_raw.parquet")
    return df["total_supply_usd"].rename("stable_supply")


def fetch_prices(universe: list[str], start: str, end: str) -> pd.DataFrame:
    """Fetch daily close prices from Yahoo Finance. Returns DataFrame indexed by Date."""
    prices_cache = DATA_DIR / "prices_cache.parquet"
    if prices_cache.exists():
        cached = pd.read_parquet(prices_cache)
        if (cached.index[0].date().isoformat() <= start
                and cached.index[-1].date().isoformat() >= end):
            print(f"  Using cached prices: {cached.shape}")
            return cached

    print("  Fetching prices from Yahoo Finance ...")
    import yfinance as yf
    import warnings

    # yfinance tickers: BTC-USD, ETH-USD, etc. — native format for universe
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw = yf.download(universe, start=start, end=end,
                          auto_adjust=True, progress=False)

    if isinstance(raw.columns, pd.MultiIndex):
        prices = raw["Close"]
    else:
        prices = raw[["Close"]].rename(columns={"Close": universe[0]})

    prices.index = pd.to_datetime(prices.index).normalize()
    prices = prices.sort_index()
    prices.to_parquet(prices_cache)
    print(f"  Fetched {prices.shape[1]} assets, {len(prices)} rows, "
          f"{prices.index[0].date()} → {prices.index[-1].date()}")
    return prices


# ── Regime score ──────────────────────────────────────────────────────────────

def compute_regime_score(
    net_flow: pd.Series,
    stable_supply: pd.Series,
    flow_smooth: int = 7,
    stable_smooth: int = 7,
    z_window: int = 30,
) -> pd.Series:
    """
    Deterministic regime score (no fitting).

    flow_7d(t)      = rolling 7-day sum of net ETF flow
    Δstable_7d(t)   = 7-day pct growth of stablecoin supply
    regime_score(t) = 0.5 × z_30d(flow_7d) + 0.5 × z_30d(Δstable_7d)

    All operations on calendar-day series; result indexed by calendar day.
    .shift(1) is applied at the call site (backtest) to enforce T-1 use.
    """
    flow_7d = net_flow.rolling(flow_smooth).sum()
    flow_z = (
        (flow_7d - flow_7d.rolling(z_window).mean())
        / (flow_7d.rolling(z_window).std() + 1e-8)
    )

    delta_7d = stable_supply.pct_change(stable_smooth)
    stable_z = (
        (delta_7d - delta_7d.rolling(z_window).mean())
        / (delta_7d.rolling(z_window).std() + 1e-8)
    )

    return (0.5 * flow_z + 0.5 * stable_z).rename("regime_score")


# ── HAC t-stat ────────────────────────────────────────────────────────────────

def hac_t_stat(x: pd.Series, lag: int = HAC_LAG) -> tuple[float, float, float]:
    """
    Newey-West HAC t-stat for H0: E[x] = 0.

    Returns (mean, hac_se, t_stat).
    """
    n = len(x)
    mean = x.mean()
    # Newey-West sandwich estimator
    gamma0 = np.sum((x - mean) ** 2) / n
    nw_var = gamma0
    for k in range(1, lag + 1):
        w = 1.0 - k / (lag + 1.0)
        cov_k = np.sum((x.iloc[k:].values - mean) * (x.iloc[:-k].values - mean)) / n
        nw_var += 2 * w * cov_k
    hac_se = np.sqrt(max(nw_var, 0) / n)
    t = mean / hac_se if hac_se > 1e-10 else 0.0
    return float(mean), float(hac_se), float(t)


# ── Phase 2 analysis ──────────────────────────────────────────────────────────

def run_phase2() -> dict:
    print("\n=== Phase 2: Conditional Analysis (Gate 2) ===")
    print(f"  TAU = {TAU}, HAC_LAG = {HAC_LAG}")

    # 1. Load macro data
    net_flow = load_etf_flows()
    stable_supply = load_stablecoin_supply()
    print(f"\nETF flows: {len(net_flow)} days, {net_flow.index[0].date()} → {net_flow.index[-1].date()}")
    print(f"Stablecoin: {len(stable_supply)} days, {stable_supply.index[0].date()} → {stable_supply.index[-1].date()}")

    # 2. Compute regime score on full calendar-day index
    all_dates = pd.date_range(
        start=min(net_flow.index[0], stable_supply.index[0]),
        end=max(net_flow.index[-1], stable_supply.index[-1]),
        freq="D",
    )
    net_flow_cal = net_flow.reindex(all_dates, method="ffill")
    stable_cal = stable_supply.reindex(all_dates, method="ffill")

    regime_score = compute_regime_score(net_flow_cal, stable_cal)
    print(f"\nRegime score: {regime_score.dropna().shape[0]} non-NaN days")
    print(f"  mean={regime_score.mean():.3f}, std={regime_score.std():.3f}")
    print(f"  % > {TAU}: {(regime_score > TAU).mean() * 100:.1f}%")

    # 3. Fetch/load Strategy A prices
    start_date = "2024-01-11"
    end_date = regime_score.dropna().index[-1].date().isoformat()
    prices = fetch_prices(UNIVERSE, start_date, end_date)

    # 4. Compute Strategy A signal
    signal = compute_signal(prices, lookback=LOOKBACK_DAYS)
    weekly_signal = apply_weekly_rebalance(signal, rebalance_weekday=REBALANCE_WEEKDAY)

    # 5. Compute daily Strategy A returns (equal-weight, no vol-targeting for IC analysis)
    log_returns = np.log(prices / prices.shift(1))
    # Portfolio return: mean of signal × next-day return across assets
    # signal at t (Monday rebalance, T-1 data) × log_return at t+1 (T)
    strategy_returns = (weekly_signal.shift(1) * log_returns).mean(axis=1).dropna()
    strategy_returns.name = "strategy_A_ret"

    # Align regime score (T-1 shift applied here)
    regime_t1 = regime_score.reindex(strategy_returns.index, method="ffill").shift(1)
    regime_active = regime_t1 > TAU

    common_idx = strategy_returns.index.intersection(regime_active.dropna().index)
    strat = strategy_returns.reindex(common_idx)
    active = regime_active.reindex(common_idx)

    # 6. Conditional return statistics
    ret_active = strat[active]
    ret_inactive = strat[~active]

    mean_active = ret_active.mean()
    mean_inactive = ret_inactive.mean()
    diff = mean_active - mean_inactive

    # HAC t-stat on difference series
    diff_series = strat.copy()
    diff_series[:] = np.nan
    diff_series[active] = strat[active] - mean_inactive
    diff_series[~active] = strat[~active] - mean_active
    # Simpler: HAC on the centered difference
    diff_centered = pd.Series(
        np.where(active.values, strat.values - mean_inactive, strat.values - mean_active),
        index=common_idx,
    )
    # Standard: run HAC on (ret_active - E[ret_inactive]) separately
    _, _, t_active = hac_t_stat(ret_active - mean_inactive)
    _, _, t_diff_raw = hac_t_stat(diff_centered)

    # Sharpe (annualized, no cost adjustment)
    sharpe_active = mean_active / (ret_active.std() + 1e-8) * np.sqrt(365)
    sharpe_inactive = mean_inactive / (ret_inactive.std() + 1e-8) * np.sqrt(365)
    sharpe_unfiltered = strat.mean() / (strat.std() + 1e-8) * np.sqrt(365)

    # Time in market
    pct_active = active.mean()

    print(f"\n--- Gate 2 Results ---")
    print(f"  Period: {common_idx[0].date()} → {common_idx[-1].date()} ({len(common_idx)} days)")
    print(f"  Time-in-market (regime_active): {pct_active * 100:.1f}%  [expected ~31% at τ=+0.5σ]")
    print(f"  Days active: {active.sum()}, inactive: {(~active).sum()}")
    print(f"\n  E[ret | active]   = {mean_active * 100:.4f}%/day  (Sharpe ann = {sharpe_active:.2f})")
    print(f"  E[ret | inactive] = {mean_inactive * 100:.4f}%/day  (Sharpe ann = {sharpe_inactive:.2f})")
    print(f"  Difference        = {diff * 100:.4f}%/day")
    print(f"  HAC t-stat (lag={HAC_LAG}): {t_diff_raw:.2f}")
    print(f"  Unfiltered Sharpe: {sharpe_unfiltered:.2f}")

    # 7. Gate 2 evaluation
    GATE2_PASS_THRESHOLD = 0.0010   # 0.10%/day
    GATE2_BORDERLINE = 0.0005       # 0.05%/day
    if diff >= GATE2_PASS_THRESHOLD:
        gate2 = "PASS"
        gate2_msg = f"Δ={diff*100:.4f}%/day ≥ 0.10%/day → PROCEED to Phase 3"
    elif diff >= GATE2_BORDERLINE:
        gate2 = "BORDERLINE"
        gate2_msg = f"Δ={diff*100:.4f}%/day ∈ [0.05%, 0.10%)/day → FLAG for user decision"
    else:
        gate2 = "FAIL"
        gate2_msg = f"Δ={diff*100:.4f}%/day < 0.05%/day → STOP, archive"

    print(f"\n  Gate 2: {gate2} — {gate2_msg}")

    # 8. Robustness: per-year conditional returns
    print("\n--- Per-year breakdown ---")
    for year in sorted(strat.index.year.unique()):
        mask = strat.index.year == year
        yr_strat = strat[mask]
        yr_active = active[mask]
        if yr_active.sum() < 5 or (~yr_active).sum() < 5:
            continue
        yr_diff = yr_strat[yr_active].mean() - yr_strat[~yr_active].mean()
        print(f"  {year}: Δ={yr_diff*100:.4f}%/day, "
              f"active={yr_active.sum()}d, inactive={(~yr_active).sum()}d")

    results = {
        "gate2": gate2,
        "gate2_msg": gate2_msg,
        "tau": TAU,
        "hac_lag": HAC_LAG,
        "period_start": common_idx[0].date().isoformat(),
        "period_end": common_idx[-1].date().isoformat(),
        "n_days_total": int(len(common_idx)),
        "n_days_active": int(active.sum()),
        "n_days_inactive": int((~active).sum()),
        "pct_active": float(pct_active),
        "mean_ret_active_pct_per_day": float(mean_active * 100),
        "mean_ret_inactive_pct_per_day": float(mean_inactive * 100),
        "diff_pct_per_day": float(diff * 100),
        "hac_t_stat": float(t_diff_raw),
        "sharpe_active_ann": float(sharpe_active),
        "sharpe_inactive_ann": float(sharpe_inactive),
        "sharpe_unfiltered_ann": float(sharpe_unfiltered),
        "regime_score_mean": float(regime_score.mean()),
        "regime_score_std": float(regime_score.std()),
    }

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved → {RESULTS_PATH}")

    return results


if __name__ == "__main__":
    results = run_phase2()
