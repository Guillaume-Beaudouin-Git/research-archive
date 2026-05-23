"""
guardrails.py — Propfirm guardrails for Strategy C (Tradeify Select Flex $25K)
================================================================================
Phase-aware defense against propfirm account bust:

  Pre-lock (eval + pre_lock phases):
    L1: Trailing DD from equity peak > $1,300 (Tradeify limit $1,500, buffer $200)
    L2: Self-imposed daily loss > $400 (2 × max SL at 3 MNQ, Tradeify has no DLL)
    L3: Bracket integrity — TP and SL orders still alive

  Post-lock (post_lock phase):
    L1: Balance < $25,175 (Tradeify locked floor $25,100, buffer $75)
    L2: Same daily self-limit $400
    L3: Same bracket integrity

Emergency flat: client.emergency_close() → write HALT sentinel → Telegram CRITICAL.
Never raises — if flat fails, logs and retries 3 times.
"""
from __future__ import annotations

import logging
import os
import sys
import time

log = logging.getLogger(__name__)

from Futures.live.strategy_c_live.config import (
    GUARDRAIL_TRAILING_DD_USD,
    GUARDRAIL_POST_LOCK_FLOOR,
    GUARDRAIL_DAILY_SELF_LIMIT,
    HALT_SENTINEL_PATH,
    TRADEIFY_TRAILING_DD_USD,
    # Legacy aliases kept for validate_mt5.py offline tests
    GUARDRAIL_DD_PCT,
    GUARDRAIL_DAILY_BUFFER_PCT,
    GUARDRAIL_TRAILING_DD_PCT,
)


# ─────────────────────────────────────────────────────────────────────────────
# Telegram helper
# ─────────────────────────────────────────────────────────────────────────────

def _send_telegram(msg: str) -> None:
    token   = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        log.warning("Telegram not configured — skipping alert: %s", msg[:80])
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
    except Exception as e:
        log.warning("Telegram send failed: %s", e)


# ─────────────────────────────────────────────────────────────────────────────
# Exception
# ─────────────────────────────────────────────────────────────────────────────

class GuardrailTriggered(Exception):
    pass


# ─────────────────────────────────────────────────────────────────────────────
# Guardrails
# ─────────────────────────────────────────────────────────────────────────────

class PropfirmGuardrails:
    """
    Phase-aware guardrail system for Tradeify Select Flex $50K.
    Call check_all() every 30s in the monitor loop.
    On GuardrailTriggered: call emergency_flat() then exit the loop.
    """

    def __init__(self, state, client) -> None:
        self.state  = state   # ChallengeState
        self.client = client

    def check_all(
        self,
        current_balance: float,
        open_trade: dict | None = None,
    ) -> None:
        """
        Run all checks in priority order.
        Raises GuardrailTriggered on first failure.
        Pass open_trade=None when no position is open (skips L3).
        """
        self._check_drawdown(current_balance)
        self._check_daily_self_limit(current_balance)
        if open_trade is not None:
            self._check_position_integrity(open_trade)

    def _check_drawdown(self, current_balance: float) -> None:
        """
        Phase-aware DD check:
          Post-lock: absolute floor at $25,175 (Tradeify floor $25,100 + $75 buffer)
          Pre-lock / eval: trailing DD from peak, guardrail at $1,300 (limit $1,500)
        """
        phase = self.state.get_phase()

        if phase == 'post_lock':
            if current_balance < GUARDRAIL_POST_LOCK_FLOOR:
                raise GuardrailTriggered(
                    f"POST_LOCK_FLOOR_BREACH: balance ${current_balance:,.2f} < "
                    f"guardrail ${GUARDRAIL_POST_LOCK_FLOOR:,.0f} "
                    f"(Tradeify floor ${self.state.lock_floor:,.0f})"
                )
        else:
            trailing_dd = self.state.trailing_dd_usd(current_balance)
            if trailing_dd >= GUARDRAIL_TRAILING_DD_USD:
                raise GuardrailTriggered(
                    f"TRAILING_DD_BREACH: ${trailing_dd:,.2f} from peak "
                    f"${self.state.peak_balance:,.2f} >= ${GUARDRAIL_TRAILING_DD_USD:,} guardrail "
                    f"(Tradeify limit ${TRADEIFY_TRAILING_DD_USD:,}, phase={phase})"
                )

    def _check_daily_self_limit(self, current_balance: float) -> None:
        """Self-imposed daily cap (Tradeify has no DLL; this is our own safety net)."""
        daily_loss = self.state.balance_at_day_open - current_balance
        if daily_loss >= GUARDRAIL_DAILY_SELF_LIMIT:
            raise GuardrailTriggered(
                f"DAILY_SELF_LIMIT: ${daily_loss:,.2f} >= ${GUARDRAIL_DAILY_SELF_LIMIT:,} "
                f"(self-imposed; Tradeify has no DLL)"
            )

    def _check_position_integrity(self, open_trade: dict) -> None:
        """
        Verify bracket orders are still live.
        Tradovate path: open_trade has 'orderId', 'tp_orderId', 'sl_orderId'.
        'Filled' = position already exited (TP/SL hit between polls) — not an error.
        """
        ticket = open_trade.get("ticket")
        if ticket is not None:
            # MT5 legacy path
            status = self.client.get_order_status(ticket)
            if status == "Cancelled":
                raise GuardrailTriggered(
                    f"BRACKET_MISSING: MT5 position has sl=0 or tp=0 (ticket={ticket})"
                )
        else:
            # Tradovate / IBKR path: separate TP and SL order IDs
            tp_key = "tp_orderId" if "tp_orderId" in open_trade else "tp"
            sl_key = "sl_orderId" if "sl_orderId" in open_trade else "sl"
            for label, key in [("TP", tp_key), ("SL", sl_key)]:
                order_id = open_trade.get(key)
                if order_id is None:
                    continue
                status = self.client.get_order_status(order_id)
                if status not in ("Submitted", "PreSubmitted", "Filled"):
                    raise GuardrailTriggered(
                        f"BRACKET_MISSING: {label} order status={status!r} (id={order_id})"
                    )

    def emergency_flat(
        self,
        contract,
        qty,
        direction: str,
        reason: str,
    ) -> None:
        """
        Emergency flatten — broker-agnostic. Never raises.
        1. client.emergency_close()  (3 attempts, 5s between)
        2. Write HALT_SENTINEL_PATH
        3. Telegram CRITICAL
        """
        log.critical("EMERGENCY FLAT — %s", reason)

        flat_placed = False
        for attempt in range(1, 4):
            try:
                if hasattr(self.client, "emergency_close"):
                    self.client.emergency_close()
                else:
                    close_action = "SELL" if direction == "BUY" else "BUY"
                    self.client.ib.reqGlobalCancel()
                    time.sleep(2)
                    self.client.place_market_order(contract, close_action, qty)
                log.info("Emergency flat executed (attempt %d)", attempt)
                flat_placed = True
                break
            except Exception as e:
                log.error("Emergency flat attempt %d/3 failed: %s", attempt, e)
                _send_telegram(f"NQ-C EMERGENCY FLAT FAILED attempt {attempt}/3: {e}")
                time.sleep(5)

        try:
            HALT_SENTINEL_PATH.touch()
            log.info("HALT sentinel written: %s", HALT_SENTINEL_PATH)
        except Exception as e:
            log.error("Failed to write HALT sentinel: %s", e)

        flat_status = ("Position flatten attempted."
                       if flat_placed
                       else "FLAT FAILED — check position manually!")
        _send_telegram(
            f"NQ-C GUARDRAIL: {reason}\n"
            f"{flat_status}\n"
            f"HALTED sentinel created. Manual review required.\n"
            f"Delete {HALT_SENTINEL_PATH.name} after review to resume."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Halt sentinel check
# ─────────────────────────────────────────────────────────────────────────────

def check_halt_sentinel() -> None:
    """
    Check for HALTED sentinel file. Call at the very top of run_daily.py.
    If present: print instructions + Telegram alert + sys.exit(1).
    """
    if not HALT_SENTINEL_PATH.exists():
        return
    msg = (
        f"HALTED sentinel active.\n"
        f"File: {HALT_SENTINEL_PATH}\n"
        f"Review the incident, then: rm {HALT_SENTINEL_PATH}\n"
        f"No trade will execute until the file is removed."
    )
    print(msg)
    log.error("HALTED sentinel active — aborting run_daily")
    _send_telegram(
        f"NQ-C | HALTED sentinel active — no trade today.\n"
        f"({HALT_SENTINEL_PATH.name})"
    )
    sys.exit(1)
