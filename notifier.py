"""
notifier.py

Telegram alerting for the live trader.

Usage:
    from notifier import send
    send("Trade opened: BTC-USD LONG @ 84000", level="info")
    send("Exception in run(): ConnectionError", level="error")

Environment variables (loaded from .env at project root):
    TELEGRAM_BOT_TOKEN  — bot token from @BotFather, e.g. 123456:ABC-DEF...
    TELEGRAM_CHAT_ID    — target chat/channel ID, e.g. -1001234567890

If either variable is missing, send() logs a WARNING and no-ops silently
so the trader continues running in development / dry-run environments.

Dependencies: requests, python-dotenv (both in requirements.txt).
"""

import logging
import os
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env once at import time.  dotenv is a no-op when the file doesn't
# exist, so this is always safe to call.
load_dotenv(Path(__file__).parent / ".env")

# Telegram Bot API endpoint
_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# Map level → emoji prefix so messages are scannable in a busy chat
_LEVEL_PREFIX = {
    "info":    "ℹ️",
    "warning": "⚠️",
    "error":   "🚨",
    "critical":"🔴",
}

# HTTP timeout for the Telegram API call (seconds)
_REQUEST_TIMEOUT = 10


def send(message: str, level: str = "info") -> None:
    """
    Post a message to the configured Telegram chat.

    If TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is absent, logs a WARNING
    once and returns without raising — the trader must keep running even
    when alerts are not configured.

    If the HTTP request fails (network error, bad token, rate-limit),
    the exception is caught and logged as ERROR so the caller is never
    interrupted.

    Args:
        message: Human-readable alert text (plain text, no HTML/Markdown).
        level:   Severity string — "info", "warning", "error", "critical".
                 Controls the emoji prefix.  Unknown values default to "ℹ️".
    """
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        logger.warning(
            "Telegram alert suppressed — TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID "
            "not set.  Add them to .env (see .env.example)."
        )
        return

    prefix  = _LEVEL_PREFIX.get(level.lower(), "ℹ️")
    full_msg = f"{prefix} {message}"

    url     = _TELEGRAM_API.format(token=token)
    payload = {"chat_id": chat_id, "text": full_msg}

    try:
        resp = requests.post(url, json=payload, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        logger.debug(f"Telegram alert sent (level={level}): {message[:80]}")
    except requests.exceptions.RequestException as exc:
        logger.error(f"Telegram alert failed: {exc} | message was: {message[:120]}")
