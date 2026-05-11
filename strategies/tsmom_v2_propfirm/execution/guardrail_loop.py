"""
Guardrail loop for TSMOM v2.

Daemon thread that polls equity every 60s and triggers an emergency flatten
if daily or total drawdown exceeds the hard limits.
"""

from __future__ import annotations

import logging
import sqlite3
import sys
import threading
import time
from datetime import datetime, timezone

from . import MAX_DAILY_DD, MAX_TOTAL_DD, STATE_DB_PATH
from .equity_monitor import EquityMonitor
from .order_executor import flatten_all

logger = logging.getLogger(__name__)

_POLL_INTERVAL: int = 60  # seconds

_CREATE_KILL_SWITCH = """
CREATE TABLE IF NOT EXISTS kill_switch (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ts                  TEXT NOT NULL,
    kill_switch_triggered INTEGER NOT NULL DEFAULT 0,
    daily_dd_pct        REAL,
    total_dd_pct        REAL,
    reason              TEXT
);
"""


def _record_kill_switch(daily_dd: float, total_dd: float, reason: str) -> None:
    with sqlite3.connect(STATE_DB_PATH) as conn:
        conn.execute(_CREATE_KILL_SWITCH)
        conn.execute(
            "INSERT INTO kill_switch (ts, kill_switch_triggered, daily_dd_pct, total_dd_pct, reason)"
            " VALUES (?, 1, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), daily_dd, total_dd, reason),
        )
        conn.commit()
    logger.critical("Kill switch recorded: %s", reason)


def is_kill_switch_set() -> bool:
    """Return True if any kill_switch row has kill_switch_triggered=1."""
    try:
        with sqlite3.connect(STATE_DB_PATH) as conn:
            conn.execute(_CREATE_KILL_SWITCH)
            row = conn.execute(
                "SELECT 1 FROM kill_switch WHERE kill_switch_triggered = 1 LIMIT 1"
            ).fetchone()
        return row is not None
    except Exception:
        return False


def _try_send_alert(message: str, level: str = "error") -> None:
    try:
        from notifier import send  # type: ignore[import-not-found]
        send(message, level=level)
    except ImportError:
        logger.warning("Telegram notifier not available")
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)


def _guardrail_poll(
    account_id: str,
    attempt_id: str,
    api_key: str,
    monitor: EquityMonitor,
) -> None:
    """Single guardrail check iteration."""
    try:
        status = monitor.get_status()
    except Exception as exc:
        logger.error("Guardrail poll: failed to fetch equity: %s", exc)
        return

    daily_dd = status["daily_dd"]
    total_dd = status["total_dd"]
    equity = status["equity"]

    logger.debug(
        "Guardrail check: equity=$%.2f daily_dd=%.3f%% total_dd=%.3f%%",
        equity, daily_dd * 100, total_dd * 100,
    )

    breach_reason: str | None = None
    if daily_dd >= MAX_DAILY_DD:
        breach_reason = f"Daily DD {daily_dd:.3%} ≥ limit {MAX_DAILY_DD:.3%}"
    elif total_dd >= MAX_TOTAL_DD:
        breach_reason = f"Total DD {total_dd:.3%} ≥ limit {MAX_TOTAL_DD:.3%}"

    if breach_reason:
        alert = (
            f"🚨 GUARDRAIL BREACH — Emergency flatten triggered\n"
            f"  Reason    : {breach_reason}\n"
            f"  Equity    : ${equity:.2f}\n"
            f"  Daily DD  : {daily_dd:.3%}\n"
            f"  Total DD  : {total_dd:.3%}"
        )
        logger.critical(alert)
        _try_send_alert(alert, level="error")

        flatten_all(account_id, api_key)
        _record_kill_switch(daily_dd, total_dd, breach_reason)
        sys.exit(1)


def start_guardrail_loop(
    account_id: str,
    attempt_id: str,
    api_key: str,
) -> threading.Thread:
    """
    Start the guardrail daemon thread.

    Polls equity every 60 seconds. On breach:
      1. Calls flatten_all().
      2. Sends Telegram alert.
      3. Writes kill_switch_triggered=1 to challenge_state.db.
      4. Calls sys.exit(1).

    Returns the Thread object (already started).
    """
    monitor = EquityMonitor(attempt_id, account_id, api_key)

    def _loop() -> None:
        logger.info("Guardrail loop started (poll every %ds)", _POLL_INTERVAL)
        while True:
            _guardrail_poll(account_id, attempt_id, api_key, monitor)
            time.sleep(_POLL_INTERVAL)

    thread = threading.Thread(target=_loop, daemon=True, name="guardrail-loop")
    thread.start()
    return thread
