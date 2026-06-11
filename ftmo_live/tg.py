#!/usr/bin/env python3
"""tg.py — envoi Telegram avec garde anti-token-compromis.

Token/chat depuis l'env (.env via run_with_env.sh, jamais commité, jamais loggé).
REFUSE de démarrer si sha256(token) est dans config/token_blocklist.sha256
(ancien token compromis — rotation 2026-05-30). FTMO_LIVE_TG_DISABLED=1 ->
stdout (tests/dev).

Usage: tg.py "message"
"""
import hashlib
import os
import sys
from pathlib import Path

import requests

LIVE_ROOT = Path(__file__).resolve().parent
BLOCKLIST = LIVE_ROOT / "config" / "token_blocklist.sha256"


class TokenBlockedError(RuntimeError):
    pass


def _blocklist() -> set:
    if not BLOCKLIST.exists():
        return set()
    return {l.strip() for l in BLOCKLIST.read_text().splitlines()
            if l.strip() and not l.startswith("#")}


def check_token(token: str) -> None:
    """TokenBlockedError si le token est blocklisté ; RuntimeError si absent."""
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN non défini")
    if hashlib.sha256(token.encode()).hexdigest() in _blocklist():
        raise TokenBlockedError(
            "TELEGRAM_BOT_TOKEN = token COMPROMIS blocklisté — rotation requise "
            "(README §secrets), refus de démarrer")


def send(text: str, timeout: int = 15) -> bool:
    """Envoie `text` au chat configuré. True si accepté par l'API."""
    if os.environ.get("FTMO_LIVE_TG_DISABLED") == "1":
        print(f"[TG-DISABLED] {text}")
        return True
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "")
    check_token(token)
    if not chat:
        raise RuntimeError("TELEGRAM_CHAT_ID non défini")
    r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat, "text": text}, timeout=timeout)
    r.raise_for_status()
    return bool(r.json().get("ok"))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: tg.py \"message\"")
        sys.exit(2)
    send(" ".join(sys.argv[1:]))
    print("envoyé")
