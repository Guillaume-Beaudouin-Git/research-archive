"""
Tests for ChallengeState lock trigger logic.

Invariant: lock triggers on FIRST of (balance >= $26,600) OR (payout_requested).
Lock only applies in funded phase (is_funded=True).
"""
from unittest.mock import patch

import pytest

from Futures.live.strategy_c_live.challenge_state import ChallengeState
from Futures.live.strategy_c_live.config import TRADEIFY_LOCK_BALANCE, TRADEIFY_LOCKED_FLOOR


def _funded_state(**kwargs) -> ChallengeState:
    """Create an in-memory funded ChallengeState without filesystem writes."""
    defaults = dict(
        initial_balance=25_000.0,
        peak_balance=25_000.0,
        challenge_start_date="2026-01-01",
        is_funded=True,
    )
    defaults.update(kwargs)
    state = ChallengeState(**defaults)
    state._save = lambda: None  # suppress filesystem writes
    return state


def _eval_state(**kwargs) -> ChallengeState:
    """Create an in-memory eval-phase ChallengeState."""
    defaults = dict(
        initial_balance=25_000.0,
        peak_balance=25_000.0,
        challenge_start_date="2026-01-01",
        is_funded=False,
    )
    defaults.update(kwargs)
    state = ChallengeState(**defaults)
    state._save = lambda: None
    return state


class TestLockTrigger:

    def test_lock_triggers_on_balance_alone(self):
        """Lock must trigger if balance >= $26,600 even without payout requested."""
        state = _funded_state()
        result = state.check_lock_trigger(TRADEIFY_LOCK_BALANCE)
        assert result is True
        assert state.lock_triggered is True
        assert state.lock_trigger_reason == "balance"

    def test_lock_triggers_on_payout_alone(self):
        """Lock must trigger if payout requested even with balance below $26,600."""
        state = _funded_state(first_payout_requested=True)
        result = state.check_lock_trigger(26_400.0)   # below threshold
        assert result is True
        assert state.lock_triggered is True
        assert state.lock_trigger_reason == "payout"

    def test_lock_does_not_trigger_neither_condition(self):
        """No lock if balance < $26,600 and payout not requested."""
        state = _funded_state()
        result = state.check_lock_trigger(26_500.0)   # below threshold, no payout
        assert result is False
        assert state.lock_triggered is False

    def test_lock_persistent_after_trigger(self):
        """Once locked, stays locked and check_lock_trigger returns False (idempotent)."""
        state = _funded_state()
        state.check_lock_trigger(TRADEIFY_LOCK_BALANCE)   # triggers
        assert state.lock_triggered is True
        # Subsequent calls return False (already locked)
        result_2 = state.check_lock_trigger(25_000.0)     # balance dropped
        assert result_2 is False
        assert state.lock_triggered is True               # still locked

    def test_lock_does_not_trigger_in_eval_phase(self):
        """Lock mechanism must not fire during eval phase (is_funded=False)."""
        state = _eval_state()
        # Even with balance above $26,600 AND payout requested — no lock in eval
        state.first_payout_requested = True
        result = state.check_lock_trigger(30_000.0)
        assert result is False
        assert state.lock_triggered is False


class TestSessionStartLockSync:
    """
    Session-start lock sync: check_lock_trigger is called at run_daily.py startup
    to catch lock conditions from prior no-trade days (balance rose without EOD check).
    """

    def test_lock_triggers_on_session_start_balance_above_threshold(self):
        """Balance may have risen on a no-trade day; session-start check must catch it."""
        state = _funded_state(peak_balance=27_000.0)
        assert not state.lock_triggered
        triggered = state.check_lock_trigger(TRADEIFY_LOCK_BALANCE)
        assert triggered is True
        assert state.lock_triggered is True
        assert state.lock_trigger_reason == "balance"

    def test_no_lock_if_not_funded_at_session_start(self):
        """Session-start check must not trigger lock during eval phase."""
        state = _eval_state()
        triggered = state.check_lock_trigger(TRADEIFY_LOCK_BALANCE)
        assert triggered is False
        assert not state.lock_triggered


class TestMarkPayoutRequested:

    def test_mark_payout_sets_lock_trigger_reason(self):
        state = _funded_state()
        state.mark_payout_requested()
        assert state.lock_triggered is True
        assert state.lock_trigger_reason == "payout"
        assert state.first_payout_requested is True

    def test_mark_payout_idempotent(self):
        state = _funded_state()
        state.mark_payout_requested()
        # Second call should warn and not change state
        state.mark_payout_requested()
        assert state.lock_triggered is True
