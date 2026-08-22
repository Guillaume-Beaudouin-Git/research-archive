"""Regression test for the financing sign convention (the iteration-2 bug).
swap_bps_night is SIGNED (negative = you pay). Correct P&L = gross + signed_swap (a cost REDUCES P&L)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import ftmo_costs as C


def test_swap_sign_is_negative_for_long_index():
    assert C.swap_bps_night("US100", "long") < 0, "long index CFD financing must be a cost (negative)"
    assert C.swap_bps_night("XAUUSD", "long") < 0


def test_correct_pnl_adds_signed_swap_and_reduces_long_return():
    gross = 0.0010                      # +10 bps gross on a long index day
    swap = C.swap_bps_night("US100", "long") / 1e4   # signed, negative
    net_correct = gross + swap          # ADD signed swap
    net_bug = gross - swap              # the bug (subtracts a negative -> adds income)
    assert net_correct < gross, "financing must reduce a long position's return"
    assert net_bug > gross, "the bug would inflate it (guard against regression)"


if __name__ == "__main__":
    test_swap_sign_is_negative_for_long_index()
    test_correct_pnl_adds_signed_swap_and_reduces_long_return()
    print("cost-sign convention OK: financing is a cost; net = gross + signed_swap")
