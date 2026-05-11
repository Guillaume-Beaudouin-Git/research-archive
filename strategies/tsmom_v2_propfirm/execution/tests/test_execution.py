"""
Integration tests for TSMOM v2 execution layer.

All tests use real API calls against the Propr demo account.
Run with: pytest strategies/tsmom_v2_propfirm/execution/tests/ -v

Requires: PROPR_API_KEY environment variable set.
"""

from __future__ import annotations

import os
import sqlite3
import tempfile
import time
from unittest.mock import MagicMock, patch  # MagicMock used in test_05

import pytest
import requests

# ── Constants ───────────────────────────────────────────────────────────────
ACCOUNT_ID = "urn:prp-account:KBNeHP5eN3mz"
ATTEMPT_ID = "urn:prp-challenge-attempt:YrWnSPahXiz2"
BTC_ASSET = "BTC"

API_KEY = os.environ.get("PROPR_API_KEY", "")
if not API_KEY:
    pytest.skip("PROPR_API_KEY not set", allow_module_level=True)


# ── Test 01 — API health ────────────────────────────────────────────────────

def test_01_api_health() -> None:
    """GET /health → 200 OK."""
    from strategies.tsmom_v2_propfirm.execution import BASE_URL
    resp = requests.get(f"{BASE_URL}/health", timeout=10)
    assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
    assert resp.json().get("status") == "OK"


# ── Test 02 — EquityMonitor live ────────────────────────────────────────────

def test_02_equity_monitor() -> None:
    """Live equity monitor sanity checks."""
    from strategies.tsmom_v2_propfirm.execution.equity_monitor import EquityMonitor

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name

    with patch("strategies.tsmom_v2_propfirm.execution.equity_monitor.STATE_DB_PATH", tmp_db):
        monitor = EquityMonitor(ATTEMPT_ID, ACCOUNT_ID, API_KEY)
        equity = monitor.get_equity()
        daily_dd = monitor.get_daily_dd()
        total_dd = monitor.get_total_dd()
        safe = monitor.is_safe()

    assert equity > 0, f"Equity should be positive, got {equity}"
    assert 0.0 <= daily_dd < 1.0, f"Daily DD out of range: {daily_dd}"
    assert 0.0 <= total_dd < 1.0, f"Total DD out of range: {total_dd}"
    assert safe is True, f"Account should be safe, got daily_dd={daily_dd:.3%} total_dd={total_dd:.3%}"


# ── Test 03 — Daily DD formula ──────────────────────────────────────────────

def test_03_daily_dd_formula() -> None:
    """
    With equity_at_day_start=5000 and marginBalance=4860:
        daily_dd = (5000 - 4860) / 5000 = 0.028
        is_safe() must return False (at the limit).
    """
    from strategies.tsmom_v2_propfirm.execution.equity_monitor import EquityMonitor

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name

    with patch("strategies.tsmom_v2_propfirm.execution.equity_monitor.STATE_DB_PATH", tmp_db):
        monitor = EquityMonitor(ATTEMPT_ID, ACCOUNT_ID, API_KEY)

        # Pre-populate DB with known day-start equity
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        monitor._set_day_start_equity(today, 5000.0)

        # Mock _fetch_account to return controlled values
        mock_account = {
            "marginBalance": "4860",
            "highWaterMark": "5000",
            "totalUnrealizedPnl": "0",
        }
        with patch.object(monitor, "_fetch_account", return_value=mock_account):
            daily_dd = monitor.get_daily_dd()
            total_dd = monitor.get_total_dd()
            safe = monitor.is_safe()

    assert daily_dd == pytest.approx(0.028, abs=1e-6), f"Expected 0.028, got {daily_dd}"
    assert total_dd == pytest.approx(0.028, abs=1e-6), f"Expected 0.028, got {total_dd}"
    assert safe is False, "is_safe() must be False when daily_dd == MAX_DAILY_DD"


# ── Test 04 — Order lifecycle ───────────────────────────────────────────────

def test_04_order_lifecycle() -> None:
    """
    Place a real BTC market buy ($50 notional) then attempt cancel.

    Uses ProprClient with the correct schema:
        {"orders": [{accountId, intentId(ULID), exchange, type, side,
                     positionSide, productType, timeInForce(IOC),
                     asset, base, quote, quantity(str), reduceOnly, closePosition}]}

    Market orders are IOC and typically fill immediately, so cancel_order
    returns False (already filled) — both True and False are valid outcomes.
    """
    from strategies.tsmom_v2_propfirm.execution.order_executor import (
        cancel_order,
        place_market_order,
    )

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name

    with patch("strategies.tsmom_v2_propfirm.execution.order_executor.ORDERS_DB_PATH", tmp_db):
        order_id = place_market_order(ACCOUNT_ID, BTC_ASSET, "buy", 50.0, API_KEY)
        assert order_id is not None, "order_id must not be None"
        assert len(order_id) > 0, "order_id must be non-empty"
        assert "urn:prp-order:" in order_id, f"unexpected order_id format: {order_id}"

        time.sleep(1)  # IOC market orders fill instantly; pause before cancel attempt

        ok = cancel_order(ACCOUNT_ID, order_id, API_KEY)
        # True  = cancelled before fill (rare for IOC)
        # False = already filled (expected for IOC market orders)
        assert isinstance(ok, bool), f"cancel_order must return bool, got {type(ok)}"


# ── Test 05 — Guardrail flatten ─────────────────────────────────────────────

def test_05_guardrail_flatten() -> None:
    """
    With get_daily_dd mocked to 0.029 (> MAX_DAILY_DD 0.028):
      - flatten_all must be called exactly once
      - kill_switch_triggered must be written to DB
    """
    from strategies.tsmom_v2_propfirm.execution.guardrail_loop import _guardrail_poll

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp_db = f.name

    with (
        patch("strategies.tsmom_v2_propfirm.execution.guardrail_loop.STATE_DB_PATH", tmp_db),
        patch("strategies.tsmom_v2_propfirm.execution.guardrail_loop.flatten_all") as mock_flatten,
        patch("sys.exit") as mock_exit,
    ):
        from strategies.tsmom_v2_propfirm.execution.equity_monitor import EquityMonitor

        mock_monitor = MagicMock(spec=EquityMonitor)
        mock_monitor.get_status.return_value = {
            "equity": 4855.0,
            "daily_dd": 0.029,   # exceeds MAX_DAILY_DD = 0.028
            "total_dd": 0.029,
            "is_safe": False,
        }

        _guardrail_poll(ACCOUNT_ID, ATTEMPT_ID, API_KEY, mock_monitor)

        mock_flatten.assert_called_once_with(ACCOUNT_ID, API_KEY)
        mock_exit.assert_called_once_with(1)

        # Verify kill_switch was written to DB
        with sqlite3.connect(tmp_db) as conn:
            row = conn.execute(
                "SELECT kill_switch_triggered FROM kill_switch WHERE kill_switch_triggered = 1"
            ).fetchone()
        assert row is not None, "kill_switch_triggered=1 must be written to DB"


# ── Test 06 — Dry-run rebalance ─────────────────────────────────────────────

def test_06_dry_run_rebalance() -> None:
    """
    dry_run=True must produce zero POST orders and log a dry_run=1 row.
    """
    from strategies.tsmom_v2_propfirm.execution.rebalance import run_weekly_rebalance

    with (
        tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f1,
        tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f2,
    ):
        tmp_state_db = f1.name
        tmp_orders_db = f2.name

    with (
        patch("strategies.tsmom_v2_propfirm.execution.rebalance.STATE_DB_PATH", tmp_state_db),
        patch("strategies.tsmom_v2_propfirm.execution.equity_monitor.STATE_DB_PATH", tmp_state_db),
        patch("strategies.tsmom_v2_propfirm.execution.order_executor.ORDERS_DB_PATH", tmp_orders_db),
        patch("strategies.tsmom_v2_propfirm.execution.rebalance.place_market_order") as mock_place,
        patch("strategies.tsmom_v2_propfirm.execution.rebalance.close_position") as mock_close,
    ):
        run_weekly_rebalance(ACCOUNT_ID, ATTEMPT_ID, API_KEY, dry_run=True)

        # No real orders placed
        mock_place.assert_not_called()
        mock_close.assert_not_called()

        # Rebalance log has dry_run=1 row
        with sqlite3.connect(tmp_state_db) as conn:
            row = conn.execute(
                "SELECT dry_run FROM rebalance_log WHERE dry_run = 1"
            ).fetchone()
        assert row is not None, "rebalance_log must have a dry_run=1 row after dry run"

        # Orders log is empty (no real API calls)
        with sqlite3.connect(tmp_orders_db) as conn:
            try:
                count = conn.execute("SELECT COUNT(*) FROM orders_log").fetchone()[0]
            except sqlite3.OperationalError:
                count = 0  # table not created = no orders placed
        assert count == 0, f"orders_log should have 0 rows in dry run, got {count}"


# ── Result summary ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    result = pytest.main([__file__, "-v", "--tb=short"])
    if result == 0:
        print("\n✅ 6/6 integration tests passed — execution layer ready")
    sys.exit(result)
