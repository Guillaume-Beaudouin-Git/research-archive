#!/usr/bin/env python
"""
CS Carry Full Sweep
===================
Comprehensive feasibility study for cross-sectional funding rate carry on crypto
perpetuals. Sweeps 90 parameter combinations across:
  - 6 signal variants  (raw, z-score, EMA×3, percentile rank)
  - 5 rebalance freqs  (1h, 4h, 8h, 24h, 168h)
  - 3 leverage levels  (1×, 2×, 3×)

Usage:
    source "<HOME>/Desktop/Unholy returns/Python3.12.9/myenv/bin/activate"
    cd ~/Desktop/Algo_claude
    python -m strategies.cs_carry.feasibility_full
"""

from __future__ import annotations

import time
import warnings
from dataclasses import dataclass
from itertools import product
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
import scipy.stats as sp_stats
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Directories ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_CSV = BASE_DIR / "feasibility_full_results.csv"

# ── Universe ──────────────────────────────────────────────────────────────────
ASSETS = ["BTC", "ETH", "SOL", "AVAX", "LINK", "DOGE",
          "ADA", "DOT", "LTC", "BCH", "ARB", "OP"]
YF_MAP  = {a: f"{a}-USD" for a in ASSETS}
BIN_MAP = {a: f"{a}USDT" for a in ASSETS}

# ── Time range ────────────────────────────────────────────────────────────────
DATA_START = "2024-01-01"
DATA_END   = "2026-05-11"
TRAIN_END  = "2025-06-30"
TEST_START = "2025-07-01"

# ── Cost model ────────────────────────────────────────────────────────────────
COST_PER_LEG     = 0.00085   # 0.085 % taker + slippage per leg → 0.17 % RT
PROPR_DAILY_LIMIT = 0.03
TSMOM_BREACHES    = 26

# ── Sweep parameters ──────────────────────────────────────────────────────────
EMA_SPANS    = [8, 24, 72]
REBAL_FREQS  = [1, 4, 8, 24, 168]
FREQ_LABELS  = {1: "1h", 4: "4h", 8: "8h", 24: "Daily", 168: "Weekly"}
LEVERAGES    = [1.0, 2.0, 3.0]
MIN_ASSETS   = 3   # minimum assets with valid data to enter a bar

# ── API constants ─────────────────────────────────────────────────────────────
HL_URL      = "https://api.hyperliquid.xyz/info"
BIN_URL     = "https://fapi.binance.com/fapi/v1/fundingRate"
API_SLEEP   = 0.2   # seconds between HL requests
API_RETRIES = 3
CHUNK_DAYS  = 14    # days per HL pagination request (14 × 24 = 336 rows < 500 limit)


# ══════════════════════════════════════════════════════════════════════════════
# DATA FETCHING & CACHING
# ══════════════════════════════════════════════════════════════════════════════

def _ms(ts: str | pd.Timestamp) -> int:
    if isinstance(ts, str):
        ts = pd.Timestamp(ts, tz="UTC")
    return int(ts.timestamp() * 1000)


def _from_cache(path: Path) -> pd.Series | None:
    if not path.exists():
        return None
    df = pd.read_csv(path, index_col=0, parse_dates=True)
    s = df.iloc[:, 0]
    s.index = (
        pd.DatetimeIndex(s.index).tz_localize("UTC")
        if s.index.tz is None
        else pd.DatetimeIndex(s.index).tz_convert("UTC")
    )
    return s.sort_index()


def _hl_request(coin: str, start_ms: int, end_ms: int) -> list[dict]:
    for attempt in range(API_RETRIES):
        try:
            resp = requests.post(
                HL_URL,
                json={"type": "fundingHistory", "coin": coin,
                      "startTime": start_ms, "endTime": end_ms},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception as exc:
            if attempt == API_RETRIES - 1:
                print(f"      [WARN] HL request failed {coin}: {exc}")
                return []
            time.sleep(1.0)
    return []


def fetch_hl_funding(coin: str) -> pd.Series:
    """Fetch hourly HL funding with 14-day pagination. Returns Series indexed UTC."""
    cache = DATA_DIR / f"{coin}_hl_funding.csv"
    cached = _from_cache(cache)
    if cached is not None:
        return cached

    print(f"    Downloading HL funding: {coin}")
    start = pd.Timestamp(DATA_START, tz="UTC")
    end   = pd.Timestamp(DATA_END,   tz="UTC")
    all_rows: list[tuple] = []
    cursor = start

    while cursor < end:
        chunk_end = min(cursor + pd.Timedelta(days=CHUNK_DAYS), end)
        data = _hl_request(coin, _ms(cursor), _ms(chunk_end))
        if data:
            for item in data:
                ts = pd.to_datetime(int(item["time"]), unit="ms", utc=True)
                all_rows.append((ts, float(item["fundingRate"])))
        cursor = chunk_end + pd.Timedelta(hours=1)
        time.sleep(API_SLEEP)

    if not all_rows:
        return pd.Series(dtype=float, name=coin)

    s = (
        pd.Series(
            [r[1] for r in all_rows],
            index=pd.DatetimeIndex([r[0] for r in all_rows]),
            name=coin,
        )
        .sort_index()
        .drop_duplicates()
    )
    s.to_csv(cache)
    return s


def _bin_request(symbol: str, start_ms: int, end_ms: int) -> list[dict]:
    for attempt in range(API_RETRIES):
        try:
            resp = requests.get(
                BIN_URL,
                params={"symbol": symbol, "startTime": start_ms,
                        "endTime": end_ms, "limit": 1000},
                timeout=20,
            )
            resp.raise_for_status()
            return resp.json() or []
        except Exception as exc:
            if attempt == API_RETRIES - 1:
                print(f"      [WARN] Binance request failed {symbol}: {exc}")
                return []
            time.sleep(1.0)
    return []


def fetch_bin_funding(coin: str) -> pd.Series:
    """Fetch 8h Binance funding, forward-fill to hourly. Returns Series indexed UTC."""
    cache = DATA_DIR / f"{coin}_bin_funding.csv"
    cached = _from_cache(cache)
    if cached is not None:
        return cached

    symbol = BIN_MAP[coin]
    print(f"    Downloading Binance funding: {symbol}")
    start_ms = _ms(DATA_START)
    end_ms   = _ms(DATA_END)
    all_rows: list[tuple] = []
    cursor = start_ms

    while cursor < end_ms:
        data = _bin_request(symbol, cursor, end_ms)
        if not data:
            break
        for item in data:
            ts = pd.to_datetime(int(item["fundingTime"]), unit="ms", utc=True)
            all_rows.append((ts, float(item["fundingRate"])))
        last_ts = max(int(item["fundingTime"]) for item in data)
        cursor = last_ts + 1
        time.sleep(API_SLEEP)
        if len(data) < 1000:
            break

    if not all_rows:
        return pd.Series(dtype=float, name=coin)

    s = (
        pd.Series(
            [r[1] for r in all_rows],
            index=pd.DatetimeIndex([r[0] for r in all_rows]),
            name=coin,
        )
        .sort_index()
        .drop_duplicates()
        .resample("1h")
        .ffill()
    )
    s.to_csv(cache)
    return s


def fetch_prices() -> pd.DataFrame:
    """Fetch daily close prices via yfinance. Cached to data/prices_daily.csv."""
    cache = DATA_DIR / "prices_daily.csv"
    if cache.exists():
        df = pd.read_csv(cache, index_col=0, parse_dates=True)
        if df.index.tz is None:
            df.index = df.index.tz_localize("UTC")
        else:
            df.index = df.index.tz_convert("UTC")
        return df.sort_index()

    print("    Downloading daily prices (yfinance)...")
    symbols = [YF_MAP[a] for a in ASSETS]
    raw = yf.download(
        symbols, start=DATA_START, end=DATA_END,
        interval="1d", auto_adjust=True, progress=False,
    )
    df: pd.DataFrame
    if isinstance(raw.columns, pd.MultiIndex):
        df = raw["Close"].copy()
    else:
        df = raw[["Close"]].copy()
    df.columns = [c.replace("-USD", "") for c in df.columns]
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    df = df.sort_index()
    df.to_csv(cache)
    return df


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load funding (hourly) and price (daily) DataFrames.
    Uses HL as primary; falls back to Binance if < 6 months returned.
    Returns: (funding_hourly, prices_daily)
    """
    MIN_DAYS = 180
    series: dict[str, pd.Series] = {}

    for coin in ASSETS:
        s = fetch_hl_funding(coin)
        n_days = (s.index.max() - s.index.min()).days if len(s) > 1 else 0
        if n_days < MIN_DAYS:
            print(f"    HL < {MIN_DAYS}d for {coin} ({n_days}d) → trying Binance")
            s = fetch_bin_funding(coin)
        if len(s) > 100:
            series[coin] = s
        else:
            print(f"    [SKIP] No usable funding data for {coin}")

    if not series:
        raise RuntimeError("No funding data loaded!")

    # Align to common hourly UTC index
    global_start = max(s.index.min() for s in series.values())
    global_end   = min(s.index.max() for s in series.values())
    hourly_idx   = pd.date_range(global_start, global_end, freq="1h", tz="UTC")
    funding_df   = (
        pd.DataFrame(series)
        .reindex(hourly_idx)
        .ffill()
        .fillna(0.0)
    )

    prices_df = fetch_prices()
    # Keep only assets present in both
    common = list(set(funding_df.columns) & set(prices_df.columns))
    funding_df = funding_df[sorted(common)]
    prices_df  = prices_df[sorted(common)]

    print(f"\n  Data loaded: {len(funding_df)} hourly funding bars, "
          f"{len(prices_df)} daily price bars, {len(common)} assets")
    print(f"  Coverage: {funding_df.index[0].date()} → {funding_df.index[-1].date()}")
    return funding_df, prices_df


# ══════════════════════════════════════════════════════════════════════════════
# SIGNAL COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def signal_raw(funding: pd.DataFrame) -> pd.DataFrame:
    """Variant 1: Raw funding rate, 1-bar lag (no look-ahead)."""
    return funding.shift(1)


def signal_zscore(funding: pd.DataFrame) -> pd.DataFrame:
    """Variant 2: Cross-sectional z-score at each timestamp, 1-bar lag."""
    lagged = funding.shift(1)
    mu    = lagged.mean(axis=1)
    sigma = lagged.std(axis=1).replace(0.0, np.nan)
    return lagged.sub(mu, axis=0).div(sigma, axis=0)


def signal_ema(funding: pd.DataFrame, span: int) -> pd.DataFrame:
    """Variant 3: EMA of funding rate (time-series), 1-bar lag."""
    return funding.ewm(span=span, adjust=False, min_periods=span // 2).mean().shift(1)


def signal_rank(funding: pd.DataFrame) -> pd.DataFrame:
    """Variant 4: Cross-sectional percentile rank [0,1], 1-bar lag."""
    return funding.shift(1).rank(axis=1, pct=True)


def get_signal(funding: pd.DataFrame, signal_type: str, ema_span: int | None) -> pd.DataFrame:
    if signal_type == "raw":
        return signal_raw(funding)
    if signal_type == "zscore":
        return signal_zscore(funding)
    if signal_type == "ema":
        assert ema_span is not None
        return signal_ema(funding, ema_span)
    if signal_type == "rank":
        return signal_rank(funding)
    raise ValueError(f"Unknown signal type: {signal_type}")


# ══════════════════════════════════════════════════════════════════════════════
# POSITION CONSTRUCTION
# ══════════════════════════════════════════════════════════════════════════════

def compute_weights_vectorized(signal: pd.DataFrame, leverage: float) -> pd.DataFrame:
    """
    Convert signal scores to portfolio weights (vectorized).
    Long:  bottom tercile (lowest score → receive funding or pay least)
    Short: top tercile   (highest score → we receive their funding payment)
    Weight = ±leverage / n_per_leg (equal weight within each leg).
    """
    # Count non-NaN assets per row
    valid = signal.notna().sum(axis=1)

    # Cross-sectional percentile rank (NaN → NaN)
    rank_pct = signal.rank(axis=1, pct=True, na_option="keep")

    # Masks
    long_mask  = (rank_pct <= 1.0 / 3.0) & (valid >= MIN_ASSETS).values[:, None]
    short_mask = (rank_pct >  2.0 / 3.0) & (valid >= MIN_ASSETS).values[:, None]

    # Per-row leg counts (avoid division by zero)
    n_long  = long_mask.sum(axis=1).astype(float).replace(0.0, np.nan)
    n_short = short_mask.sum(axis=1).astype(float).replace(0.0, np.nan)

    long_w  = long_mask.astype(float).div(n_long,  axis=0) *  leverage
    short_w = short_mask.astype(float).div(n_short, axis=0) * -leverage

    weights = (long_w.fillna(0.0) + short_w.fillna(0.0))
    return weights


def build_hourly_weights(
    signal_df: pd.DataFrame,
    leverage: float,
    rebal_freq: int,
) -> pd.DataFrame:
    """
    Compute target weights at each rebalance timestamp, then forward-fill
    to all hourly timestamps.  Positions change ONLY at rebalance ticks.
    """
    hourly_idx = signal_df.index
    # Rebalance ticks: every rebal_freq rows
    rebal_mask = np.zeros(len(hourly_idx), dtype=bool)
    rebal_mask[::rebal_freq] = True
    rebal_idx = hourly_idx[rebal_mask]

    rebal_signal  = signal_df.loc[rebal_idx]
    rebal_weights = compute_weights_vectorized(rebal_signal, leverage)

    # Forward-fill to full hourly index
    hourly_weights = rebal_weights.reindex(hourly_idx).ffill().fillna(0.0)
    return hourly_weights


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def run_simulation(
    weights_h: pd.DataFrame,   # hourly weights (±leverage/n)
    funding_h: pd.DataFrame,   # hourly funding rates
    prices_d: pd.DataFrame,    # daily close prices
    rebal_freq: int,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Simulate P&L and return three daily Series:
      funding_pnl_d  — daily funding income (% of equity)
      price_pnl_d    — daily MTM price return (% of equity)
      costs_d        — daily transaction costs (% of equity, positive = drag)

    Funding convention:
      pnl_i = -(w_i × f_i)
      • Short (w<0) + positive funding (f>0) → earn ✓
      • Long  (w>0) + negative funding (f<0) → earn ✓

    Costs: charged only at rebalance timestamps.
    """
    # ── Funding P&L (hourly) ──────────────────────────────────────────────────
    # Align columns
    common = weights_h.columns.intersection(funding_h.columns)
    w = weights_h[common]
    f = funding_h[common].reindex(w.index).fillna(0.0)

    funding_h_pnl = -(w * f).sum(axis=1)
    funding_d = funding_h_pnl.resample("1D").sum()

    # ── Transaction costs ─────────────────────────────────────────────────────
    # Weight changes only at rebalance ticks; all other diffs ≈ 0
    w_diff = w.diff().abs()
    w_diff.iloc[0] = w.iloc[0].abs()  # first bar counts as a full entry

    rebal_mask = pd.Series(False, index=w.index)
    rebal_mask.iloc[::rebal_freq] = True

    costs_h = w_diff.sum(axis=1).where(rebal_mask, 0.0) * COST_PER_LEG
    costs_d = costs_h.resample("1D").sum()

    # ── Price P&L (daily) ─────────────────────────────────────────────────────
    # Use end-of-day weight (position carried into the next day's close)
    daily_w = w.resample("1D").last()
    price_ret = prices_d[common].pct_change()

    common_dates = daily_w.index.intersection(price_ret.index)
    price_d = (
        daily_w.shift(1).loc[common_dates]
        .mul(price_ret.loc[common_dates])
        .sum(axis=1)
    )

    return funding_d, price_d, costs_d


# ══════════════════════════════════════════════════════════════════════════════
# METRIC COMPUTATION
# ══════════════════════════════════════════════════════════════════════════════

def compute_metrics(
    funding_d: pd.Series,
    price_d: pd.Series,
    costs_d: pd.Series,
    btc_daily_ret: pd.Series,
) -> dict[str, Any]:
    """
    Combine P&L components, cut to OOS test set, compute all metrics.
    Returns dict with scalar values (NaN if insufficient data).
    """
    all_idx = funding_d.index.union(price_d.index).union(costs_d.index)
    daily_pnl = (
        funding_d.reindex(all_idx).fillna(0.0)
        + price_d.reindex(all_idx).fillna(0.0)
        - costs_d.reindex(all_idx).fillna(0.0)
    )

    # Separate gross (before costs)
    daily_gross = daily_pnl + costs_d.reindex(all_idx).fillna(0.0)

    # Cut to OOS test set
    test_start = pd.Timestamp(TEST_START, tz="UTC")
    rets   = daily_pnl.loc[daily_pnl.index >= test_start].dropna()
    gross  = daily_gross.loc[daily_gross.index >= test_start].dropna()
    costs  = costs_d.loc[costs_d.index >= test_start].fillna(0.0)
    fund   = funding_d.loc[funding_d.index >= test_start].fillna(0.0)

    nan_result: dict[str, Any] = {
        "sharpe": np.nan, "gross_sharpe": np.nan, "ann_ret": np.nan,
        "max_dd": np.nan, "beta": np.nan, "total_costs_pct": np.nan,
        "total_funding_pct": np.nan, "net_carry_pct": np.nan,
        "breaches": np.nan, "turnover_yr": np.nan,
    }
    if len(rets) < 30:
        return nan_result

    # Annualized return & Sharpe
    ann_ret = float(rets.mean() * 252)
    std     = float(rets.std())
    sharpe  = float(rets.mean() / std * np.sqrt(252)) if std > 0 else 0.0
    g_std   = float(gross.std())
    gross_sharpe = float(gross.mean() / g_std * np.sqrt(252)) if g_std > 0 else 0.0

    # Max drawdown
    equity = (1.0 + rets).cumprod()
    peak   = equity.cummax()
    max_dd = float((equity / peak - 1.0).min())

    # Beta to BTC (daily)
    btc = btc_daily_ret.reindex(rets.index).dropna()
    strat_aligned = rets.reindex(btc.index)
    if len(btc) > 30:
        beta = float(np.polyfit(btc.values, strat_aligned.values, 1)[0])
    else:
        beta = 0.0

    # Costs & funding (annualised %)
    n_years         = len(rets) / 252.0
    total_costs_pct = float(costs.sum() * 100 / max(n_years, 0.01))
    total_fund_pct  = float(fund.sum() * 100 / max(n_years, 0.01))
    net_carry_pct   = total_fund_pct - total_costs_pct

    # Turnover (total weight traded / year)
    turnover_yr = float(costs.sum() / COST_PER_LEG / max(n_years, 0.01))

    # Propr daily loss breaches
    breaches = int((rets < -PROPR_DAILY_LIMIT).sum())

    return {
        "sharpe":            sharpe,
        "gross_sharpe":      gross_sharpe,
        "ann_ret":           ann_ret,
        "max_dd":            max_dd,
        "beta":              beta,
        "total_costs_pct":   total_costs_pct,
        "total_funding_pct": total_fund_pct,
        "net_carry_pct":     net_carry_pct,
        "breaches":          breaches,
        "turnover_yr":       turnover_yr,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CONFIG DEFINITION & SWEEP
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class Config:
    signal_type: str
    ema_span:    int | None
    rebal_freq:  int   # hours
    leverage:    float

    @property
    def label(self) -> str:
        sig = f"EMA{self.ema_span}" if self.signal_type == "ema" else self.signal_type.capitalize()
        return f"{sig:<10} | {FREQ_LABELS[self.rebal_freq]:<7} | {self.leverage:.0f}x"

    @property
    def short_label(self) -> str:
        sig = f"EMA{self.ema_span}" if self.signal_type == "ema" else self.signal_type
        return f"{sig}|{FREQ_LABELS[self.rebal_freq]}|{self.leverage:.0f}x"


def generate_configs() -> list[Config]:
    """Generate all 90 configurations:
       (1 raw + 1 zscore + 1 rank + 3 ema) × 5 freqs × 3 levs = 90
    """
    configs: list[Config] = []
    for freq, lev in product(REBAL_FREQS, LEVERAGES):
        configs.append(Config("raw",    None, freq, lev))
        configs.append(Config("zscore", None, freq, lev))
        configs.append(Config("rank",   None, freq, lev))
        for span in EMA_SPANS:
            configs.append(Config("ema", span, freq, lev))
    return configs  # 5 × 3 × 6 = 90


def run_sweep(
    funding_h: pd.DataFrame,
    prices_d: pd.DataFrame,
) -> tuple[list[dict], list[Config]]:
    """
    Run all 90 configs. Returns (results_list, configs_list).
    Pre-computes signals by variant to avoid redundant computation.
    """
    configs = generate_configs()
    n_total = len(configs)

    # Pre-compute BTC daily returns for beta calculation
    btc_daily = prices_d["BTC"].pct_change() if "BTC" in prices_d.columns else prices_d.iloc[:, 0].pct_change()

    # Pre-compute all unique (signal_type, ema_span) signals
    # Keys: ("raw", None), ("zscore", None), ("rank", None), ("ema", 8), etc.
    print("\n  Pre-computing signals...")
    signal_cache: dict[tuple, pd.DataFrame] = {}
    unique_sigs = {(c.signal_type, c.ema_span) for c in configs}
    for stype, span in sorted(unique_sigs):
        key = (stype, span)
        signal_cache[key] = get_signal(funding_h, stype, span)

    results: list[dict] = []

    for i, cfg in enumerate(configs):
        print(f"  Testing config {i+1:>3}/{n_total}: {cfg.label}", end="  ", flush=True)

        sig = signal_cache[(cfg.signal_type, cfg.ema_span)]
        weights_h = build_hourly_weights(sig, cfg.leverage, cfg.rebal_freq)
        funding_d, price_d, costs_d = run_simulation(
            weights_h, funding_h, prices_d, cfg.rebal_freq
        )
        metrics = compute_metrics(funding_d, price_d, costs_d, btc_daily)

        row = {
            "signal_type": cfg.signal_type,
            "ema_span":    cfg.ema_span if cfg.ema_span else "",
            "rebal_freq":  FREQ_LABELS[cfg.rebal_freq],
            "leverage":    cfg.leverage,
            "label":       cfg.short_label,
            **metrics,
        }
        results.append(row)
        s = metrics.get("sharpe", np.nan)
        b = metrics.get("beta",   np.nan)
        tag = ("PASS" if (not np.isnan(s) and s > 0.5 and abs(b) < 0.20) else "    ")
        print(f"Sharpe={s:+.2f}  β={b:+.4f}  {tag}")

    return results, configs


# ══════════════════════════════════════════════════════════════════════════════
# WALK-FORWARD VALIDATION (TOP 5)
# ══════════════════════════════════════════════════════════════════════════════

def walk_forward(
    cfg: Config,
    funding_h: pd.DataFrame,
    prices_d: pd.DataFrame,
    n_folds: int = 4,
    fold_months: int = 6,
) -> dict[str, Any]:
    """
    Expanding-window walk-forward over the full dataset.
    Each OOS window = fold_months months.
    Returns {fold_sharpes, mean, std, worst, unstable}.
    """
    sig = get_signal(funding_h, cfg.signal_type, cfg.ema_span)
    btc_daily = prices_d["BTC"].pct_change() if "BTC" in prices_d.columns else prices_d.iloc[:, 0].pct_change()

    fold_sharpes: list[float] = []
    data_start = funding_h.index[0]

    for fold in range(n_folds):
        oos_start = data_start + pd.DateOffset(
            months=6 + fold * fold_months
        )
        oos_end = oos_start + pd.DateOffset(months=fold_months)

        # Use all data up to oos_start for warmup; evaluate on OOS window
        sig_window = sig.loc[:oos_end]
        w_h = build_hourly_weights(sig_window, cfg.leverage, cfg.rebal_freq)

        w_oos   = w_h.loc[oos_start:oos_end]
        f_oos   = funding_h.loc[oos_start:oos_end]
        p_oos   = prices_d.loc[oos_start:oos_end]

        f_d, p_d, c_d = run_simulation(w_oos, f_oos, p_oos, cfg.rebal_freq)

        # For WF, evaluate on the OOS window regardless of TEST_START
        all_idx = f_d.index.union(p_d.index).union(c_d.index)
        rets = (
            f_d.reindex(all_idx).fillna(0.0)
            + p_d.reindex(all_idx).fillna(0.0)
            - c_d.reindex(all_idx).fillna(0.0)
        ).dropna()

        if len(rets) < 10 or rets.std() == 0:
            fold_sharpes.append(np.nan)
        else:
            fold_sharpes.append(float(rets.mean() / rets.std() * np.sqrt(252)))

    valid = [s for s in fold_sharpes if not np.isnan(s)]
    return {
        "fold_sharpes": fold_sharpes,
        "mean":         np.mean(valid) if valid else np.nan,
        "std":          np.std(valid)  if valid else np.nan,
        "worst":        min(valid)     if valid else np.nan,
        "unstable":     (min(valid) < 0.0) if valid else True,
    }


# ══════════════════════════════════════════════════════════════════════════════
# COST SENSITIVITY (#1 CONFIG)
# ══════════════════════════════════════════════════════════════════════════════

def cost_sensitivity(
    cfg: Config,
    funding_h: pd.DataFrame,
    prices_d: pd.DataFrame,
) -> list[dict]:
    """Re-run best config with 0.5×, 1×, 1.5×, 2× baseline costs."""
    sig  = get_signal(funding_h, cfg.signal_type, cfg.ema_span)
    w_h  = build_hourly_weights(sig, cfg.leverage, cfg.rebal_freq)
    btc  = prices_d["BTC"].pct_change() if "BTC" in prices_d.columns else prices_d.iloc[:, 0].pct_change()

    # Get base components once
    funding_d, price_d, base_costs_d = run_simulation(w_h, funding_h, prices_d, cfg.rebal_freq)

    rows: list[dict] = []
    for mult in [0.5, 1.0, 1.5, 2.0]:
        scaled_costs = base_costs_d * mult
        test_start   = pd.Timestamp(TEST_START, tz="UTC")
        all_idx = funding_d.index.union(price_d.index).union(scaled_costs.index)
        rets = (
            funding_d.reindex(all_idx).fillna(0.0)
            + price_d.reindex(all_idx).fillna(0.0)
            - scaled_costs.reindex(all_idx).fillna(0.0)
        ).loc[lambda s: s.index >= test_start].dropna()

        if len(rets) > 10 and rets.std() > 0:
            sharpe = float(rets.mean() / rets.std() * np.sqrt(252))
        else:
            sharpe = np.nan
        rows.append({"cost_mult": mult, "sharpe": sharpe,
                     "eff_cost_rt": COST_PER_LEG * 2 * mult * 100})
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# PER-PERIOD BREAKDOWN (#1 CONFIG)
# ══════════════════════════════════════════════════════════════════════════════

def period_breakdown(
    cfg: Config,
    funding_h: pd.DataFrame,
    prices_d: pd.DataFrame,
) -> list[dict]:
    """Compute year-half P&L for the best config."""
    sig = get_signal(funding_h, cfg.signal_type, cfg.ema_span)
    w_h = build_hourly_weights(sig, cfg.leverage, cfg.rebal_freq)
    fund_d, price_d, costs_d = run_simulation(w_h, funding_h, prices_d, cfg.rebal_freq)

    all_idx = fund_d.index.union(price_d.index).union(costs_d.index)
    daily_pnl = (
        fund_d.reindex(all_idx).fillna(0.0)
        + price_d.reindex(all_idx).fillna(0.0)
        - costs_d.reindex(all_idx).fillna(0.0)
    )

    periods = [
        ("2024 H2", "2024-07-01", "2024-12-31"),
        ("2025 H1", "2025-01-01", "2025-06-30"),
        ("2025 H2", "2025-07-01", "2025-12-31"),
        ("2026 H1", "2026-01-01", "2026-05-11"),
    ]
    rows = []
    for label, s, e in periods:
        sl = pd.Timestamp(s, tz="UTC")
        el = pd.Timestamp(e, tz="UTC")
        chunk = daily_pnl.loc[sl:el].dropna()
        if len(chunk) < 5:
            rows.append({"period": label, "sharpe": np.nan, "ann_ret": np.nan, "n_days": 0})
            continue
        sharpe  = float(chunk.mean() / chunk.std() * np.sqrt(252)) if chunk.std() > 0 else 0.0
        ann_ret = float(chunk.mean() * 252 * 100)
        rows.append({"period": label, "sharpe": sharpe, "ann_ret": ann_ret, "n_days": len(chunk)})
    return rows


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUT FORMATTING
# ══════════════════════════════════════════════════════════════════════════════

def print_header() -> None:
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║   CS CARRY FEASIBILITY — FULL SWEEP RESULTS          ║")
    print("╚══════════════════════════════════════════════════════╝")


def print_top10(df_results: pd.DataFrame) -> None:
    filtered = df_results[
        (df_results["beta"].abs() < 0.20) &
        (~df_results["sharpe"].isna())
    ].sort_values("sharpe", ascending=False).head(10)

    print("\nTOP 10 CONFIGS (OOS Sharpe, |β| < 0.20):")
    header = (f"{'Rank':>4} | {'Signal':<12} | {'Freq':<7} | {'Lev':>3} | "
              f"{'Sharpe':>7} | {'Beta':>6} | {'MaxDD':>7} | {'Breaches':>8}")
    print(header)
    print("-" * len(header))
    for rank, (_, row) in enumerate(filtered.iterrows(), 1):
        sig  = f"{row['signal_type']}"
        if row["ema_span"]:
            sig += f"{row['ema_span']}"
        freq = str(row["rebal_freq"])
        lev  = f"{row['leverage']:.0f}x"
        sharpe   = f"{row['sharpe']:+.3f}"
        beta     = f"{row['beta']:+.4f}"
        dd       = f"{row['max_dd']*100:+.1f}%"
        breaches = str(int(row["breaches"])) if not np.isnan(row["breaches"]) else "?"
        print(f"{rank:>4} | {sig:<12} | {freq:<7} | {lev:>3} | "
              f"{sharpe:>7} | {beta:>6} | {dd:>7} | {breaches:>8}")


def print_best_detail(
    best: pd.Series,
    wf: dict,
    cost_rows: list[dict],
    periods: list[dict],
) -> None:
    sig_label = best["signal_type"]
    if best.get("ema_span"):
        sig_label += f"(span={best['ema_span']})"

    print("\nBEST CONFIG DETAIL:")
    print(f"  Signal      : {sig_label}")
    print(f"  Frequency   : {best['rebal_freq']}")
    print(f"  Leverage    : {best['leverage']:.0f}x")
    print(f"  OOS Sharpe  : {best['sharpe']:+.3f}")
    print(f"  OOS Beta    : {best['beta']:+.4f}")
    print(f"  Max DD      : {best['max_dd']*100:.1f}%")
    print(f"  Daily limit : {int(best['breaches'])} breaches (vs TSMOM baseline: {TSMOM_BREACHES})")
    print(f"  Funding/yr  : +{best['total_funding_pct']:.1f}% of capital")
    print(f"  Costs/yr    : -{best['total_costs_pct']:.1f}% of capital")
    print(f"  Net carry   : {best['net_carry_pct']:+.1f}% (funding − costs)")

    print("\n  Year-by-year breakdown (train periods shown for context):")
    for p in periods:
        tag = "[OOS]" if p["period"] in ("2025 H2", "2026 H1") else "[TRAIN]"
        if p["n_days"] > 0:
            print(f"    {p['period']} {tag}: Sharpe={p['sharpe']:+.2f}  AnnRet={p['ann_ret']:+.1f}%  ({p['n_days']}d)")
        else:
            print(f"    {p['period']} {tag}: insufficient data")

    print("\n  Walk-forward (4 expanding windows, 6-month OOS each):")
    for k, s in enumerate(wf["fold_sharpes"]):
        mark = "✓" if not np.isnan(s) and s > 0 else "✗"
        val  = f"{s:+.3f}" if not np.isnan(s) else "n/a"
        print(f"    Window {k+1}: Sharpe = {val} {mark}")
    unstable = "UNSTABLE" if wf["unstable"] else "stable"
    print(f"    Summary: mean={wf['mean']:+.3f}  std={wf['std']:.3f}  "
          f"worst={wf['worst']:+.3f}  → {unstable}")

    print("\n  Cost sensitivity analysis:")
    print(f"    {'Cost mult':>10} | {'RT cost':>10} | {'Sharpe':>8}")
    print(f"    {'-'*32}")
    for r in cost_rows:
        tag = " ← baseline" if r["cost_mult"] == 1.0 else ""
        print(f"    {r['cost_mult']:>10.1f}× | {r['eff_cost_rt']:>9.3f}% | {r['sharpe']:>+8.3f}{tag}")
    # Break-even
    sharpes = [r["sharpe"] for r in cost_rows]
    if sharpes[0] > 0 > sharpes[-1]:
        print(f"    Break-even: somewhere between {cost_rows[-2]['cost_mult']:.1f}× and {cost_rows[-1]['cost_mult']:.1f}× baseline")
    elif sharpes[-1] > 0:
        print("    Break-even: beyond 2× baseline costs (robust)")
    else:
        print(f"    Break-even: below {cost_rows[0]['cost_mult']:.1f}× baseline costs (fragile)")


def print_verdict(best: pd.Series, wf: dict) -> None:
    s = best["sharpe"]
    b = best["beta"]
    br = int(best["breaches"]) if not np.isnan(best["breaches"]) else 999

    print("\nVERDICT:")
    if s >= 1.0 and abs(b) < 0.20 and br <= 10 and not wf["unstable"]:
        verdict = "PROMISING"
    elif s >= 0.5 and abs(b) < 0.20:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    if verdict == "PROMISING":
        sig_label = best["signal_type"]
        if best.get("ema_span"):
            sig_label += f"(span={best['ema_span']})"
        print(f"  PROMISING — OOS Sharpe {s:.2f} clears 1.0 threshold with β={b:.3f} "
              f"well under 0.20. Walk-forward is stable (worst={wf['worst']:.2f}).")
        print(f"\n  Recommended next step: full backtest with walk-forward using "
              f"config [{sig_label} | {best['rebal_freq']} | {best['leverage']:.0f}x], "
              f"starting 2024-01-01")
    elif verdict == "WEAK":
        print(f"  WEAK — OOS Sharpe {s:.2f} is positive but below 1.0 threshold. "
              f"Signal exists but insufficient to clear execution costs reliably.")
        print(f"\n  Root cause: {'costs too high' if best['net_carry_pct'] < 0 else 'signal too weak'} "
              f"— net carry = {best['net_carry_pct']:+.1f}%/yr "
              f"({'positive' if best['net_carry_pct']>0 else 'negative'}).")
    else:
        print(f"  SKIP — Best OOS Sharpe {s:.2f} fails threshold (need ≥ 1.0). "
              f"β={b:.3f}. Net carry = {best['net_carry_pct']:+.1f}%/yr.")
        root = []
        if best["total_funding_pct"] < best["total_costs_pct"]:
            root.append("costs too high")
        if best.get("gross_sharpe", 0) < 0.5:
            root.append("signal too weak")
        if abs(b) >= 0.20:
            root.append("beta too high")
        print(f"\n  Root cause: {' / '.join(root) if root else 'insufficient alpha after costs'}")


def print_comparison(best: pd.Series) -> None:
    print("\nCOMPARISON WITH TSMOM BASELINE:")
    print(f"  {'Metric':<16} | {'CS Carry (best)':>16} | {'TSMOM v2':>12}")
    print(f"  {'-'*50}")
    s = f"{best['sharpe']:+.2f}" if not np.isnan(best["sharpe"]) else "n/a"
    b = f"{best['beta']:+.3f}"   if not np.isnan(best["beta"]) else "n/a"
    br = str(int(best["breaches"])) if not np.isnan(best["breaches"]) else "?"
    print(f"  {'Sharpe':<16} | {s:>16} | {'~1.60':>12}")
    print(f"  {'Beta BTC':<16} | {b:>16} | {'~0.85':>12}")
    print(f"  {'Daily breaches':<16} | {br:>16} | {'26/44 sims':>12}")
    corr_note = "low (market-neutral)" if abs(best["beta"]) < 0.2 else "moderate"
    print(f"  {'BTC correlation':<16} | {corr_note:>16} | {'high':>12}")


def save_results(results: list[dict]) -> None:
    if not results:
        return
    df = pd.DataFrame(results)
    df.to_csv(RESULTS_CSV, index=False)
    print(f"\n  Results saved → {RESULTS_CSV}")


def save_plot(df_results: pd.DataFrame) -> None:
    """Save scatter plot: Sharpe vs Beta, colored by frequency."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))
    fig.suptitle("CS Carry Full Sweep — OOS Test Set", fontsize=13, fontweight="bold")

    # Left: Sharpe vs Beta, colored by freq
    ax = axes[0]
    freq_colors = {
        "1h": "#e74c3c", "4h": "#e67e22", "8h": "#f1c40f",
        "Daily": "#2ecc71", "Weekly": "#3498db",
    }
    for freq, grp in df_results.groupby("rebal_freq"):
        color = freq_colors.get(str(freq), "gray")
        ax.scatter(
            grp["beta"].abs(), grp["sharpe"],
            c=color, label=str(freq), alpha=0.7, s=40, edgecolors="white", linewidth=0.3,
        )
    ax.axhline(1.0, color="navy", linewidth=1.2, linestyle="--", label="Sharpe=1.0")
    ax.axhline(0.5, color="gray", linewidth=0.8, linestyle=":", label="Sharpe=0.5")
    ax.axvline(0.20, color="red", linewidth=0.8, linestyle="--", label="|β|=0.20")
    ax.set_xlabel("|Beta to BTC|")
    ax.set_ylabel("OOS Sharpe")
    ax.set_title("Sharpe vs |Beta|  (color = rebal freq)")
    ax.legend(fontsize=8)

    # Right: Sharpe vs Net Carry
    ax = axes[1]
    for sig, grp in df_results.groupby("signal_type"):
        ax.scatter(
            grp["net_carry_pct"], grp["sharpe"],
            label=sig, alpha=0.7, s=40, edgecolors="white", linewidth=0.3,
        )
    ax.axhline(1.0, color="navy", linewidth=1.2, linestyle="--")
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.axvline(0.0, color="red", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Net Carry (funding − costs) % / yr")
    ax.set_ylabel("OOS Sharpe")
    ax.set_title("Sharpe vs Net Carry  (color = signal variant)")
    ax.legend(fontsize=8)

    plt.tight_layout()
    plot_path = BASE_DIR / "feasibility_full_results.png"
    plt.savefig(plot_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  Plot saved     → {plot_path}")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    t0 = time.time()
    print_header()
    print(f"\nRun date: {pd.Timestamp.now(tz='UTC').strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Train: {DATA_START} → {TRAIN_END}  |  OOS test: {TEST_START} → {DATA_END}")
    print(f"Total configs: {len(generate_configs())}")

    # ── 1. Load data ──────────────────────────────────────────────────────────
    print("\n[1/5] Loading data...")
    funding_h, prices_d = load_data()

    # ── 2. Run full sweep ────────────────────────────────────────────────────
    print(f"\n[2/5] Running {len(generate_configs())}-config sweep...")
    results, configs = run_sweep(funding_h, prices_d)
    save_results(results)

    df = pd.DataFrame(results)

    # ── 3. Print top 10 ───────────────────────────────────────────────────────
    print("\n[3/5] Analysis...")
    print_top10(df)

    # Best config (β < 0.20)
    eligible = df[df["beta"].abs() < 0.20].sort_values("sharpe", ascending=False)
    if eligible.empty:
        print("\n[WARN] No config passed β < 0.20 filter. Showing best overall.")
        eligible = df.sort_values("sharpe", ascending=False)

    best     = eligible.iloc[0]
    top5_idx = eligible.head(5).index

    # Best Config → walk-forward
    best_cfg = configs[best.name]  # type: ignore[call-overload]
    # Re-find the Config matching best row
    for cfg in configs:
        if (cfg.signal_type == best["signal_type"]
                and str(cfg.ema_span or "") == str(best["ema_span"])
                and FREQ_LABELS[cfg.rebal_freq] == best["rebal_freq"]
                and cfg.leverage == best["leverage"]):
            best_cfg = cfg
            break

    # ── 4. Walk-forward (top 5) ───────────────────────────────────────────────
    print("\n[4/5] Walk-forward validation (top 5)...")
    wf_results: list[dict] = []
    for rank_i, row_idx in enumerate(top5_idx):
        row = df.loc[row_idx]
        for cfg in configs:
            if (cfg.signal_type == row["signal_type"]
                    and str(cfg.ema_span or "") == str(row["ema_span"])
                    and FREQ_LABELS[cfg.rebal_freq] == row["rebal_freq"]
                    and cfg.leverage == row["leverage"]):
                print(f"    WF {rank_i+1}/5: {cfg.label}", end="  ", flush=True)
                wf = walk_forward(cfg, funding_h, prices_d)
                wf_results.append(wf)
                print(f"mean={wf['mean']:+.3f}  worst={wf['worst']:+.3f}  "
                      f"{'UNSTABLE' if wf['unstable'] else 'stable'}")
                break
    best_wf = wf_results[0] if wf_results else {"fold_sharpes": [], "mean": np.nan, "std": np.nan, "worst": np.nan, "unstable": True}

    # ── 5. Print full detail + cost sensitivity ───────────────────────────────
    print("\n[5/5] Printing detailed results...")
    cost_rows = cost_sensitivity(best_cfg, funding_h, prices_d)
    periods   = period_breakdown(best_cfg, funding_h, prices_d)
    print_best_detail(best, best_wf, cost_rows, periods)
    print_verdict(best, best_wf)
    print_comparison(best)

    save_plot(df)

    elapsed = time.time() - t0
    print(f"\nTotal runtime: {elapsed/60:.1f} minutes")


if __name__ == "__main__":
    main()
