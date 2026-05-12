#!/usr/bin/env python
"""
Market-Neutral Feasibility Check — 3 strategies on crypto perps.

Strategies tested:
  A. Cross-Sectional Funding Carry (Hyperliquid, 12 assets, hourly rebalance)
  B. BTC/ETH Stat-Arb (z-score of log spread, 1h bars)
  C. Overnight Gap Mean Reversion (00:00–08:00 UTC gaps >1.5%, daily 08:00 UTC)

5-Step protocol per strategy:
  1. Raw signal t-test (threshold 2.0)
  2. Net Sharpe after costs (threshold > 0.5)
  3. Beta to BTC (threshold < 0.20)
  4. Walk-forward (4 folds, 70/30 split)
  5. Propr daily loss limit simulation

Usage:
    python -m strategies.market_neutral.feasibility
"""

from __future__ import annotations

import json
import time
import warnings
from datetime import datetime, timezone
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import scipy.stats as stats
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Constants ────────────────────────────────────────────────────────────────

RESULTS_PNG = "strategies/market_neutral/feasibility_results.png"

# Thresholds
T_STAT_THRESHOLD   = 2.0
SHARPE_THRESHOLD   = 0.5
BETA_THRESHOLD     = 0.20
WF_SHARPE_MIN      = 0.0   # each fold must be positive
PROPR_DAILY_LIMIT  = 0.03  # 3% daily loss limit

# Strategy A — Funding carry
CARRY_ASSETS = [
    "BTC", "ETH", "SOL", "BNB", "XRP",
    "DOGE", "ADA", "AVAX", "LINK", "DOT",
    "MATIC", "UNI",
]
CARRY_COST_RT = 0.0007   # 0.07% round-trip taker fee
FUNDING_LOOKBACK_H = 8   # hours of funding to average for signal

# Strategy B — Stat-Arb
STAT_ARB_WINDOW  = 30 * 24   # 30d in hours
STAT_ARB_ENTRY   = 1.5       # z-score entry threshold
STAT_ARB_EXIT    = 0.5       # z-score exit
STAT_ARB_STOP    = 3.0       # z-score stop-loss
STAT_ARB_COST_RT = 0.0009    # 0.09% RT (two legs)

# Strategy C — Overnight Gap
GAP_THRESHOLD  = 0.015   # 1.5% gap to trigger fade
GAP_COST_RT    = 0.0009  # 0.09% RT
GAP_ASSETS     = ["BTC-USD", "ETH-USD", "SOL-USD"]

TSMOM_BASELINE_DAILY_BREACHES = 26  # from challenge simulator


# ═══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING
# ═══════════════════════════════════════════════════════════════════════════════

def fetch_hyperliquid_funding(coin: str, days_back: int = 365) -> pd.Series:
    """
    Fetch funding rates for `coin` from Hyperliquid with pagination.
    Hyperliquid returns ~500 records per request (8h intervals → ~167 days).
    We paginate backwards in time to cover the full `days_back` window.
    """
    url = "https://api.hyperliquid.xyz/info"
    all_rows: list[tuple] = []
    end_ms = int(time.time() * 1000)
    start_ms = int((time.time() - days_back * 86400) * 1000)

    cursor_ms = end_ms
    MAX_PAGES = 6
    for _page in range(MAX_PAGES):
        page_start = max(start_ms, cursor_ms - 180 * 86400 * 1000)  # 180-day chunks
        payload = {"type": "fundingHistory", "coin": coin,
                   "startTime": page_start, "endTime": cursor_ms}
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  [WARN] Hyperliquid funding page {_page} failed for {coin}: {exc}")
            break
        if not data:
            break
        for item in data:
            ts = pd.to_datetime(int(item["time"]), unit="ms", utc=True)
            rate = float(item["fundingRate"])
            all_rows.append((ts, rate))
        # advance cursor to just before the earliest record returned
        earliest_in_page = min(int(item["time"]) for item in data)
        if earliest_in_page <= start_ms:
            break
        cursor_ms = earliest_in_page - 1
        time.sleep(0.05)

    if not all_rows:
        return pd.Series(dtype=float)
    s = pd.Series(
        [r[1] for r in all_rows],
        index=pd.DatetimeIndex([r[0] for r in all_rows]),
        name=coin,
    )
    return s.sort_index().drop_duplicates()


def fetch_hyperliquid_prices(coin: str, days_back: int = 365) -> pd.Series:
    """Fetch hourly close prices for `coin` from Hyperliquid candles with pagination."""
    url = "https://api.hyperliquid.xyz/info"
    all_rows: list[tuple] = []
    end_ms = int(time.time() * 1000)
    start_ms = int((time.time() - days_back * 86400) * 1000)

    cursor_ms = start_ms
    MAX_PAGES = 6
    for _page in range(MAX_PAGES):
        payload = {
            "type": "candleSnapshot",
            "req": {"coin": coin, "interval": "1h",
                    "startTime": cursor_ms, "endTime": end_ms},
        }
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            print(f"  [WARN] Hyperliquid price page {_page} failed for {coin}: {exc}")
            break
        if not data:
            break
        for candle in data:
            ts = pd.to_datetime(int(candle["t"]), unit="ms", utc=True)
            close = float(candle["c"])
            all_rows.append((ts, close))
        latest_in_page = max(int(candle["t"]) for candle in data)
        if latest_in_page >= end_ms - 3600 * 1000:
            break
        cursor_ms = latest_in_page + 1
        time.sleep(0.05)

    if not all_rows:
        return pd.Series(dtype=float)
    s = pd.Series(
        [r[1] for r in all_rows],
        index=pd.DatetimeIndex([r[0] for r in all_rows]),
        name=coin,
    )
    return s.sort_index().drop_duplicates()


def fetch_binance_funding_fallback(symbol_map: dict[str, str], days_back: int = 365) -> pd.DataFrame:
    """Fallback: fetch 8h funding rates from Binance Futures."""
    dfs = {}
    limit = min(1000, days_back * 3)   # 3 × 8h per day
    for coin, symbol in symbol_map.items():
        url = (
            f"https://fapi.binance.com/fapi/v1/fundingRate"
            f"?symbol={symbol}&limit={limit}"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            rows = [(pd.to_datetime(int(r["fundingTime"]), unit="ms", utc=True),
                     float(r["fundingRate"])) for r in data]
            s = pd.Series([r[1] for r in rows],
                          index=pd.DatetimeIndex([r[0] for r in rows]),
                          name=coin)
            dfs[coin] = s.sort_index()
        except Exception as exc:
            print(f"  [WARN] Binance funding fetch failed for {symbol}: {exc}")
    if dfs:
        return pd.DataFrame(dfs).sort_index()
    return pd.DataFrame()


def fetch_1h_prices_yf(assets: list[str], days_back: int = 365) -> pd.DataFrame:
    """Fetch 1h close prices via yfinance."""
    period = f"{min(days_back, 729)}d"
    raw = yf.download(
        tickers=assets,
        period=period,
        interval="1h",
        auto_adjust=True,
        progress=False,
        threads=True,
    )
    if raw.empty:
        return pd.DataFrame()
    if isinstance(raw.columns, pd.MultiIndex):
        closes = raw["Close"]
    else:
        closes = raw[["Close"]] if "Close" in raw.columns else raw
    closes.index = closes.index.tz_localize("UTC") if closes.index.tz is None else closes.index.tz_convert("UTC")
    return closes.sort_index()


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY A — CROSS-SECTIONAL FUNDING CARRY
# ═══════════════════════════════════════════════════════════════════════════════

def _strategy_a_signals_and_returns(
    funding_df: pd.DataFrame,
    prices_df: pd.DataFrame,
) -> tuple[pd.Series, pd.Series]:
    """
    Hourly cross-sectional funding carry.

    Signal: at each hour, rank assets by average funding rate over last
    FUNDING_LOOKBACK_H periods. Long bottom tercile (lowest funding = funding receivers),
    short top tercile (highest funding = funding payers).

    Returns: (gross_hourly_returns, funding_collected_hourly)
    """
    # Align indices
    common_idx = funding_df.index.intersection(prices_df.index)
    funding_df = funding_df.loc[common_idx]
    prices_df  = prices_df.loc[common_idx]

    # Rolling mean funding signal (lookback window)
    roll_funding = funding_df.rolling(FUNDING_LOOKBACK_H, min_periods=1).mean()

    hourly_rets = prices_df.pct_change()
    port_rets   = []
    fund_coll   = []

    for i in range(FUNDING_LOOKBACK_H, len(common_idx) - 1):
        sig_row    = roll_funding.iloc[i].dropna()
        if len(sig_row) < 4:
            port_rets.append(np.nan)
            fund_coll.append(np.nan)
            continue

        tercile = len(sig_row) // 3
        ranked  = sig_row.sort_values()
        longs   = ranked.index[:tercile]     # lowest funding → we receive
        shorts  = ranked.index[-tercile:]    # highest funding → we pay

        # Price returns (long − short)
        long_ret  = hourly_rets.iloc[i + 1][longs].mean()
        short_ret = hourly_rets.iloc[i + 1][shorts].mean()
        price_ret = long_ret - short_ret

        # Funding collected: longs collect funding when positive, pay when negative
        # shorts collect when negative (we're short, funding is positive → we pay, effectively +ve for us)
        fund_long  = funding_df.iloc[i][longs].mean()
        fund_short = funding_df.iloc[i][shorts].mean()
        fund_net   = fund_long - fund_short   # net funding income per 8h settled at hour

        port_rets.append(price_ret)
        fund_coll.append(fund_net)

    idx_slice = common_idx[FUNDING_LOOKBACK_H + 1:]
    return (
        pd.Series(port_rets, index=idx_slice, name="carry_price_ret"),
        pd.Series(fund_coll, index=idx_slice, name="carry_funding"),
    )


def run_strategy_a(days_back: int = 365) -> dict[str, Any]:
    print("\n" + "="*60)
    print("STRATEGY A: Cross-Sectional Funding Carry")
    print("="*60)

    # 1. Fetch data
    print("  Fetching funding rates from Hyperliquid...")
    funding_series: dict[str, pd.Series] = {}
    prices_series:  dict[str, pd.Series] = {}

    for coin in CARRY_ASSETS:
        f = fetch_hyperliquid_funding(coin, days_back)
        p = fetch_hyperliquid_prices(coin, days_back)
        if len(f) > 100 and len(p) > 100:
            funding_series[coin] = f
            prices_series[coin]  = p
        time.sleep(0.1)

    # Always use yfinance for prices (more reliable, longer history)
    yf_symbols = [f"{a}-USD" for a in CARRY_ASSETS]
    print("  Fetching 1h prices from yfinance...")
    prices_yf = fetch_1h_prices_yf(yf_symbols, days_back)
    if not prices_yf.empty:
        prices_yf.columns = [c.replace("-USD", "") for c in prices_yf.columns]

    if len(funding_series) < 4:
        print("  [FALLBACK] Hyperliquid returned < 4 assets, trying Binance...")
        symbol_map = {a: f"{a}USDT" for a in CARRY_ASSETS}
        funding_df_fb = fetch_binance_funding_fallback(symbol_map, days_back)
        if funding_df_fb.empty:
            print("  [ERROR] Both Hyperliquid and Binance funding fetch failed.")
            return {"strategy": "A", "verdict": "DATA_ERROR", "passed": False}
        # Binance funding is 8h — forward-fill to hourly
        funding_df = funding_df_fb.resample("1h").ffill()
    else:
        # Resample Hyperliquid funding (8h intervals) to hourly for alignment
        funding_df = pd.DataFrame(funding_series).resample("1h").ffill()

    prices_df = prices_yf if not prices_yf.empty else pd.DataFrame(prices_series)

    # Align common columns
    common_cols = list(set(funding_df.columns) & set(prices_df.columns))
    if len(common_cols) < 4:
        print(f"  [ERROR] Only {len(common_cols)} assets with both funding and prices.")
        return {"strategy": "A", "verdict": "DATA_ERROR", "passed": False}

    funding_df = funding_df[common_cols].sort_index()
    prices_df  = prices_df[common_cols].sort_index()

    print(f"  Data: {len(funding_df)} funding bars, {len(prices_df)} price bars, {len(common_cols)} assets")

    # 2. Signals and returns
    price_rets, funding_coll = _strategy_a_signals_and_returns(funding_df, prices_df)
    total_rets = (price_rets + funding_coll).dropna()

    if len(total_rets) < 100:
        print(f"  [ERROR] Insufficient return observations ({len(total_rets)}).")
        return {"strategy": "A", "verdict": "DATA_ERROR", "passed": False}

    # Train/test split (70/30)
    split = int(len(total_rets) * 0.70)
    train_rets = total_rets.iloc[:split]
    test_rets  = total_rets.iloc[split:]

    # Step 1 — Raw signal t-test on TEST set
    t_stat, p_val = stats.ttest_1samp(test_rets.dropna(), 0.0)
    print(f"\n  Step 1 — Raw signal t-test (test set):")
    print(f"    t-stat = {t_stat:.3f}  (threshold ≥ {T_STAT_THRESHOLD})")
    step1_pass = abs(t_stat) >= T_STAT_THRESHOLD

    # Step 2 — Net Sharpe after costs
    # Costs applied at every rebalance (each hour = 1 trade)
    net_rets = test_rets - CARRY_COST_RT / 2  # per-bar cost (one-way per hour)
    ann_factor = np.sqrt(24 * 365)
    sharpe_net = (net_rets.mean() / net_rets.std()) * ann_factor if net_rets.std() > 0 else 0.0
    sharpe_gross = (test_rets.mean() / test_rets.std()) * ann_factor if test_rets.std() > 0 else 0.0
    print(f"\n  Step 2 — Net Sharpe after costs:")
    print(f"    Sharpe gross = {sharpe_gross:.3f}")
    print(f"    Sharpe net   = {sharpe_net:.3f}  (threshold ≥ {SHARPE_THRESHOLD})")
    step2_pass = sharpe_net >= SHARPE_THRESHOLD

    # Step 3 — Beta to BTC
    btc_prices = prices_df.get("BTC", prices_df.iloc[:, 0])
    btc_rets = btc_prices.pct_change().reindex(test_rets.index).dropna()
    aligned_strat = net_rets.reindex(btc_rets.index).dropna()
    aligned_btc   = btc_rets.reindex(aligned_strat.index)
    if len(aligned_strat) > 30:
        beta_result = np.polyfit(aligned_btc.values, aligned_strat.values, 1)
        beta = beta_result[0]
    else:
        beta = 0.0
    print(f"\n  Step 3 — Beta to BTC:")
    print(f"    Beta = {beta:.4f}  (threshold |β| < {BETA_THRESHOLD})")
    step3_pass = abs(beta) < BETA_THRESHOLD

    # Step 4 — Walk-forward (4 folds on TEST set)
    fold_sharpes = []
    fold_size = len(test_rets) // 4
    for i in range(4):
        fold = net_rets.iloc[i * fold_size: (i + 1) * fold_size]
        if fold.std() > 0:
            fs = (fold.mean() / fold.std()) * ann_factor
        else:
            fs = 0.0
        fold_sharpes.append(fs)
    print(f"\n  Step 4 — Walk-forward (4 folds):")
    for i, fs in enumerate(fold_sharpes):
        mark = "✓" if fs > WF_SHARPE_MIN else "✗"
        print(f"    Fold {i+1}: Sharpe = {fs:.3f} {mark}")
    wf_pass_count = sum(1 for fs in fold_sharpes if fs > WF_SHARPE_MIN)
    step4_pass = wf_pass_count >= 3

    # Step 5 — Propr daily loss limit simulation
    # Convert hourly returns to daily
    daily_rets_test = (1 + net_rets).resample("1D").prod() - 1
    daily_breach_count = (daily_rets_test < -PROPR_DAILY_LIMIT).sum()
    print(f"\n  Step 5 — Propr daily loss limit (3%):")
    print(f"    Days exceeding limit: {daily_breach_count}  (TSMOM baseline: {TSMOM_BASELINE_DAILY_BREACHES})")
    step5_pass = daily_breach_count <= TSMOM_BASELINE_DAILY_BREACHES

    # Verdict
    steps_passed = sum([step1_pass, step2_pass, step3_pass, step4_pass, step5_pass])
    overall_pass = steps_passed >= 4  # must pass at least 4/5
    verdict = "VIABLE" if overall_pass else "SKIP"

    print(f"\n  VERDICT: {verdict} ({steps_passed}/5 steps passed)")

    return {
        "strategy": "A",
        "name": "CS Funding Carry",
        "verdict": verdict,
        "passed": overall_pass,
        "t_stat": t_stat,
        "sharpe_gross": sharpe_gross,
        "sharpe_net": sharpe_net,
        "beta_btc": beta,
        "wf_pass_count": wf_pass_count,
        "daily_breaches": int(daily_breach_count),
        "steps_passed": steps_passed,
        "step1": step1_pass, "step2": step2_pass, "step3": step3_pass,
        "step4": step4_pass, "step5": step5_pass,
        "net_rets_test": net_rets,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY B — BTC/ETH STAT-ARB
# ═══════════════════════════════════════════════════════════════════════════════

def _stat_arb_positions(log_spread: pd.Series, z_score: pd.Series) -> pd.Series:
    """
    Generate position series from z-score.
    +1 = long spread (long BTC, short ETH)
    -1 = short spread (short BTC, long ETH)
     0 = flat
    """
    position = pd.Series(0.0, index=z_score.index)
    pos = 0.0

    for i in range(1, len(z_score)):
        z = z_score.iloc[i]
        if np.isnan(z):
            position.iloc[i] = 0.0
            pos = 0.0
            continue

        if pos == 0.0:
            if z >= STAT_ARB_ENTRY:
                pos = -1.0   # spread high → short spread
            elif z <= -STAT_ARB_ENTRY:
                pos = 1.0    # spread low → long spread
        elif pos == 1.0:
            if z >= -STAT_ARB_EXIT or z <= -STAT_ARB_STOP:
                pos = 0.0
        elif pos == -1.0:
            if z <= STAT_ARB_EXIT or z >= STAT_ARB_STOP:
                pos = 0.0

        position.iloc[i] = pos

    return position


def run_strategy_b(days_back: int = 365) -> dict[str, Any]:
    print("\n" + "="*60)
    print("STRATEGY B: BTC/ETH Stat-Arb")
    print("="*60)

    # 1. Fetch 1h data
    print("  Fetching 1h price data from yfinance...")
    prices = fetch_1h_prices_yf(["BTC-USD", "ETH-USD"], days_back)
    if prices.empty or prices.shape[1] < 2:
        print("  [ERROR] Could not fetch price data.")
        return {"strategy": "B", "verdict": "DATA_ERROR", "passed": False}

    # Normalize column names
    prices.columns = [c.replace("-USD", "") for c in prices.columns]
    prices = prices.dropna()

    print(f"  Data: {len(prices)} hourly bars")

    # Compute log spread and z-score
    log_spread = np.log(prices["BTC"] / prices["ETH"])
    roll_mean = log_spread.rolling(STAT_ARB_WINDOW, min_periods=STAT_ARB_WINDOW // 2).mean()
    roll_std  = log_spread.rolling(STAT_ARB_WINDOW, min_periods=STAT_ARB_WINDOW // 2).std()
    z_score   = (log_spread - roll_mean) / roll_std

    # Train/test split (70/30)
    split = int(len(prices) * 0.70)
    z_test     = z_score.iloc[split:]
    spread_test = log_spread.iloc[split:]
    prices_test = prices.iloc[split:]

    # Step 1 — Raw signal: mean-reversion t-test
    # Signal: when z > ENTRY, expect reversion to mean → short spread next bar
    # Measure: 1-bar forward return conditioned on |z| > ENTRY
    signals = np.sign(-z_test.shift(1))  # -z because we fade extremes
    fwd_spread_ret = spread_test.diff()
    signal_rets = (signals * fwd_spread_ret).dropna()
    signal_rets = signal_rets[abs(z_test.shift(1).reindex(signal_rets.index)) >= STAT_ARB_ENTRY]

    if len(signal_rets) < 30:
        print("  [WARN] Very few signal observations — market rarely crosses entry threshold.")
        t_stat, p_val = 0.0, 1.0
    else:
        t_stat, p_val = stats.ttest_1samp(signal_rets.dropna(), 0.0)
    print(f"\n  Step 1 — Raw signal t-test (test set):")
    print(f"    N signal obs  = {len(signal_rets)}")
    print(f"    t-stat = {t_stat:.3f}  (threshold ≥ {T_STAT_THRESHOLD})")
    step1_pass = abs(t_stat) >= T_STAT_THRESHOLD

    # Step 2 — Full backtest with entry/exit/stop, costs
    position = _stat_arb_positions(spread_test, z_test)
    btc_ret = prices_test["BTC"].pct_change()
    eth_ret = prices_test["ETH"].pct_change()
    spread_return = btc_ret - eth_ret  # long BTC, short ETH
    strat_ret = (position.shift(1) * spread_return).dropna()

    # Apply costs on position changes
    pos_changes = position.diff().abs()
    costs = pos_changes * STAT_ARB_COST_RT
    net_strat_ret = strat_ret - costs.reindex(strat_ret.index).fillna(0)

    ann_factor = np.sqrt(24 * 365)
    sharpe_gross = (strat_ret.mean() / strat_ret.std() * ann_factor) if strat_ret.std() > 0 else 0.0
    sharpe_net   = (net_strat_ret.mean() / net_strat_ret.std() * ann_factor) if net_strat_ret.std() > 0 else 0.0
    print(f"\n  Step 2 — Net Sharpe after costs:")
    print(f"    Sharpe gross = {sharpe_gross:.3f}")
    print(f"    Sharpe net   = {sharpe_net:.3f}  (threshold ≥ {SHARPE_THRESHOLD})")
    step2_pass = sharpe_net >= SHARPE_THRESHOLD

    # Step 3 — Beta to BTC
    daily_net = (1 + net_strat_ret).resample("1D").prod() - 1
    daily_btc = (1 + btc_ret).resample("1D").prod() - 1
    aligned_strat = daily_net.dropna()
    aligned_btc   = daily_btc.reindex(aligned_strat.index).dropna()
    aligned_strat = aligned_strat.reindex(aligned_btc.index)
    if len(aligned_strat) > 30:
        beta = np.polyfit(aligned_btc.values, aligned_strat.values, 1)[0]
    else:
        beta = 0.0
    print(f"\n  Step 3 — Beta to BTC:")
    print(f"    Beta = {beta:.4f}  (threshold |β| < {BETA_THRESHOLD})")
    step3_pass = abs(beta) < BETA_THRESHOLD

    # Step 4 — Walk-forward (4 folds on TEST set)
    fold_sharpes = []
    fold_size = len(net_strat_ret) // 4
    for i in range(4):
        fold = net_strat_ret.iloc[i * fold_size: (i + 1) * fold_size]
        if fold.std() > 0:
            fs = (fold.mean() / fold.std()) * ann_factor
        else:
            fs = 0.0
        fold_sharpes.append(fs)
    print(f"\n  Step 4 — Walk-forward (4 folds):")
    for i, fs in enumerate(fold_sharpes):
        mark = "✓" if fs > WF_SHARPE_MIN else "✗"
        print(f"    Fold {i+1}: Sharpe = {fs:.3f} {mark}")
    wf_pass_count = sum(1 for fs in fold_sharpes if fs > WF_SHARPE_MIN)
    step4_pass = wf_pass_count >= 3

    # Step 5 — Propr daily loss limit simulation
    daily_breach_count = (daily_net < -PROPR_DAILY_LIMIT).sum()
    print(f"\n  Step 5 — Propr daily loss limit (3%):")
    print(f"    Days exceeding limit: {daily_breach_count}  (TSMOM baseline: {TSMOM_BASELINE_DAILY_BREACHES})")
    step5_pass = daily_breach_count <= TSMOM_BASELINE_DAILY_BREACHES

    # Verdict
    steps_passed = sum([step1_pass, step2_pass, step3_pass, step4_pass, step5_pass])
    overall_pass = steps_passed >= 4
    verdict = "VIABLE" if overall_pass else "SKIP"

    print(f"\n  VERDICT: {verdict} ({steps_passed}/5 steps passed)")

    return {
        "strategy": "B",
        "name": "BTC/ETH Stat-Arb",
        "verdict": verdict,
        "passed": overall_pass,
        "t_stat": t_stat,
        "sharpe_gross": sharpe_gross,
        "sharpe_net": sharpe_net,
        "beta_btc": beta,
        "wf_pass_count": wf_pass_count,
        "daily_breaches": int(daily_breach_count),
        "steps_passed": steps_passed,
        "step1": step1_pass, "step2": step2_pass, "step3": step3_pass,
        "step4": step4_pass, "step5": step5_pass,
        "net_rets_test": daily_net,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# STRATEGY C — OVERNIGHT GAP MEAN REVERSION
# ═══════════════════════════════════════════════════════════════════════════════

def _compute_overnight_gaps(prices_1h: pd.DataFrame) -> pd.DataFrame:
    """
    For each asset, compute the overnight gap: return from 00:00 UTC to 08:00 UTC.
    Returns a DataFrame of gap returns indexed by date (trading day start = 08:00 UTC).
    """
    gaps = {}
    for col in prices_1h.columns:
        series = prices_1h[col].dropna()
        # Price at 00:00 UTC each day (start of night)
        midnight = series[series.index.hour == 0]
        # Price at 08:00 UTC each day (end of night window)
        open_8am = series[series.index.hour == 8]

        # Align by date
        midnight_by_date = midnight.copy()
        midnight_by_date.index = midnight_by_date.index.normalize()
        open_8am_by_date = open_8am.copy()
        open_8am_by_date.index = open_8am_by_date.index.normalize()

        common_dates = midnight_by_date.index.intersection(open_8am_by_date.index)
        if len(common_dates) < 30:
            continue
        gap_ret = open_8am_by_date[common_dates] / midnight_by_date[common_dates] - 1
        gaps[col] = gap_ret

    if not gaps:
        return pd.DataFrame()
    return pd.DataFrame(gaps).sort_index()


def _gap_reversion_returns(gaps_df: pd.DataFrame) -> pd.Series:
    """
    At 08:00 UTC: fade gaps > GAP_THRESHOLD (i.e. sell if gap up, buy if gap down).
    Hold for 1 period (until next 08:00 UTC).
    Return is: -sign(gap) × next_day_return if |gap| > threshold, else 0.
    """
    # Next day's return (hold from 08:00 UTC to 08:00 UTC next day)
    # Use gap_df index aligned to daily close as proxy
    port_rets = []
    for i in range(len(gaps_df) - 1):
        row = gaps_df.iloc[i]
        # Filter assets with gap exceeding threshold
        triggered = row[row.abs() >= GAP_THRESHOLD]
        if len(triggered) == 0:
            port_rets.append(0.0)
            continue
        # Fade the gap: opposite sign of gap
        # Next day return (using gap_df.iloc[i+1] as proxy for full-day return)
        next_row = gaps_df.iloc[i + 1]
        signals = -np.sign(triggered)
        # Only use assets that also have a next-day return
        common = triggered.index.intersection(next_row.index)
        if len(common) == 0:
            port_rets.append(0.0)
            continue
        ret = (signals[common] * next_row[common]).mean()
        port_rets.append(ret)

    return pd.Series(port_rets, index=gaps_df.index[:-1], name="gap_rev_ret")


def run_strategy_c(days_back: int = 365) -> dict[str, Any]:
    print("\n" + "="*60)
    print("STRATEGY C: Overnight Gap Mean Reversion")
    print("="*60)

    # 1. Fetch 1h data
    print("  Fetching 1h price data from yfinance...")
    prices = fetch_1h_prices_yf(GAP_ASSETS, days_back)
    if prices.empty:
        print("  [ERROR] Could not fetch price data.")
        return {"strategy": "C", "verdict": "DATA_ERROR", "passed": False}
    prices.columns = [c.replace("-USD", "") for c in prices.columns]
    prices = prices.dropna(how="all")

    print(f"  Data: {len(prices)} hourly bars, {prices.shape[1]} assets")

    # 2. Compute overnight gaps
    gaps_df = _compute_overnight_gaps(prices)
    if gaps_df.empty or len(gaps_df) < 100:
        print("  [ERROR] Insufficient gap observations.")
        return {"strategy": "C", "verdict": "DATA_ERROR", "passed": False}
    print(f"  Overnight gaps: {len(gaps_df)} trading days, {gaps_df.shape[1]} assets")

    # Strategy returns (daily, based on 08:00 UTC)
    port_rets = _gap_reversion_returns(gaps_df)

    # Train/test split (70/30)
    split = int(len(port_rets) * 0.70)
    test_rets = port_rets.iloc[split:]

    # Only signal days (non-zero returns)
    signal_days = test_rets[test_rets != 0]
    print(f"  Signal frequency: {len(signal_days)}/{len(test_rets)} days ({100*len(signal_days)/max(len(test_rets),1):.1f}%)")

    # Step 1 — Raw signal t-test (signal days only)
    if len(signal_days) < 20:
        t_stat, p_val = 0.0, 1.0
        print(f"\n  Step 1 — Raw signal t-test: INSUFFICIENT DATA (N={len(signal_days)})")
    else:
        t_stat, p_val = stats.ttest_1samp(signal_days.dropna(), 0.0)
        print(f"\n  Step 1 — Raw signal t-test (signal days only):")
    print(f"    N signal days = {len(signal_days)}")
    print(f"    t-stat = {t_stat:.3f}  (threshold ≥ {T_STAT_THRESHOLD})")
    step1_pass = abs(t_stat) >= T_STAT_THRESHOLD

    # Step 2 — Net Sharpe (apply cost on signal days only)
    # Only signal days incur costs; non-signal days earn zero
    net_rets = test_rets.copy()
    net_rets[net_rets != 0] -= GAP_COST_RT
    ann_factor = np.sqrt(365)
    sharpe_gross = (test_rets.mean() / test_rets.std() * ann_factor) if test_rets.std() > 0 else 0.0
    sharpe_net   = (net_rets.mean() / net_rets.std() * ann_factor) if net_rets.std() > 0 else 0.0
    print(f"\n  Step 2 — Net Sharpe after costs:")
    print(f"    Sharpe gross = {sharpe_gross:.3f}")
    print(f"    Sharpe net   = {sharpe_net:.3f}  (threshold ≥ {SHARPE_THRESHOLD})")
    step2_pass = sharpe_net >= SHARPE_THRESHOLD

    # Step 3 — Beta to BTC
    btc_daily = prices["BTC"].resample("1D").last().pct_change() if "BTC" in prices.columns else None
    if btc_daily is not None:
        aligned_strat = net_rets.reindex(btc_daily.index).dropna()
        aligned_btc   = btc_daily.reindex(aligned_strat.index).dropna()
        aligned_strat = aligned_strat.reindex(aligned_btc.index)
        if len(aligned_strat) > 30:
            beta = np.polyfit(aligned_btc.values, aligned_strat.values, 1)[0]
        else:
            beta = 0.0
    else:
        beta = 0.0
    print(f"\n  Step 3 — Beta to BTC:")
    print(f"    Beta = {beta:.4f}  (threshold |β| < {BETA_THRESHOLD})")
    step3_pass = abs(beta) < BETA_THRESHOLD

    # Step 4 — Walk-forward (4 folds on TEST set)
    fold_sharpes = []
    fold_size = len(net_rets) // 4
    for i in range(4):
        fold = net_rets.iloc[i * fold_size: (i + 1) * fold_size]
        if fold.std() > 0:
            fs = (fold.mean() / fold.std()) * ann_factor
        else:
            fs = 0.0
        fold_sharpes.append(fs)
    print(f"\n  Step 4 — Walk-forward (4 folds):")
    for i, fs in enumerate(fold_sharpes):
        mark = "✓" if fs > WF_SHARPE_MIN else "✗"
        print(f"    Fold {i+1}: Sharpe = {fs:.3f} {mark}")
    wf_pass_count = sum(1 for fs in fold_sharpes if fs > WF_SHARPE_MIN)
    step4_pass = wf_pass_count >= 3

    # Step 5 — Propr daily loss limit
    daily_breach_count = (net_rets < -PROPR_DAILY_LIMIT).sum()
    print(f"\n  Step 5 — Propr daily loss limit (3%):")
    print(f"    Days exceeding limit: {daily_breach_count}  (TSMOM baseline: {TSMOM_BASELINE_DAILY_BREACHES})")
    step5_pass = daily_breach_count <= TSMOM_BASELINE_DAILY_BREACHES

    # Verdict
    steps_passed = sum([step1_pass, step2_pass, step3_pass, step4_pass, step5_pass])
    overall_pass = steps_passed >= 4
    verdict = "VIABLE" if overall_pass else "SKIP"

    print(f"\n  VERDICT: {verdict} ({steps_passed}/5 steps passed)")

    return {
        "strategy": "C",
        "name": "Overnight Gap MR",
        "verdict": verdict,
        "passed": overall_pass,
        "t_stat": t_stat,
        "sharpe_gross": sharpe_gross,
        "sharpe_net": sharpe_net,
        "beta_btc": beta,
        "wf_pass_count": wf_pass_count,
        "daily_breaches": int(daily_breach_count),
        "steps_passed": steps_passed,
        "step1": step1_pass, "step2": step2_pass, "step3": step3_pass,
        "step4": step4_pass, "step5": step5_pass,
        "net_rets_test": net_rets,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# COMPARISON TABLE AND PLOT
# ═══════════════════════════════════════════════════════════════════════════════

def print_comparison_table(results: list[dict]) -> None:
    print("\n" + "="*80)
    print("COMPARISON TABLE — Market-Neutral vs TSMOM v2 Baseline")
    print("="*80)

    # Header
    header = f"{'Strategy':<25} {'Verdict':<10} {'t-stat':>7} {'Sharpe':>7} {'Beta':>6} {'WF':>4} {'Breaches':>9} {'Steps':>6}"
    print(header)
    print("-" * 80)

    # TSMOM v2 baseline row
    print(f"{'TSMOM v2 (baseline)':<25} {'LIVE':<10} {'—':>7} {'~0.7':>7} {'—':>6} {'—':>4} {TSMOM_BASELINE_DAILY_BREACHES:>9} {'—':>6}")

    for r in results:
        if "verdict" not in r:
            continue
        name     = r.get("name", f"Strategy {r['strategy']}")
        verdict  = r.get("verdict", "?")
        t_stat   = f"{r.get('t_stat', float('nan')):.2f}" if isinstance(r.get("t_stat"), float) else "?"
        sharpe   = f"{r.get('sharpe_net', float('nan')):.2f}" if isinstance(r.get("sharpe_net"), float) else "?"
        beta     = f"{r.get('beta_btc', float('nan')):.3f}" if isinstance(r.get("beta_btc"), float) else "?"
        wf       = f"{r.get('wf_pass_count', 0)}/4"
        breach   = str(r.get("daily_breaches", "?"))
        steps    = f"{r.get('steps_passed', 0)}/5"
        print(f"{name:<25} {verdict:<10} {t_stat:>7} {sharpe:>7} {beta:>6} {wf:>4} {breach:>9} {steps:>6}")

    print("-" * 80)
    viable = [r for r in results if r.get("passed", False)]
    print(f"\nViable strategies: {len(viable)}/3")
    if viable:
        print(f"  → Recommend further development: {', '.join(r['name'] for r in viable)}")
    else:
        print("  → All strategies failed — continue with TSMOM v2 only")


def save_comparison_plot(results: list[dict], save_path: str) -> None:
    """Save a 2×2 comparison plot."""
    valid = [r for r in results if "net_rets_test" in r and not r.get("verdict") == "DATA_ERROR"]
    if not valid:
        print("[WARN] No valid results to plot.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Market-Neutral Feasibility — Test Set Performance", fontsize=14, fontweight="bold")

    colors = {"VIABLE": "#2ecc71", "SKIP": "#e74c3c", "DATA_ERROR": "#95a1a4"}

    # Subplot 1-3: Equity curves
    for idx, r in enumerate(valid[:3]):
        ax = axes[idx // 2][idx % 2]
        net_rets = r["net_rets_test"]
        if isinstance(net_rets, pd.Series):
            cum_ret = (1 + net_rets.fillna(0)).cumprod()
            color = colors.get(r.get("verdict", "SKIP"), "#e74c3c")
            ax.plot(cum_ret.index, cum_ret.values, color=color, linewidth=1.2)
            ax.axhline(1.0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
            ax.set_title(
                f"Strategy {r['strategy']}: {r.get('name', '')} — {r.get('verdict', '?')}\n"
                f"Sharpe(net)={r.get('sharpe_net', 0):.2f}  β={r.get('beta_btc', 0):.3f}  "
                f"Steps={r.get('steps_passed', 0)}/5",
                fontsize=9,
            )
            ax.set_ylabel("Cumulative Return")
            ax.tick_params(axis="x", rotation=30)

    # Subplot 4: Summary bar chart
    ax = axes[1][1]
    strategy_names = [r.get("name", f"Strat {r['strategy']}") for r in results]
    sharpes = [r.get("sharpe_net", 0) for r in results]
    verdicts = [r.get("verdict", "SKIP") for r in results]
    bar_colors = [colors.get(v, "#95a1a4") for v in verdicts]

    bars = ax.bar(strategy_names, sharpes, color=bar_colors, edgecolor="white", linewidth=0.5)
    ax.axhline(SHARPE_THRESHOLD, color="navy", linewidth=1.2, linestyle="--",
               label=f"Threshold ({SHARPE_THRESHOLD})")
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Net Sharpe Ratio Comparison", fontsize=10)
    ax.set_ylabel("Annualized Sharpe")
    ax.legend(fontsize=8)
    for bar, verdict in zip(bars, verdicts):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            verdict,
            ha="center", va="bottom", fontsize=8, fontweight="bold",
        )

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\nPlot saved: {save_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("\n" + "#"*60)
    print("  MARKET-NEUTRAL FEASIBILITY CHECK")
    print(f"  Run date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("#"*60)

    results = []

    # Run all 3 strategies sequentially
    result_a = run_strategy_a(days_back=365)
    results.append(result_a)

    result_b = run_strategy_b(days_back=730)
    results.append(result_b)

    result_c = run_strategy_c(days_back=730)
    results.append(result_c)

    # Summary
    print_comparison_table(results)
    save_comparison_plot(results, RESULTS_PNG)


if __name__ == "__main__":
    main()
