#!/usr/bin/env python
"""
TSMOM v2 — Daily summary report sent to Telegram.

Usage:
    PROPR_API_KEY=pk_live_... TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... \
    python -m strategies.tsmom_v2_propfirm.execution.daily_summary

Cron (08:30 UTC daily):
    30 8 * * * cd ~/projects/Algo_claude && source ~/venv/bin/activate && \
    PROPR_API_KEY=pk_live_XXX python -m \
    strategies.tsmom_v2_propfirm.execution.daily_summary \
    >> logs/tsmom_v2_cron.log 2>&1
"""

from __future__ import annotations

import logging
import os
import sqlite3
import sys
from datetime import datetime, timezone

import requests

from . import STATE_DB_PATH
from .equity_monitor import EquityMonitor
from .guardrail_loop import is_kill_switch_set
from .propr_sdk import ProprClient

logger = logging.getLogger(__name__)

# ── Constants ───────────────────────────────────────────────────────────────
ACCOUNT_ID = "urn:prp-account:KBNeHP5eN3mz"
ATTEMPT_ID = "urn:prp-challenge-attempt:YrWnSPahXiz2"
PROFIT_TARGET = 5500.0   # $5000 × 110% — Propr 10% profit target


# ── Telegram ────────────────────────────────────────────────────────────────

def _send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    resp = requests.post(
        url,
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    resp.raise_for_status()
    msg_id = resp.json().get("result", {}).get("message_id")
    logger.info("Telegram message sent (message_id=%s)", msg_id)


# ── DB helpers ───────────────────────────────────────────────────────────────

def _count_trading_days() -> int:
    try:
        with sqlite3.connect(STATE_DB_PATH) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM rebalance_log WHERE dry_run = 0"
            ).fetchone()
            return int(row[0]) if row else 0
    except Exception:
        return 0


# ── Attempt metadata ─────────────────────────────────────────────────────────

def _get_attempt_metadata(client: ProprClient) -> dict:
    """Fetch startedAt / createdAt from GET /challenge-attempts/{attemptId}."""
    try:
        data = client.get_challenge_attempt(ATTEMPT_ID)
        # Response may be the attempt dict directly or wrapped under a key
        if isinstance(data, dict):
            return data
        return {}
    except Exception as exc:
        logger.warning("Could not fetch attempt metadata: %s", exc)
        return {}


# ── Message builder ──────────────────────────────────────────────────────────

def build_message(
    status: dict,
    positions: list[dict],
    attempt: dict,
    trading_days: int,
    kill_switch: bool,
) -> str:
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d %H:%M")

    equity = status["equity"]
    daily_dd = status["daily_dd"]
    total_dd = status["total_dd"]
    pct_to_target = (equity / PROFIT_TARGET) * 100

    # Challenge start date + days elapsed
    started_raw = (
        attempt.get("startedAt")
        or attempt.get("createdAt")
        or ""
    )
    if started_raw:
        try:
            started_dt = datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
            started_label = started_dt.strftime("%Y-%m-%d")
            days_elapsed: int | str = (now - started_dt).days
        except Exception:
            started_label = started_raw[:10]
            days_elapsed = "?"
    else:
        started_label = "unknown"
        days_elapsed = "?"

    # Positions block
    if positions:
        pos_lines = "\n".join(
            f"    {p['asset']} LONG ${float(p.get('notionalValue', 0)):.0f}"
            for p in sorted(positions, key=lambda p: p["asset"])
        )
    else:
        pos_lines = "    (none)"

    kill_label = "🔴 TRIGGERED" if kill_switch else "🟢 OK"

    lines = [
        f"📊 TSMOM v2 | PROPR CHALLENGE | {date_str} UTC",
        "",
        "💰 ACCOUNT",
        f"  Equity     : ${equity:.2f} USDC",
        f"  Daily DD   : {daily_dd:.2%}",
        f"  Total DD   : {total_dd:.2%}",
        f"  vs target  : ${equity:.2f} / ${PROFIT_TARGET:.2f} ({pct_to_target:.1f}% of way)",
        "",
        f"📈 POSITIONS ({len(positions)} assets)",
        pos_lines,
        "",
        "📅 CHALLENGE",
        f"  Trading days   : {trading_days}",
        f"  Started        : {started_label}",
        f"  Days elapsed   : {days_elapsed}",
        "",
        "⚙️ GUARDRAILS",
        f"  Daily limit  : 2.8% (used {daily_dd:.2%})",
        f"  Total limit  : 5.5% (used {total_dd:.2%})",
        f"  Kill switch  : {kill_label}",
    ]
    return "\n".join(lines)


# ── Entry point ──────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )

    api_key = os.environ.get("PROPR_API_KEY", "")
    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    telegram_chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    if not api_key:
        logger.critical("PROPR_API_KEY not set — aborting")
        sys.exit(1)
    if not telegram_token or not telegram_chat_id:
        logger.critical("TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — aborting")
        sys.exit(1)

    monitor = EquityMonitor(ATTEMPT_ID, ACCOUNT_ID, api_key)
    status = monitor.get_status()

    client = ProprClient(api_key=api_key)
    client.account_id = ACCOUNT_ID
    positions = client.get_open_positions()

    attempt = _get_attempt_metadata(client)
    trading_days = _count_trading_days()
    kill_switch = is_kill_switch_set()

    message = build_message(status, positions, attempt, trading_days, kill_switch)
    logger.info("Sending daily summary:\n%s", message)

    _send_telegram(telegram_token, telegram_chat_id, message)
    logger.info("Daily summary sent.")

    print(
        "\nCron line for VPS deployment (PROPR_API_KEY + TELEGRAM_* must live in ~/projects/Algo_claude/.env, never inline):\n"
        "  30 8 * * * cd ~/projects/Algo_claude && \\\n"
        "    /bin/bash -c 'source ~/venv/bin/activate && source .env && \\\n"
        "      python -m strategies.tsmom_v2_propfirm.execution.daily_summary' \\\n"
        "    >> ~/projects/Algo_claude/logs/tsmom_v2_cron.log 2>&1"
    )


if __name__ == "__main__":
    main()
