"""Miroir V2+E7 (règles micro-ORB de l'EA) : goldens synthétiques dérivés à la
main + identités sémantiques du ledger canonique (4013 trades) que l'EA mirror.
"""
import numpy as np
import pandas as pd
import pytest

from lib import REPO
from lib import invariants as inv

LEDGER = (REPO / "PropFirms/ftmo/program_2026-06/ftmo_research/audit/"
          "nq_v2_trades.parquet")


# ---------------------------------------------------------------- goldens V2
def test_or_levels():
    hi, lo = inv.or_levels([100, 102, 101], [99, 98.5, 99.2])
    assert (hi, lo) == (102.0, 98.5)


def test_v2_width_filter_basis_or_end_close():
    # largeur 30 pts sur close 21500 = 13.95 bps -> pass ; sur 45000 = 6.7 -> fail
    assert inv.v2_width_ok(21520.0, 21490.0, 21500.0)
    assert not inv.v2_width_ok(45020.0, 44990.0, 45000.0)
    assert not inv.v2_width_ok(100.0, 100.0, 100.0)      # OR dégénéré


def test_break_long_first_bar():
    b = inv.orb_break([103, 104], [101, 102], or_hi=102.5, or_lo=99.0)
    assert b == dict(direction=1, level=102.5, stop=99.0, bar=0)


def test_break_short_later_bar():
    b = inv.orb_break([101, 101.5, 101.0], [100, 99.5, 98.0],
                      or_hi=102.0, or_lo=99.0)
    assert b == dict(direction=-1, level=99.0, stop=102.0, bar=2)


def test_break_tiebreak_long_priority():
    # même barre casse les deux côtés -> long (high testé avant low, builder)
    b = inv.orb_break([103], [98], or_hi=102.0, or_lo=99.0)
    assert b["direction"] == 1


def test_no_break():
    assert inv.orb_break([101, 101], [100, 100], 102.0, 99.0) is None


# ---------------------------------------------------------------- goldens E7
def test_e7_stop_out():
    ex = inv.e7_exit(highs=[101, 100.5], lows=[100, 98.9], closes=[100.5, 99.0],
                     entry=102.0, stop=99.0, direction=1)
    assert ex == dict(exit_px=99.0, reason="stop", be_armed=False)


def test_e7_be_armed_then_retrace():
    # long entry 102, R=3 : touche 105 (arme BE), retombe à 102 -> sortie BE
    ex = inv.e7_exit(highs=[105.2, 103.0], lows=[103.5, 101.8],
                     closes=[105.0, 102.5], entry=102.0, stop=99.0, direction=1)
    assert ex == dict(exit_px=102.0, reason="be", be_armed=True)


def test_e7_stop_checked_before_arming_same_bar():
    # même barre touche stop ET +1R -> stop d'abord (ordre conservateur builder)
    ex = inv.e7_exit(highs=[105.5], lows=[98.5], closes=[104.0],
                     entry=102.0, stop=99.0, direction=1)
    assert ex["reason"] == "stop" and ex["exit_px"] == 99.0


def test_e7_time_stop():
    ex = inv.e7_exit(highs=[103, 103.5], lows=[101, 101.5], closes=[103, 103.2],
                     entry=102.0, stop=99.0, direction=1)
    assert ex == dict(exit_px=103.2, reason="time_stop", be_armed=False)


def test_e7_short_be():
    ex = inv.e7_exit(highs=[100.0, 102.1], lows=[98.9, 99.5],
                     closes=[99.0, 102.0], entry=102.0, stop=105.0, direction=-1)
    # short R=3: touche 99 (arme BE), remonte à 102 -> BE
    assert ex == dict(exit_px=102.0, reason="be", be_armed=True)


def test_micro_sizing():
    assert inv.micro_risk_usd(150.0, 1.0, 0.01) == pytest.approx(1.5)


# ------------------------------------------------------- identités du ledger
@pytest.fixture(scope="module")
def ledger():
    if not LEDGER.exists():
        pytest.skip("ledger absent")
    return pd.read_parquet(LEDGER)


def test_ledger_semantics_entry_at_level(ledger):
    assert (ledger["entry"] == ledger["level"]).all()      # stop dormant AU niveau


def test_ledger_semantics_stop_opposite_side(ledger):
    longs = ledger[ledger.direction == 1]
    shorts = ledger[ledger.direction == -1]
    assert (longs["level"] == longs["or_hi"]).all()
    assert (longs["stop_eff"] == longs["or_lo"]).all()
    assert (shorts["level"] == shorts["or_lo"]).all()
    assert (shorts["stop_eff"] == shorts["or_hi"]).all()


def test_ledger_semantics_r_gross_identity(ledger):
    r = ((ledger["exit_px"] - ledger["entry"]) / ledger["or_range"]
         * ledger["direction"])
    assert np.allclose(r, ledger["r_gross"], atol=1e-5)


def test_ledger_v2_width_filter_effective(ledger):
    bps = ledger["or_range"] / ledger["level"] * 1e4
    assert (bps < 10.0).mean() < 0.01    # filtre 10 bps (résidus = base close OR)
