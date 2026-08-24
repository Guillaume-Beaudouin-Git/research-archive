"""
TDD tests for ZN Baltussen feasibility module.
Minimum 4 tests required for STOP-POINT 2.

Tests
-----
1. Signal timing: entry at 15:00, exit proxy is midpoint of 15:00 bar
2. Event-day classification: FOMC/NFP/CPI/PCE correctly identified
3. SL 8-tick hard stop fires on breaching bar
4. VIX skip filter: days with VIX > 25 are excluded from backtest
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

_REPO = Path(__file__).parents[5]
sys.path.insert(0, str(_REPO))

from Futures.research.active.zn_baltussen.data_setup import (
    ZN_TICK_VALUE,
    build_macro_calendar,
    compute_session_features,
    DataSource,
)
from Futures.research.active.zn_baltussen.feasibility import (
    COST_RT_USD,
    SL_TICKS,
    ZN_POINT_VALUE,
    _pnl_single_trade,
    run_backtest,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def _make_1h_bar(
    date: str,
    hour: int,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> pd.Series:
    ts = pd.Timestamp(f"{date} {hour:02d}:00", tz="America/New_York")
    return pd.Series(
        {"open": open_, "high": high, "low": low, "close": close, "volume": 1000},
        name=ts,
    )


def _make_day_df(date: str, bars: list[dict]) -> pd.DataFrame:
    """Build a 1h DataFrame for one trading day."""
    rows = []
    for b in bars:
        ts = pd.Timestamp(f"{date} {b['hour']:02d}:00", tz="America/New_York")
        rows.append({
            "open":  b["open"],
            "high":  b["high"],
            "low":   b["low"],
            "close": b["close"],
            "volume": b.get("volume", 1000),
        })
        idx = pd.Timestamp(f"{date} {b['hour']:02d}:00", tz="America/New_York")
        rows[-1]["_ts"] = idx

    df = pd.DataFrame(rows)
    df = df.set_index("_ts").sort_index()
    df.index.name = "ts_et"
    return df


def _standard_day(date: str, p_open: float = 110.0, rtd: float = 0.003) -> pd.DataFrame:
    """
    Synthetic ZN day: positive rest-of-day return (long signal).
    10:00 bar open = p_open, 15:00 bar open = p_open * (1 + rtd).
    """
    p_1500 = p_open * (1 + rtd)
    return _make_day_df(date, [
        {"hour": 9,  "open": p_open - 0.05, "high": p_open, "low": p_open - 0.1, "close": p_open},
        {"hour": 10, "open": p_open,         "high": p_open + 0.05, "low": p_open - 0.05, "close": p_open + 0.02},
        {"hour": 11, "open": p_open + 0.02,  "high": p_open + 0.1, "low": p_open,         "close": p_open + 0.08},
        {"hour": 12, "open": p_open + 0.08,  "high": p_open + 0.12, "low": p_open + 0.05, "close": p_open + 0.1},
        {"hour": 13, "open": p_open + 0.1,   "high": p_open + 0.15, "low": p_open + 0.08, "close": p_open + 0.12},
        {"hour": 14, "open": p_open + 0.12,  "high": p_open + 0.2, "low": p_open + 0.1,  "close": p_1500},
        {"hour": 15, "open": p_1500,          "high": p_1500 + 0.1, "low": p_1500 - 0.02, "close": p_1500 + 0.05},
    ])


# ── TEST 1: signal timing ─────────────────────────────────────────────────────

def test_signal_timing_entry_at_1500():
    """
    Entry price must be the Open of the 15:00 bar.
    Exit proxy must be midpoint of 15:00-16:00 bar = (Open + Close) / 2.
    Signal direction = +1 if (p_1500 - p_open_proxy) > 0.
    """
    date   = "2024-10-01"
    p_open = 110.0
    p_1500 = 110.33  # positive rest-of-day return → long signal
    p_close_15 = 110.40

    df = _make_day_df(date, [
        {"hour": 10, "open": p_open,  "high": p_open + 0.1, "low": p_open - 0.1, "close": p_open},
        {"hour": 15, "open": p_1500,  "high": p_1500 + 0.1, "low": p_1500 - 0.02, "close": p_close_15},
    ])

    cal = pd.DataFrame({"date": [], "is_event_day": [], "event_type": []})
    vix = pd.Series(dtype=float)
    sessions = compute_session_features(df, DataSource.YFINANCE, calendar=cal, vix=vix)

    assert len(sessions) == 1, "Should produce exactly 1 session row"
    row = sessions.iloc[0]

    assert abs(row["p_1500"] - p_1500) < 1e-6, (
        f"p_1500 should be Open of 15:00 bar ({p_1500}), got {row['p_1500']}"
    )
    expected_exit = (p_1500 + p_close_15) / 2.0
    assert abs(row["p_exit_proxy"] - expected_exit) < 1e-6, (
        f"Exit proxy should be midpoint {expected_exit:.4f}, got {row['p_exit_proxy']:.4f}"
    )
    assert row["direction"] == 1, (
        f"Positive return_rtd should give direction=+1, got {row['direction']}"
    )
    assert row["return_rtd"] > 0, "return_rtd should be positive (long signal)"


# ── TEST 2: event-day classification ─────────────────────────────────────────

def test_event_day_classification():
    """
    FOMC, NFP, CPI, PCE dates must be flagged as is_event_day=True.
    Non-event dates must have is_event_day=False.
    """
    cal = build_macro_calendar(start_year=2024, end_year=2024)

    # Known 2024 event dates from prespec
    fomc_dates = ["2024-01-31", "2024-03-20", "2024-06-12", "2024-09-18"]
    cpi_dates  = ["2024-02-13", "2024-04-10", "2024-08-14"]
    nfp_dates  = ["2024-01-05", "2024-02-02", "2024-03-01"]

    for d in fomc_dates:
        row = cal[cal["date"] == pd.Timestamp(d)]
        assert not row.empty, f"FOMC date {d} missing from calendar"
        assert row.iloc[0]["is_fomc"], f"{d} should be is_fomc=True"
        assert row.iloc[0]["is_event_day"], f"{d} should be is_event_day=True"

    for d in cpi_dates:
        row = cal[cal["date"] == pd.Timestamp(d)]
        assert not row.empty, f"CPI date {d} missing from calendar"
        assert row.iloc[0]["is_cpi"], f"{d} should be is_cpi=True"

    for d in nfp_dates:
        row = cal[cal["date"] == pd.Timestamp(d)]
        assert not row.empty, f"NFP date {d} missing from calendar"
        assert row.iloc[0]["is_nfp"], f"{d} should be is_nfp=True"

    # Non-event Wednesday
    non_event = cal[cal["date"] == pd.Timestamp("2024-01-17")]
    assert non_event.empty, "2024-01-17 should NOT be an event day"

    # Sanity: total events in 2024 ≈ 44-50
    n_events = len(cal)
    assert 40 <= n_events <= 60, (
        f"Expected 40-60 event days in 2024, got {n_events}"
    )


# ── TEST 3: SL 8-tick hard stop ───────────────────────────────────────────────

def test_sl_8tick_hard_stop():
    """
    If bar Low (for long) crosses entry - 8 ticks, P&L must equal SL loss - cost.
    SL = 8 ticks × $15.625 = $125. Net loss = -$125 - $20 cost = -$145.
    """
    sl_pts   = SL_TICKS * (1.0 / 64.0)  # 8/64 = 0.125 ZN points
    entry    = 110.0
    sl_price = entry - sl_pts            # 109.875

    # Bar Low breaches the SL level
    bar_high = entry + 0.05
    bar_low  = sl_price - 0.01          # bar goes below SL → SL fills at sl_price

    pnl = _pnl_single_trade(
        direction=1,        # long
        entry=entry,
        exit_proxy=entry + 0.2,   # target never reached
        bar_high=bar_high,
        bar_low=bar_low,
        cost_rt=COST_RT_USD,
    )

    sl_loss_gross = (sl_price - entry) * ZN_POINT_VALUE  # = -0.125 × 1000 = -$125
    expected_net  = sl_loss_gross - COST_RT_USD           # -$125 - $20 = -$145

    assert abs(pnl - expected_net) < 0.01, (
        f"SL P&L should be {expected_net:.2f}, got {pnl:.2f}"
    )
    assert pnl < 0, "SL trade should produce a loss"

    # SHORT side SL: bar High breaches entry + sl_pts
    pnl_short = _pnl_single_trade(
        direction=-1,
        entry=entry,
        exit_proxy=entry - 0.2,
        bar_high=sl_price + 0.01 + sl_pts * 2,   # High > sl_price for short
        bar_low=entry - 0.05,
        cost_rt=COST_RT_USD,
    )
    assert pnl_short < 0, "Short SL trade should also produce a loss"


# ── TEST 4: VIX skip filter ───────────────────────────────────────────────────

def test_vix_skip_filter():
    """
    Days with vix_close > VIX_SKIP (25.0) must produce 0 trades in the backtest.
    Days with vix_close ≤ 25.0 must produce trades normally.
    """
    date_low_vix  = "2024-10-01"
    date_high_vix = "2024-10-02"

    # Build synthetic sessions manually
    p_open = 110.0
    p_1500 = 110.3
    p_exit = 110.35

    sessions = pd.DataFrame({
        "p_open_proxy": [p_open, p_open],
        "p_1500":       [p_1500, p_1500],
        "p_exit_proxy": [p_exit, p_exit],
        "return_rtd":   [0.003,  0.003],
        "direction":    [1,      1],
        "vix_close":    [15.0,   30.0],    # low VIX on day 1, high on day 2
        "is_event_day": [False,  False],
        "event_type":   ["none", "none"],
    }, index=pd.DatetimeIndex(
        [pd.Timestamp(date_low_vix), pd.Timestamp(date_high_vix)]
    ))

    df_1h = pd.concat([_standard_day(date_low_vix),
                       _standard_day(date_high_vix)])

    pnl = run_backtest(sessions, df_1h, cost_rt=COST_RT_USD, vix_skip=25.0)

    assert len(pnl) == 1, (
        f"Only 1 trade should fire (VIX filter removes date_high_vix), got {len(pnl)}"
    )
    assert pd.Timestamp(date_low_vix) in pnl.index, (
        "Low-VIX day should produce a trade"
    )
    assert pd.Timestamp(date_high_vix) not in pnl.index, (
        "High-VIX day should be skipped"
    )
