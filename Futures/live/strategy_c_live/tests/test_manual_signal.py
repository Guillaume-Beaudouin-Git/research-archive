"""
Tests for manual_signal._atr15 scope — Finding #4.

Invariant: _atr15 must use only today's ORB bars, not the full 2-day fetch.
  generate_signal_and_alert() must call _atr15(today_bars), NOT _atr15(bars).
  These tests document the bug (2-day inflation) and pin the correct behavior.
"""
import datetime

import pandas as pd
import pytest

from zoneinfo import ZoneInfo

from Futures.live.strategy_c_live.manual_signal import _atr15
from Futures.live.strategy_c_live.config import ORB_OPEN, ORB_CLOSE

ET = ZoneInfo("America/New_York")


def _make_2day_bars() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (full_2day, today_only) DataFrames.

    Yesterday ORB: high=18100, low=17900 → range=200 pts.
    Today ORB:     high=18060, low=18020 → range=40 pts.
    """
    rows = []

    # Yesterday 09:30 bar — wide range
    yday = datetime.datetime(2024, 1, 1, 9, 30, tzinfo=ET)
    rows.append((yday, 18000, 18100, 17900, 18000, 1000))

    # Today 09:30-09:45 bars — narrow range
    for i in range(16):
        t = datetime.datetime(2024, 1, 2, 9, 30, tzinfo=ET) + datetime.timedelta(minutes=i)
        rows.append((t, 18040, 18060, 18020, 18040, 1000))

    cols = ["open", "high", "low", "close", "volume"]
    idx = pd.DatetimeIndex([r[0] for r in rows])
    data = {c: [r[i + 1] for r in rows] for i, c in enumerate(cols)}
    full_2day = pd.DataFrame(data, index=idx)
    today_only = full_2day[full_2day.index.date == datetime.date(2024, 1, 2)]
    return full_2day, today_only


class TestAtr15Scope:

    def test_full_2day_inflates_atr(self):
        """_atr15(full_2day) picks up yesterday's wider range — confirms the bug."""
        full, _ = _make_2day_bars()
        result = _atr15(full)
        # Yesterday: high=18100, low=17900 → range 200 contaminates result
        assert result > 40, (
            f"Expected inflated ATR >40 from 2-day frame, got {result}"
        )

    def test_today_only_gives_correct_atr(self):
        """_atr15(today_bars) returns the correct today-only ORB range."""
        _, today = _make_2day_bars()
        result = _atr15(today)
        assert result == pytest.approx(40.0, abs=0.01), (
            f"Expected 40 pts (today ORB range), got {result}"
        )


