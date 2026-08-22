"""
Engine integrity tests — the verification backbone for every module's numbers.
Run: python tests/test_engine.py   (plain asserts, no pytest needed)

Covers: (1) no-look-ahead execution (entry at next bar's open), (2) intrabar
SL/TP resolution and pessimistic stop-first tie-break, (3) trade-for-trade
equivalence of the primary loop engine and the vectorised engine, (4) cost
accounting.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine import backtest as bt  # noqa: E402


def _df(o, h, l, c):
    idx = pd.date_range("2020-01-01", periods=len(c), freq="h")
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def test_entry_at_next_open():
    df = _df([10, 10, 10, 10, 10], [10, 10, 12, 10, 10],
             [10, 10, 10, 10, 10], [10, 10, 11, 10, 10])
    sig = pd.Series([0, 1, 0, 0, 0], index=df.index)  # decide long at bar 1 close
    tr = bt.run_backtest(df, sig, sl_pct=0.5, tp_pct=0.10, cost_rt=0.0)
    assert len(tr) == 1, tr
    assert tr.iloc[0]["entry_time"] == df.index[2], "entry must be at bar-2 open (next bar)"
    assert tr.iloc[0]["reason"] == "tp" and abs(tr.iloc[0]["exit_px"] - 11.0) < 1e-9
    print("OK  entry at next bar open + TP fill")


def test_stop_first_on_tie():
    # entry 100 at bar1 open; bar1 hits BOTH sl(99) and tp(103) -> stop-first
    df = _df([100, 100, 100], [100, 103, 100], [100, 99, 100], [100, 100, 100])
    sig = pd.Series([1, 0, 0], index=df.index)
    tr = bt.run_backtest(df, sig, sl_pct=0.01, tp_pct=0.03, cost_rt=0.0)
    assert len(tr) == 1 and tr.iloc[0]["reason"] == "sl", tr
    print("OK  same-bar SL/TP resolves pessimistically (stop-first)")


def test_cost_accounting():
    df = _df([100, 100, 100], [100, 103, 100], [100, 100, 100], [100, 100, 100])
    sig = pd.Series([1, 0, 0], index=df.index)
    tr = bt.run_backtest(df, sig, sl_pct=0.5, tp_pct=0.03, cost_rt=0.001)
    g = tr.iloc[0]["ret_gross"]
    n = tr.iloc[0]["ret_net"]
    assert abs((g - n) - 0.001) < 1e-9, "net = gross - cost_rt"
    print("OK  cost accounting (net = gross - round-trip cost)")


def test_fast_reference_equivalence():
    rng = np.random.default_rng(0)
    n = 5000
    c = 100 + np.cumsum(rng.normal(0, 1, n))
    o = c + rng.normal(0, 0.2, n)
    h = np.maximum(o, c) + np.abs(rng.normal(0, 0.5, n))
    l = np.minimum(o, c) - np.abs(rng.normal(0, 0.5, n))
    df = _df(o, h, l, c)
    sig = pd.Series(rng.choice([-1, 0, 1], n), index=df.index)
    a = bt.run_backtest(df, sig, sl_pct=0.02, tp_pct=0.03, cost_rt=0.001, max_hold=20)
    b = bt.run_backtest_vectorized(df, sig, sl_pct=0.02, tp_pct=0.03, cost_rt=0.001, max_hold=20)
    assert len(a) == len(b), (len(a), len(b))
    assert np.allclose(a["ret_net"].values, b["ret_net"].values, atol=1e-12)
    assert (a["reason"].values == b["reason"].values).all()
    print(f"OK  loop vs vectorised engine identical ({len(a)} trades)")


def test_no_lookahead_invariance():
    # A signal that fires only on the final bar can never produce a (closed) trade,
    # because entry would be at a non-existent next bar.
    df = _df([10] * 6, [11] * 6, [9] * 6, [10] * 6)
    sig = pd.Series([0, 0, 0, 0, 0, 1], index=df.index)
    tr = bt.run_backtest(df, sig, sl_pct=0.2, tp_pct=0.2, cost_rt=0.0)
    assert len(tr) == 0, "a last-bar signal cannot be entered (no future bar)"
    print("OK  last-bar signal cannot look ahead")


if __name__ == "__main__":
    test_entry_at_next_open()
    test_stop_first_on_tie()
    test_cost_accounting()
    test_fast_reference_equivalence()
    test_no_lookahead_invariance()
    print("\nALL ENGINE TESTS PASSED")
