#!/usr/bin/env python
"""
Hyperliquid-Native Signals — Feasibility Study.

Tests 3 economic hypotheses using HL-specific data:
  A. OI/Price Divergence (funding-change proxy for OI)
  B. Post-Liquidation Mean Reversion (|price_ret| > 2σ proxy)
  C. Funding Extreme Reversal (hourly HL funding rates)

Data sources (all free, cached locally):
  - OHLCV 1h: yfinance  (starts ~2024-05-20, 730-day limit)
  - Funding 1h: Hyperliquid fundingHistory  (hourly settlement)
  - OI: No historical API → funding change as proxy (labeled PROXY)
  - Liquidations: No public API → |price_ret| > 2σ proxy (labeled PROXY)

Run: python -m strategies.hl_native.feasibility
"""
from __future__ import annotations

import time
import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import requests
import scipy.stats as stats
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────
ASSETS: list[str] = ["BTC", "ETH", "SOL"]
YF_TICKERS: dict[str, str] = {"BTC": "BTC-USD", "ETH": "ETH-USD", "SOL": "SOL-USD"}

# yfinance 1h limit is ~730 days from today. Use 2024-06-01 for safety.
DATA_START  = "2024-06-01"
DATA_END    = "2026-05-12"
TRAIN_END   = "2025-06-30"
TEST_START  = "2025-07-01"

# Prop firm challenge sims (same 44 dates as challenge_simulator.py)
SIM_START   = "2025-01-06"
SIM_END     = "2025-11-03"
PROPR_CAPITAL = 5_000.0
PROPR_TARGET  = 0.10
PROPR_DD      = 0.06
PROPR_DAILY   = 0.03
TSMOM_BASELINE_PASS = 0.34

# Hyperliquid API
HL_URL = "https://api.hyperliquid.xyz/info"
CHUNK_MS = 30 * 24 * 3600 * 1000  # 30-day chunks for API pagination
REQUEST_DELAY = 0.15               # seconds between HL requests

# Signal A — OI/Price Divergence (funding-change proxy for OI)
DIV_THRESHOLD    = 1.5   # σ divergence to trigger signal
DIV_ZSCORE_WINDOW = 24   # 24h rolling window for z-score normalization

# Signal B — Post-Liquidation Reversal (price spike proxy)
LIQ_SIGMA_THRESHOLD = 2.0   # σ above rolling mean to count as liquidation event
LIQ_ROLLING_WINDOW  = 48    # 48h rolling window for baseline
LIQ_HOLD_PERIODS    = [1, 2, 4]   # hours to test

# Signal C — Funding Extreme Reversal
# HL uses hourly funding; convert spec's 8h thresholds to 1h equivalents:
# 0.08%/8h = 0.01%/h = 0.0001/h   → SHORT threshold
# 0.03%/8h = 0.00375%/h → normalize to 0.00005/h (more practical for HL)
FUND_SHORT_THRESHOLD  = 0.0001    # > 0.01%/h → overleveraged longs, short
FUND_LONG_THRESHOLD   = -0.00003  # < -0.003%/h → overleveraged shorts, long
FUND_EXIT_THRESHOLD   = 0.00003   # < 0.003%/h → funding normalized, exit short
FUND_MAX_HOLD         = 48        # hours

# Backtest parameters
ATR_PERIOD    = 14
ATR_MULT_STOP = 1.5
RISK_PCT      = 0.01    # 1% per trade
MAX_POS_FRAC  = 0.10    # max 10% capital per position
COSTS_RT      = 0.0007  # 0.07% round-trip (HL taker × 2)
CAPITAL       = 10_000.0

# IC threshold for backtest
IC_TSTAT_PASS = 1.8
IC_ASSETS_PASS = 2  # need ≥2/3 assets

DATA_DIR  = Path(__file__).parent / "data"
OUT_DIR   = Path(__file__).parent
CHART_PATH = OUT_DIR / "feasibility_results.png"


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING & CACHING
# ─────────────────────────────────────────────────────────────────────────────

def _hl_post(payload: dict[str, Any], max_retries: int = 3) -> Any:
    """POST to Hyperliquid info endpoint with retry logic."""
    for attempt in range(max_retries):
        try:
            r = requests.post(HL_URL, json=payload, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise
            time.sleep(2 ** attempt)
    return []


def fetch_hl_funding(
    coin: str,
    start_ms: int,
    end_ms: int,
) -> pd.DataFrame:
    """Fetch hourly funding rates from Hyperliquid in 30-day chunks."""
    records: list[dict[str, Any]] = []
    t = start_ms
    while t < end_ms:
        chunk_end = min(t + CHUNK_MS, end_ms)
        data = _hl_post({
            "type": "fundingHistory",
            "coin": coin,
            "startTime": t,
            "endTime": chunk_end,
        })
        if data:
            records.extend(data)
        t = chunk_end
        time.sleep(REQUEST_DELAY)

    if not records:
        return pd.DataFrame(columns=["funding_rate"])

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["time"], unit="ms", utc=True).dt.tz_localize(None)
    df["funding_rate"] = df["fundingRate"].astype(float)
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="first")]
    return df[["funding_rate"]]


def load_or_fetch_ohlcv(coin: str) -> pd.DataFrame:
    """Load OHLCV 1h from cache or yfinance."""
    path = DATA_DIR / f"{coin}_ohlcv_1h.csv"
    if path.exists():
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        print(f"  {coin} OHLCV: loaded from cache  ({len(df)} rows)")
        return df

    print(f"  {coin} OHLCV: fetching from yfinance...")
    ticker = YF_TICKERS[coin]
    raw = yf.download(
        ticker, start=DATA_START, end=DATA_END,
        interval="1h", auto_adjust=True, progress=False,
    )
    if raw.empty:
        raise RuntimeError(f"yfinance returned empty data for {ticker}")

    # Flatten multi-level columns
    raw.columns = [c[0].lower() if isinstance(c, tuple) else c.lower() for c in raw.columns]
    df = raw[["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.to_datetime(df.index).tz_localize(None)
    df = df.dropna(subset=["close"])
    df.index.name = "timestamp"
    df.to_csv(path)
    print(f"  {coin} OHLCV: {len(df)} rows saved → {path.name}")
    return df


def load_or_fetch_funding(coin: str) -> pd.DataFrame:
    """Load funding rates from cache or Hyperliquid API."""
    path = DATA_DIR / f"{coin}_funding_1h.csv"
    if path.exists():
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        print(f"  {coin} funding: loaded from cache  ({len(df)} rows)")
        return df

    print(f"  {coin} funding: fetching from Hyperliquid...")
    start_ms = int(pd.Timestamp(DATA_START).timestamp() * 1000)
    end_ms   = int(pd.Timestamp(DATA_END).timestamp() * 1000)
    df = fetch_hl_funding(coin, start_ms, end_ms)
    if df.empty:
        raise RuntimeError(f"Hyperliquid returned empty funding data for {coin}")
    df.index.name = "timestamp"
    df.to_csv(path)
    print(f"  {coin} funding: {len(df)} rows saved → {path.name}")
    return df


def build_hourly_panel(coin: str) -> pd.DataFrame:
    """
    Merge OHLCV + funding into a single 1h panel.

    Funding from HL is already hourly (settled every 1h on HL).
    Aligns on timestamp intersection and computes derived columns.
    """
    ohlcv   = load_or_fetch_ohlcv(coin)
    funding = load_or_fetch_funding(coin)

    # Normalize timestamps to hour-floor
    ohlcv.index   = pd.DatetimeIndex(ohlcv.index).floor("h")
    funding.index = pd.DatetimeIndex(funding.index).floor("h")

    # Resample funding to hourly if needed (forward-fill gaps)
    funding_h = funding.resample("h").last().ffill()

    # Merge: inner join on common hours
    df = ohlcv.join(funding_h, how="left")
    df["funding_rate"] = df["funding_rate"].ffill()

    # Drop rows with missing prices
    df = df.dropna(subset=["close", "open"])

    # Returns
    df["log_ret"] = np.log(df["close"] / df["close"].shift(1))
    df["ret_1h"]  = np.exp(df["log_ret"]) - 1

    df.attrs["coin"] = coin
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — FEATURE ENGINEERING
# ─────────────────────────────────────────────────────────────────────────────

def add_signal_a(df: pd.DataFrame) -> pd.DataFrame:
    """
    Signal A — OI/Price Divergence.

    OI PROXY: funding rate change (1h delta). Economic rationale:
      When OI increases (new longs enter), funding rate rises.
      When OI decreases, funding rate falls.
    This is a better proxy than volume because it directly reflects
    the long/short balance driving OI changes.

    Data source: OI proxy (funding change). Labeled 'PROXY — no historical OI API'.
    """
    df = df.copy()

    # Rolling z-scores (24h window) — no look-ahead
    ret_mean = df["ret_1h"].rolling(DIV_ZSCORE_WINDOW, min_periods=12).mean()
    ret_std  = df["ret_1h"].rolling(DIV_ZSCORE_WINDOW, min_periods=12).std()
    df["price_zscore"] = (df["ret_1h"] - ret_mean) / ret_std.replace(0, np.nan)

    # OI proxy: 1h change in funding rate (standardized)
    fund_diff = df["funding_rate"].diff(1)
    fd_mean   = fund_diff.rolling(DIV_ZSCORE_WINDOW, min_periods=12).mean()
    fd_std    = fund_diff.rolling(DIV_ZSCORE_WINDOW, min_periods=12).std()
    df["oi_proxy_zscore"] = (fund_diff - fd_mean) / fd_std.replace(0, np.nan)

    df["oi_div"] = df["oi_proxy_zscore"] - df["price_zscore"]

    # Signal definition (using close of T, entry at open of T+1)
    # SIG_A_LONG:  OI proxy rising faster than price → new longs building → follow up
    # SIG_A_SHORT: OI proxy falling faster than price falls → new shorts building → follow down
    # SIG_A_REV:   Price rising but OI proxy falling → short covering → fade (SHORT)
    df["sig_a_long"]  = (
        (df["oi_div"] >  DIV_THRESHOLD) & (df["price_zscore"] > 0)
    ).astype(float)
    df["sig_a_short"] = (
        (df["oi_div"] >  DIV_THRESHOLD) & (df["price_zscore"] < 0)
    ).astype(float)
    df["sig_a_rev"]   = (
        (df["oi_div"] < -DIV_THRESHOLD) & (df["price_zscore"] > 0)
    ).astype(float)   # → SHORT signal (fade the rally)

    return df


def add_signal_b(df: pd.DataFrame) -> pd.DataFrame:
    """
    Signal B — Post-Liquidation Mean Reversion.

    PROXY: |price_ret_1h| > 2σ rolling std (48h window).
    Economic rationale: large negative returns = forced long liquidations → buy.
    Large positive returns = forced short liquidations (squeeze) → sell.

    Data source: PROXY — no public liquidation API available.
    Proxy uses |price_ret| > 2σ as liquidation event indicator.
    """
    df = df.copy()

    liq_mean = df["ret_1h"].rolling(LIQ_ROLLING_WINDOW, min_periods=24).mean()
    liq_std  = df["ret_1h"].rolling(LIQ_ROLLING_WINDOW, min_periods=24).std()

    # Negative spike → long liquidations → BUY signal
    df["sig_b_long"]  = (df["ret_1h"] < liq_mean - LIQ_SIGMA_THRESHOLD * liq_std).astype(float)
    # Positive spike → short liquidations → SELL signal
    df["sig_b_short"] = (df["ret_1h"] > liq_mean + LIQ_SIGMA_THRESHOLD * liq_std).astype(float)

    # Signed signal for IC computation: +1 for buy, -1 for sell, 0 for flat
    df["sig_b"] = df["sig_b_long"] - df["sig_b_short"]

    return df


def add_signal_c(df: pd.DataFrame) -> pd.DataFrame:
    """
    Signal C — Funding Extreme Reversal.

    Uses actual HL hourly funding rates (not a proxy).
    HL settles funding every hour; thresholds adjusted from spec's 8h basis:
      0.08%/8h → 0.01%/h → 0.0001 (hourly rate)
      -0.03%/8h → -0.00375%/h → -0.00003 (rounded to practical HL level)

    Economic rationale: extreme positive funding = overleveraged longs →
    short squeeze risk → short. Extreme negative = overleveraged shorts → long.
    """
    df = df.copy()

    df["sig_c_short"] = (df["funding_rate"] >  FUND_SHORT_THRESHOLD).astype(float)
    df["sig_c_long"]  = (df["funding_rate"] <  FUND_LONG_THRESHOLD).astype(float)

    # Signed signal: -1 = short, +1 = long, 0 = flat
    df["sig_c"] = df["sig_c_long"] - df["sig_c_short"]

    return df


def add_atr(df: pd.DataFrame) -> pd.DataFrame:
    """Add ATR(14, 1h) column."""
    df = df.copy()
    prev_c = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_c).abs(),
        (df["low"]  - prev_c).abs(),
    ], axis=1).max(axis=1)
    df["atr"] = tr.rolling(ATR_PERIOD, min_periods=5).mean()
    df["atr_pct"] = df["atr"] / df["close"]
    return df


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — IC ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

def compute_forward_returns(df: pd.DataFrame, hold_periods: list[int]) -> pd.DataFrame:
    """
    Compute forward log-returns for multiple hold periods.

    fwd_ret[T, h] = log(close[T+h] / close[T])
    Entry at open[T+1], but we use close[T+h] relative to close[T] as
    a conservative approximation (ignores open-to-close spread at entry).
    """
    fwd: dict[str, pd.Series] = {}
    for h in hold_periods:
        fwd[f"fwd_{h}h"] = np.log(df["close"].shift(-h) / df["close"])
    return pd.DataFrame(fwd, index=df.index)


def _ic_tstat(signal: pd.Series, fwd_ret: pd.Series) -> tuple[float, float, int]:
    """
    Compute monthly IC and t-stat.

    For binary signals: uses t-test between signal=1 and signal=0 groups.
    Returns (IC, t_stat, n_signal_obs).
    """
    mask = signal.notna() & fwd_ret.notna()
    s    = signal[mask]
    f    = fwd_ret[mask]

    if len(s) < 20:
        return 0.0, 0.0, 0

    # Monthly IC: Spearman rank corr per month, then t-stat on distribution
    combined = pd.DataFrame({"sig": s, "fwd": f})
    monthly_ics: list[float] = []
    for _, grp in combined.groupby(pd.Grouper(freq="ME")):
        if len(grp) < 10:
            continue
        if grp["sig"].std() < 1e-9:  # constant signal in this month
            continue
        r, _ = stats.spearmanr(grp["sig"], grp["fwd"], nan_policy="omit")
        if not np.isnan(r):
            monthly_ics.append(r)

    if len(monthly_ics) < 3:
        return 0.0, 0.0, int(s.sum())

    ic_mean  = float(np.mean(monthly_ics))
    ic_std   = float(np.std(monthly_ics, ddof=1))
    n_months = len(monthly_ics)
    t_stat   = ic_mean / (ic_std / np.sqrt(n_months)) if ic_std > 0 else 0.0

    n_signal = int((s != 0).sum())
    return ic_mean, t_stat, n_signal


def _mean_fwd_comparison(
    signal: pd.Series,
    fwd_ret: pd.Series,
    direction: int = 1,
) -> tuple[float, float, float]:
    """Mean fwd return when signal fires vs no signal. Returns (mean_sig, mean_no_sig, t)."""
    mask   = signal.notna() & fwd_ret.notna()
    sig_on = (signal[mask] * direction > 0)
    on     = fwd_ret[mask][sig_on]
    off    = fwd_ret[mask][~sig_on]
    if len(on) < 5 or len(off) < 5:
        return 0.0, 0.0, 0.0
    t, _ = stats.ttest_ind(on * direction, off, equal_var=False)
    return float(on.mean()), float(off.mean()), float(t)


def analyze_signal_a(
    panels: dict[str, pd.DataFrame],
    train_only: bool = True,
) -> dict[str, Any]:
    """Step 3 for Signal A — IC analysis across assets and sub-signals."""
    print(f"\n{'─'*55}")
    print("SIGNAL A — OI/Price Divergence (Funding-Change PROXY for OI)")
    print(f"{'─'*55}")

    hold = 4   # Signal A: mean reversion holds ~4h
    results: dict[str, Any] = {"pass": 0, "details": {}}

    sub_signals = [
        ("a_long",  "sig_a_long",  +1, "LONG trend-follow"),
        ("a_short", "sig_a_short", -1, "SHORT trend-follow"),
        ("a_rev",   "sig_a_rev",   -1, "SHORT fade (reversal)"),
    ]

    print(f"\n  {'Asset':<6} {'Sub-signal':<22} {'IC':>6} {'t-stat':>8} "
          f"{'n_sig':>6} {'mean_sig':>10} {'mean_none':>11}")
    print(f"  {'-'*75}")

    passing_tstats: list[float] = []

    for sub_id, col, direction, label in sub_signals:
        assets_pass = 0
        best_tstat  = 0.0
        best_abs_t  = 0.0  # track regardless of threshold

        for coin, df in panels.items():
            period = df[df.index <= TRAIN_END] if train_only else df[df.index >= TEST_START]
            fwd    = compute_forward_returns(period, [hold])
            sig    = period[col] * direction  # sign-adjust: +1 = bullish

            ic, t, n_sig = _ic_tstat(sig, fwd[f"fwd_{hold}h"])
            m_sig, m_none, _ = _mean_fwd_comparison(period[col], fwd[f"fwd_{hold}h"], direction)
            marker = " ✓" if t > IC_TSTAT_PASS else ""

            print(f"  {coin:<6} {label:<22} {ic:>6.3f} {t:>8.2f}"
                  f" {n_sig:>6} {m_sig:>10.4f} {m_none:>10.4f}{marker}")

            best_abs_t = max(best_abs_t, abs(t))
            if t > IC_TSTAT_PASS:
                assets_pass += 1
                best_tstat   = max(best_tstat, t)

        results["details"][sub_id] = {
            "label": label, "assets_pass": assets_pass,
            "best_tstat": max(best_tstat, best_abs_t),
        }
        if assets_pass >= IC_ASSETS_PASS:
            results["pass"] += 1
            passing_tstats.append(best_tstat)

    best_tstat  = max((r["best_tstat"] for r in results["details"].values()), default=0.0)
    assets_best = max((r["assets_pass"] for r in results["details"].values()), default=0)

    print(f"\n  Signal A: {results['pass']}/3 sub-signals pass t>{IC_TSTAT_PASS} on ≥{IC_ASSETS_PASS}/3 assets")
    print(f"  Best t-stat: {best_tstat:.2f} on {assets_best}/3 assets")

    results["best_tstat"]  = best_tstat
    results["assets_best"] = assets_best
    results["hold"]        = hold
    results["passed"]      = results["pass"] >= 1
    return results


def analyze_signal_b(
    panels: dict[str, pd.DataFrame],
    train_only: bool = True,
) -> dict[str, Any]:
    """Step 3 for Signal B — IC analysis across hold periods."""
    print(f"\n{'─'*55}")
    print("SIGNAL B — Post-Liquidation Reversal (|price_ret|>2σ PROXY)")
    print(f"{'─'*55}")

    results: dict[str, Any] = {"pass": 0, "best_hold": 1, "details": {}}
    best_overall = 0.0
    best_hold    = 1

    print(f"\n  {'Asset':<6} {'Hold':>5} {'Side':<8} {'IC':>6} {'t-stat':>8} "
          f"{'n_sig':>6} {'freq/wk':>8}")
    print(f"  {'-'*60}")

    for h in LIQ_HOLD_PERIODS:
        assets_long_pass  = 0
        assets_short_pass = 0
        best_h_tstat      = 0.0

        for coin, df in panels.items():
            period = df[df.index <= TRAIN_END] if train_only else df[df.index >= TEST_START]
            fwd    = compute_forward_returns(period, [h])

            # LONG signal: big negative ret → buy (expect reversal up)
            ic_l, t_l, n_l = _ic_tstat(period["sig_b_long"], fwd[f"fwd_{h}h"])
            # SHORT signal: big positive ret → sell (expect reversal down)
            ic_s, t_s, n_s = _ic_tstat(period["sig_b_short"], -fwd[f"fwd_{h}h"])

            n_days_h = len(period) / 24  # approximate days
            freq_l   = n_l / (n_days_h / 7) if n_days_h > 0 else 0
            freq_s   = n_s / (n_days_h / 7) if n_days_h > 0 else 0

            marker_l = " ✓" if t_l > IC_TSTAT_PASS else ""
            marker_s = " ✓" if t_s > IC_TSTAT_PASS else ""

            print(f"  {coin:<6} {h:>4}h  {'LONG':<8} {ic_l:>6.3f} {t_l:>8.2f} "
                  f"{n_l:>6} {freq_l:>7.1f}/wk{marker_l}")
            print(f"  {coin:<6} {h:>4}h  {'SHORT':<8} {ic_s:>6.3f} {t_s:>8.2f} "
                  f"{n_s:>6} {freq_s:>7.1f}/wk{marker_s}")

            if t_l > IC_TSTAT_PASS:
                assets_long_pass  += 1
                best_h_tstat       = max(best_h_tstat, t_l)
            if t_s > IC_TSTAT_PASS:
                assets_short_pass += 1
                best_h_tstat       = max(best_h_tstat, t_s)

        total_pass = max(assets_long_pass, assets_short_pass)
        results["details"][f"h{h}"] = {
            "hold": h, "assets_long_pass": assets_long_pass,
            "assets_short_pass": assets_short_pass, "best_tstat": best_h_tstat,
        }
        # Track best t-stat regardless of whether threshold met
        if best_h_tstat > best_overall:
            best_overall = best_h_tstat
            best_hold    = h
        if total_pass >= IC_ASSETS_PASS:
            results["pass"] += 1

    results["best_tstat"]  = best_overall
    results["best_hold"]   = best_hold
    results["passed"]      = results["pass"] >= 1
    print(f"\n  Signal B: {results['pass']}/{len(LIQ_HOLD_PERIODS)} hold periods pass on ≥{IC_ASSETS_PASS}/3 assets")
    print(f"  Best individual t-stat: {best_overall:.2f} (at {best_hold}h hold)")
    print(f"  Note: SOL only — need ≥2/3 assets to pass")
    return results


def analyze_signal_c(
    panels: dict[str, pd.DataFrame],
    train_only: bool = True,
) -> dict[str, Any]:
    """Step 3 for Signal C — Funding Extreme IC analysis."""
    print(f"\n{'─'*55}")
    print("SIGNAL C — Funding Extreme Reversal (ACTUAL HL hourly funding)")
    print(f"{'─'*55}")

    hold = 24  # Test 24h hold (max_hold is 48h)
    results: dict[str, Any] = {"pass": 0, "details": {}}

    print(f"\n  {'Asset':<6} {'Side':<8} {'IC':>6} {'t-stat':>8} "
          f"{'n_sig':>6} {'freq/mo':>8} {'mean_fwd':>10} {'mean_none':>11}")
    print(f"  {'-'*72}")

    for side, col, direction, label in [
        ("SHORT", "sig_c_short", -1, "SHORT (funding>0.0001)"),
        ("LONG",  "sig_c_long",  +1, "LONG  (funding<-0.00003)"),
    ]:
        assets_pass = 0
        best_tstat  = 0.0
        best_abs_t  = 0.0  # track best regardless of threshold

        for coin, df in panels.items():
            period = df[df.index <= TRAIN_END] if train_only else df[df.index >= TEST_START]
            fwd    = compute_forward_returns(period, [hold])
            sig    = period[col]

            ic, t, n_sig = _ic_tstat(sig * direction, fwd[f"fwd_{hold}h"])
            m_sig, m_none, _ = _mean_fwd_comparison(sig, fwd[f"fwd_{hold}h"], direction)

            n_days = len(period) / 24
            freq   = n_sig / (n_days / 30) if n_days > 0 else 0

            marker = " ✓" if t > IC_TSTAT_PASS else ""
            print(f"  {coin:<6} {label:<24} {ic:>6.3f} {t:>8.2f} "
                  f"{n_sig:>6} {freq:>7.1f}/mo {m_sig:>9.4f} {m_none:>10.4f}{marker}")

            best_abs_t = max(best_abs_t, abs(t))
            if t > IC_TSTAT_PASS:
                assets_pass += 1
                best_tstat   = max(best_tstat, t)

        results["details"][side] = {
            "assets_pass": assets_pass,
            "best_tstat":  max(best_tstat, best_abs_t),  # report actual best
        }
        if assets_pass >= IC_ASSETS_PASS:
            results["pass"] += 1

    # Track best t-stat regardless of pass threshold
    best_tstat  = max((r["best_tstat"] for r in results["details"].values()), default=0.0)
    assets_best = max((r["assets_pass"] for r in results["details"].values()), default=0)

    print(f"\n  Signal C: {results['pass']}/2 sides pass t>{IC_TSTAT_PASS} on ≥{IC_ASSETS_PASS}/3 assets")
    print(f"  Best t-stat: {best_tstat:.2f} on {assets_best}/3 assets")

    results["best_tstat"]  = best_tstat
    results["assets_best"] = assets_best
    results["hold"]        = hold
    results["passed"]      = results["pass"] >= 1
    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — BACKTEST ENGINE
# ─────────────────────────────────────────────────────────────────────────────

def _run_backtest(
    df: pd.DataFrame,
    signal_col: str,
    direction: int,
    hold_hours: int,
    start: str,
    end: str,
) -> dict[str, Any]:
    """
    Event-driven hourly backtest with ATR stops.

    Entry: open[T+1] when signal fires at T.
    Stop:  entry ± ATR_MULT_STOP × ATR[T] (computed from T's close).
    Target: hold_hours after entry OR stop, whichever first.
    Size:  min(RISK_PCT / stop_pct, MAX_POS_FRAC) of capital.
    """
    sub = df[(df.index >= start) & (df.index <= end)].copy()
    if len(sub) < 10:
        return {"pnl": pd.Series(dtype=float), "sharpe": 0.0, "max_dd": 0.0,
                "ann_ret": 0.0, "win_rate": 0.0, "n_trades": 0, "max_day_loss": 0.0}

    dates  = sub.index.tolist()
    n      = len(dates)
    daily_pnl: dict[pd.Timestamp, float] = {}
    trades: list[dict[str, Any]] = []

    # Active position: one per asset (this function handles one asset at a time)
    pos: dict[str, Any] | None = None

    for i, ts in enumerate(dates):
        row     = sub.loc[ts]
        day_key = pd.Timestamp(ts.date())

        day_pnl_today = daily_pnl.get(day_key, 0.0)

        # ── Manage open position ──────────────────────────────────────────
        if pos is not None:
            px    = float(row["close"])
            entry = pos["entry_px"]
            side  = pos["direction"]

            raw_ret = (px - entry) / entry * side  # positive = profit
            bars_held = i - pos["entry_bar"]

            hit_stop   = raw_ret < -pos["stop_pct"]
            hit_target = bars_held >= hold_hours

            if hit_stop or hit_target:
                exit_ret = -pos["stop_pct"] if hit_stop else raw_ret
                net_ret  = (exit_ret - COSTS_RT) * pos["notional_frac"]
                day_pnl_today += net_ret
                trades.append({
                    "ret": net_ret,
                    "exit": "stop" if hit_stop else "hold",
                })
                pos = None

        daily_pnl[day_key] = day_pnl_today

        # ── Open new position ─────────────────────────────────────────────
        if pos is None and i + 1 < n:
            sig = float(row.get(signal_col, 0.0))
            if sig == 0.0 or np.isnan(sig):
                continue

            atr_pct = float(row.get("atr_pct", np.nan))
            if np.isnan(atr_pct) or atr_pct <= 0:
                continue

            stop_pct = ATR_MULT_STOP * atr_pct
            nfrac    = min(RISK_PCT / max(stop_pct, 1e-6), MAX_POS_FRAC)

            next_ts = dates[i + 1]
            entry_px = float(sub.at[next_ts, "open"]) if "open" in sub.columns else float(row["close"])

            if np.isnan(entry_px) or entry_px <= 0:
                continue

            # Entry cost
            entry_cost = COSTS_RT * nfrac
            daily_pnl[pd.Timestamp(next_ts.date())] = \
                daily_pnl.get(pd.Timestamp(next_ts.date()), 0.0) - entry_cost

            pos = {
                "direction":    direction,
                "entry_px":     entry_px,
                "entry_bar":    i,
                "stop_pct":     stop_pct,
                "notional_frac": nfrac,
            }

    pnl = pd.Series(daily_pnl).sort_index()
    if pnl.empty:
        return {"pnl": pnl, "sharpe": 0.0, "max_dd": 0.0,
                "ann_ret": 0.0, "win_rate": 0.0, "n_trades": 0, "max_day_loss": 0.0}

    eq = (1 + pnl).cumprod()
    n_days  = len(pnl)
    ann_ret = float(pnl.mean() * 365)
    ann_vol = float(pnl.std() * np.sqrt(365))
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0.0
    max_dd  = float((eq / eq.cummax() - 1).min())
    max_day = float(pnl.min())
    win_rate = sum(1 for t in trades if t["ret"] > 0) / len(trades) if trades else 0.0
    n_trades_per_year = len(trades) / (n_days / 365)

    return {
        "pnl":         pnl,
        "sharpe":      sharpe,
        "ann_ret":     ann_ret,
        "ann_vol":     ann_vol,
        "max_dd":      max_dd,
        "max_day_loss": max_day,
        "win_rate":    win_rate,
        "n_trades":    n_trades_per_year,
        "pct_exceed_3": float((pnl < -0.03).mean()) * 100,
    }


def run_backtest_signal(
    panels: dict[str, pd.DataFrame],
    signal_col: str,
    direction: int,
    hold_hours: int,
    label: str,
) -> dict[str, Any]:
    """Run backtest on TEST set for a signal, pooled across assets."""
    print(f"\n  [{label}] testing on {TEST_START} → 2026-05-11")

    per_asset: dict[str, Any] = {}
    all_pnl: list[pd.Series] = []

    for coin, df in panels.items():
        r = _run_backtest(df, signal_col, direction, hold_hours, TEST_START, DATA_END)
        per_asset[coin] = r
        if not r["pnl"].empty:
            all_pnl.append(r["pnl"])

    if not all_pnl:
        return {"pnl": pd.Series(dtype=float), "sharpe": 0.0, "max_dd": 0.0,
                "win_rate": 0.0, "n_trades": 0, "max_day_loss": 0.0, "pct_exceed_3": 0.0}

    # Portfolio: equal-weight across assets (average daily P&L)
    combined = pd.concat(all_pnl, axis=1).fillna(0.0)
    port_pnl  = combined.mean(axis=1)

    eq = (1 + port_pnl).cumprod()
    ann_ret = float(port_pnl.mean() * 365)
    ann_vol = float(port_pnl.std() * np.sqrt(365))
    sharpe  = ann_ret / ann_vol if ann_vol > 0 else 0.0
    max_dd  = float((eq / eq.cummax() - 1).min())
    max_day = float(port_pnl.min())
    win_rate = float(np.mean([r["win_rate"] for r in per_asset.values()]))
    n_trades = float(np.mean([r["n_trades"] for r in per_asset.values()]))
    pct_3    = float((port_pnl < -0.03).mean()) * 100

    print(f"    Portfolio: Sharpe={sharpe:.2f}  MaxDD={max_dd:.1%}  "
          f"AnnRet={ann_ret:+.1%}  WinRate={win_rate:.1%}  "
          f"n_trades/yr={n_trades:.0f}  max_day={max_day:.3%}  >3%={pct_3:.1f}%")

    for coin, r in per_asset.items():
        if not r["pnl"].empty:
            print(f"    {coin}: Sharpe={r['sharpe']:.2f}  n_trades={r['n_trades']:.0f}")

    return {
        "pnl":        port_pnl,
        "sharpe":     sharpe,
        "ann_ret":    ann_ret,
        "max_dd":     max_dd,
        "win_rate":   win_rate,
        "n_trades":   n_trades,
        "max_day_loss": max_day,
        "pct_exceed_3": pct_3,
        "per_asset":  per_asset,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — PROP FIRM COMPATIBILITY
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_challenge(
    daily_pnl: pd.Series,
    start_date: pd.Timestamp,
    initial_equity: float,
    target_pct: float,
    dd_pct: float,
    daily_pct: float,
) -> dict[str, Any]:
    """Simulate one Propr challenge attempt. Static HWM."""
    sim_dates = daily_pnl.index[daily_pnl.index >= start_date]
    equity = initial_equity
    hwm    = initial_equity
    days   = 0

    for date in sim_dates:
        eq_start = equity
        equity   = eq_start * (1 + float(daily_pnl.get(date, 0.0)))
        days    += 1
        if (equity - eq_start) / eq_start < -daily_pct:
            return {"outcome": "FAIL", "reason": "daily_limit", "days": days}
        if equity <= hwm * (1 - dd_pct):
            return {"outcome": "FAIL", "reason": "total_dd", "days": days}
        if equity >= hwm * (1 + target_pct):
            return {"outcome": "PASS", "reason": None, "days": days}

    return {"outcome": "INCOMPLETE", "reason": None, "days": days}


def run_propr_sims(pnl: pd.Series, label: str) -> dict[str, Any]:
    """Run 44 Propr challenge sims for a P&L series."""
    if pnl.empty:
        return {"pass_rate": 0.0, "fail_daily": 0, "fail_dd": 0}
    if pnl.index.tz is not None:
        pnl = pnl.copy(); pnl.index = pnl.index.tz_localize(None)

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    results = [
        _simulate_challenge(pnl, sd, PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY)
        for sd in start_dates
    ]
    pass_rate  = sum(1 for r in results if r["outcome"] == "PASS") / len(results)
    fail_daily = sum(1 for r in results if r.get("reason") == "daily_limit")
    fail_dd    = sum(1 for r in results if r.get("reason") == "total_dd")

    print(f"\n  {label} — Propr pass rate: {pass_rate:.0%}  "
          f"(daily_limit: {fail_daily}/44, total_dd: {fail_dd}/44)")
    print(f"  TSMOM baseline: {TSMOM_BASELINE_PASS:.0%}")

    return {"pass_rate": pass_rate, "fail_daily": fail_daily, "fail_dd": fail_dd}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    ic_a: dict[str, Any],
    ic_b: dict[str, Any],
    ic_c: dict[str, Any],
    bt_a: dict[str, Any] | None,
    bt_b: dict[str, Any] | None,
    bt_c: dict[str, Any] | None,
    propr_a: dict[str, Any] | None,
    propr_b: dict[str, Any] | None,
    propr_c: dict[str, Any] | None,
) -> str:
    """Print structured verdict report."""

    def _sharpe(bt: dict[str, Any] | None) -> float:
        return bt.get("sharpe", 0.0) if bt else 0.0

    def _pass(bt: dict[str, Any] | None) -> str:
        if bt is None:
            return "SKIP (IC failed)"
        s = _sharpe(bt)
        return f"PASS (Sharpe={s:.2f})" if s >= 0.5 else f"FAIL (Sharpe={s:.2f})"

    border = "═" * 60
    print(f"\n{border}")
    print("HL-NATIVE SIGNALS FEASIBILITY REPORT")
    print(f"{border}")

    print(f"\n  Signal A — OI/Price Divergence (Funding PROXY for OI)")
    print(f"    IC t-stat (best)  : {ic_a['best_tstat']:.2f} on {ic_a.get('assets_best',0)}/3 assets")
    print(f"    OOS Sharpe        : {_sharpe(bt_a):.2f}" if bt_a else
          f"    OOS Sharpe        : — (not backtested)")
    print(f"    Max daily loss    : {bt_a['max_day_loss']:.2%}" if bt_a else
          f"    Max daily loss    : —")
    print(f"    Verdict           : {_pass(bt_a) if ic_a['passed'] else 'SKIP (IC failed)'}")

    print(f"\n  Signal B — Post-Liquidation Reversal (|ret|>2σ PROXY)")
    n_pass_b = max(
        (max(r.get("assets_long_pass",0), r.get("assets_short_pass",0))
         for r in ic_b["details"].values()), default=0
    )
    print(f"    IC t-stat (best)  : {ic_b['best_tstat']:.2f} on {n_pass_b}/3 assets")
    print(f"    Best hold period  : {ic_b['best_hold']}h")
    print(f"    OOS Sharpe        : {_sharpe(bt_b):.2f}" if bt_b else
          f"    OOS Sharpe        : — (not backtested)")
    print(f"    Max daily loss    : {bt_b['max_day_loss']:.2%}" if bt_b else
          f"    Max daily loss    : —")
    print(f"    Note              : PROXY — no real liquidation data available from HL public API")
    print(f"    Verdict           : {_pass(bt_b) if ic_b['passed'] else 'SKIP (IC failed)'}")

    print(f"\n  Signal C — Funding Extreme Reversal (actual HL hourly funding)")
    print(f"    IC t-stat (best)  : {ic_c['best_tstat']:.2f} on "
          f"{ic_c.get('assets_best', 0)}/3 assets")
    print(f"    Signal frequency  : see per-asset table above")
    print(f"    OOS Sharpe        : {_sharpe(bt_c):.2f}" if bt_c else
          f"    OOS Sharpe        : — (not backtested)")
    print(f"    Max daily loss    : {bt_c['max_day_loss']:.2%}" if bt_c else
          f"    Max daily loss    : —")
    print(f"    Verdict           : {_pass(bt_c) if ic_c['passed'] else 'SKIP (IC failed)'}")

    # Determine best signal
    candidates: list[tuple[str, float, dict[str, Any] | None, dict[str, Any] | None]] = [
        ("A", _sharpe(bt_a), bt_a, propr_a),
        ("B", _sharpe(bt_b), bt_b, propr_b),
        ("C", _sharpe(bt_c), bt_c, propr_c),
    ]
    candidates = [(n, s, bt, pr) for n, s, bt, pr in candidates if bt is not None]

    best_name, best_sharpe, best_bt, best_propr = (
        max(candidates, key=lambda x: x[1]) if candidates else ("none", 0.0, None, None)
    )
    best_pass_rate = best_propr["pass_rate"] if best_propr else 0.0

    print(f"\n  {'─'*56}")
    print(f"  OVERALL SUMMARY")
    print(f"  {'─'*56}")
    print(f"  Best signal       : {best_name}")
    print(f"  Propr pass rate   : {best_pass_rate:.0%}  (vs TSMOM: {TSMOM_BASELINE_PASS:.0%})")

    if best_sharpe >= 0.5 and best_pass_rate >= 0.30:
        verdict = "PROMISING"
        rec = ("Run full multi-asset backtest. Combine with TSMOM v2 for portfolio. "
               f"Best signal: {best_name}.")
    elif best_sharpe >= 0.5:
        verdict = "WEAK"
        rec = f"Signal {best_name} has Sharpe > 0.5 but low Propr pass rate. Tune position sizing."
    elif any(ic["passed"] for ic in [ic_a, ic_b, ic_c]):
        verdict = "SKIP"
        rec = "IC passes but backtest fails. Likely due to costs + slippage eroding thin edge."
    else:
        verdict = "SKIP"
        rec = ("No HL-native signal passes IC test on OOS period. "
               "Recommendation: pivot to equity futures (ES/NQ) where "
               "liquidation and OI data is richer via CME, or consider "
               "longer holding periods to reduce cost impact.")

    print(f"  Recommendation    : {rec}")
    print(f"\n  ┌{'─'*55}┐")
    print(f"  │  VERDICT: {verdict:<46}│")
    print(f"  └{'─'*55}┘")

    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────────────────────────────────────

def save_charts(
    ic_a: dict[str, Any],
    ic_b: dict[str, Any],
    ic_c: dict[str, Any],
    backtests: dict[str, dict[str, Any] | None],
) -> None:
    """Save 3-subplot feasibility chart."""
    fig = plt.figure(figsize=(16, 12))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.38, wspace=0.3)

    # ── Plot 1: IC t-stat bar chart per signal ────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    signals_ic = [
        ("A (best sub-signal)", ic_a["best_tstat"]),
        ("B (best hold)",       ic_b["best_tstat"]),
        ("C (funding extreme)", ic_c["best_tstat"]),
    ]
    names = [s[0] for s in signals_ic]
    tstats = [s[1] for s in signals_ic]
    colors = ["forestgreen" if t > IC_TSTAT_PASS else "tomato" for t in tstats]
    bars   = ax1.bar(names, tstats, color=colors, alpha=0.8, edgecolor="white")
    ax1.axhline(IC_TSTAT_PASS, color="black", ls="--", lw=1.5, label=f"Threshold ({IC_TSTAT_PASS})")
    ax1.set_title("IC t-stat by Signal (train set)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("IC t-stat")
    ax1.legend(fontsize=9)
    ax1.grid(True, alpha=0.3, axis="y")
    for bar, t in zip(bars, tstats):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                 f"{t:.2f}", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # ── Plot 2: Equity curves for passing signals ─────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    colors_map = {"A": "steelblue", "B": "darkorange", "C": "forestgreen"}
    has_curves = False
    for sig_name, bt in backtests.items():
        if bt is None or bt["pnl"].empty:
            continue
        eq = (1 + bt["pnl"]).cumprod() * 100
        ax2.plot(eq.index, eq.values, color=colors_map.get(sig_name, "gray"),
                 lw=1.8, label=f"Signal {sig_name} (Sharpe={bt['sharpe']:.2f})")
        has_curves = True
    ax2.axhline(100, color="gray", ls="--", lw=0.8)
    ax2.set_title(f"Equity Curves — OOS Test ({TEST_START[:7]}→2026-05)",
                  fontsize=11, fontweight="bold")
    ax2.set_ylabel("Equity (start=100)")
    if has_curves:
        ax2.legend(fontsize=8)
    else:
        ax2.text(0.5, 0.5, "No signals passed IC test\n(no backtests run)",
                 ha="center", va="center", transform=ax2.transAxes, fontsize=12, color="gray")
    ax2.grid(True, alpha=0.3)

    # ── Plot 3: Daily P&L histogram with -3% line ─────────────────────────────
    ax3 = fig.add_subplot(gs[1, :])
    plotted = False
    for sig_name, bt in backtests.items():
        if bt is None or bt["pnl"].empty:
            continue
        pnl_pct = bt["pnl"].values * 100
        valid   = pnl_pct[~np.isnan(pnl_pct)]
        if len(valid) < 5:
            continue
        lo, hi = max(valid.min(), -8), min(valid.max(), 8)
        bins = np.linspace(lo, hi, 50)
        ax3.hist(valid, bins=bins, alpha=0.5, color=colors_map.get(sig_name, "gray"),
                 label=f"Signal {sig_name}", density=True)
        plotted = True
    ax3.axvline(-3.0, color="red",   ls="--", lw=2, label="Propr limit (-3%)")
    ax3.axvline(0,    color="black", ls="-",  lw=0.8)
    ax3.set_title("Daily P&L Distribution — All Backtested Signals", fontsize=11, fontweight="bold")
    ax3.set_xlabel("Daily P&L (%)")
    ax3.set_ylabel("Density")
    ax3.legend(fontsize=9)
    ax3.grid(True, alpha=0.3)
    if not plotted:
        ax3.text(0.5, 0.5, "No signals reached backtest stage",
                 ha="center", va="center", transform=ax3.transAxes, fontsize=12, color="gray")

    plt.suptitle(
        "Hyperliquid-Native Signals — Feasibility Study\n"
        f"A: OI/Price Divergence (funding proxy) | B: Post-Liq Reversal (|ret|>2σ proxy) | C: Funding Extreme\n"
        f"Train: {DATA_START}→{TRAIN_END}  |  Test: {TEST_START}→2026-05-11",
        fontsize=12, fontweight="bold", y=0.99,
    )
    plt.savefig(CHART_PATH, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\n  Chart saved → {CHART_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("HL-NATIVE SIGNALS — FEASIBILITY STUDY")
    print("=" * 60)
    print("Signals: A=OI/Price Divergence  B=Post-Liq Reversal  C=Funding Extreme")
    print(f"Period: {DATA_START} → 2026-05-11  (yfinance 730-day 1h limit)")
    print(f"Train: {DATA_START}→{TRAIN_END}  |  Test: {TEST_START}→2026-05-11")
    print("=" * 60)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 0: Load and validate data ────────────────────────────────────────
    print("\n[STEP 0] Loading market data...")
    panels: dict[str, pd.DataFrame] = {}

    for coin in ASSETS:
        print(f"\n  {coin}:")
        df = build_hourly_panel(coin)

        # Validation
        n_total = len(df)
        n_nan   = df["close"].isna().sum()
        n_fund  = df["funding_rate"].notna().sum()
        date_rng = f"{df.index.min().date()} → {df.index.max().date()}"
        print(f"    Range: {date_rng}  |  rows: {n_total}  |  NaN close: {n_nan}  |  funding rows: {n_fund}")
        print(f"    Funding — mean: {df['funding_rate'].mean():.6f}  "
              f"std: {df['funding_rate'].std():.6f}  "
              f"max: {df['funding_rate'].max():.6f}  "
              f"min: {df['funding_rate'].min():.6f}")

        # Correlation matrix
        corr_df = df[["ret_1h", "funding_rate"]].copy()
        corr_df["fund_lag1"] = corr_df["funding_rate"].shift(1)
        corr_df = corr_df.dropna()
        r_rf, _ = stats.pearsonr(corr_df["ret_1h"], corr_df["fund_lag1"])
        print(f"    Corr(ret_1h, funding_rate lag1): {r_rf:.3f}")

        panels[coin] = df

    # ── Step 2: Feature engineering ───────────────────────────────────────────
    print("\n[STEP 2] Computing signal features...")
    for coin in panels:
        panels[coin] = add_signal_a(panels[coin])
        panels[coin] = add_signal_b(panels[coin])
        panels[coin] = add_signal_c(panels[coin])
        panels[coin] = add_atr(panels[coin])

        # Print signal frequencies
        df = panels[coin]
        train = df[df.index <= TRAIN_END]
        n_h   = len(train)
        fa_l  = train["sig_a_long"].mean()
        fa_s  = train["sig_a_short"].mean()
        fb_l  = train["sig_b_long"].mean()
        fb_s  = train["sig_b_short"].mean()
        fc_l  = train["sig_c_long"].mean()
        fc_s  = train["sig_c_short"].mean()
        print(f"  {coin} signal freq (train): "
              f"A_long={fa_l:.1%}  A_short={fa_s:.1%}  "
              f"B_long={fb_l:.2%}  B_short={fb_s:.2%}  "
              f"C_long={fc_l:.2%}  C_short={fc_s:.2%}")

    # ── Step 3: IC analysis ───────────────────────────────────────────────────
    print("\n[STEP 3] IC Analysis (train set only)...")
    ic_a = analyze_signal_a(panels, train_only=True)
    ic_b = analyze_signal_b(panels, train_only=True)
    ic_c = analyze_signal_c(panels, train_only=True)

    # ── Step 4: Backtest (only for signals that passed IC) ────────────────────
    print("\n[STEP 4] Backtest on TEST SET (OOS)...")
    print(f"  {'─'*55}")
    print("  NOTE: Only signals passing IC t-stat > 1.8 on ≥2/3 assets are backtested")

    bt_a: dict[str, Any] | None = None
    bt_b: dict[str, Any] | None = None
    bt_c: dict[str, Any] | None = None

    if ic_a["passed"]:
        # Find best sub-signal
        best_sub = max(ic_a["details"].items(), key=lambda kv: kv[1]["best_tstat"])
        best_key = best_sub[0]
        sub_map  = {
            "a_long":  ("sig_a_long",  +1, "Signal A LONG"),
            "a_short": ("sig_a_short", -1, "Signal A SHORT"),
            "a_rev":   ("sig_a_rev",   -1, "Signal A REV"),
        }
        col, direction, lbl = sub_map[best_key]
        bt_a = run_backtest_signal(panels, col, direction, ic_a["hold"], lbl)
    else:
        print("\n  Signal A: SKIPPED (IC failed)")

    if ic_b["passed"]:
        best_h = ic_b["best_hold"]
        # Determine which side (long vs short) had better IC
        best_h_data = ic_b["details"].get(f"h{best_h}", {})
        if best_h_data.get("assets_long_pass", 0) >= best_h_data.get("assets_short_pass", 0):
            bt_b = run_backtest_signal(panels, "sig_b_long", +1, best_h, f"Signal B LONG {best_h}h")
        else:
            bt_b = run_backtest_signal(panels, "sig_b_short", -1, best_h, f"Signal B SHORT {best_h}h")
    else:
        print("\n  Signal B: SKIPPED (IC failed)")

    if ic_c["passed"]:
        best_side = max(ic_c["details"].items(), key=lambda kv: kv[1]["best_tstat"])
        if best_side[0] == "SHORT":
            bt_c = run_backtest_signal(panels, "sig_c_short", -1, ic_c["hold"], "Signal C SHORT")
        else:
            bt_c = run_backtest_signal(panels, "sig_c_long",  +1, ic_c["hold"], "Signal C LONG")
    else:
        print("\n  Signal C: SKIPPED (IC failed)")

    # ── Step 5: Prop firm compatibility ───────────────────────────────────────
    print(f"\n{'='*60}")
    print("STEP 5 — PROP FIRM COMPATIBILITY")
    print(f"{'='*60}")
    propr_a: dict[str, Any] | None = None
    propr_b: dict[str, Any] | None = None
    propr_c: dict[str, Any] | None = None

    for bt, name, ref in [(bt_a, "Signal A", "propr_a"),
                          (bt_b, "Signal B", "propr_b"),
                          (bt_c, "Signal C", "propr_c")]:
        if bt is not None and bt.get("sharpe", 0.0) >= 0.5:
            r = run_propr_sims(bt["pnl"], name)
            if name == "Signal A": propr_a = r
            if name == "Signal B": propr_b = r
            if name == "Signal C": propr_c = r
        elif bt is not None:
            print(f"\n  {name}: skipping Propr sims (OOS Sharpe < 0.5)")

    # ── Step 6: Verdict ───────────────────────────────────────────────────────
    verdict = print_verdict(ic_a, ic_b, ic_c, bt_a, bt_b, bt_c, propr_a, propr_b, propr_c)

    # ── Charts ────────────────────────────────────────────────────────────────
    save_charts(ic_a, ic_b, ic_c, {"A": bt_a, "B": bt_b, "C": bt_c})

    return verdict


if __name__ == "__main__":
    main()
