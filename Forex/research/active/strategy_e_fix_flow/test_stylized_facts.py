"""
test_stylized_facts.py
======================
4 TDD tests for stylized_facts.py using EURUSD 2016 canary parquet.
Run: /usr/bin/python3 -m pytest Forex/research/active/strategy_e_fix_flow/test_stylized_facts.py -v
"""
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).parent))
from stylized_facts import (
    aggregate_w_shape,
    build_returns_panel,
    compute_fix_window_utc,
    compute_returns_relative_to_fix,
    load_pair_data,
)


def test_load_canary():
    """EURUSD 2016: UTC-indexed, >5000 rows, no NaN in OHLC."""
    df = load_pair_data("EURUSD", [2016])
    assert str(df.index.tz) == "UTC", f"Expected UTC tz, got {df.index.tz}"
    assert len(df) > 5000, f"Expected >5000 rows, got {len(df)}"
    assert df.isnull().sum().sum() == 0, "Found NaN values in OHLC data"


def test_fix_window_dst():
    """Jan (GMT=UTC+0) → fix at 15:57:30 UTC; Jul (BST=UTC+1) → 14:57:30 UTC."""
    jan_s, jan_e = compute_fix_window_utc(date(2024, 1, 15))
    assert (jan_s.hour, jan_s.minute, jan_s.second) == (15, 57, 30), \
        f"Jan fix start: expected 15:57:30 UTC, got {jan_s.time()}"
    assert (jan_e.hour, jan_e.minute, jan_e.second) == (16, 2, 30), \
        f"Jan fix end: expected 16:02:30 UTC, got {jan_e.time()}"

    jul_s, jul_e = compute_fix_window_utc(date(2024, 7, 15))
    assert (jul_s.hour, jul_s.minute, jul_s.second) == (14, 57, 30), \
        f"Jul fix start: expected 14:57:30 UTC (BST), got {jul_s.time()}"
    assert (jul_e.hour, jul_e.minute, jul_e.second) == (15, 2, 30), \
        f"Jul fix end: expected 15:02:30 UTC (BST), got {jul_e.time()}"


def test_returns_relative_to_fix():
    """Series length 241, index from −180 to +60 (inclusive)."""
    df        = load_pair_data("EURUSD", [2016])
    fix_start, _ = compute_fix_window_utc(date(2016, 1, 4))   # first 2016 trading day
    result    = compute_returns_relative_to_fix(df, fix_start)
    assert len(result) == 241,       f"Expected 241 elements, got {len(result)}"
    assert result.index[0]  == -180, f"Expected index start −180, got {result.index[0]}"
    assert result.index[-1] ==  60,  f"Expected index end +60, got {result.index[-1]}"


def test_w_shape_aggregation_canary():
    """Panel → aggregate: 241 rows, 'mean' and 't_hac' columns present."""
    df    = load_pair_data("EURUSD", [2016])
    panel = build_returns_panel(df, "EURUSD")
    assert len(panel) > 0, "build_returns_panel returned empty DataFrame"
    agg   = aggregate_w_shape(panel)
    assert len(agg) == 241,         f"Expected 241 minute offsets, got {len(agg)}"
    assert "mean"  in agg.columns,  "Missing 'mean' column in aggregate"
    assert "t_hac" in agg.columns,  "Missing 't_hac' column in aggregate"
