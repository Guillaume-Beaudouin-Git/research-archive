"""
tests/test_rf_magnitude.py — Validate rf annual-decimal contract and fwd_ret correctness.

Run:  /usr/bin/python3 -m pytest Equities/research/active/indices_swing/tests/test_rf_magnitude.py -v
Or:   /usr/bin/python3 Equities/research/active/indices_swing/tests/test_rf_magnitude.py
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[4]))

import numpy as np
import pandas as pd
import pytest

from Equities.research.active.indices_swing.data.universe import load_universe


@pytest.fixture(scope="module")
def universe():
    return load_universe(start="2020-01-01")


def test_rf_is_annual_decimal(universe):
    """rf must be annual decimal (≈ 0.00–0.10), not daily (≈ 1e-5 to 2e-4)."""
    rf = universe["rf"]
    mean_rf = rf.dropna().mean()
    # Annual: 3M T-bill ~0.01–0.06 range over 2020-2026
    assert 0.0 <= mean_rf <= 0.15, (
        f"rf mean={mean_rf:.6f} looks wrong. "
        "Expected annual decimal (~0.01-0.06). "
        "Check: rf = DGS3MO/100, NOT DGS3MO/100/252."
    )
    assert mean_rf > 1e-3, (
        f"rf mean={mean_rf:.2e} is too small (daily scale). "
        "rf should be annual decimal, not daily."
    )


def test_rf_h_period_magnitude(universe):
    """
    h-period rf accrual must be rf * h / 252 (correct).
    For h=10 and mean rf ≈ 0.03–0.05 (2022-2024):
      correct rf_h = 0.04 * 10 / 252 ≈ 0.00159
      buggy  rf_h = (0.04/252) * 10 / 252 ≈ 6.3e-6 (off by 252)
    """
    rf   = universe["rf"]
    dgs  = universe["macro"]["dgs3mo"]
    h    = 10
    rf_h_correct = rf["2022":"2024"] * h / 252
    rf_h_buggy   = (dgs["2022":"2024"] / 100 / 252) * h / 252   # simulates old bug

    mean_correct = rf_h_correct.dropna().mean()
    mean_buggy   = rf_h_buggy.dropna().mean()
    ratio        = mean_correct / mean_buggy

    assert ratio > 200, (
        f"rf_h ratio correct/buggy = {ratio:.1f}; expected ~252 if bug is absent. "
        f"correct={mean_correct:.4e}, buggy={mean_buggy:.4e}"
    )


def test_fwd_ret_excess_is_smaller_than_raw(universe):
    """
    Vol-scaled excess return must be systematically smaller than vol-scaled raw return
    because we subtract a positive risk-free accrual.
    """
    prices = universe["prices"]
    rf     = universe["rf"]
    fwd    = universe["fwd_ret"]

    ticker, h = "SPY", 10
    close  = prices[(ticker, "close")]
    log_c  = np.log(close)
    raw    = log_c.shift(-h) - log_c
    vol63  = log_c.diff().rolling(63).std()
    raw_scaled = (raw / vol63).dropna()

    excess_scaled = fwd[(ticker, h)].dropna()

    # Align
    common = raw_scaled.index.intersection(excess_scaled.index)
    diff   = (raw_scaled.loc[common] - excess_scaled.loc[common]).mean()

    # diff should be positive (we subtracted rf) and ~rf_h / vol
    # For SPY vol ≈ 15%, h=10, rf≈4%: rf_h/vol ≈ 0.0016/0.009 ≈ 0.18 scaled units
    assert diff > 0.001, (
        f"Mean(raw_scaled - excess_scaled) = {diff:.4f} should be > 0 "
        "(excess return is always below raw return when rf > 0). "
        "This suggests rf_h is essentially zero — double-division bug may remain."
    )


def test_fwd_ret_nan_tail(universe):
    """Last h rows of fwd_ret must be NaN (no future prices available)."""
    fwd = universe["fwd_ret"]
    for ticker in ["SPY", "QQQ"]:
        for h in [1, 5, 10]:
            if (ticker, h) not in fwd.columns:
                continue
            tail_nan = fwd[(ticker, h)].iloc[-h:].isna().sum()
            assert tail_nan == h, (
                f"fwd_ret[{ticker},{h}] last {h} rows: expected {h} NaN, got {tail_nan}. "
                "Temporal alignment broken."
            )


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.WARNING)

    U = load_universe(start="2020-01-01")
    rf   = U["rf"]
    dgs  = U["macro"]["dgs3mo"]
    fwd  = U["fwd_ret"]

    print("=== RF MAGNITUDE REPORT ===")
    print(f"rf.describe():\n{rf.describe().to_string()}")
    print(f"\nDGS3MO mean 2022-2024: {dgs['2022':'2024'].mean():.3f}%")
    print(f"rf   mean 2022-2024: {rf['2022':'2024'].mean():.4f}  (should be ~0.03-0.05 annual)")
    print()

    # Before/after diff stats for SPY h=10 on 2022
    import numpy as np
    prices = U["prices"]
    close  = prices[("SPY", "close")]
    log_c  = np.log(close)
    h      = 10
    raw    = log_c.shift(-h) - log_c
    vol63  = log_c.diff().rolling(63).std()

    # Correct (after fix)
    rf_h_correct = rf * h / 252
    excess_correct = (raw - rf_h_correct) / vol63
    # Buggy (before fix, rf was daily decimal)
    rf_buggy = dgs / 100 / 252                    # old code
    rf_h_buggy = rf_buggy * h / 252              # old _compute_fwd_ret
    excess_buggy = (raw - rf_h_buggy) / vol63

    w2022 = slice("2022-01-01", "2022-12-31")
    print("=== SPY h=10 EXCESS RETURN — 2022 WINDOW ===")
    print(f"BEFORE FIX (rf daily, double-divided): mean={excess_buggy[w2022].mean():.4f}, std={excess_buggy[w2022].std():.4f}")
    print(f"AFTER  FIX (rf annual, single /252):   mean={excess_correct[w2022].mean():.4f}, std={excess_correct[w2022].std():.4f}")
    print(f"\nrf_h(h=10) before: {rf_h_buggy.mean():.2e}  |  after: {rf_h_correct.mean():.2e}  |  factor: {rf_h_correct.mean()/rf_h_buggy.mean():.0f}×")
