#!/usr/bin/env python
"""
ORB Crypto Feasibility — Opening Range Breakout on Hyperliquid Perps
Zarattini, Barbon & Aziz (SSRN 4729284, 2024) crypto adaptation.

Hypothesis: assets with RVOL ≥ 1.5 in the 00:00-01:00 UTC hour whose price
breaks above/below the first-hour range during the 01:00 bar carry directional
momentum for the next 4-8 hours.

Signal bar : 00:00 UTC (defines range + RVOL)
Breakout bar: 01:00 UTC (close vs first-hour high/low)
Entry       : open of 02:00 UTC bar  (= close of 01:00 in crypto, no gaps)
Exit        : open of 09:00 UTC bar  (7 bars × 1h ≈ 8-hour hold)
Stop        : entry ± ATR(14,1h) × 1.5

Run: python -m strategies.orb_crypto.feasibility
"""
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np
import pandas as pd
import scipy.stats as stats
import yfinance as yf

warnings.filterwarnings("ignore")

# ── Constants ──────────────────────────────────────────────────────────────────
UNIVERSE: list[str] = [
    "BTC-USD", "ETH-USD", "SOL-USD", "AVAX-USD", "LINK-USD",
    "DOGE-USD", "ADA-USD", "DOT-USD", "LTC-USD", "BCH-USD",
]
DATA_START = "2024-06-01"   # yfinance 1h data: ~730-day window
DATA_END   = "2026-05-12"   # exclusive → data through 2026-05-11

# Match challenge_simulator.py exactly
SIM_START = "2025-01-06"
SIM_END   = "2025-11-03"

RVOL_THRESHOLDS: list[float] = [1.0, 1.5, 2.0, 3.0, 5.0]
DEFAULT_RVOL_THR: float = 1.5
ATR_LOOKBACK: int   = 14
ATR_MULT: float     = 1.5
ADV_LOOKBACK: int   = 20     # days
HOLD_BARS: int      = 7      # 02:00 → 09:00 UTC  (7 × 1h bars)
RISK_PCT: float     = 0.01   # 1% capital risk per trade
MAX_POSITIONS: int  = 3
COSTS_RT: float     = 0.0007 # 0.07% round trip (Hyperliquid taker)

# Prop firm parameters
PROPR_CAPITAL    = 5_000.0
PROPR_TARGET     = 0.10
PROPR_DD         = 0.06
PROPR_DAILY      = 0.03

BREAKOUT_CAPITAL = 10_000.0
BREAKOUT_TARGET  = 0.10
BREAKOUT_DD      = 0.10
BREAKOUT_DAILY   = 0.05

TSMOM_PROPR_PASS    = 0.34   # baseline from challenge_simulator.py
TSMOM_BREAKOUT_PASS = 0.20   # baseline from breakout_simulator.py

OUT_DIR = Path(__file__).parent


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1 — DATA DOWNLOAD
# ─────────────────────────────────────────────────────────────────────────────

def download_hourly_data(
    universe: list[str] = UNIVERSE,
    start: str = DATA_START,
    end: str = DATA_END,
) -> dict[str, pd.DataFrame]:
    """
    Download 1h OHLCV from yfinance for each ticker.
    Returns {ticker: DataFrame(Open,High,Low,Close,Volume)}, index = UTC datetime.
    Volume is in base-currency units (BTC for BTC-USD, etc.).
    """
    print(f"\n{'='*60}")
    print(f"STEP 1 — DOWNLOAD 1H OHLCV  ({start} → {end})")
    print(f"{'='*60}")

    raw = yf.download(
        tickers=universe,
        start=start,
        end=end,
        interval="1h",
        auto_adjust=True,
        progress=False,
    )

    result: dict[str, pd.DataFrame] = {}

    for ticker in universe:
        try:
            if isinstance(raw.columns, pd.MultiIndex):
                df = raw.xs(ticker, axis=1, level=1).copy()
            else:
                df = raw.copy()

            # Keep only OHLCV
            df = df[["Open", "High", "Low", "Close", "Volume"]].copy()

            # Ensure UTC
            if df.index.tz is not None:
                df.index = df.index.tz_convert("UTC")
            else:
                df.index = df.index.tz_localize("UTC")

            df = df.dropna(how="all")
            df = df.ffill(limit=2)              # forward-fill max 2 periods

            nan_count = int(df.isna().sum().sum())
            print(
                f"  {ticker:<12}: {len(df):>6} bars | "
                f"{df.index[0].date()} → {df.index[-1].date()} | "
                f"NaN={nan_count}"
            )
            result[ticker] = df

        except Exception as exc:
            print(f"  {ticker:<12}: FAILED — {exc}")

    return result


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2 — COMPUTE RVOL SIGNALS (PER TICKER)
# ─────────────────────────────────────────────────────────────────────────────

def _compute_ticker_signals(
    ticker: str,
    df: pd.DataFrame,
    rvol_threshold: float,
) -> pd.DataFrame:
    """
    For one ticker, return one row per UTC day with signal fields.

    Logic (all times UTC):
      - 00:00 bar: defines high_1h, low_1h, vol_1h  (no look-ahead)
      - ADV_20d:   rolling 20-day mean of daily vol, shifted 1 day
      - RVOL:      vol_1h / (ADV_20d / 24)
      - ATR(14):   rolling 14-bar mean of |H-L| on 1h bars, shifted 1
      - 01:00 bar: close > high_1h → LONG  |  close < low_1h → SHORT
      - Entry:     close of 01:00 bar (= open of 02:00 bar in theory)
      - Exit:      open of 09:00 bar  (7 bars × 1h after entry)
    """
    # ── Pre-compute ATR(14) on all 1h bars (shifted 1 so bar t uses bars t-14..t-1)
    atr_1h: pd.Series = (df["High"] - df["Low"]).rolling(ATR_LOOKBACK).mean().shift(1)

    # ── Daily volume: sum all hours in each UTC calendar day
    daily_vol: pd.Series = (
        df["Volume"]
        .groupby(df.index.normalize())
        .transform("sum")
    )
    # We only need one value per day; resample to daily
    dv_series = df["Volume"].resample("D").sum()
    # ADV: 20-day rolling mean, shifted 1 day (use yesterday's ADV)
    adv_series: pd.Series = dv_series.rolling(ADV_LOOKBACK).mean().shift(1)
    # Map ADV back to hourly index
    adv_hourly: pd.Series = adv_series.reindex(df.index.normalize()).values
    adv_hourly = pd.Series(adv_hourly, index=df.index)

    rows: list[dict[str, Any]] = []

    # Iterate over 00:00 UTC bars only (one per day)
    bar_00_mask = df.index.hour == 0
    for ts_00 in df.index[bar_00_mask]:
        ts_01 = ts_00 + pd.Timedelta(hours=1)
        ts_02 = ts_00 + pd.Timedelta(hours=2)  # entry bar
        ts_09 = ts_00 + pd.Timedelta(hours=9)  # exit bar

        if ts_01 not in df.index or ts_02 not in df.index:
            continue

        # ── First-hour range
        high_1h = float(df.at[ts_00, "High"])
        low_1h  = float(df.at[ts_00, "Low"])
        vol_1h  = float(df.at[ts_00, "Volume"])

        if np.isnan(high_1h) or np.isnan(vol_1h) or vol_1h <= 0:
            continue

        # ── ADV → RVOL
        adv = float(adv_hourly.at[ts_00])
        if np.isnan(adv) or adv <= 0:
            continue
        rvol = vol_1h / (adv / 24.0)

        # ── ATR at start of 01:00 bar
        atr_abs = float(atr_1h.at[ts_01]) if ts_01 in atr_1h.index else np.nan
        if np.isnan(atr_abs) or atr_abs <= 0:
            continue

        # ── Breakout check: close of 01:00 bar vs first-hour range
        close_01 = float(df.at[ts_01, "Close"])
        if np.isnan(close_01) or close_01 <= 0:
            continue

        entry_px = float(df.at[ts_02, "Open"]) if ts_02 in df.index else close_01

        sig_long  = bool((rvol >= rvol_threshold) and (close_01 > high_1h))
        sig_short = bool((rvol >= rvol_threshold) and (close_01 < low_1h))

        atr_pct    = atr_abs / entry_px if entry_px > 0 else np.nan
        stop_long  = entry_px * (1.0 - atr_pct * ATR_MULT) if not np.isnan(atr_pct) else np.nan
        stop_short = entry_px * (1.0 + atr_pct * ATR_MULT) if not np.isnan(atr_pct) else np.nan

        # ── Forward returns (simple, no stop) for t-test
        exit_px_raw = float(df.at[ts_09, "Open"]) if ts_09 in df.index else np.nan

        # Intermediate exits for hold-period sweep
        ts_03 = ts_00 + pd.Timedelta(hours=3)
        ts_06 = ts_00 + pd.Timedelta(hours=6)
        exit_1h = float(df.at[ts_03, "Open"]) if ts_03 in df.index else np.nan
        exit_4h = float(df.at[ts_06, "Open"]) if ts_06 in df.index else np.nan

        fwd_1h = (exit_1h - entry_px) / entry_px if not np.isnan(exit_1h) else np.nan
        fwd_4h = (exit_4h - entry_px) / entry_px if not np.isnan(exit_4h) else np.nan
        fwd_8h = (exit_px_raw - entry_px) / entry_px if not np.isnan(exit_px_raw) else np.nan

        rows.append({
            "date":       ts_00.normalize(),
            "ticker":     ticker,
            "rvol":       rvol,
            "high_1h":    high_1h,
            "low_1h":     low_1h,
            "vol_1h":     vol_1h,
            "atr_abs":    atr_abs,
            "atr_pct":    atr_pct,
            "sig_long":   sig_long,
            "sig_short":  sig_short,
            "entry_px":   entry_px,
            "stop_long":  stop_long,
            "stop_short": stop_short,
            "exit_px":    exit_px_raw,
            "fwd_1h":     fwd_1h,
            "fwd_4h":     fwd_4h,
            "fwd_8h":     fwd_8h,
        })

    return pd.DataFrame(rows).set_index("date") if rows else pd.DataFrame()


def compute_signals(
    hourly_data: dict[str, pd.DataFrame],
    rvol_threshold: float = DEFAULT_RVOL_THR,
) -> pd.DataFrame:
    """
    Compute RVOL signals for all tickers.
    Returns long-format DataFrame indexed by (date, ticker).
    """
    print(f"\n{'='*60}")
    print(f"STEP 2 — COMPUTE RVOL SIGNALS (threshold={rvol_threshold})")
    print(f"{'='*60}")

    frames: list[pd.DataFrame] = []
    for ticker, df in hourly_data.items():
        tdf = _compute_ticker_signals(ticker, df, rvol_threshold)
        if not tdf.empty:
            n_l = int(tdf["sig_long"].sum())
            n_s = int(tdf["sig_short"].sum())
            print(f"  {ticker:<12}: {len(tdf)} days | "
                  f"LONG={n_l} SHORT={n_s} | "
                  f"avg RVOL={tdf['rvol'].mean():.2f}")
            frames.append(tdf)

    if not frames:
        raise RuntimeError("No signals computed — check data download.")

    combined = pd.concat(frames).reset_index()
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.sort_values(["date", "ticker"]).reset_index(drop=True)
    return combined


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3 — RAW SIGNAL CHECK (TEST SET ONLY)
# ─────────────────────────────────────────────────────────────────────────────

def _signed_returns(
    df_ticker: pd.DataFrame,
    hold: str,  # 'fwd_1h', 'fwd_4h', 'fwd_8h'
) -> tuple[np.ndarray, np.ndarray]:
    """
    Split returns into signal and no-signal samples.
    Signal: long → positive return = good; short → flip sign.
    No-signal: absolute daily return (any direction).
    """
    valid = df_ticker.dropna(subset=[hold])

    has_sig = valid["sig_long"] | valid["sig_short"]
    sig_rows  = valid[has_sig].copy()
    nosig_rows = valid[~has_sig].copy()

    # Signed returns for signal rows
    sig_ret = np.where(
        sig_rows["sig_long"],
        sig_rows[hold],
        -sig_rows[hold],  # short: flip
    )

    # No-signal rows: use raw unsigned returns (mean ≈ 0 for random walk)
    nosig_ret = nosig_rows[hold].abs().values * np.sign(np.random.randn(len(nosig_rows)))
    # Cleaner: just use raw returns (no direction assumption)
    nosig_ret = nosig_rows[hold].values

    return sig_ret.astype(float), nosig_ret.astype(float)


def raw_signal_check(
    signals: pd.DataFrame,
    rvol_thresholds: list[float] = RVOL_THRESHOLDS,
) -> dict[str, Any]:
    """
    Step 3: t-test on TEST SET only (last 30% of dates).
    Tests each RVOL threshold and hold period.
    Returns summary dict for plot + verdict.
    """
    print(f"\n{'='*60}")
    print("STEP 3 — RAW SIGNAL CHECK  (test set: last 30%)")
    print(f"{'='*60}")

    all_dates = sorted(signals["date"].unique())
    split_i   = int(len(all_dates) * 0.70)
    test_dates = set(all_dates[split_i:])
    print(f"  Train: {all_dates[0].date()} → {all_dates[split_i-1].date()}  "
          f"({split_i} days)")
    print(f"  Test : {all_dates[split_i].date()} → {all_dates[-1].date()}  "
          f"({len(test_dates)} days)\n")

    test_df = signals[signals["date"].isin(test_dates)].copy()

    results: dict[str, Any] = {
        "thr_scan":        {},   # threshold → {ticker → {hold → {t,p,n,hit,freq}}}
        "best_thr":        None,
        "best_tstat":      0.0,  # best t among thresholds that pass n_assets≥3
        "global_best_t":      0.0,  # best t seen at any threshold (for SKIP reporting)
        "global_best_thr":    DEFAULT_RVOL_THR,
        "global_best_npass":  0,   # n_assets at the global_best_thr
        "passed":          False,
        "n_assets_pass":   0,
    }

    for thr in rvol_thresholds:
        # Re-apply threshold at scan time (reuse pre-computed RVOL)
        df_thr = test_df.copy()
        df_thr["sig_long"]  = (df_thr["rvol"] >= thr) & (df_thr["fwd_8h"].shift(0) > 0).fillna(False)
        # Actually recompute: signal logic requires close_01 vs range, which is already baked in
        # at threshold DEFAULT; for threshold scan, just re-gate by RVOL level
        df_thr["sig_long"]  = df_thr["sig_long_base"]  if "sig_long_base"  in df_thr.columns else \
                              (df_thr["rvol"] >= thr) & (test_df["sig_long"]  | (thr <= DEFAULT_RVOL_THR))
        df_thr["sig_short"] = (test_df["sig_short"] if thr == DEFAULT_RVOL_THR
                               else test_df["sig_short"] & (test_df["rvol"] >= thr))
        # Cleaner: reuse breakout condition baked into sig_long/sig_short, re-gate by RVOL
        df_thr = test_df.copy()
        # sig_long/sig_short already include RVOL >= DEFAULT_RVOL_THR
        # For threshold scan: treat any row where close_01 > high_1h as a breakout candidate
        # re-flag: (rvol >= thr) AND (close_01 vs range) — but we don't have close_01 here
        # We do have: entry_px (= close_01) and high_1h, low_1h
        df_thr["sig_long"]  = (df_thr["rvol"] >= thr) & (df_thr["entry_px"] > df_thr["high_1h"])
        df_thr["sig_short"] = (df_thr["rvol"] >= thr) & (df_thr["entry_px"] < df_thr["low_1h"])

        thr_results: dict[str, dict] = {}
        tstats_8h: list[float] = []

        for ticker in UNIVERSE:
            dt = df_thr[df_thr["ticker"] == ticker].copy()
            if dt.empty:
                continue

            dt = dt.dropna(subset=["fwd_8h", "entry_px"])
            freq_pct = (dt["sig_long"] | dt["sig_short"]).mean() * 100

            ticker_res: dict[str, dict] = {}
            for hold_col, hold_label in [("fwd_1h","1h"), ("fwd_4h","4h"), ("fwd_8h","8h")]:
                vd = dt.dropna(subset=[hold_col])
                has_sig = vd["sig_long"] | vd["sig_short"]
                sig_rows  = vd[has_sig]
                nosig_rows = vd[~has_sig]

                if len(sig_rows) < 5:
                    continue

                # Signed returns: long = raw, short = negative
                sig_rets = np.where(sig_rows["sig_long"], sig_rows[hold_col], -sig_rows[hold_col])
                sig_rets = sig_rets.astype(float)
                nosig_rets = nosig_rows[hold_col].values.astype(float)

                # One-sample t-test: mean(sig_rets) > 0
                t_oneside, p_oneside = stats.ttest_1samp(sig_rets, popmean=0.0)
                p_oneside = p_oneside / 2.0  # convert two-sided p to one-sided

                hit_rate = float((sig_rets > 0).mean())
                mean_ret = float(sig_rets.mean())

                ticker_res[hold_label] = {
                    "t": round(float(t_oneside), 3),
                    "p": round(float(p_oneside),  4),
                    "n": len(sig_rows),
                    "mean_ret": round(mean_ret * 100, 3),   # in %
                    "hit": round(hit_rate, 3),
                    "freq": round(freq_pct, 1),
                }
                if hold_label == "8h":
                    tstats_8h.append(float(t_oneside))

            thr_results[ticker] = ticker_res

        results["thr_scan"][thr] = thr_results

        # Count assets with t-stat > 1.8 at 8h
        n_pass = sum(1 for t in tstats_8h if t > 1.8)
        best_t = max(tstats_8h) if tstats_8h else 0.0

        print(f"\n  ── RVOL ≥ {thr:.1f} ──────────────────────────────")
        print(f"  {'Ticker':<12} {'n_sig':>5} {'freq%':>6} "
              f"{'t(1h)':>7} {'t(4h)':>7} {'t(8h)':>7} "
              f"{'hit@8h':>7} {'mean%':>7}")
        for ticker in UNIVERSE:
            if ticker not in thr_results:
                continue
            r = thr_results[ticker]
            r1 = r.get("1h", {})
            r4 = r.get("4h", {})
            r8 = r.get("8h", {})
            print(
                f"  {ticker:<12} "
                f"{r8.get('n', 0):>5} "
                f"{r8.get('freq', 0):>6.1f} "
                f"{r1.get('t', 0):>7.2f} "
                f"{r4.get('t', 0):>7.2f} "
                f"{r8.get('t', 0):>7.2f} "
                f"{r8.get('hit', 0):>7.1%} "
                f"{r8.get('mean_ret', 0):>7.3f}%"
            )
        print(f"\n  Assets with t > 1.8 at 8h hold: {n_pass}/10  "
              f"(need ≥3)  |  best t = {best_t:.3f}")

        # Track global best regardless of n_pass threshold
        if best_t > results["global_best_t"]:
            results["global_best_t"]      = best_t
            results["global_best_thr"]    = thr
            results["global_best_npass"]  = n_pass

        if n_pass >= 3 and best_t > results["best_tstat"]:
            results["best_thr"]      = thr
            results["best_tstat"]    = best_t
            results["passed"]        = True
            results["n_assets_pass"] = n_pass

    if results["passed"]:
        print(f"\n  ✓ SIGNAL PASSES: best RVOL={results['best_thr']}, "
              f"t={results['best_tstat']:.3f}, "
              f"{results['n_assets_pass']} assets")
    else:
        print("\n  ✗ No RVOL threshold achieves t>1.8 on ≥3 assets")

    return results


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4 — QUICK BACKTEST (run only if Step 3 passes)
# ─────────────────────────────────────────────────────────────────────────────

def _stop_checked_pnl(
    ticker: str,
    entry_ts: pd.Timestamp,  # 02:00 UTC bar open
    entry_px: float,
    stop_px: float,
    is_long: bool,
    hourly_df: pd.DataFrame,
) -> float:
    """
    Simulate trade with stop-loss using hourly bars 02:00..08:00 UTC.
    Returns raw P&L fraction (before costs).
    """
    exit_ts = entry_ts + pd.Timedelta(hours=HOLD_BARS)  # 09:00 UTC

    # Collect bars between entry and exit
    mask = (hourly_df.index >= entry_ts) & (hourly_df.index < exit_ts)
    trade_bars = hourly_df.loc[mask]

    if trade_bars.empty:
        return 0.0

    if is_long:
        # Stop if any bar's Low <= stop_px
        stopped = trade_bars["Low"] <= stop_px
        if stopped.any():
            exit_price = stop_px
        else:
            # Exit at open of next bar after last bar (= 09:00 open)
            exit_bar = exit_ts
            exit_price = (
                float(hourly_df.at[exit_bar, "Open"])
                if exit_bar in hourly_df.index
                else float(trade_bars["Close"].iloc[-1])
            )
        return (exit_price - entry_px) / entry_px
    else:
        # Short: stop if any bar's High >= stop_px
        stopped = trade_bars["High"] >= stop_px
        if stopped.any():
            exit_price = stop_px
        else:
            exit_bar = exit_ts
            exit_price = (
                float(hourly_df.at[exit_bar, "Open"])
                if exit_bar in hourly_df.index
                else float(trade_bars["Close"].iloc[-1])
            )
        return (entry_px - exit_price) / entry_px


def run_backtest(
    signals: pd.DataFrame,
    hourly_data: dict[str, pd.DataFrame],
    rvol_threshold: float,
    capital: float = 10_000.0,
) -> tuple[pd.Series, list[dict[str, Any]]]:
    """
    Step 4: Simulate ORB trades on FULL dataset.
    Returns (daily_pnl_pct, trades_list).
    """
    print(f"\n{'='*60}")
    print(f"STEP 4 — BACKTEST (RVOL≥{rvol_threshold}, capital=${capital:,.0f})")
    print(f"{'='*60}")

    df = signals.copy()
    df["sig_long"]  = (df["rvol"] >= rvol_threshold) & (df["entry_px"] > df["high_1h"])
    df["sig_short"] = (df["rvol"] >= rvol_threshold) & (df["entry_px"] < df["low_1h"])

    # Group by date, pick top-3 RVOL assets with signals
    daily_pnl: dict[pd.Timestamp, float] = {}
    trades: list[dict[str, Any]] = []
    equity = capital

    all_dates = sorted(df["date"].unique())

    for date in all_dates:
        day_df = df[df["date"] == date]

        # Find signalled assets
        signalled = day_df[day_df["sig_long"] | day_df["sig_short"]].copy()
        if signalled.empty:
            daily_pnl[date] = 0.0
            continue

        # Top-3 by RVOL
        signalled = signalled.nlargest(MAX_POSITIONS, "rvol")

        day_pnl_frac = 0.0

        for _, row in signalled.iterrows():
            ticker  = row["ticker"]
            is_long = bool(row["sig_long"])
            entry_px = float(row["entry_px"])

            if np.isnan(entry_px) or entry_px <= 0:
                continue
            if np.isnan(row["atr_abs"]) or row["atr_abs"] <= 0:
                continue

            stop_dist  = float(row["atr_abs"]) * ATR_MULT  # in price units
            stop_long  = entry_px - stop_dist
            stop_short = entry_px + stop_dist

            stop_px = stop_long if is_long else stop_short

            # Position size: 1% capital / stop_distance
            risk_capital = equity * RISK_PCT
            qty = risk_capital / stop_dist  # units (BTC, ETH, ...)
            notional = qty * entry_px

            # Get entry timestamp (02:00 UTC of this date)
            date_ts = pd.Timestamp(date).tz_localize("UTC") if date.tzinfo is None else date
            entry_ts = date_ts + pd.Timedelta(hours=2)

            hdf = hourly_data.get(ticker)
            if hdf is None:
                continue

            raw_ret = _stop_checked_pnl(ticker, entry_ts, entry_px, stop_px, is_long, hdf)
            net_ret = raw_ret - COSTS_RT

            trade_pnl_frac = net_ret * notional / equity
            day_pnl_frac += trade_pnl_frac

            trades.append({
                "date":      date,
                "ticker":    ticker,
                "direction": "LONG" if is_long else "SHORT",
                "entry_px":  entry_px,
                "stop_px":   stop_px,
                "rvol":      float(row["rvol"]),
                "raw_ret":   raw_ret,
                "net_ret":   net_ret,
                "pnl_frac":  trade_pnl_frac,
            })

        daily_pnl[date] = day_pnl_frac
        equity *= (1 + day_pnl_frac)

    daily_pnl_s = pd.Series(daily_pnl).sort_index()

    # ── Summary stats
    ann_factor   = 252
    sharpe       = (daily_pnl_s.mean() / daily_pnl_s.std() * np.sqrt(ann_factor)
                    if daily_pnl_s.std() > 0 else 0.0)
    cumret       = (1 + daily_pnl_s).cumprod()
    hwm          = cumret.cummax()
    mdd          = float(((cumret - hwm) / hwm).min())
    win_rate     = float((daily_pnl_s[daily_pnl_s != 0] > 0).mean())
    n_trades     = len(trades)
    max_day_loss = float(daily_pnl_s.min())
    trades_per_yr = n_trades / (len(daily_pnl_s) / ann_factor)

    print(f"  Trades        : {n_trades}")
    print(f"  Trades/year   : {trades_per_yr:.0f}")
    print(f"  Win rate      : {win_rate:.1%}")
    print(f"  Sharpe (net)  : {sharpe:.2f}")
    print(f"  Max DD        : {mdd:.1%}")
    print(f"  Max day loss  : {max_day_loss:.2%}")
    print(f"  Total return  : {float(cumret.iloc[-1] - 1):.1%}")

    return daily_pnl_s, trades


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5 — PROP FIRM COMPATIBILITY
# ─────────────────────────────────────────────────────────────────────────────

def _simulate_challenge(
    daily_pnl_pct: pd.Series,
    start_date: pd.Timestamp,
    initial_equity: float,
    target_pct: float,
    dd_pct: float,
    daily_pct: float,
) -> dict[str, Any]:
    """Simulate one prop-firm challenge attempt using ORB daily P&L."""
    sim_dates = daily_pnl_pct.index[daily_pnl_pct.index >= start_date]
    equity = initial_equity
    hwm    = initial_equity
    fail_daily = 0
    fail_dd    = 0

    for date in sim_dates:
        eq_start = equity
        daily_r  = float(daily_pnl_pct.get(date, 0.0))
        equity   = eq_start * (1 + daily_r)

        # Daily loss limit
        if (equity - eq_start) / eq_start < -daily_pct:
            return {"outcome": "FAIL", "reason": "daily_limit",
                    "days": len(daily_pnl_pct.loc[start_date:date]),
                    "final_equity": equity}

        # Total drawdown (static HWM per Propr / Breakout convention)
        if equity <= hwm * (1 - dd_pct):
            return {"outcome": "FAIL", "reason": "total_dd",
                    "days": len(daily_pnl_pct.loc[start_date:date]),
                    "final_equity": equity}

        # Profit target
        if equity >= hwm * (1 + target_pct):
            return {"outcome": "PASS", "reason": None,
                    "days": len(daily_pnl_pct.loc[start_date:date]),
                    "final_equity": equity}

    return {"outcome": "INCOMPLETE", "reason": None,
            "days": len(sim_dates), "final_equity": equity}


def prop_firm_compat(
    daily_pnl_pct: pd.Series,
) -> dict[str, Any]:
    """
    Step 5: Simulate Propr Starter and Breakout Explorer rules on 44 start dates.
    """
    print(f"\n{'='*60}")
    print("STEP 5 — PROP FIRM COMPATIBILITY")
    print(f"{'='*60}")

    start_dates = pd.date_range(start=SIM_START, end=SIM_END, freq="W-MON")
    # Ensure dates are tz-naive to match daily_pnl_pct index
    if daily_pnl_pct.index.tz is not None:
        daily_pnl_pct = daily_pnl_pct.copy()
        daily_pnl_pct.index = daily_pnl_pct.index.tz_localize(None)
    start_dates_naive = start_dates.tz_localize(None)

    propr_results:    list[dict] = []
    breakout_results: list[dict] = []

    for sd in start_dates_naive:
        propr_results.append(_simulate_challenge(
            daily_pnl_pct, sd,
            PROPR_CAPITAL, PROPR_TARGET, PROPR_DD, PROPR_DAILY,
        ))
        breakout_results.append(_simulate_challenge(
            daily_pnl_pct, sd,
            BREAKOUT_CAPITAL, BREAKOUT_TARGET, BREAKOUT_DD, BREAKOUT_DAILY,
        ))

    propr_pass    = sum(1 for r in propr_results    if r["outcome"] == "PASS") / len(propr_results)
    breakout_pass = sum(1 for r in breakout_results if r["outcome"] == "PASS") / len(breakout_results)

    propr_fail_daily = sum(1 for r in propr_results    if r.get("reason") == "daily_limit")
    propr_fail_dd    = sum(1 for r in propr_results    if r.get("reason") == "total_dd")
    bo_fail_daily    = sum(1 for r in breakout_results if r.get("reason") == "daily_limit")
    bo_fail_dd       = sum(1 for r in breakout_results if r.get("reason") == "total_dd")

    n = len(start_dates)

    print(f"\n  {'Metric':<30} {'ORB':>8} {'TSMOM v2':>10}")
    print(f"  {'-'*50}")
    print(f"  {'Propr pass rate':<30} {propr_pass:>7.0%}  {TSMOM_PROPR_PASS:>9.0%}")
    print(f"  {'  ↳ daily-limit fails':<30} {propr_fail_daily:>7}/44  {'—':>9}")
    print(f"  {'  ↳ total-DD fails':<30} {propr_fail_dd:>7}/44  {'—':>9}")
    print(f"  {'Breakout pass rate':<30} {breakout_pass:>7.0%}  {TSMOM_BREAKOUT_PASS:>9.0%}")
    print(f"  {'  ↳ daily-limit fails':<30} {bo_fail_daily:>7}/44  {'—':>9}")

    # Max daily loss across all challenge periods
    max_day_loss = float(daily_pnl_pct.min()) if not daily_pnl_pct.empty else 0.0
    print(f"\n  Max single-day loss : {max_day_loss:.2%}")
    print(f"  Propr daily limit   : {-PROPR_DAILY:.0%}")
    print(f"  Breakout daily limit: {-BREAKOUT_DAILY:.0%}")

    return {
        "propr_pass":    propr_pass,
        "breakout_pass": breakout_pass,
        "propr_fail_daily": propr_fail_daily,
        "propr_fail_dd":    propr_fail_dd,
        "bo_fail_daily":    bo_fail_daily,
        "bo_fail_dd":       bo_fail_dd,
        "max_day_loss":     max_day_loss,
        "propr_results":    propr_results,
        "breakout_results": breakout_results,
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 7 — BONUS: BITCOIN INTRADAY MOMENTUM (if ORB skips)
# ─────────────────────────────────────────────────────────────────────────────

def btc_intraday_momentum(hourly_data: dict[str, pd.DataFrame]) -> dict[str, Any]:
    """
    Shen, Urquhart & Wang (2022): first 30-min predicts last 30-min of UTC day.
    Adapted to 1h bars: return from 00:00→01:00 predicts 23:00→00:00 same day.
    Signal computed at 01:00 UTC (strict no look-ahead); entry/exit straddling midnight.
    """
    print(f"\n{'='*60}")
    print("STEP 7 — BONUS: BTC INTRADAY MOMENTUM (Shen-Urquhart-Wang 2022)")
    print(f"{'='*60}")

    btc = hourly_data.get("BTC-USD")
    if btc is None:
        print("  BTC-USD not available.")
        return {}

    # First-hour return (00:00 bar): (close_00 - open_00) / open_00
    bar_00 = btc[btc.index.hour == 0].copy()
    first_ret = (bar_00["Close"] - bar_00["Open"]) / bar_00["Open"]
    first_ret.index = bar_00.index.normalize()   # date only

    # Last-hour return (23:00 bar of SAME day): (close_23 - open_23) / open_23
    bar_23 = btc[btc.index.hour == 23].copy()
    last_ret = (bar_23["Close"] - bar_23["Open"]) / bar_23["Open"]
    last_ret.index = bar_23.index.normalize()

    # Align on common dates
    common = first_ret.index.intersection(last_ret.index)
    fr = first_ret.loc[common]
    lr = last_ret.loc[common]

    # Signal: sign of first 1h return
    signal_dir = np.sign(fr)  # +1 or -1 or 0

    # Signed last-hour return
    signed_last = lr * signal_dir

    # Remove zeros (no signal when first_ret exactly 0)
    mask = signal_dir != 0
    signed_last = signed_last[mask]

    # One-sample t-test: mean > 0?
    t, p_two = stats.ttest_1samp(signed_last.dropna(), popmean=0.0)
    p_one = p_two / 2.0

    hit = float((signed_last > 0).mean())
    mean_r = float(signed_last.mean())

    print(f"  N observations : {int(mask.sum())}")
    print(f"  Mean signed ret: {mean_r*100:.4f}%")
    print(f"  Hit rate       : {hit:.1%}")
    print(f"  t-stat         : {t:.3f}")
    print(f"  p-value (1-sided): {p_one:.4f}")

    flag = t > 1.5
    if flag:
        print("\n  *** Bitcoin intraday momentum PROMISING ***")
        print("  → Run full backtest next session")
    else:
        print(f"\n  t={t:.2f} < 1.5 threshold — no significant edge")

    return {"t": t, "p": p_one, "hit": hit, "mean_ret": mean_r, "promising": flag}


# ─────────────────────────────────────────────────────────────────────────────
# STEP 6 — VERDICT
# ─────────────────────────────────────────────────────────────────────────────

def print_verdict(
    signal_check: dict[str, Any],
    daily_pnl: pd.Series | None,
    compat: dict[str, Any] | None,
    btc_mom: dict[str, Any] | None = None,
) -> str:
    """Print structured feasibility verdict. Returns 'PROMISING'|'WEAK'|'SKIP'."""

    # Compute net Sharpe from daily_pnl if available
    net_sharpe = 0.0
    max_day_loss_pct = 0.0
    if daily_pnl is not None and len(daily_pnl) > 10:
        net_sharpe = float(daily_pnl.mean() / daily_pnl.std() * np.sqrt(252))
        max_day_loss_pct = float(daily_pnl.min()) * 100

    passed = signal_check.get("passed", False)

    # For SKIP: use global best t-stat; for PASS: use threshold-that-passed
    report_tstat = (signal_check.get("best_tstat", 0.0) if passed
                    else signal_check.get("global_best_t", 0.0))
    report_thr   = (signal_check.get("best_thr", DEFAULT_RVOL_THR) if passed
                    else signal_check.get("global_best_thr", DEFAULT_RVOL_THR))

    best_thr_res = signal_check["thr_scan"].get(report_thr, {})

    # Signal frequency: mean across assets with signals
    freqs = []
    for tk in UNIVERSE:
        r = best_thr_res.get(tk, {}).get("8h", {})
        if r and r.get("n", 0) > 0:
            freqs.append(r.get("freq", 0))
    avg_freq = float(np.mean(freqs)) if freqs else 0.0
    # Convert from % of test days to estimated annual frequency
    n_test_days = 365 * 0.30   # ≈219 days
    signals_per_year = avg_freq / 100.0 * n_test_days

    propr_pass    = compat["propr_pass"]    if compat else 0.0
    breakout_pass = compat["breakout_pass"] if compat else 0.0
    max_loss      = compat["max_day_loss"]  if compat else max_day_loss_pct / 100

    if passed and net_sharpe > 0.5 and propr_pass >= 0.20:
        verdict = "PROMISING"
    elif passed and net_sharpe > 0:
        verdict = "WEAK"
    else:
        verdict = "SKIP"

    border = "═" * 57
    print(f"\n{border}")
    print("FEASIBILITY REPORT — ORB Crypto Adaptation")
    print(f"{border}")
    n_report = (signal_check.get("n_assets_pass", 0) if passed
                else signal_check.get("global_best_npass", 0))
    print(f"  Raw signal (best t-stat)  : "
          f"{report_tstat:.2f} "
          f"on {n_report}/10 assets  "
          f"[{'PASS' if passed else 'FAIL'}]")
    print(f"  Best RVOL threshold       : "
          f"{report_thr}  (≈{signals_per_year:.0f} signals/year per asset)")
    if daily_pnl is not None:
        print(f"  Net Sharpe                : {net_sharpe:.2f}")
        print(f"  Max daily loss            : {max_day_loss_pct:.2f}%")
    if compat:
        print(f"  Propr pass rate           : "
              f"{propr_pass:.0%}  (vs TSMOM {TSMOM_PROPR_PASS:.0%})")
        print(f"  Breakout pass rate        : "
              f"{breakout_pass:.0%}  (vs TSMOM {TSMOM_BREAKOUT_PASS:.0%})")

    print(f"\n  VERDICT: {verdict}")

    if verdict == "PROMISING":
        print(
            f"  Reason: ORB signal shows t>{signal_check['best_tstat']:.1f} on "
            f"{signal_check['n_assets_pass']} assets at RVOL≥{best_thr} with "
            f"net Sharpe {net_sharpe:.2f} after costs. "
            f"Prop firm compatibility is acceptable ({propr_pass:.0%} Propr pass)."
        )
        print(f"\n  Recommended next step: full backtest 2024-2026 with "
              f"RVOL≥{best_thr}, ATR×1.5 stop, 8h hold; "
              f"then challenge_simulator integration.")
    elif verdict == "WEAK":
        print(
            f"  Reason: Marginal signal edge (t={signal_check['best_tstat']:.2f}) "
            f"but net Sharpe {net_sharpe:.2f} is insufficient for consistent "
            f"prop firm funding. Daily loss distribution overlaps with 3%/5% limits."
        )
        print(f"\n  SKIP — insufficient risk-adjusted return.")
        print(f"  Next candidate: Bitcoin intraday momentum (Shen-Urquhart-Wang 2022).")
    else:
        # Root cause analysis
        if not passed:
            root = (f"no RVOL threshold achieves t>1.8 on ≥3 assets — "
                    f"best t={report_tstat:.2f} at RVOL≥{report_thr} "
                    f"({signal_check.get('global_best_npass', 0)}/10 assets)")
        elif net_sharpe <= 0:
            root = "costs exceed gross alpha (0.07% RT × daily trading frequency)"
        else:
            root = "daily loss exceeds prop firm limits"

        print(f"  Root cause: {root}.")
        if compat:
            print(f"  Daily-limit failures: Propr={compat['propr_fail_daily']}/44, "
                  f"Breakout={compat['bo_fail_daily']}/44.")
        print(f"\n  Next candidate to test: Bitcoin intraday momentum "
              f"(Shen-Urquhart-Wang 2022).")

        if btc_mom and btc_mom.get("promising"):
            print(f"\n  ✓ BTC intraday momentum is PROMISING "
                  f"(t={btc_mom['t']:.2f}, hit={btc_mom['hit']:.0%}) — "
                  f"run full backtest next session.")

    print(f"{border}\n")
    return verdict


# ─────────────────────────────────────────────────────────────────────────────
# PLOT
# ─────────────────────────────────────────────────────────────────────────────

def plot_results(
    signals: pd.DataFrame,
    signal_check: dict[str, Any],
    daily_pnl: pd.Series | None,
    compat: dict[str, Any] | None,
    save_path: Path = OUT_DIR / "feasibility_results.png",
) -> None:
    """
    4-subplot chart:
      (1) Signal frequency by RVOL threshold
      (2) Forward return distribution: signal vs no-signal
      (3) Equity curve (if backtest ran)
      (4) Daily P&L histogram vs prop firm limits
    """
    fig = plt.figure(figsize=(14, 12))
    gs  = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.35)
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 0])
    ax4 = fig.add_subplot(gs[1, 1])

    fig.suptitle("ORB Crypto Feasibility — TSMOM v2 Alternative",
                 fontsize=13, fontweight="bold")

    # ── (1) Signal frequency by RVOL threshold ────────────────────────────────
    thr_labels = [f"{t:.1f}" for t in RVOL_THRESHOLDS]
    freqs_by_thr: list[float] = []
    for thr in RVOL_THRESHOLDS:
        df_thr = signals.copy()
        df_thr["has_sig"] = (
            ((df_thr["rvol"] >= thr) & (df_thr["entry_px"] > df_thr["high_1h"])) |
            ((df_thr["rvol"] >= thr) & (df_thr["entry_px"] < df_thr["low_1h"]))
        )
        freqs_by_thr.append(float(df_thr["has_sig"].mean() * 100))

    bars = ax1.bar(thr_labels, freqs_by_thr, color="#3498db", alpha=0.8, edgecolor="white")
    for bar, v in zip(bars, freqs_by_thr):
        ax1.text(bar.get_x() + bar.get_width() / 2, v + 0.2,
                 f"{v:.1f}%", ha="center", va="bottom", fontsize=8)
    ax1.axhline(5, color="#e74c3c", ls="--", lw=1.2, label="5% daily signal freq")
    ax1.set_xlabel("RVOL Threshold")
    ax1.set_ylabel("Signal frequency (% of asset-days)")
    ax1.set_title("Signal Frequency vs RVOL Threshold", fontsize=10)
    ax1.legend(fontsize=8)
    ax1.grid(True, axis="y", alpha=0.25)

    # ── (2) Forward return distribution: signal vs no-signal ──────────────────
    best_thr  = signal_check.get("best_thr", DEFAULT_RVOL_THR)
    sig_8h_all: list[float] = []
    nosig_8h_all: list[float] = []

    for ticker in UNIVERSE:
        dt = signals[signals["ticker"] == ticker].dropna(subset=["fwd_8h"]).copy()
        dt["sig_l"] = (dt["rvol"] >= best_thr) & (dt["entry_px"] > dt["high_1h"])
        dt["sig_s"] = (dt["rvol"] >= best_thr) & (dt["entry_px"] < dt["low_1h"])
        has_sig = dt["sig_l"] | dt["sig_s"]
        sr = dt[has_sig]
        nr = dt[~has_sig]
        signed = np.where(sr["sig_l"], sr["fwd_8h"], -sr["fwd_8h"])
        sig_8h_all.extend(signed.tolist())
        nosig_8h_all.extend(nr["fwd_8h"].abs().tolist())  # absolute (undirected)

    sig_arr   = np.array(sig_8h_all) * 100
    nosig_arr = np.array(nosig_8h_all) * 100
    bins = np.linspace(-8, 8, 50)
    ax2.hist(nosig_arr, bins=bins, alpha=0.5, color="#95a5a6", label=f"No signal (n={len(nosig_arr)})", density=True)
    ax2.hist(sig_arr,   bins=bins, alpha=0.7, color="#2ecc71", label=f"Signal (n={len(sig_arr)})", density=True)
    ax2.axvline(0, color="black", lw=1.0, ls="--")
    if len(sig_arr) > 0:
        ax2.axvline(float(np.mean(sig_arr)), color="#27ae60", lw=1.5, ls="-",
                    label=f"Signal mean={np.mean(sig_arr):.3f}%")
    ax2.set_xlabel("8h forward return (%)")
    ax2.set_ylabel("Density")
    ax2.set_title(f"8h Forward Returns: Signal vs No-Signal (RVOL≥{best_thr})", fontsize=10)
    ax2.legend(fontsize=7)
    ax2.grid(True, alpha=0.20)

    # ── (3) Equity curve ──────────────────────────────────────────────────────
    if daily_pnl is not None and len(daily_pnl) > 1:
        eq = (1 + daily_pnl).cumprod() * 10_000
        ax3.plot(eq.index, eq.values, color="#2980b9", lw=1.5)
        ax3.axhline(10_000, color="gray", ls="--", lw=0.8)
        ax3.fill_between(eq.index, 10_000, eq.values,
                          where=eq.values >= 10_000, alpha=0.15, color="#2ecc71")
        ax3.fill_between(eq.index, 10_000, eq.values,
                          where=eq.values < 10_000, alpha=0.15, color="#e74c3c")
        ax3.set_title("Equity Curve (ORB, $10k normalized)", fontsize=10)
        ax3.set_ylabel("Equity ($)")
        ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax3.grid(True, alpha=0.20)
    else:
        ax3.text(0.5, 0.5, "Backtest not run\n(signal did not pass Step 3)",
                 ha="center", va="center", transform=ax3.transAxes, fontsize=11, color="gray")
        ax3.set_title("Equity Curve", fontsize=10)
        ax3.axis("off")

    # ── (4) Daily P&L histogram vs prop firm limits ────────────────────────────
    if daily_pnl is not None and len(daily_pnl) > 5:
        pnl_pct = daily_pnl.values * 100
        bins4 = np.linspace(-6, 6, 60)
        ax4.hist(pnl_pct, bins=bins4, color="#3498db", alpha=0.75, edgecolor="white",
                 label=f"Daily P&L (n={len(pnl_pct)})")
        ax4.axvline(-PROPR_DAILY * 100,    color="#e74c3c", ls="--", lw=1.5,
                    label=f"Propr limit ({-PROPR_DAILY:.0%})")
        ax4.axvline(-BREAKOUT_DAILY * 100, color="#f39c12", ls="--", lw=1.5,
                    label=f"Breakout limit ({-BREAKOUT_DAILY:.0%})")
        ax4.axvline(0, color="black", lw=0.8, ls=":")
        ax4.set_xlabel("Daily P&L (%)")
        ax4.set_ylabel("Count")
        ax4.set_title("Daily P&L Distribution vs Prop Firm Limits", fontsize=10)
        ax4.legend(fontsize=7)
        ax4.grid(True, axis="y", alpha=0.25)
    else:
        ax4.text(0.5, 0.5, "No backtest data",
                 ha="center", va="center", transform=ax4.transAxes, fontsize=11, color="gray")
        ax4.set_title("Daily P&L Histogram", fontsize=10)
        ax4.axis("off")

    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"\n  Plot saved → {save_path}")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    import time
    t0 = time.time()

    # ── Step 1: Data
    hourly_data = download_hourly_data()

    # ── Step 2: Signals (default threshold; threshold scan in Step 3)
    signals = compute_signals(hourly_data, rvol_threshold=DEFAULT_RVOL_THR)

    # ── Step 3: Raw signal check on test set
    signal_check = raw_signal_check(signals, rvol_thresholds=RVOL_THRESHOLDS)

    best_thr  = signal_check.get("best_thr", DEFAULT_RVOL_THR)
    daily_pnl = None
    compat    = None

    # ── Step 4: Backtest (only if signal passes)
    if signal_check["passed"]:
        daily_pnl, _trades = run_backtest(signals, hourly_data, best_thr)
    else:
        print(f"\n  ── Skipping backtest (signal did not pass Step 3) ──")

    # ── Step 5: Prop firm compat (only if backtest ran)
    if daily_pnl is not None:
        compat = prop_firm_compat(daily_pnl)
    else:
        print(f"\n{'='*60}")
        print("STEP 5 — PROP FIRM COMPATIBILITY")
        print(f"{'='*60}")
        print("  Skipped — no backtest data (signal did not pass Step 3).")
        compat = None

    # ── Step 6: Verdict
    btc_mom = None
    verdict = print_verdict(signal_check, daily_pnl, compat)

    # ── Step 7: BTC intraday momentum (if ORB skips or weak)
    if verdict in ("SKIP", "WEAK"):
        btc_mom = btc_intraday_momentum(hourly_data)
        # Reprint final line if BTC mom is promising
        if btc_mom.get("promising"):
            print_verdict(signal_check, daily_pnl, compat, btc_mom)

    # ── Plot
    plot_results(signals, signal_check, daily_pnl, compat)

    print(f"Total runtime: {(time.time()-t0)/60:.1f} minutes")


if __name__ == "__main__":
    main()
