"""
Equity monitor for TSMOM v2 Propr challenge.

Source of truth: GET /challenge-attempts/{attemptId}
Equity state (day-start) persisted in SQLite to survive restarts.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import datetime, timezone

import requests

from . import BASE_URL, MAX_DAILY_DD, MAX_TOTAL_DD, STATE_DB_PATH

logger = logging.getLogger(__name__)

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS equity_state (
    date           TEXT NOT NULL,
    equity_at_day_start REAL NOT NULL,
    recorded_at    TEXT NOT NULL
);
"""


class EquityMonitor:
    """
    Tracks account equity and enforces Propr challenge drawdown guardrails.

    Guardrail limits:
        MAX_DAILY_DD = 2.8%   (Propr limit 3%, buffer 0.2%)
        MAX_TOTAL_DD = 5.5%   (Propr limit 6%, buffer 0.5%)

    Daily DD formula:
        daily_dd = (equity_at_day_start - equity) / equity_at_day_start

    Total DD formula:
        total_dd = (high_water_mark - equity) / high_water_mark
    """

    MAX_DAILY_DD: float = MAX_DAILY_DD
    MAX_TOTAL_DD: float = MAX_TOTAL_DD

    def __init__(self, attempt_id: str, account_id: str, api_key: str) -> None:
        self._attempt_id = attempt_id
        self._account_id = account_id
        self._headers = {
            "X-API-Key": api_key,
            "Accept": "application/json",
        }
        self._db = STATE_DB_PATH
        self._init_db()

    # ── DB helpers ─────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute(_CREATE_TABLE)
            conn.commit()

    def _get_day_start_equity(self, today: str) -> float | None:
        with sqlite3.connect(self._db) as conn:
            row = conn.execute(
                "SELECT equity_at_day_start FROM equity_state WHERE date = ?",
                (today,),
            ).fetchone()
        return float(row[0]) if row else None

    def _set_day_start_equity(self, today: str, equity: float) -> None:
        with sqlite3.connect(self._db) as conn:
            conn.execute("DELETE FROM equity_state WHERE date != ?", (today,))
            conn.execute(
                "INSERT OR REPLACE INTO equity_state (date, equity_at_day_start, recorded_at)"
                " VALUES (?, ?, ?)",
                (today, equity, datetime.now(timezone.utc).isoformat()),
            )
            conn.commit()
        logger.debug("Day-start equity set: date=%s equity=%.4f", today, equity)

    # ── API ────────────────────────────────────────────────────────────────

    def _fetch_account(self) -> dict:
        """Raw call to GET /challenge-attempts/{attemptId}. Returns account sub-dict."""
        url = f"{BASE_URL}/challenge-attempts/{self._attempt_id}"
        resp = requests.get(url, headers=self._headers, timeout=15)
        resp.raise_for_status()
        return resp.json()["account"]

    # ── Public interface ───────────────────────────────────────────────────

    def get_equity(self) -> float:
        return float(self._fetch_account()["marginBalance"])

    def get_daily_dd(self) -> float:
        """
        Returns fraction of equity lost since 00:00 UTC today.
        Positive value = drawdown (e.g. 0.028 = 2.8% daily loss).
        Resets day-start equity automatically at midnight UTC.
        """
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        equity = self.get_equity()

        day_start = self._get_day_start_equity(today)
        if day_start is None:
            # First call of the day — record current equity as day start
            self._set_day_start_equity(today, equity)
            return 0.0

        return (day_start - equity) / day_start

    def get_total_dd(self) -> float:
        """
        Returns fraction of equity lost from the high-water mark.
        Positive value = drawdown (e.g. 0.055 = 5.5% total drawdown).
        """
        account = self._fetch_account()
        hwm = float(account["highWaterMark"])
        equity = float(account["marginBalance"])
        if hwm <= 0:
            return 0.0
        return (hwm - equity) / hwm

    def is_safe(self) -> bool:
        """Return True only if BOTH daily and total drawdowns are within limits."""
        return (
            self.get_daily_dd() < self.MAX_DAILY_DD
            and self.get_total_dd() < self.MAX_TOTAL_DD
        )

    def get_status(self) -> dict:
        """Full snapshot for Telegram alerts and logging."""
        account = self._fetch_account()
        equity = float(account["marginBalance"])
        hwm = float(account["highWaterMark"])
        unrealized = float(account["totalUnrealizedPnl"])

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        day_start = self._get_day_start_equity(today)
        if day_start is None:
            self._set_day_start_equity(today, equity)
            day_start = equity

        daily_dd = (day_start - equity) / day_start
        total_dd = (hwm - equity) / hwm if hwm > 0 else 0.0

        return {
            "equity": equity,
            "high_water_mark": hwm,
            "unrealized_pnl": unrealized,
            "equity_at_day_start": day_start,
            "daily_dd": daily_dd,
            "total_dd": total_dd,
            "is_safe": daily_dd < self.MAX_DAILY_DD and total_dd < self.MAX_TOTAL_DD,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
