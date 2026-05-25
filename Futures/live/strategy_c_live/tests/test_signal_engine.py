"""
Tests for signal_engine — VWAP formula correctness vs iter_10 backtest.

Key invariant: compute_vwap(bars_9h31_to_9h45) must reproduce the
Kaggle vwap_rth column at 9:45 within floating-point tolerance.
"""
import datetime
import math
from unittest.mock import patch
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from Futures.live.strategy_c_live.signal_engine import compute_signal, compute_vwap

TZ_ET = ZoneInfo("America/New_York")


def _make_bars(rows: list[tuple]) -> pd.DataFrame:
    """Build a 1-min OHLCV DataFrame from (time_str, o, h, l, c, vol) tuples."""
    idx = [
        datetime.datetime.strptime(f"2024-01-02 {t}", "%Y-%m-%d %H:%M").replace(
            tzinfo=TZ_ET
        )
        for t, *_ in rows
    ]
    data = {
        "open":   [r[1] for r in rows],
        "high":   [r[2] for r in rows],
        "low":    [r[3] for r in rows],
        "close":  [r[4] for r in rows],
        "volume": [r[5] for r in rows],
    }
    return pd.DataFrame(data, index=pd.DatetimeIndex(idx, name="timestamp_et"))


class TestComputeVwap:

    def test_single_bar_equals_hlc3(self):
        # Single bar: VWAP = HLC3 exactly
        bars = _make_bars([("09:31", 100.0, 110.0, 90.0, 105.0, 500)])
        hlc3 = (110.0 + 90.0 + 105.0) / 3.0
        assert compute_vwap(bars) == pytest.approx(hlc3, abs=1e-4)

    def test_two_bars_weighted(self):
        # Two bars, volumes 1000 and 2000 → weight = 1:2
        bars = _make_bars([
            ("09:31", 100.0, 110.0, 90.0, 100.0, 1000),
            ("09:32", 100.0, 120.0, 100.0, 110.0, 2000),
        ])
        hlc3_1 = (110.0 + 90.0 + 100.0) / 3.0   # 100.0
        hlc3_2 = (120.0 + 100.0 + 110.0) / 3.0  # 110.0
        expected = (hlc3_1 * 1000 + hlc3_2 * 2000) / 3000
        assert compute_vwap(bars) == pytest.approx(expected, abs=1e-4)

    def test_differs_from_close_vwap(self):
        # With asymmetric high/low, HLC3 VWAP != close VWAP
        bars = _make_bars([
            ("09:31", 100.0, 150.0, 50.0, 100.0, 1000),  # HLC3=100, close=100 — same here
            ("09:32", 100.0, 180.0, 80.0, 110.0, 1000),  # HLC3=(180+80+110)/3=123.33, close=110
        ])
        hlc3_2 = (180.0 + 80.0 + 110.0) / 3.0
        close_vwap = (100.0 * 1000 + 110.0 * 1000) / 2000
        hlc3_1 = (150.0 + 50.0 + 100.0) / 3.0
        hlc3_vwap = (hlc3_1 * 1000 + hlc3_2 * 1000) / 2000
        result = compute_vwap(bars)
        assert result == pytest.approx(hlc3_vwap, abs=1e-4)
        assert result != pytest.approx(close_vwap, abs=0.1)

    def test_zero_volume_fallback(self):
        bars = _make_bars([("09:31", 100.0, 110.0, 90.0, 105.0, 0)])
        # Falls back to mean close
        assert compute_vwap(bars) == pytest.approx(105.0, abs=1e-4)

    def test_kaggle_day_2023_01_31(self):
        """
        Spot-check against known Kaggle vwap_rth value.
        Date: 2023-01-31. Expected bt_vwap at 9:45: 14663.3516
        (HLC3 cumulative 9:31-9:45, verified by cross-check script).
        """
        import sys
        sys.path.insert(0, ".")
        try:
            from data.cache import load_nq_1min
        except Exception:
            pytest.skip("Kaggle CSV not available in this environment")

        df = load_nq_1min()
        d = datetime.date(2023, 1, 31)
        day_df = df[df.index.date == d]
        orb_open  = datetime.time(9, 30)
        orb_close = datetime.time(9, 45)
        orb_1m = day_df[
            (day_df.index.time >= orb_open) & (day_df.index.time <= orb_close)
        ]
        assert len(orb_1m) == 16, f"Expected 16 ORB bars, got {len(orb_1m)}"

        # Skip 9:30 bar — matches backtest formula
        orb_for_vwap = orb_1m[orb_1m.index.time > orb_open]
        live_vwap = compute_vwap(orb_for_vwap)
        bt_vwap   = orb_1m.iloc[-1]["vwap_rth"]

        assert abs(live_vwap - bt_vwap) < 0.01, (
            f"VWAP mismatch: live={live_vwap:.4f} bt={bt_vwap:.4f} diff={abs(live_vwap-bt_vwap):.4f}"
        )

    def test_full_dataset_zero_signal_flips(self):
        """
        Across all 764 ORB days in the Kaggle dataset, fixed live VWAP (HLC3,
        skip 9:30) must agree with backtest vwap_rth on VWAP-filter direction
        (close_945 above/below VWAP) for every single day.
        """
        import sys
        sys.path.insert(0, ".")
        try:
            from data.cache import load_nq_1min
        except Exception:
            pytest.skip("Kaggle CSV not available in this environment")

        df = load_nq_1min()
        orb_open  = datetime.time(9, 30)
        orb_close = datetime.time(9, 45)
        flips = []

        for d in sorted(set(df.index.date)):
            day_df = df[df.index.date == d]
            orb_1m = day_df[
                (day_df.index.time >= orb_open) & (day_df.index.time <= orb_close)
            ]
            if len(orb_1m) < 16:
                continue
            close_945 = orb_1m.iloc[-1]["close"]
            bt_vwap   = orb_1m.iloc[-1]["vwap_rth"]
            live_vwap = compute_vwap(orb_1m[orb_1m.index.time > orb_open])
            if (close_945 >= bt_vwap) != (close_945 >= live_vwap):
                flips.append((d, close_945, bt_vwap, live_vwap))

        assert len(flips) == 0, (
            f"{len(flips)} signal flip(s) detected — live VWAP diverges from backtest:\n"
            + "\n".join(f"  {d}: close={c:.2f} bt={b:.4f} live={l:.4f}" for d,c,b,l in flips)
        )


# ─────────────────────────────────────────────────────────────────────────────
# Helper for compute_signal tests
# ─────────────────────────────────────────────────────────────────────────────

def _make_compute_signal_bars() -> pd.DataFrame:
    """Minimal 2-day 1-min bars that produce a clean BUY signal.

    Yesterday (2024-01-01): single RTH bar at 15:59, close=17960.
    Today    (2024-01-02): 16 ORB bars 09:30-09:45.
      open_price (5-min resample)  = 17960  (09:30 bar open)
      close_price (5-min resample) = 18020  (09:41-09:45 bars close)
      orb_range = 60 pts > 30 (passes RANGE_MIN_PTS)
      gap       = 0.0 %   (passes GAP_FILTER ≤ 1.2 %)
      VWAP      ≈ 18002   (HLC3-weighted, 09:31-09:45) < close → BUY ✓

    With normal data the function returns a non-None BUY signal.
    Tests inject failures (NaN VWAP, patched NaN) to verify guard behaviour.
    """
    rows = []

    # Yesterday: only last close matters for gap computation
    rows.append((
        datetime.datetime(2024, 1, 1, 15, 59, tzinfo=TZ_ET),
        17960.0, 17965.0, 17955.0, 17960.0, 5000,
    ))

    # Today ORB 09:30-09:45 (16 bars)
    for i in range(16):
        t = datetime.datetime(2024, 1, 2, 9, 30, tzinfo=TZ_ET) + datetime.timedelta(minutes=i)
        if i == 0:
            rows.append((t, 17960.0, 17965.0, 17955.0, 17962.0, 1000))
        else:
            rows.append((t, 17965.0, 18025.0, 17960.0, 18020.0, 1200))

    cols = ["open", "high", "low", "close", "volume"]
    idx  = pd.DatetimeIndex([r[0] for r in rows])
    data = {c: [r[i + 1] for r in rows] for i, c in enumerate(cols)}
    return pd.DataFrame(data, index=idx)


# ─────────────────────────────────────────────────────────────────────────────
# Finding #1 regression tests
# ─────────────────────────────────────────────────────────────────────────────

class TestComputeSignalVwapGuards:
    """VWAP computation failures must skip the trade, never bypass the filter."""

    def test_compute_vwap_returns_nan_on_empty_frame(self):
        """Explicit contract: compute_vwap([]) returns NaN (not a price)."""
        empty = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
        result = compute_vwap(empty)
        assert math.isnan(result), f"Expected NaN for empty frame, got {result!r}"

    def test_compute_signal_skips_when_vwap_returns_nan(self):
        """compute_vwap returning NaN must produce None from compute_signal (skip trade).

        Without guard: NaN comparisons in the VWAP filter both evaluate to False,
        so neither branch fires and the trade is taken — wrong direction possible.
        """
        bars = _make_compute_signal_bars()
        with patch(
            "Futures.live.strategy_c_live.signal_engine.compute_vwap",
            return_value=float("nan"),
        ):
            result = compute_signal(bars)
        assert result is None, (
            f"VWAP=NaN must skip trade (return None), got signal dict: {result}"
        )

    def test_compute_signal_skips_on_nan_in_price_data(self):
        """NaN in every post-9:30 bar's high → all HLC3 are NaN → NaN VWAP → skip trade.

        When ALL bars in orb_1m_for_vwap have NaN in 'high', every HLC3 term is NaN,
        the cumulative sum is all-NaN, and compute_vwap returns NaN.  Without a guard
        the VWAP filter comparisons both evaluate to False and the trade fires anyway.

        Note: a single-bar NaN produces wrong (non-NaN) VWAP via pandas skipna cumsum.
        All-bars NaN guarantees a NaN VWAP, which is the case we need the guard to catch.
        """
        bars = _make_compute_signal_bars().copy()
        # Corrupt every bar used for VWAP (09:31-09:45) — makes all HLC3 NaN → NaN VWAP
        mask = (bars.index.date == datetime.date(2024, 1, 2)) & (
            bars.index.time > datetime.time(9, 30)
        ) & (bars.index.time <= datetime.time(9, 45))
        bars.loc[mask, "high"] = float("nan")

        result = compute_signal(bars)
        assert result is None, (
            f"NaN VWAP from corrupt price data must skip trade (return None), got: {result}"
        )
