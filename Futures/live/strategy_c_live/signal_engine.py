"""
signal_engine.py — Signal computation for Strategy C live trading
==================================================================
Replicates iter_10 logic using 1-min bars from IBKR.
Opening range: 09:30-09:45 ET (15 minutes, 3 × 5-min bars for OHLC).
VWAP computed on 1-min ORB bars — matches iter_10 backtest exactly.
Filters: VWAP confirmation + gap filter + range minimum.
"""
from __future__ import annotations

import logging
from datetime import date, time
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# Import config values
from Futures.live.strategy_c_live.config import (
    ORB_OPEN, ORB_CLOSE, GAP_FILTER, RANGE_MIN_PTS,
    TP_RATIO, SL_RATIO, SL_CAP_PTS,
)


# ─────────────────────────────────────────────────────────────────────────────
# VWAP
# ─────────────────────────────────────────────────────────────────────────────

def compute_vwap(bars: pd.DataFrame) -> float:
    """
    Cumulative VWAP using (close × volume) / cumulative_volume.
    Falls back to simple average close if volume is zero or missing.
    """
    if "volume" not in bars.columns or bars["volume"].sum() == 0:
        return float(bars["close"].mean())
    cum_vp = (bars["close"] * bars["volume"]).cumsum()
    cum_v  = bars["volume"].cumsum()
    vwap   = cum_vp / cum_v
    return float(vwap.iloc[-1])


# ─────────────────────────────────────────────────────────────────────────────
# Gap computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_gap(bars_today: pd.DataFrame, bars_prev: pd.DataFrame) -> Optional[float]:
    """
    Overnight gap = (today_rth_open - prev_day_rth_close) / prev_day_rth_close.
    Works with both 1-min and 5-min bars (uses first open / last close).
    Returns None if insufficient data.
    """
    if bars_today.empty or bars_prev.empty:
        return None
    today_open = float(bars_today.iloc[0]["open"])
    prev_close = float(bars_prev.iloc[-1]["close"])
    if prev_close <= 0:
        return None
    return (today_open - prev_close) / prev_close


# ─────────────────────────────────────────────────────────────────────────────
# Main signal function
# ─────────────────────────────────────────────────────────────────────────────

def compute_signal(bars_1min: pd.DataFrame) -> Optional[dict]:
    """
    Compute iter_10 signal from 1-min IBKR bars.

    OHLC / range / direction come from 5-min resample (09:30–09:45 window).
    VWAP is computed on raw 1-min ORB bars — matches iter_10 backtest exactly.

    Parameters
    ----------
    bars_1min : 1-min RTH bars with DatetimeIndex (US/Eastern tz-aware).
                Columns: open, high, low, close, volume.
                Should include today and yesterday's RTH data.

    Returns
    -------
    dict with keys: direction, tp_price, sl_price, tp_pts, sl_pts,
                    opening_range, vwap_at_945, gap_pct, entry_estimate,
                    signal_strength
    OR None if any filter fails.
    """
    if bars_1min.empty:
        log.warning("compute_signal: empty bars")
        return None

    today     = bars_1min.index[-1].date()
    yesterday = _prev_trading_day(today)

    # Split today / yesterday
    bars_today_1m = bars_1min[bars_1min.index.date == today]
    bars_prev_1m  = bars_1min[bars_1min.index.date == yesterday]

    if bars_today_1m.empty:
        log.warning("compute_signal: no bars for today (%s)", today)
        return None

    # ── 5-min resample for ORB OHLC ──────────────────────────────────────
    bars_5m = bars_today_1m.resample("5min", label="right", closed="right").agg(
        open=("open", "first"), high=("high", "max"),
        low=("low", "min"),   close=("close", "last"),
        volume=("volume", "sum"),
    ).dropna(subset=["open"])

    # Opening range 5-min bars: 09:30 ≤ t ≤ 09:45
    orb_5m = bars_5m[
        (bars_5m.index.time >= ORB_OPEN) &
        (bars_5m.index.time <= ORB_CLOSE)
    ]

    if len(orb_5m) < 2:
        log.info("Signal SKIP: only %d ORB 5-min bars (need ≥2)", len(orb_5m))
        return None

    open_price  = float(orb_5m.iloc[0]["open"])
    close_price = float(orb_5m.iloc[-1]["close"])
    orb_range   = abs(close_price - open_price)

    # ── Filter 1: Range minimum (M1, rng ≥ 30 pts) ──────────────────────
    if orb_range < RANGE_MIN_PTS:
        log.info("Signal SKIP: range=%.1f < %d pts (M1 filter)", orb_range, RANGE_MIN_PTS)
        return None

    # ── Direction ────────────────────────────────────────────────────────
    direction = "BUY" if close_price > open_price else "SELL"
    dir_int   = 1 if direction == "BUY" else -1

    # ── VWAP from 1-min ORB bars (matches iter_10 backtest) ─────────────
    orb_1m = bars_today_1m[
        (bars_today_1m.index.time >= ORB_OPEN) &
        (bars_today_1m.index.time <= ORB_CLOSE)
    ]
    vwap_at_945 = compute_vwap(orb_1m)

    # ── Filter 2: VWAP confirmation ──────────────────────────────────────
    if direction == "BUY" and close_price <= vwap_at_945:
        log.info("Signal SKIP: BUY but close=%.2f ≤ VWAP=%.2f", close_price, vwap_at_945)
        return None
    if direction == "SELL" and close_price >= vwap_at_945:
        log.info("Signal SKIP: SELL but close=%.2f ≥ VWAP=%.2f", close_price, vwap_at_945)
        return None

    # ── Filter 3: Gap filter (B1.2%) ─────────────────────────────────────
    gap_pct = compute_gap(bars_today_1m, bars_prev_1m)
    if gap_pct is None:
        log.warning("Signal: could not compute gap (no prev day data) — proceeding without gap filter")
        gap_pct = 0.0
    elif abs(gap_pct) > GAP_FILTER:
        log.info("Signal SKIP: |gap|=%.2f%% > %.1f%%", abs(gap_pct)*100, GAP_FILTER*100)
        return None

    # ── TP / SL computation ──────────────────────────────────────────────
    sl_pts = min(orb_range * SL_RATIO, SL_CAP_PTS)
    tp_pts = orb_range * TP_RATIO

    entry_estimate = close_price   # approximate (actual entry = next bar open)

    if direction == "BUY":
        tp_price = entry_estimate + tp_pts
        sl_price = entry_estimate - sl_pts
    else:
        tp_price = entry_estimate - tp_pts
        sl_price = entry_estimate + sl_pts

    # ── Signal strength ──────────────────────────────────────────────────
    signal_strength = "strong" if 38 <= orb_range <= 63 else "normal"

    return {
        "direction":       direction,
        "dir_int":         dir_int,
        "tp_price":        round(tp_price, 2),
        "sl_price":        round(sl_price, 2),
        "tp_pts":          round(tp_pts, 2),
        "sl_pts":          round(sl_pts, 2),
        "opening_range":   round(orb_range, 2),
        "vwap_at_945":     round(vwap_at_945, 2),
        "gap_pct":         round(gap_pct * 100, 3),
        "entry_estimate":  round(entry_estimate, 2),
        "signal_strength": signal_strength,
        "orb_open_price":  round(open_price, 2),
        "orb_close_price": round(close_price, 2),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _prev_trading_day(d: date) -> date:
    """Return the previous Mon-Fri date (simple, no holiday calendar)."""
    prev = d - pd.Timedelta(days=1)
    while prev.weekday() >= 5:  # Saturday=5, Sunday=6
        prev -= pd.Timedelta(days=1)
    return prev
